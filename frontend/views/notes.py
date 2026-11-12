"""Notes: pick a paper, then add, edit or delete as many notes on it as you like."""

import streamlit as st

from api_client import ApiError, create_note, delete_note, edit_note, list_notes, list_papers

st.title("📝 Notes")

try:
    papers = list_papers()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not papers:
    st.info("📥 Upload a paper first, then you can write notes on it.")
    st.page_link("views/papers.py", label="Go to My Papers", icon="📄")
    st.stop()

labels = {p["id"]: p["title"] or p["filename"] for p in papers}
paper_id = st.selectbox("Choose a paper", list(labels), format_func=labels.get)

# ---------- add a note ----------
# clear_on_submit empties the box after saving, ready for the next note.
with st.form("add_note", clear_on_submit=True):
    text = st.text_area("Write a note", placeholder="What do you want to remember about this paper?")
    if st.form_submit_button("➕ Add note") and text.strip():
        try:
            create_note(paper_id, text.strip())
            st.toast("Note added")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

# ---------- the notes on this paper ----------
try:
    notes = list_notes(paper_id)
except ApiError as exc:
    st.error(str(exc))
    st.stop()

st.subheader(f"Notes on {labels[paper_id]} ({len(notes)})")
if not notes:
    st.caption("No notes on this paper yet. Add your first one above.")

for note in notes:
    with st.container(border=True):
        st.write(note["content"])
        st.caption(f"Last changed {note['updated_at'][:16].replace('T', ' ')}")
        with st.expander("✏️ Edit"):
            new_text = st.text_area("Edit note", value=note["content"], key=f"edit_text_{note['id']}")
            if st.button("💾 Save changes", key=f"save_{note['id']}") and new_text.strip():
                try:
                    edit_note(note["id"], new_text.strip())
                    st.toast("Note updated")
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))
        if st.button("🗑️ Delete", key=f"delete_{note['id']}"):
            try:
                delete_note(note["id"])
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
