import os
import psycopg
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

from .schema import OverallState
from .tool import basic_book_search, price_description_book_search, keyword_generator, book_memo_analyzer

llm = ChatOpenAI(model="gpt-5.2")

# ---- 프롬프트 ----
BOOK_SEARCH_PROMPT = """You are a book search assistant.
Use basic_book_search for title, author, publisher, link, ISBN and publication date.
Use price_description_book_search for lowest price and book description.
Call both tools when the request needs both. Answer based on the tool results."""

BOOK_RECOMMEND_PROMPT = """You are a book recommendation assistant.
Use keyword_generator to derive keywords from the request, then use basic_book_search with those keywords
to find real books. Recommend books based on the search results."""

BOOK_MEMO_PROMPT = """You are a reading memo assistant.
Use book_memo_analyzer to extract pages read and the impression from the user's memo.
Use basic_book_search to look up the book's metadata (title, author, publisher, ISBN) mentioned in the memo.
Summarize the recorded memo together with the book information."""

SUPERVISOR_PROMPT = """You are a helpful book assistant. Route the user's request to the right tool.
- book_search: searching books, lowest price, book description
- book_recommendation: recommending books
- book_memo: the user writes a note about a book they are reading
  (book title together with pages read and/or impression)

A single message may contain several requests: call all the needed tools in the same turn.
The tools only see the `request` string, NOT the conversation history. When the user refers to earlier turns
(e.g. "아까 그 책 가격은?"), resolve the reference and put the concrete book title and details into `request`.

If the request is unrelated to book search, recommendation or memo, do not call any tool. Just answer that
we only provide the features 'book_search', 'book_recommendation' and 'book_memo'.
After the tools return, write the final answer for the user based on their results."""


# ---- 서브에이전트 (agent ↔ tools 루프 팩토리) ----
def build_subagent(name: str, tools: list, system_prompt: str):
    model = llm.bind_tools(tools)

    def agent(state: MessagesState):
        return {"messages": [model.invoke([SystemMessage(system_prompt), *state["messages"]])]}

    b = StateGraph(MessagesState)
    b.add_node(name, agent)
    b.add_node("tools", ToolNode(tools))
    b.add_edge(START, name)
    b.add_conditional_edges(name, tools_condition)  # tools / END
    b.add_edge("tools", name)
    return b.compile()


book_search_subagent = build_subagent(
    "book_search", [basic_book_search, price_description_book_search], BOOK_SEARCH_PROMPT)
book_recommendation_subagent = build_subagent(
    "book_recommendation", [basic_book_search, keyword_generator], BOOK_RECOMMEND_PROMPT)
book_memo_subagent = build_subagent(
    "book_memo", [basic_book_search, book_memo_analyzer], BOOK_MEMO_PROMPT)


# ---- supervisor용 도구 (docstring이 라우팅 기준) ----
@tool
def book_search(request: str) -> str:
    """제목/저자/출판사/최저가/책 소개 등 책 검색이 필요할 때. 입력: 자연어 검색 요청"""
    result = book_search_subagent.invoke({"messages": [HumanMessage(request)]})
    return result["messages"][-1].content


@tool
def book_recommendation(request: str) -> str:
    """책 추천이 필요할 때. 입력: 자연어 추천 요청"""
    result = book_recommendation_subagent.invoke({"messages": [HumanMessage(request)]})
    return result["messages"][-1].content


@tool
def book_memo(request: str) -> str:
    """읽고 있는 책의 메모(읽은 페이지, 감상)를 기록할 때. 입력: 책 제목이 포함된 메모 원문"""
    result = book_memo_subagent.invoke({"messages": [HumanMessage(request)]})
    return result["messages"][-1].content


# ---- 부모 그래프: supervisor ↔ subagent_tools ----
subagent_tools = [book_search, book_recommendation, book_memo]
supervisor_model = llm.bind_tools(subagent_tools)


def supervisor(state: OverallState) -> dict:
    response = supervisor_model.invoke([SystemMessage(SUPERVISOR_PROMPT), *state["messages"]])
    return {"messages": [response]}


builder = StateGraph(OverallState)
builder.add_node("supervisor", supervisor)
builder.add_node("subagent_tools", ToolNode(subagent_tools))

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", tools_condition, {"tools": "subagent_tools", END: END})
builder.add_edge("subagent_tools", "supervisor")
graph = builder.compile()


def _conn_string() -> str:
    """PostgreSQL 연결 문자열 (호출 시점에 환경변수 조회)"""
    return (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@localhost:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB')}"
    )


def build_graph_with_checkpointer():
    """Streamlit용 체크포인터 포함 그래프 빌드"""
    conn = psycopg.Connection.connect(_conn_string(), autocommit=True)
    cp = PostgresSaver(conn)
    cp.setup()
    return builder.compile(checkpointer=cp)