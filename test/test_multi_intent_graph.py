from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from book_chatbot.graph import graph


def test_multi_intent_parallel_tool_calls():
    # 주의: 현재 이 테스트는 실패함 (GitHub 이슈 #11)
    # price_description_book_search가 d_titl을 넘기면 네이버 book.json이 404를 반환하고,
    # 도구 오류가 처리되지 않아 그래프 전체가 중단됨. 이슈 해결 후 통과해야 함.
    query = "천문학을 배우고 싶은데 어떤 책이 좋을까? 그리고 용의자 X의 헌신 최저가도 알려줘"

    result = graph.invoke({"messages": [HumanMessage(content=query)]})

    # supervisor가 한 턴에 도구 호출을 여러 개 냈는지 확인 (병렬 처리)
    supervisor_calls = [
        {call["name"] for call in m.tool_calls}
        for m in result["messages"]
        if isinstance(m, AIMessage) and m.tool_calls
    ]
    print("supervisor 도구 호출:", supervisor_calls)
    assert any(
        {"book_recommendation", "book_search"} <= names for names in supervisor_calls
    ), "supervisor가 book_recommendation과 book_search를 같은 턴에 호출하지 않았습니다"

    # 서브에이전트 결과는 부모에 ToolMessage 문자열로만 들어온다
    tool_results = {
        m.name: m.content for m in result["messages"] if isinstance(m, ToolMessage)
    }
    assert tool_results.get("book_recommendation"), "book_recommendation 결과가 없습니다"
    assert tool_results.get("book_search"), "book_search 결과가 없습니다"

    final_response = result["messages"][-1].content
    print("최종 응답:", final_response)
    assert final_response


if __name__ == "__main__":
    test_multi_intent_parallel_tool_calls()
