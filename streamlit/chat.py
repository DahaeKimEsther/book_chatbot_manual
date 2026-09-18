import uuid
import streamlit as st
from langchain_core.messages import HumanMessage
from book_chatbot.graph import build_graph_with_checkpointer
from db import save_message, load_messages, get_threads


@st.cache_resource
def _graph():
    """Streamlit 재실행 시에도 그래프 인스턴스 재사용 (DB 연결 누적 방지)"""
    return build_graph_with_checkpointer()

def show_chat():
    st.title("Chatbot")

    with st.sidebar:
        st.write(f"**{st.session_state.user['username']}** 님")
        if st.button("➕ 새 대화", use_container_width=True):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        st.divider()

        threads = get_threads(st.session_state.user["id"])
        for thread in threads:
            is_current = thread["thread_id"] == st.session_state.thread_id
            label = f"**{thread['title']}**" if is_current else thread["title"]
            if st.button(label, key=thread["thread_id"], use_container_width=True):
                st.session_state.thread_id = thread["thread_id"]
                st.session_state.messages = load_messages(thread["thread_id"])
                st.rerun()

        st.divider()

        if st.button("로그아웃", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("메시지를 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(st.session_state.thread_id, st.session_state.user["id"], "user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                result = _graph().invoke(
                    {"messages": [HumanMessage(content=prompt)]},
                    config=config,
                )
                response = result.get("draft_response", "응답을 생성하지 못했습니다.")
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        save_message(st.session_state.thread_id, st.session_state.user["id"], "assistant", response)
