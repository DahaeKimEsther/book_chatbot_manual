import os
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition

from .schema import OverallState, IntentClassifications
from .tool import basic_book_search, price_description_book_search, keyword_generator

llm = ChatOpenAI(model="gpt-5.2")
book_search_tool_node = ToolNode([basic_book_search, price_description_book_search])
book_recommendation_tool_node = ToolNode([basic_book_search, keyword_generator])

INTENT_TO_NODE = {
    "book_search": "book_search",
    "book_recommendation": "book_recommendation",
    "introduce_features": "introduce_features",
}

def classify_intent(state: OverallState) -> Command[Literal["book_search", "book_recommendation", "introduce_features"]]:
    """Use LLM to classify book search intent (supports multiple intents)"""
    structured_llm = llm.with_structured_output(IntentClassifications)

    classification_prompt = f"""
    Analyze this customer message and classify his/her intentions.
    There may be MORE THAN ONE intention in a single message — identify all of them.

    Messages: {state['messages']}

    Provide a list of classifications. Each item must include:
    - intent: one of book_search, book_recommendation, introduce_features
    - query_related_to_intent: the sub-query relevant to that specific intent

    classify intent as 'introduce_features' when user asks about things not related to book_search or book_recommendation.
    """
    classification = structured_llm.invoke(classification_prompt)
    intents = classification["intents"]

    first_intent = intents[0]
    remaining = intents[1:]

    return Command(
        update={
            "classification": intents,
            "remaining_intents": remaining,
            "messages": [HumanMessage(content=first_intent["query_related_to_intent"])],
        },
        goto=INTENT_TO_NODE[first_intent["intent"]],
    )
    
def book_search(state: OverallState) -> dict:
    """LLM이 어느 tool 노드로 갈지, 혹은 둘 다 갈지 결정."""
    model_with_tools = llm.bind_tools([basic_book_search, price_description_book_search])
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

def book_recommendation(state: OverallState) -> dict:
    """LLM이 어느 tool 노드로 갈지, 혹은 둘 다 갈지 결정."""
    model_with_tools = llm.bind_tools([basic_book_search, keyword_generator])
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def introduce_features(state: OverallState) -> Command[Literal["route_next_intent"]]:

    answer = llm.invoke(
        [SystemMessage(content=f"""
        Just answer that we have features including 'book_search' and 'book_recommendation' and cannot answer to your question because we have just these features.

        Intents of user: {state["classification"]}
        Messages: {state['messages']}
        """)]
    )
    return Command(update={"messages": [answer]}, goto="route_next_intent")

def route_next_intent(state: OverallState) -> Command[Literal["book_search", "book_recommendation", "introduce_features", "draft_response"]]:
    """남은 인텐트가 있으면 다음 노드로, 없으면 draft_response로"""
    remaining = state["remaining_intents"]
    if not remaining:
        return Command(goto="draft_response")

    next_intent = remaining[0]
    return Command(
        update={
            "remaining_intents": remaining[1:],
            "messages": [HumanMessage(content=next_intent["query_related_to_intent"])],
        },
        goto=INTENT_TO_NODE[next_intent["intent"]],
    )
    
def draft_response(state: OverallState):
    response = llm.invoke([
        SystemMessage(content="You are a helpful book assistant. Answer the user's question based on the search results provided."),
        *state["messages"],  # tool 결과(ToolMessage)가 여기 있음
    ])
    return {"draft_response": response.content}


# ---- Graph ----
builder = StateGraph(OverallState)

#NODE
builder.add_node("classify_intent", classify_intent)
builder.add_node("route_next_intent", route_next_intent)
builder.add_node("book_search", book_search)
builder.add_node("book_search_tool_node", book_search_tool_node)
builder.add_node("book_recommendation", book_recommendation)
builder.add_node("book_recommendation_tool_node", book_recommendation_tool_node)
builder.add_node("introduce_features", introduce_features)
builder.add_node("draft_response", draft_response)

# EDGE
builder.add_edge(START, "classify_intent")
# 1. book_search agent
builder.add_conditional_edges("book_search", tools_condition, {"tools": "book_search_tool_node", "__end__": "route_next_intent"})
builder.add_edge("book_search_tool_node", "book_search")
# 2. book_recommendation agent
builder.add_conditional_edges("book_recommendation", tools_condition, {"tools": "book_recommendation_tool_node", "__end__": "route_next_intent"})
builder.add_edge("book_recommendation_tool_node", "book_recommendation")
builder.add_edge("draft_response", END)

#GRAPH
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