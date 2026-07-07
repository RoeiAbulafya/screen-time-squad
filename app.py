import streamlit as st
import uuid
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="Screen Time Squad", layout="centered")

# --- INITIALIZATION ---
if "user_name" not in st.session_state: st.session_state["user_name"] = None
if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = ["Instagram", "YouTube", "Facebook", "TikTok"]

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# --- LOGIN ---
if not st.session_state["user_name"]:
    st.title("👋 Welcome to Screen Time Squad!")
    name = st.text_input("Your Name:")
    if st.button("Enter"):
        if name.strip():
            st.session_state["user_name"] = name.strip().capitalize()
            st.rerun()
    st.stop()

# --- TOP BAR ---
st.title(f"📱 Screen Time Squad | {st.session_state['user_name']}")
# Fetch unique users from logs
users_data = supabase.table("logs").select("user").execute().data
unique_users = sorted(list(set([u['user'] for u in users_data]))) if users_data else []
st.caption(f"Squad Members: {', '.join(unique_users) if unique_users else 'Be the first to join!'}")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🏆 Challenges", "📝 Squad Blog"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Log Your Time")
    log_date = st.date_input("Date")
    total_hours = st.number_input("Total Hours:", min_value=0.0, max_value=24.0, step=0.1)
    
    app_logs = {app: st.number_input(f"{app} (hrs):", min_value=0.0, max_value=24.0, step=0.1) 
                for app in st.session_state["tracked_apps"]}

    if st.button("Save Daily Log"):
        supabase.table("logs").insert({
            "date": str(log_date), "user": st.session_state["user_name"], 
            "total_hours": total_hours, "app_data": app_logs
        }).execute()
        st.success("Log saved!")
        st.rerun()

    st.divider()
    st.subheader("Squad Progress Chart")
    selected_user = st.selectbox("Filter Chart by User:", ["All"] + unique_users)
    logs_df = supabase.table("logs").select("*").execute().data
    if logs_df:
        df = pd.DataFrame(logs_df)
        plot_df = df if selected_user == "All" else df[df["user"] == selected_user]
        st.line_chart(plot_df.set_index("date")["total_hours"])

# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("🏆 Leaderboard")
    leaderboard = supabase.table("leaderboard").select("*").order("points", desc=True).execute().data
    if leaderboard:
        import pandas as pd
        st.dataframe(pd.DataFrame(leaderboard), use_container_width=True)
    
    st.subheader("✅ Daily Challenges")
    challenges = supabase.table("challenges").select("*").execute().data
    with st.form("challenges_form"):
        selected_points = 0
        for ch in challenges:
            if st.checkbox(f"{ch['task']} ({ch['points']} pts)", key=f"ch_{ch['task']}"):
                selected_points += ch['points']
        
        if st.form_submit_button("Submit Points"):
            user = st.session_state['user_name']
            curr = supabase.table("leaderboard").select("points").eq("user", user).execute().data
            if curr:
                supabase.table("leaderboard").update({"points": curr[0]['points'] + selected_points}).eq("user", user).execute()
            else:
                supabase.table("leaderboard").insert({"user": user, "points": selected_points}).execute()
            st.rerun()

# --- TAB 3: BLOG ---
with tab3:
    st.header("Squad Feed")
    with st.form("blog_form", clear_on_submit=True):
        post = st.text_area("Share a reflection:")
        if st.form_submit_button("Post") and post:
            supabase.table("blog").insert({"user": st.session_state["user_name"], "post": post}).execute()
            st.rerun()

    posts = supabase.table("blog").select("*").order("created_at", desc=True).execute().data
    for p in posts:
        st.markdown(f"**{p['user']}**")
        st.info(p['post'])
        if p["user"] == st.session_state["user_name"]:
            if st.button("🗑️ Delete", key=f"del_{p['id']}"):
                supabase.table("blog").delete().eq("id", p['id']).execute()
                st.rerun()