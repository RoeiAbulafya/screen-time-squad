import uuid
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Screen Time Squad", layout="centered")

# --- INITIALIZATION ---
if "user_name" not in st.session_state: st.session_state["user_name"] = None
if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = ["Instagram", "YouTube", "Facebook", "TikTok"]

# --- CONNECTIONS & CACHING ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data():
    return {
        "logs": conn.read(worksheet="Logs", ttl=0),
        "leaderboard": conn.read(worksheet="Leaderboard", ttl=0),
        "blog": conn.read(worksheet="Blog", ttl=0),
        "comments": conn.read(worksheet="Comments", ttl=0),
        "challenges": conn.read(worksheet="Challenges", ttl=0)
    }

# --- LOGIN ---
if not st.session_state["user_name"]:
    st.title("👋 Welcome to Screen Time Squad!")
    name = st.text_input("Your Name:")
    if st.button("Enter"):
        if name.strip():
            st.session_state["user_name"] = name.strip().capitalize()
            st.rerun()
    st.stop()

# --- DATA LOADING ---
data = load_data()
logs_df, leaderboard_df = data["logs"], data["leaderboard"]
blog_df, comments_df = data["blog"], data["comments"]
challenges_df = data["challenges"]

# --- TOP BAR ---
st.title(f"📱 Screen Time Squad | {st.session_state['user_name']}")
unique_users = sorted(logs_df["User"].unique().tolist()) if not logs_df.empty else []
st.caption(f"Squad Members: {', '.join(unique_users) if unique_users else 'Be the first to join!'}")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🏆 Challenges", "📝 Squad Blog"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Log Your Time")
    log_date = st.date_input("Date")
    total_hours = st.number_input("Total Hours:", min_value=0.0, max_value=24.0, step=0.1)
    
    app_logs = {}
    cols = st.columns(2)
    for i, app in enumerate(st.session_state["tracked_apps"]):
        with cols[i % 2]:
            app_logs[app] = st.number_input(f"{app} (hrs):", min_value=0.0, max_value=24.0, step=0.1)

    if st.button("Save Daily Log"):
        new_row = {"Date": str(log_date), "User": st.session_state["user_name"], "Total Hours": total_hours}
        new_row.update(app_logs)
        conn.update(data=pd.concat([logs_df, pd.DataFrame([new_row])]), worksheet="Logs")
        st.cache_data.clear()
        st.success("Log saved!")
        st.rerun()

    st.divider()
    st.subheader("Squad Progress Chart")
    selected_user = st.selectbox("Filter Chart by User:", ["All"] + unique_users)
    if not logs_df.empty:
        plot_df = logs_df if selected_user == "All" else logs_df[logs_df["User"] == selected_user]
        st.line_chart(plot_df.pivot(index="Date", columns="User", values="Total Hours"))

# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("🏆 Leaderboard")
    if not leaderboard_df.empty:
        st.dataframe(leaderboard_df.sort_values(by="Points", ascending=False), use_container_width=True)
    
    st.subheader("✅ Daily Challenges")
    with st.form("challenges_form"):
        selected_points = 0
        for _, row in challenges_df.iterrows():
            if st.checkbox(f"{row['Task']} ({row['Points']} pts)", key=f"ch_{row['Task']}"):
                selected_points += row['Points']
        
        if st.form_submit_button("Submit Points"):
            if st.session_state['user_name'] in leaderboard_df['User'].values:
                idx = leaderboard_df[leaderboard_df["User"] == st.session_state["user_name"]].index[0]
                leaderboard_df.at[idx, "Points"] += selected_points
            else:
                leaderboard_df = pd.concat([leaderboard_df, pd.DataFrame([{"User": st.session_state['user_name'], "Points": selected_points}])], ignore_index=True)
            conn.update(data=leaderboard_df, worksheet="Leaderboard")
            st.cache_data.clear()
            st.rerun()

    with st.expander("➕ Create New Challenge"):
        new_task = st.text_input("Task Description")
        new_pts = st.number_input("Points Reward", min_value=1, value=10)
        if st.button("Add Challenge"):
            conn.update(data=pd.concat([challenges_df, pd.DataFrame([{"Task": new_task, "Points": new_pts}])]), worksheet="Challenges")
            st.cache_data.clear()
            st.rerun()

# --- TAB 3: BLOG & COMMENTS ---
with tab3:
    st.header("Squad Feed")
    with st.form("blog_form", clear_on_submit=True):
        post = st.text_area("Share a reflection:")
        if st.form_submit_button("Post") and post:
            new_p = {"PostID": str(uuid.uuid4())[:8], "Timestamp": datetime.now().strftime("%H:%M"), "User": st.session_state["user_name"], "Post": post, "Likes": ""}
            conn.update(data=pd.concat([blog_df, pd.DataFrame([new_p])]), worksheet="Blog")
            st.cache_data.clear()
            st.rerun()

    for _, row in blog_df.iloc[::-1].iterrows():
        pid = row["PostID"]
        st.markdown(f"**{row['User']}** ({row['Timestamp']})")
        st.info(row['Post'])
        
        if row["User"] == st.session_state["user_name"]:
            if st.button("🗑️ Delete Post", key=f"del_{pid}"):
                conn.update(data=blog_df[blog_df["PostID"] != pid], worksheet="Blog")
                st.cache_data.clear()
                st.rerun()

        with st.expander("💬 Comments"):
            post_comments = comments_df[comments_df["PostID"] == pid] if "PostID" in comments_df.columns else pd.DataFrame()
            for _, c_row in post_comments.iterrows():
                st.markdown(f"**{c_row['User']}:** {c_row['Comment']}")
            with st.form(key=f"c_form_{pid}", clear_on_submit=True):
                new_c = st.text_input("Add comment...")
                if st.form_submit_button("Reply") and new_c:
                    conn.update(data=pd.concat([comments_df, pd.DataFrame([{"PostID": pid, "User": st.session_state["user_name"], "Comment": new_c}])]), worksheet="Comments")
                    st.cache_data.clear()
                    st.rerun()
        st.markdown("---")