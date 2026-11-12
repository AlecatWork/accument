"""The login / sign-up page (the only page a logged-out visitor can see)."""

import streamlit as st

from api_client import ApiError, health, login, signup

st.title("📄 Accument")
st.caption("A reading helper for research papers: upload a paper, ask questions, get answers with page numbers.")

# A quick "is the backend alive?" light, which also helps with troubleshooting.
try:
    info = health()
    if info["status"] == "ok":
        st.success("Backend is running.")
    else:
        st.warning("Backend is running, but its database isn't reachable yet. Give it a few seconds and refresh.")
except ApiError as exc:
    st.error(str(exc))

tab_login, tab_signup = st.tabs(["🔐 Log in", "✨ Sign up"])

with tab_login:
    # st.form lets you press Enter to submit.
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        try:
            data = login(email, password)
            st.session_state.token = data["access_token"]
            st.session_state.email = email.lower()
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
    st.caption("Want to look around first? After running the seed script, use demo@example.com / demodemo123.")

with tab_signup:
    with st.form("signup_form"):
        email2 = st.text_input("Email", key="signup_email")
        password2 = st.text_input("Password (at least 8 characters)", type="password", key="signup_password")
        created = st.form_submit_button("Create account")
    if created:
        try:
            data = signup(email2, password2)
            st.session_state.token = data["access_token"]
            st.session_state.email = email2.lower()
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
