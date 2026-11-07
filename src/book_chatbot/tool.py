from langchain.tools import tool
import os
from langchain_openai import ChatOpenAI

from .utils import aladin_search_api, naver_book_api, kakao_book_api
from .tool_schema import AladinBookSearchParams, NaverBookSearchParams, KakaoBookSearchParams, KeywordAnswer, ReadingMemo

@tool(args_schema=KakaoBookSearchParams)
def kakao_book_search(query:str,
                target:str | None = None,
                sort:str="accuracy",
                size:int=10):
    """search books with Kakao(Daum) book search API

        Available Response
        title, authors, publisher, isbn, datetime(published date), price, sale_price, contents(description), url, status
    """
    params = {"query": query, "target": target, "sort": sort, "size": size}
    result = kakao_book_api(params)
    output_keys = ["title", "authors", "publisher", "isbn", "datetime", "price", "sale_price", "contents", "url", "status"]
    return [{k: v for k, v in doc.items() if k in output_keys} for doc in result["documents"]]

@tool(args_schema=AladinBookSearchParams)
def basic_book_search(Query:str,
                QueryType:str="Keyword",
                SearchTarget:str="Book",
                Sort:str="Accuracy"):
    """search books according to parameters

        Available Response:
        link, title, author, pubdate, publisher, isbn13

    """
    input_params = locals()
    fixed_params = {
        "ttbkey": os.getenv("ALADIN_API_KEY"),
        "MaxResults": 10,
        "start": 1,
        "output": "xml",
    }
    params = {**input_params, **fixed_params}
    output_keys = ["link", "item.title", "item.link", "item.author", "item.pubdate", "item.publisher", "item.isbn13"]
    result = aladin_search_api(params, output_keys)
    return result

@tool(args_schema=NaverBookSearchParams)
def price_description_book_search(query:str,
                sort:str="sim",
                d_titl:str | None = None,
                d_isbn:str | None = None):
    """search books according to parameters
    
        Available Response
        discount(lowest price of book), description
    """
    params = locals()
    result = naver_book_api(params)
    result_items = [{ k:v for k, v in item.items() if k in ["title", "discount", "description"]} for item in result["items"]]
    return result_items

@tool
def keyword_generator(search_query:str):
    """
    keyword maker to generate keywords related to question that user made so that user can get recommended books by searching keywords in book store's web page
    """
    model = ChatOpenAI(model="gpt-4o-mini")
    structured_model = model.with_structured_output(schema=KeywordAnswer)
    messages = [
        (
            "system",
            "You are keyword maker to generate keywords related to question that user made so that you can recommend books by searching keywords in book store's web page",
        ),
        ("human", search_query),
    ]
    result = structured_model.invoke(input=messages)
    return result

@tool
def book_memo_analyzer(memo_text:str):
    """
    Analyze a user's reading memo and extract how many pages they have read
    and their impression/thoughts about the book.

        Available Response:
        pages_read (읽은 페이지), impression (감상)
    """
    model = ChatOpenAI(model="gpt-4o")
    structured_model = model.with_structured_output(schema=ReadingMemo)
    messages = [
        (
            "system",
            "Extract how many pages the user has read (읽은 페이지) and their impression or "
            "thoughts about the book (감상) from the memo they wrote.",
        ),
        ("human", memo_text),
    ]
    result = structured_model.invoke(input=messages)
    return result

if __name__ == "__main__":
    # # keyword generator test
    # result = keyword_generator.invoke({"search_query": "천문학을 배우고 싶은데 어떤 책이 좋을까?"})
    # print(result)
    
    # price description test
    result = price_description_book_search.invoke({"query": "천문학"})
    print(result)