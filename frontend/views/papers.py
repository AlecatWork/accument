"""My Papers: upload files (PDF, Word, text, Markdown, web pages), track reading progress, delete."""

import streamlit as st

from api_client import ApiError, delete_paper, list_papers, set_reading_status, upload_paper

FILE_TYPES = ["pdf", "docx", "txt", "md", "markdown", "html", "htm"]
READING_OPTIONS = {"To read": "to_read", "Reading": "reading", "Done": "done"}
STATUS_ICONS = {"ready": "✅", "processing": "⏳", "failed": "❌", "uploaded": "⏳"}

if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0  # changing this number empties the uploader after a successful upload


def save_reading_status(paper_id: str) -> None:
    """Runs the moment someone changes the "To read / Reading / Done" dropdown."""
    label = st.session_state[f"reading_{paper_id}"]
    try:
        set_reading_status(paper_id, READING_OPTIONS[label])
        st.toast(f"Marked as {label.lower()}")
    except ApiError as exc:
        st.toast(str(exc), icon="⚠️")


st.title("📄 My Papers")

# Messages left over from the last upload (they survive the page refresh).
for kind, text in st.session_state.pop("papers_flash", []):
    {"ok": st.success, "warn": st.warning, "error": st.error}[kind](text)

uploads = st.file_uploader(
    "Add papers (PDF, Word, text, Markdown or web page). You can pick several at once.",
    type=FILE_TYPES,
    accept_multiple_files=True,
    key=f"upload_{st.session_state.upload_key}",
)
if uploads and st.button("➕ Add papers"):
    results = []
    progress = st.progress(0.0)
    for i, file in enumerate(uploads):
        with st.spinner(f"Reading {file.name}. This can take a few minutes on a laptop..."):
            try:
                paper = upload_paper(file.name, file.getvalue())
                if paper["status"] == "ready":
                    results.append(("ok", f"✅ {file.name} is ready ({paper['page_count']} pages)."))
                else:
                    results.append(("warn", f"❌ {file.name} couldn't be processed: {paper['error_message']}"))
            except ApiError as exc:
                results.append(("error", f"{file.name}: {exc}"))
        progress.progress((i + 1) / len(uploads))
    st.session_state.upload_key += 1
    st.session_state.papers_flash = results
    st.rerun()

st.divider()

try:
    papers = list_papers()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not papers:
    st.info("📥 No papers yet. Upload one above, or ask your teacher/yourself to run the demo-data script.")
    st.stop()

for paper in papers:
    pid = paper["id"]
    with st.container(border=True):
        left, middle, right = st.columns([5, 2, 3])
        left.markdown(f"**{paper['title'] or paper['filename']}**")
        left.caption(
            f"{STATUS_ICONS.get(paper['status'], '')} {paper['status']} · "
            f"{paper.get('page_count') or '?'} pages · {paper['filename']}"
        )
        if paper["status"] == "failed":
            left.error(paper.get("error_message") or "Processing failed.")

        current = next(label for label, value in READING_OPTIONS.items() if value == paper["reading_status"])
        middle.selectbox(
            "Reading status",
            list(READING_OPTIONS),
            index=list(READING_OPTIONS).index(current),
            key=f"reading_{pid}",
            on_change=save_reading_status,
            args=(pid,),
        )

        if paper["status"] == "ready" and right.button("💬 Ask this paper", key=f"ask_{pid}"):
            st.session_state["pending_paper"] = pid
            st.switch_page("views/chat.py")

        # Two-step delete, so one slip of the mouse can't destroy a paper.
        if st.session_state.get(f"confirm_{pid}"):
            right.warning("Delete this paper, its chats, notes and summaries?")
            yes, no = right.columns(2)
            if yes.button("Yes, delete", key=f"yes_{pid}"):
                try:
                    delete_paper(pid)
                except ApiError as exc:
                    st.error(str(exc))
                st.session_state.pop(f"confirm_{pid}", None)
                st.rerun()
            if no.button("Cancel", key=f"no_{pid}"):
                st.session_state.pop(f"confirm_{pid}", None)
                st.rerun()
        elif right.button("🗑️ Delete", key=f"del_{pid}"):
            st.session_state[f"confirm_{pid}"] = True
            st.rerun()
