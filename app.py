import uuid
from datetime import date, datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Screen Time Squad", layout="centered")

# --- INITIALIZATION ---
if "user_name" not in st.session_state: st.session_state["user_name"] = None
if "custom_challenges" not in st.session_state:
    st.session_state["custom_challenges"] = [
        {"text": "🚫 No Social Media Before Noon", "points": 50},
        {"text": "⏳ Under 3 Hours Total Screen Time Today", "points": 100},
        {"text": "🌳 Walk without your phone for 30 mins", "points": 40},
    ]

# --- LOGIN ---
if not st.session_state["user_name"]:
    st.title("👋 Welcome to Screen Time Squad!")
    name = st.text_input("Your Name:")
    if st.button("Enter"):
        if name.strip():
            st.session_state["user_name"] = name.strip().capitalize()
            st.rerun()
    st.stop()

# --- CONNECTIONS ---
conn = st.connection("gsheets", type=GSheetsConnection)
logs_df = conn.read(worksheet="Logs", ttl=0)
leaderboard_df = conn.read(worksheet="Leaderboard", ttl=0)
blog_df = conn.read(worksheet="Blog", ttl=0)
comments_df = conn.read(worksheet="Comments", ttl=0)

# --- APP LAYOUT ---
st.title(f"📱 Screen Time Squad | {st.session_state['user_name']}")
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🏆 Challenges", "📝 Squad Blog"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Squad Progress")
    all_users = ["All"] + sorted(logs_df["User"].unique().tolist())
    selected_user = st.selectbox("Filter by User:", all_users)
    
    plot_df = logs_df if selected_user == "All" else logs_df[logs_df["User"] == selected_user]
    st.line_chart(plot_df.pivot(index="Date", columns="User", values="Total Hours"))
    
    st.subheader("Edit Your Logs")
    edited_logs = st.data_editor(logs_df[logs_df["User"] == st.session_state["user_name"]], num_rows="dynamic")
    if st.button("Save Log Changes"):
        other_logs = logs_df[logs_df["User"] != st.session_state["user_name"]]
        conn.update(data=pd.concat([other_logs, edited_logs]), worksheet="Logs")
        st.rerun()

# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("Leaderboard")
    st.dataframe(leaderboard_df.sort_values(by="Points", ascending=False), use_container_width=True)
    
    st.subheader("Daily Challenges")
    pts = sum(ch['points'] for i, ch in enumerate(st.session_state["custom_challenges"]) if st.checkbox(ch['text'], key=f"ch_{i}"))
    if st.button("Submit"):
        idx = leaderboard_df[leaderboard_df["User"] == st.session_state["user_name"]].index
        if not idx.empty:
            leaderboard_df.at[idx[0], "Points"] += pts
        else:
            leaderboard_df = pd.concat([leaderboard_df, pd.DataFrame([{"User": st.session_state['user_name'], "Points": pts}])])
        conn.update(data=leaderboard_df, worksheet="Leaderboard")
        st.rerun()

# --- TAB 3: BLOG & COMMENTS ---
with tab3:
    st.header("Squad Feed")
    with st.form("blog_form", clear_on_submit=True):
        post = st.text_area("New Post:")
        if st.form_submit_button("Post") and post:
            new_p = {"PostID": str(uuid.uuid4())[:8], "Timestamp": datetime.now().strftime("%H:%M"), "User": st.session_state["user_name"], "Post": post, "Likes": ""}
            conn.update(data=pd.concat([blog_df, pd.DataFrame([new_p])]), worksheet="Blog")
            st.rerun()

    for _, row in blog_df.iloc[::-1].iterrows():
        pid = row["PostID"]
        st.markdown(f"**{row['User']}** ({row['Timestamp']})")
        st.info(row['Post'])
        
        # Like & Delete Row
        c1, c2 = st.columns([1, 4])
        if c1.button("❤️ Like", key=f"like_{pid}"): pass # Logic can be expanded
        if row["User"] == st.session_state["user_name"]:
            if c2.button("🗑️ Delete Post", key=f"del_{pid}"):
                conn.update(data=blog_df[blog_df["PostID"] != pid], worksheet="Blog")
                st.rerun()

        # Comments Section
        with st.expander("💬 Comments"):
            post_comments = comments_df[comments_df["PostID"] == pid] if "PostID" in comments_df.columns else pd.DataFrame()
            for _, c_row in post_comments.iterrows():
                st.markdown(f"**{c_row['User']}:** {c_row['Comment']}")
            
            with st.form(key=f"c_form_{pid}", clear_on_submit=True):
                new_c = st.text_input("Add comment...")
                if st.form_submit_button("Reply") and new_c:
                    conn.update(data=pd.concat([comments_df, pd.DataFrame([{"PostID": pid, "User": st.session_state["user_name"], "Comment": new_c}])]), worksheet="Comments")
                    st.rerun()
        st.markdown("---")