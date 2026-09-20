from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

from book_chatbot.tool import basic_book_search, price_description_book_search, keyword_generator, book_memo_analyzer
from book_chatbot.tool_schema import BookMemoRecord
model = ChatOpenAI(model="gpt-5.2")

BOOK_SEARCH_AGENT_PROMPT = (
    "Search books by extracting keywords from natural language. "
    "Use price_description_book_search if user mentions lowest price over all book sellers or user wants to know the content of every book. "
    "Otherwise, use basic_book_search as search engine of books"
)

BOOK_KEYWORD_RECOMMEND_AGENT_PROMPT = (
    "If user asks you to recommend books, then use keyword generator according to natural language of user and execute book search using those keywords generated"
)

BOOK_MEMO_AGENT_PROMPT = (
    "The user's message is a memo about a book they are reading. "
    "1) Identify the book title mentioned in the message and call basic_book_search to look it up. "
    "From the search result, determine the book's title(도서명), author(저자), publisher(출판사) and ISBN. "
    "2) Call book_memo_analyzer with the user's original message to extract how many pages they've "
    "read(읽은 페이지) and their impression(감상). "
    "3) Combine the book info and the memo info into the final structured record."
)

book_search_agent = create_agent(
    model,
    tools=[basic_book_search, price_description_book_search], # naver_book_api
    system_prompt=BOOK_SEARCH_AGENT_PROMPT,
)

book_keyword_recommend_agent = create_agent(
    model,
    tools=[basic_book_search, keyword_generator],
    system_prompt=BOOK_KEYWORD_RECOMMEND_AGENT_PROMPT,
)

book_memo_agent = create_agent(
    model,
    tools=[basic_book_search, book_memo_analyzer],
    system_prompt=BOOK_MEMO_AGENT_PROMPT,
    response_format=BookMemoRecord,
)

@tool
def book_search(request: str) -> str:
    """
    Search books using natural language.
    
    Use this when user wants to find books according to title, author, publisher, lowest price or to find books by sorting books by accuracy, publish time, title, amount of sales, customer ratings and number of reivews
    
    Input: Natural language request searching books
    """
    result = book_search_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text


@tool
def book_recommendation(request: str) -> str:
    """
    Recommend books using natural language.
    
    Use this when user wants a list of recommended books according to user query
    
    Input: Natural language request to recommend books
    """
    result = book_keyword_recommend_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def book_memo(request: str) -> str:
    """
    Record a reading memo for a book: the book's info (title, author, publisher, ISBN)
    together with the user's reading progress (pages read) and impression.

    Use this when the user writes a note about a book they are reading — mentioning the
    book title along with how far they've read and/or their thoughts/impressions.

    Input: Natural language memo mentioning the book title, pages read, and impression
    """
    result = book_memo_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    record: BookMemoRecord = result["structured_response"]
    return (
        f"도서명: {record.book.title}\n"
        f"저자: {record.book.author}\n"
        f"출판사: {record.book.publisher}\n"
        f"ISBN: {record.book.isbn}\n"
        f"읽은 페이지: {record.memo.pages_read}\n"
        f"감상: {record.memo.impression}"
    )

SUPERVISOR_PROMPT = (
    "You are a helpful book assistant. "
    "You can search books, recommend books, or record a reading memo according to user request. "
    "Use book_memo when the user writes a note about a book they are reading, mentioning the book "
    "title together with how many pages they've read and/or their thoughts or impressions about it. "
    "Break down user requests into appropriate tool calls and coordinate the results. "
    "When a request involves multiple actions, use multiple tools in sequence."
)

supervisor_agent = create_agent(
    model,
    tools=[book_search, book_recommendation, book_memo],
    system_prompt=SUPERVISOR_PROMPT,
)

if __name__ == "__main__":
    # book_keyword_recommend_agent
    query = "천문학 입문서를 추천해줘, 그리고 히가시노 게이고의 용의자X의 헌신의 최저가를 알려줘"
    for step in supervisor_agent.stream(
        {"messages": [{"role": "user", "content": query}]}
    ):
        for update in step.values():
            for message in update.get("messages", []):
                message.pretty_print()