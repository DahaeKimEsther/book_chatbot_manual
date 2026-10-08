from typing import TypedDict, Literal, Annotated
from pydantic import BaseModel
from langgraph.graph.message import add_messages

class FeatureClassification(TypedDict):
    intent: Literal["book_search", "book_recommendation", "book_memo", "introduce_features"]
    query_related_to_intent: str

class IntentClassifications(TypedDict):
    intents: list[FeatureClassification]

class OverallState(TypedDict):
    messages: Annotated[list, add_messages]  # add_messages로 ToolNode 결과 자동 축적
    classification: list[FeatureClassification] | None
    remaining_intents: list[FeatureClassification]
    search_results: list[dict]
    draft_response: str | None
    

class ToolRouting(BaseModel):
    tools: list[Literal["basic_book_search", "price_description_book_search"]]
    reason: str