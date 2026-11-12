"""The Dashboard: a one-glance picture of your library and how you use it.

Layout (top to bottom):
    stat cards | questions per day + reading status | most-cited papers | notes per paper + recent activity
"""

from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiError, get_stats

READING_LABELS = {"to_read": "To read", "reading": "Reading", "done": "Done"}
READING_COLORS = {"To read": "#9AA5B1", "Reading": "#2F6FED", "Done": "#2EAD6B"}


@st.cache_data(ttl=60, show_spinner=False)
def load_stats(token: str) -> dict:
    """Fetch the numbers, remembered for 60 seconds so flipping between pages stays instant.

    The token is only here so each person gets their own remembered copy.
    """
    return get_stats()


def delta_text(count: int) -> str:
    """The small line under a number, e.g. "+3 this week"."""
    return f"+{count} this week" if count else "0 this week"


def time_ago(iso_text: str) -> str:
    """Turn a timestamp into "3 hours ago"."""
    moment = datetime.fromisoformat(iso_text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - moment).total_seconds()
    if seconds < 90:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} minutes ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)} hours ago"
    return f"{int(seconds // 86400)} days ago"


def tidy(fig, height: int = 300):
    """Shared chart styling: compact, no legend clutter."""
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=height, showlegend=False)
    return fig


st.title("📊 Dashboard")
header_left, header_right = st.columns([6, 1])
header_left.caption("Your library and your reading activity at a glance.")
if header_right.button("🔄 Refresh"):
    load_stats.clear()
    st.rerun()

try:
    data = load_stats(st.session_state["token"])
except ApiError as exc:
    st.error(str(exc))
    st.stop()

# ---------- stat cards ----------
total_votes = data["votes_up"] + data["votes_down"]
card1, card2, card3, card4 = st.columns(4)
card1.metric("📄 Papers", data["paper_count"], delta_text(data["papers_this_week"]), delta_color="off")
card2.metric("💬 Questions", data["question_count"], delta_text(data["questions_this_week"]), delta_color="off")
card3.metric("📝 Notes", data["note_count"], delta_text(data["notes_this_week"]), delta_color="off")
card4.metric(
    "👍 Helpful answers",
    f"{data['votes_up'] / total_votes:.0%}" if total_votes else "-",
    f"{data['votes_up']} up / {data['votes_down']} down" if total_votes else "no votes yet",
    delta_color="off",
)

# ---------- friendly empty state for brand-new accounts ----------
if data["paper_count"] == 0:
    st.info("📥 **Upload your first paper to see activity here.** Charts fill in as you read, ask and take notes.")
    st.page_link("views/papers.py", label="Go to My Papers", icon="📄")
    st.stop()

# ---------- row 2: questions per day + reading status ----------
left, right = st.columns(2)
with left:
    st.subheader("Questions per day")
    days = pd.DataFrame(data["questions_by_day"])
    if days["count"].sum() == 0:
        st.caption("No questions in the last 30 days. Ask one in Chat to start the chart.")
    else:
        fig = px.bar(days, x="day", y="count", labels={"day": "", "count": "Questions"})
        st.plotly_chart(tidy(fig), width="stretch")

with right:
    st.subheader("Reading status")
    status = pd.DataFrame(
        {"status": [READING_LABELS[k] for k in data["reading_status"]], "papers": list(data["reading_status"].values())}
    )
    fig = px.pie(status, names="status", values="papers", hole=0.55, color="status", color_discrete_map=READING_COLORS)
    fig.update_traces(textinfo="label+value")
    st.plotly_chart(tidy(fig), width="stretch")

# ---------- row 3: most-cited papers ----------
st.subheader("Most-cited papers")
st.caption("How many answers were built from each paper.")
if data["most_cited"]:
    cited = pd.DataFrame(data["most_cited"]).sort_values("count")
    fig = px.bar(cited, x="count", y="name", orientation="h", labels={"count": "Answers", "name": ""})
    st.plotly_chart(tidy(fig, height=max(200, 45 * len(cited))), width="stretch")
else:
    st.caption("No cited answers yet. Ask a question in Chat and this fills in.")

# ---------- row 4: notes per paper + recent activity ----------
left, right = st.columns(2)
with left:
    st.subheader("Notes per paper")
    notes = pd.DataFrame(data["notes_per_paper"])
    if notes.empty or notes["count"].sum() == 0:
        st.caption("No notes yet. Add one on the Notes page.")
    else:
        fig = px.bar(notes, x="name", y="count", labels={"name": "", "count": "Notes"})
        st.plotly_chart(tidy(fig), width="stretch")

with right:
    st.subheader("Recent activity")
    if not data["recent_activity"]:
        st.caption("Your latest questions will show up here.")
    for i, item in enumerate(data["recent_activity"]):
        with st.container(border=True):
            st.write(item["question"])
            st.caption(f"{item['paper_title']} · {time_ago(item['asked_at'])}")
            if st.button("💬 Open in chat", key=f"recent_{i}"):
                # Chat reads these two notes-to-self when it opens, and jumps to that paper and chat.
                st.session_state["pending_paper"] = item["document_id"]
                st.session_state["pending_convo"] = item["conversation_id"]
                st.switch_page("views/chat.py")
