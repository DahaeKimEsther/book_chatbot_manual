import re

from langchain_core.messages import HumanMessage, ToolMessage

from book_chatbot.graph import graph


def test_book_memo_graph():
    query = (
        "내가 생각을 넓혀주는 독서법 31페이지까지 읽었는데 "
        "깨달음에 의한 배움과 교육에 의한 배움에 차이가 있다는 부분이 인상적이었어"
    )

    result = graph.invoke({"messages": [HumanMessage(content=query)]})

    intents = [c["intent"] for c in result["classification"]]
    assert "book_memo" in intents

    memo_messages = [
        m for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "book_memo_analyzer"
    ]
    assert memo_messages, "book_memo_analyzer 도구가 호출되지 않았습니다"

    memo_content = memo_messages[0].content
    print("book_memo_analyzer 결과:", memo_content)

    pages_read = re.search(r"pages_read=(\d+)", memo_content)
    assert pages_read and int(pages_read.group(1)) == 31

    print("최종 응답:", result["draft_response"])
    assert result["draft_response"]


if __name__ == "__main__":
    test_book_memo_graph()
