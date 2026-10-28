from typing import TypedDict, Literal, Annotated
from pydantic import BaseModel
from langgraph.graph.message import add_messages

class OverallState(TypedDict):
    messages: Annotated[list, add_messages]  # add_messages로 ToolNode 결과 자동 축적
    search_results: list[dict]


class ToolRouting(BaseModel):
    tools: list[Literal["basic_book_search", "price_description_book_search"]]
    reason: str
