import streamlit as st
import uuid
import pandas as pd  # FIXED: Added pandas import here!
from datetime import datetime
from supabase import create_client
import plotly.express as px

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

# DIAGNOSTIC TOOL 
try:
    # This tries to fetch just one row to see if the table exists
    test = supabase.table("logs").select("*").limit(1).execute()
    st.write("Connection Successful!")
except Exception as e:
    st.error(f"DEBUG ERROR: {e}")
    st.stop()
    
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
users_data = supabase.table("logs").select("user").execute().data
unique_users = sorted(list(set([u['user'] for u in users_data]))) if users_data else []
st.caption(f"Squad Members: {', '.join(unique_users) if unique_users else 'Be the first to join!'}")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🏆 Challenges", "📝 Squad Blog"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Log Your Time")
    log_date = st.date_input("Date")
    hours = st.number_input("Total Hours:", min_value=0.0, max_value=24.0, step=0.01)
    minutes = st.number_input("minutes:", min_value=0.0, max_value=24.0, step=0.01)
    app_logs = {app: [st.number_input(f"{app} (hours):", min_value=0.0, max_value=24.0, step=0.01),st.number_input(f"{app} (minutes):", min_value=0.0, max_value=24.0, step=0.01) ]
                for app in st.session_state["tracked_apps"]}

    if st.button("Save Daily Log"):
        try:
            data_to_insert = {
                "date": str(log_date), 
                "user": st.session_state["user_name"], 
                "hours": hours, 
                "minutes": minutes,
                "app_data": app_logs
            }
            supabase.table("logs").insert(data_to_insert).execute()
            st.success("Log saved!")
            st.rerun()
        except Exception as e:
            st.error(f"INSERT ERROR: {e}")
            st.stop()

    st.divider()
    st.subheader("Squad Progress Chart")  
    # 1. שליפת הנתונים מהטבלה
    logs = supabase.table("logs").select("*").execute().data
    
    if logs:
        df = pd.DataFrame(logs)
        
        # 2. המרת עמודת התאריך לפורמט זמן אם צריך
        df['date'] = pd.to_datetime(df['date'])
        
        # 3. יצירת הגרף ב-Plotly
        # color='user' הוא מה שיגרום לכל משתמש לקבל קו בצבע שונה
        fig = px.line(df, x='date', y='total_hours', color='user', 
                      markers=True, title="Screen Time by User")
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No log data to display yet.")

# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("🏆 Leaderboard")
    leaderboard = supabase.table("leaderboard").select("*").order("points", desc=True).execute().data
    if leaderboard:
        st.dataframe(pd.DataFrame(leaderboard), use_container_width=True)
    
    st.subheader("✅ Daily Challenges")
    challenges_data = supabase.table("challenges").select("*").execute().data
   
    # --- ADD NEW CHALLENGE SECTION ---
    with st.expander("➕ Suggest a New Challenge"):
        with st.form("add_challenge_form", clear_on_submit=True):
            new_task = st.text_input("What is the challenge?")
            new_points = st.number_input("How many points is it worth?", min_value=1, step=1)
            if st.form_submit_button("Submit Suggestion"):
                if new_task:
                    supabase.table("challenges").insert({"task": new_task, "points": new_points}).execute()
                    st.success(f"Added '{new_task}' to the list!")
                    st.rerun()
                else:
                    st.error("Please enter a task name.")

    st.subheader("✅ Daily Challenges")
    
    # Initialize session state for tracking previous selections
    if "prev_selections" not in st.session_state:
        st.session_state["prev_selections"] = {}

    with st.form("challenges_form"):
        current_selections = {}
        for ch in challenges_data:
            # Create checkbox and store its state
            is_checked = st.checkbox(f"{ch['task']} ({ch['points']} pts)", key=f"ch_{ch['task']}")
            current_selections[ch['task']] = (is_checked, ch['points'])
        
        if st.form_submit_button("Update Score"):
            user = st.session_state['user_name']
            
            # Calculate net change (New - Old)
            point_change = 0
            for task, (is_checked, points) in current_selections.items():
                was_checked = st.session_state["prev_selections"].get(task, False)
                if is_checked and not was_checked:
                    point_change += points      # Just checked
                elif not is_checked and was_checked:
                    point_change -= points      # Just unchecked (REDUCE POINTS)
            
            # Update Database
            curr = supabase.table("leaderboard").select("points").eq("user", user).execute().data
            if curr:
                new_total = curr[0]['points'] + point_change
                supabase.table("leaderboard").update({"points": new_total}).eq("user", user).execute()
            else:
                supabase.table("leaderboard").insert({"user": user, "points": point_change}).execute()
            
            # Save new state and rerun
            st.session_state["prev_selections"] = {k: v[0] for k, v in current_selections.items()}
            st.success("Leaderboard updated!")
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