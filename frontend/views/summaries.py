"""Summaries: have the AI summarize a whole paper in the style you choose."""

import streamlit as st

from api_client import ApiError, create_summary, list_papers, list_summaries

KINDS = {"Short (3-4 sentences)": "short", "Key points (bullets)": "key_points", "Plain English": "simple"}

st.title("📑 Summaries")

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
paper_id = st.selectbox("Paper", list(labels), format_func=labels.get)
style = st.radio("Style", list(KINDS), horizontal=True)

if st.button("✨ Write summary"):
    with st.spinner("Reading the paper and writing a summary..."):
        try:
            create_summary(paper_id, KINDS[style])
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

try:
    saved = list_summaries(paper_id)
except ApiError as exc:
    st.error(str(exc))
    st.stop()

st.subheader(f"Saved summaries ({len(saved)})")
if not saved:
    st.caption("None yet. Pick a style and click Write summary.")
kind_names = {value: label for label, value in KINDS.items()}
for item in saved:
    with st.container(border=True):
        st.caption(f"{kind_names.get(item['kind'], item['kind'])} · {item['created_at'][:16].replace('T', ' ')}")
        st.markdown(item["content"])
