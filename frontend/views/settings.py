"""Settings: who you are, and a health check for everything the app depends on."""

import streamlit as st

from api_client import ApiError, health, me

st.title("🔧 Settings")

try:
    st.write("**Signed in as:**", me()["email"])
except ApiError as exc:
    st.error(str(exc))

st.subheader("System check")
try:
    info = health()
except ApiError as exc:
    st.error(str(exc))
    st.stop()


def light(ok: bool) -> str:
    return "🟢" if ok else "🔴"


st.write(f"{light(info['database'] == 'connected')} Database: {info['database']}")
st.write(f"{light(info['ollama'] == 'connected')} Ollama (the AI program on your computer): {info['ollama']}")
st.write(f"{light(info['chat_model_ready'])} Chat model: `{info['chat_model']}`")
st.write(f"{light(info['embed_model_ready'])} Search model: `{info['embed_model']}`")

# Tell the user exactly what to type if something is missing.
if info["ollama"] != "connected":
    st.warning("Open the **Ollama** app on your computer (look for the llama icon in the menu bar), then refresh.")
else:
    if not info["chat_model_ready"]:
        st.warning(f"Install the chat model: run `ollama pull {info['chat_model']}` in Terminal.")
    if not info["embed_model_ready"]:
        st.warning(f"Install the search model: run `ollama pull {info['embed_model']}` in Terminal.")

st.caption("Models run on your own computer through Ollama, so your papers never leave your computer.")
