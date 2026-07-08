import streamlit as st
import pandas as pd 
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
    # ... (קוד הקלט נשאר אותו דבר) ...
    log_date = st.date_input("Date")
    hours_input = st.number_input("Hours:", min_value=0, max_value=24, step=1)
    minutes_input = st.number_input("Minutes:", min_value=0, max_value=59, step=1)
    
    app_logs = {app: st.number_input(f"{app} (hours):", min_value=0.0, max_value=24.0, step=0.1) 
                for app in st.session_state["tracked_apps"]}
    
    st.subheader("Add New App to Track")
    new_app = st.text_input("App Name:")
    if st.button("Add App"):
        if new_app and new_app not in st.session_state["tracked_apps"]:
            st.session_state["tracked_apps"].append(new_app)
            st.rerun()

    if st.button("Save Daily Log"):
        # ... (קוד השמירה נשאר אותו דבר) ...
        existing_log = supabase.table("logs").select("id").eq("user", st.session_state["user_name"]).eq("date", str(log_date)).execute().data
        if existing_log:
            supabase.table("logs").delete().eq("id", existing_log[0]['id']).execute()
        data_to_insert = {"date": str(log_date), "user": st.session_state["user_name"], "hours": hours_input, "minutes": minutes_input, "app_data": app_logs}
        supabase.table("logs").insert(data_to_insert).execute()
        st.success("Log saved!")
        st.rerun()

    st.divider()
    
    # 1. שליפת כל הנתונים לגרף הקווי (Squad Progress)
    all_logs = supabase.table("logs").select("*").execute().data
    
    # 2. שליפת נתוני היום בלבד (לגרף האפליקציות)
    today = str(datetime.now().date())
    logs_today = [l for l in all_logs if l['date'] == today]
    
    # --- גרף אפליקציות יומי ---
    st.subheader("Daily App Breakdown")
    if logs_today:
        chart_data = []
        for log in logs_today:
            app_data = log.get('app_data', {})
            for app, duration in app_data.items():
                if duration > 0:
                    chart_data.append({"user": log['user'], "app": app, "duration": duration})
        
        df_apps = pd.DataFrame(chart_data)
        if not df_apps.empty:
        # 1. הגדרת פלטת צבעים אישית (אפשר להוסיף עוד צבעים)
        color_map = {
            "Instagram": "#E1306C", "YouTube": "#FF0000", 
            "Reddit": "#FF4500", "TikTok": "#00F2EA",
            "Facebook": "#4267B2"
        }
        
        fig_apps = px.bar(df_apps, x="duration", y="user", color="app", 
                         orientation='h', barmode='stack',
                         color_discrete_map=color_map, # שימוש בצבעים מוגדרים
                         template="plotly_white") # רקע נקי

        # 2. עיצוב העמודות (דק יותר)
        fig_apps.update_traces(width=0.4) # שולט בעובי העמודה

        # 3. ניקוי העיצוב (להעיף צירים מיותרים שנותנים מראה של "דוח")
        fig_apps.update_layout(
            height=200, # גובה קטן לגרף דק
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title=None,
            yaxis_title=None,
            showlegend=True
        )
        
        st.plotly_chart(fig_apps, width='stretch')
    else:
        st.write("No app data logged for today.")

    st.divider()

    # --- גרף קווי (Squad Progress Chart) ---
    st.subheader("Squad Progress Chart") 
    if all_logs:
        df = pd.DataFrame(all_logs)
        df['user'] = df['user'].str.strip()
        df['date'] = pd.to_datetime(df['date'])
        df['total_time'] = df['hours'] + (df['minutes'] / 60)
        df = df.sort_values(by=['user', 'date'])
        
        fig_line = px.line(df, x='date', y='total_time', color='user', 
                          markers=True, title="Screen Time by User (Total Hours)")
        st.plotly_chart(fig_line, width='stretch')
    else:
        st.write("No log data to display yet.")
# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("🏆 Leaderboard")
    leaderboard = supabase.table("leaderboard").select("*").order("points", desc=True).execute().data
    if leaderboard:
        st.dataframe(pd.DataFrame(leaderboard), width='stretch')
    
    with st.expander("➕ Suggest a New Challenge"):
        with st.form("add_challenge_form", clear_on_submit=True):
            new_task = st.text_input("What is the challenge?")
            new_points = st.number_input("How many points is it worth?", min_value=1, step=1)
            if st.form_submit_button("Submit Suggestion"):
                supabase.table("challenges").insert({"task": new_task, "points": new_points}).execute()
                st.rerun()

    st.subheader("✅ Daily Challenges")
    challenges_data = supabase.table("challenges").select("*").execute().data
    if "prev_selections" not in st.session_state: st.session_state["prev_selections"] = {}

    with st.form("challenges_form"):
        current_selections = {}
        for ch in challenges_data:
            is_checked = st.checkbox(f"{ch['task']} ({ch['points']} pts)", key=f"ch_{ch['task']}")
            current_selections[ch['task']] = (is_checked, ch['points'])
        
        if st.form_submit_button("Update Score"):
            user = st.session_state['user_name']
            point_change = sum(pts for task, (checked, pts) in current_selections.items() 
                               if checked and not st.session_state["prev_selections"].get(task, False))
            point_change -= sum(pts for task, (checked, pts) in current_selections.items() 
                                if not checked and st.session_state["prev_selections"].get(task, False))
            
            curr = supabase.table("leaderboard").select("points").eq("user", user).execute().data
            if curr:
                supabase.table("leaderboard").update({"points": curr[0]['points'] + point_change}).eq("user", user).execute()
            else:
                supabase.table("leaderboard").insert({"user": user, "points": point_change}).execute()
            
            st.session_state["prev_selections"] = {k: v[0] for k, v in current_selections.items()}
            st.rerun()

# --- TAB 3: BLOG ---
with tab3:
    st.header("Squad Feed")
    
    # אזור פרסום פוסט חדש
    with st.form("blog_form", clear_on_submit=True):
        post = st.text_area("Share a reflection:")
        if st.form_submit_button("Post") and post:
            # וודא שיש לך עמודת 'liked_by' בטבלה כ-JSONB עם ערך דיפולטי '[]'
            supabase.table("blog").insert({
                "user": st.session_state["user_name"], 
                "post": post, 
                "liked_by": [] 
            }).execute()
            st.rerun()

    # משיכת פוסטים
    posts_resp = supabase.table("blog").select("*").order("created_at", desc=True).execute()
    posts = posts_resp.data if posts_resp.data else []

    # מעבר והצגה של כל פוסט
    for p in posts:
        with st.container():
            st.markdown(f"**{p['user']}**")
            st.info(p['post'])
            
            # --- לייק לפוסט ---
            # במקום מה שהיה, השתמש בזה:
            liked_by = p.get('liked_by') if p.get('liked_by') is not None else []
            is_liked = st.session_state["user_name"] in liked_by
            # במקום מה שהיה, השתמש בזה:

            if st.button(f"{'❤️' if is_liked else '🤍'} {len(liked_by)}", key=f"post_like_{p['id']}"):
                if is_liked:
                    liked_by.remove(st.session_state["user_name"])
                else:
                    liked_by.append(st.session_state["user_name"])
                supabase.table("blog").update({"liked_by": liked_by}).eq("id", p['id']).execute()
                st.rerun()
            
            # --- מחיקת פוסט ---
            if p["user"] == st.session_state["user_name"]:
                if st.button("🗑️ Delete Post", key=f"del_{p['id']}"):
                    supabase.table("blog").delete().eq("id", p['id']).execute()
                    st.rerun()
            
            # --- אזור תגובות ---
            # קודם נשלוף את התגובות כדי שנדע כמה יש
            comments_resp = supabase.table("comments").select("*").eq("post_id", p['id']).order("created_at").execute()
            comments = comments_resp.data if comments_resp.data else []
            
            # עכשיו נציג את ה-Expander עם המונה בכותרת
            with st.expander(f"💬 View Comments ({len(comments)})"):
                
                # הצגת התגובות הקיימות
                if comments:
                    for c in comments:
                        st.caption(f"**{c.get('user', 'Unknown')}**: {c.get('comment', '')}")
                        
                        # לייק לתגובה
                        c_liked_by = c.get('liked_by') or []
                        c_is_liked = st.session_state["user_name"] in c_liked_by
                        
                        if st.button(f"{'❤️' if c_is_liked else '🤍'} {len(c_liked_by)}", key=f"c_like_{c['id']}"):
                            if c_is_liked:
                                c_liked_by.remove(st.session_state["user_name"])
                            else:
                                c_liked_by.append(st.session_state["user_name"])
                            supabase.table("comments").update({"liked_by": c_liked_by}).eq("id", c['id']).execute()
                            st.rerun()
                        
                        # מחיקת תגובה
                        if c.get("user") == st.session_state["user_name"]:
                            if st.button("🗑️", key=f"c_del_{c['id']}"):
                                supabase.table("comments").delete().eq("id", c['id']).execute()
                                st.rerun()
                else:
                    st.caption("No comments yet.")
                
                # הוספת תגובה חדשה
                with st.form(f"comment_form_{p['id']}", clear_on_submit=True):
                    new_comment = st.text_input("Add a comment:")
                    if st.form_submit_button("Send"):
                        if new_comment.strip():
                            supabase.table("comments").insert({
                                "post_id": p['id'], 
                                "user": st.session_state["user_name"], 
                                "comment": new_comment.strip(),
                                "liked_by": []
                            }).execute()
                            st.rerun()