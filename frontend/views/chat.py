"""Chat: ask questions about one paper."""

import streamlit as st

from api_client import ApiError, list_conversations, list_messages, list_papers, send_feedback, stream_ask
from components.source_cards import show_sources

st.title("💬 Chat")



# A message left by the previous click (the page reloads after a vote, so we show it now).
if vote_message := st.session_state.pop("vote_message", None):
    st.toast(vote_message, icon="✅")

try:
    papers = [p for p in list_papers() if p["status"] == "ready"]
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not papers:
    st.info("📥 Upload a paper first and wait until it says ready.")
    st.page_link("views/papers.py", label="Go to My Papers", icon="📄")
    st.stop()

labels = {p["id"]: p["title"] or p["filename"] for p in papers}

# Other pages (Dashboard, My Papers) leave "notes-to-self" here to jump straight to a paper/chat.
# We must apply them BEFORE the dropdowns are drawn.
jump_paper = st.session_state.pop("pending_paper", None)
if jump_paper in labels:
    st.session_state["chat_paper"] = jump_paper

paper_id = st.selectbox("Paper", list(labels), format_func=labels.get, key="chat_paper")

convos = list_conversations(paper_id)
options = [None] + [c["id"] for c in convos]
names = {None: "➕ New chat", **{c["id"]: c.get("title") or "Chat" for c in convos}}
convo_key = f"chat_convo_{paper_id}"
jump_convo = st.session_state.pop("pending_convo", None)
#"None" is ALSO the first option ("New chat"). Without the `is not None` check, every page reload (any click at all) looked like a request to jump back to "New chat" and wiped your choice.
if jump_convo is not None and jump_convo in options:
    st.session_state[convo_key] = jump_convo
conversation_id = st.selectbox("Chat history", options, format_func=names.get, key=convo_key)

# ---------- the conversation so far ----------
if conversation_id:
    for message in list_messages(conversation_id):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                show_sources(message.get("sources") or [])
                # The thumb you chose is highlighted (blue), so you can see your vote was saved.
                rating = message.get("rating") or st.session_state.get(f"voted_{message['id']}")
                up, down, note = st.columns([1, 1, 12])
                voted = None
                if up.button("👍", key=f"up_{message['id']}", type="primary" if rating == "up" else "secondary"):
                    voted = "up"
                if down.button("👎", key=f"down_{message['id']}", type="primary" if rating == "down" else "secondary"):
                    voted = "down"
                if rating:
                    note.caption(
                        "✓ You rated this answer " + ("helpful" if rating == "up" else "not helpful")
                        + ". Click the other thumb to change your mind."
                    )
                if voted:
                    try:
                        send_feedback(message["id"], voted)
                        st.session_state[f"voted_{message['id']}"] = voted
                        st.session_state["vote_message"] = "Thanks! Marked as " + ("helpful" if voted == "up" else "not helpful")
                        st.cache_data.clear() 
                        st.rerun()  # redraw so the chosen thumb lights up; you stay in this chat
                    except ApiError as exc:
                        st.error(str(exc))
else:
    st.caption("Ask anything about this paper. Answers always include page references.")

# ---------- asking a new question ----------
question = st.chat_input("Ask a question about this paper")
if question:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        meta: dict = {}
        waiting = st.empty()
        waiting.caption("⏳ Searching the paper... (the first answer after a break is slower)")

        def tokens():
            """Pass the words through, and remove the waiting note when the first word arrives."""
            first = True
            for piece in stream_ask(paper_id, question, conversation_id, meta):
                if first:
                    waiting.empty()
                    first = False
                yield piece

        try:
            st.write_stream(tokens())
        except ApiError as exc:
            waiting.empty()
            st.error(str(exc))
        else:
            # Reload the page from the saved chat, so the cleaned answer, sources and thumbs appear.
            st.session_state["pending_convo"] = meta.get("conversation_id")
            st.rerun()