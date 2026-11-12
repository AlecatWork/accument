"""Compare: ask one question across 2-4 papers and get a side-by-side answer."""

import streamlit as st

from api_client import ApiError, compare, list_papers

st.title("🔀 Compare")

try:
    papers = [p for p in list_papers() if p["status"] == "ready"]
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if len(papers) < 2:
    st.info("📥 You need at least two ready papers to compare.")
    st.page_link("views/papers.py", label="Go to My Papers", icon="📄")
    st.stop()

labels = {p["id"]: p["title"] or p["filename"] for p in papers}
chosen = st.multiselect("Pick 2 to 4 papers", list(labels), format_func=labels.get, max_selections=4)
question = st.text_input("What do you want to compare?", placeholder="e.g. How much data did each paper use?")

if st.button("🔀 Compare"):
    if len(chosen) < 2 or len(question.strip()) < 3:
        st.warning("Choose at least two papers and type a question.")
    else:
        with st.spinner("Reading both papers and comparing. This can take a minute..."):
            try:
                st.markdown(compare(chosen, question.strip())["answer"])
            except ApiError as exc:
                st.error(str(exc))
