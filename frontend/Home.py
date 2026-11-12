"""The control tower of the website.

Streamlit runs THIS file first, every time you click something. It decides:
  * nobody logged in  -> show only the login page
  * somebody logged in -> show the full menu (every page has an icon) plus a Log out button
"""

import streamlit as st

st.set_page_config(page_title="Accument", page_icon="📄", layout="wide")


if not st.session_state.get("token"):
    # Logged out: a single page, and the menu is hidden.
    page = st.navigation([st.Page("views/login.py", title="Log in", icon="🔐")], position="hidden")
else:
    page = st.navigation(
        [
            st.Page("views/dashboard.py", title="Dashboard", icon="📊", default=True),
            st.Page("views/papers.py", title="My Papers", icon="📄"),
            st.Page("views/chat.py", title="Chat", icon="💬"),
            st.Page("views/notes.py", title="Notes", icon="📝"),
            st.Page("views/compare.py", title="Compare", icon="🔀"),
            st.Page("views/summaries.py", title="Summaries", icon="📑"),
            st.Page("views/settings.py", title="Settings", icon="🔧"),
        ]
    )
    with st.sidebar:
        st.divider()
        st.caption(f"Signed in as {st.session_state.get('email', 'you')}")
        if st.button("🚪 Log out"):
            st.session_state.clear() 
            st.rerun()

page.run()


