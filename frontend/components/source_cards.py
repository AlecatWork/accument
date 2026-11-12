"""A small reusable widget that shows where an answer came from."""

import streamlit as st


def show_sources(sources: list[dict]):
    """Show "Sources: Page 2, Page 3" and a folding panel with the exact excerpts used."""
    if not sources:
        return
    pages = sorted({s.get("page") for s in sources if s.get("page")})
    st.caption("📎 Sources: " + ", ".join(f"Page {p}" for p in pages))
    with st.expander("Show excerpts"):
        for s in sources:
            st.markdown(f"**[{s['n']}] Page {s['page']}**")
            st.write(s.get("snippet", ""))