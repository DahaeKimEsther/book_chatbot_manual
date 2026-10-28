from langchain_core.messages import HumanMessage, ToolMessage

from book_chatbot.graph import graph


def test_book_memo_graph():
    query = (
        "내가 생각을 넓혀주는 독서법 31페이지까지 읽었는데 "
        "깨달음에 의한 배움과 교육에 의한 배움에 차이가 있다는 부분이 인상적이었어"
    )

    result = graph.invoke({"messages": [HumanMessage(content=query)]})

    # 서브에이전트 내부 메시지는 격리되므로 부모에서는 book_memo 도구 결과만 확인
    memo_messages = [
        m for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "book_memo"
    ]
    assert memo_messages, "book_memo 도구가 호출되지 않았습니다"

    memo_content = memo_messages[0].content
    print("book_memo 결과:", memo_content)
    assert "31" in memo_content

    final_response = result["messages"][-1].content
    print("최종 응답:", final_response)
    assert final_response


if __name__ == "__main__":
    test_book_memo_graph()
