import streamlit as st
import pandas as pd 
from datetime import datetime
from supabase import create_client
import plotly.express as px

st.set_page_config(page_title="Screen Time Squad", layout="centered")

# --- INITIALIZATION ---
if "user_name" not in st.session_state: st.session_state["user_name"] = None
if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = ["Instagram", "YouTube", "Facebook"]

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# --- LOGIN ---
if not st.session_state["user_name"]:
    # עיצוב מרכזי וממוקד
    st.title("👋 Welcome to Screen Time Squad!")
    
    # שימוש ב-Container למראה נקי
    with st.container():
        st.markdown("""
        ### Ready to take back your time? 
        Join the squad to track your screen time, compete in healthy challenges, 
        and lower your digital footprint together with friends.
        """)
        
        col1, col2 = st.columns([0.6, 0.4])
        with col1:
            st.markdown("""
            *   📊 **Track:** Log your daily usage.
            *   🏆 **Compete:** Climb the leaderboard.
            *   🤝 **Connect:** Reflect with your squad.
            """)
            
            name = st.text_input("Enter your name to join:")
            if st.button("Get Started 🚀"):
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
    
    # 1. קלט זמן מסך כללי בשתי עמודות
    col_h, col_m = st.columns(2)
    with col_h:
        hours_input = st.number_input("Total Hours:", min_value=0, max_value=24, step=1)
    with col_m:
        minutes_input = st.number_input("Total Minutes:", min_value=0, max_value=59, step=1)
    
    st.divider()
    st.subheader("App Breakdown")

    # 2. לולאת קלט לאפליקציות - שעות ודקות זה לצד זה
    app_logs = {}
    for app in st.session_state["tracked_apps"]:
        st.markdown(f"**{app}**")
        c1, c2 = st.columns(2)
        with c1:
            h = st.number_input(f"{app} (Hours):", min_value=0, max_value=24, step=1, key=f"{app}_h")
        with c2:
            m = st.number_input(f"{app} (Minutes):", min_value=0, max_value=59, step=1, key=f"{app}_m")
        app_logs[app] = h + (m / 60)

    # 3. הוספת אפליקציה חדשה
    st.subheader("➕ Add New App")
    new_app = st.text_input("New App Name:")
    if st.button("Add App"):
        if new_app and new_app not in st.session_state["tracked_apps"]:
            st.session_state["tracked_apps"].append(new_app)
            st.rerun()

    # 4. שמירת נתונים
    if st.button("Save Daily Log"):
        existing_log = supabase.table("logs").select("id").eq("user", st.session_state["user_name"]).eq("date", str(log_date)).execute().data
        if existing_log:
            supabase.table("logs").delete().eq("id", existing_log[0]['id']).execute()
            
        data_to_insert = {
            "date": str(log_date), 
            "user": st.session_state["user_name"], 
            "hours": hours_input, 
            "minutes": minutes_input, 
            "app_data": app_logs
        }
        supabase.table("logs").insert(data_to_insert).execute()
        st.success("Log saved!")
        st.rerun()

    st.divider()
    
    st.divider()
    
    # 5. הצגת הגרפים
    all_logs = supabase.table("logs").select("*").execute().data
    today = str(datetime.now().date())
    logs_today = [l for l in all_logs if l['date'] == today]

    st.subheader("Daily App Breakdown")
    if logs_today:
        for log in logs_today:
            user = log['user']
            tot_h = log.get('hours', 0)
            tot_m = log.get('minutes', 0)
            
            # כותרת שם המשתמש וזמן כולל בגדול (כמו בתמונה)
            st.markdown(f"**{user}**")
            st.markdown(f"<h1 style='margin-top: -15px; margin-bottom: 0px;'>{tot_h}h {tot_m}m</h1>", unsafe_allow_html=True)

            app_data = log.get('app_data', {})
            # הכנת הנתונים לגרף
            chart_data = [{"app": app, "duration": duration, "user": ""} for app, duration in app_data.items() if duration > 0]
            
            if chart_data:
                df_apps = pd.DataFrame(chart_data)
                
                # יצירת הגרף האופקי
                fig_apps = px.bar(df_apps, x="duration", y="user", color="app", orientation='h')
                
                # עיצוב מינימליסטי ודק
                fig_apps.update_traces(width=0.15, marker_line_width=0) # עובי דק וללא מסגרת לעמודות
                
                fig_apps.update_layout(
                    height=80, # גובה קטן מאוד שיוצר מראה של פס טעינה
                    margin=dict(l=0, r=0, t=10, b=0), # הסרת שוליים מיותרים
                    paper_bgcolor="rgba(0,0,0,0)", # רקע שקוף
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=""), # העלמת ציר X
                    yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=""), # העלמת ציר Y
                    showlegend=True,
                    legend=dict(
                        orientation="h", # מקרא אופקי
                        yanchor="top",
                        y=-0.2,
                        xanchor="left",
                        x=0,
                        title="",
                        font=dict(size=11)
                    )
                )
                
                # הצגת הגרף ללא סרגל הכלים של Plotly (למראה נקי יותר)
                st.plotly_chart(fig_apps, use_container_width=True, config={'displayModeBar': False})
                
                # הוספת שורת הטקסט עם הפירוט (לדוגמה: IG 45m · Facebook 7m)
                breakdown_strs = []
                for _, row in df_apps.iterrows():
                    mins = int(row['duration'] * 60)
                    breakdown_strs.append(f"{row['app']} {mins}m")
                
                st.markdown(f"<div style='font-size: 12px; color: #a0a0a0; margin-top: -15px;'>{' · '.join(breakdown_strs)}</div>", unsafe_allow_html=True)
                
            st.divider() # קו הפרדה בין משתמש למשתמש
    else:
        st.write("No app data logged for today.")
    st.divider()
    st.subheader("Squad Progress Chart") 
    if all_logs:
        df = pd.DataFrame(all_logs)
        df['user'] = df['user'].str.strip()
        df['date'] = pd.to_datetime(df['date'])
        df['total_time'] = df['hours'] + (df['minutes'] / 60)
        df = df.sort_values(by=['user', 'date'])
        
        fig_line = px.line(df, x='date', y='total_time', color='user', 
                          markers=True, title="Screen Time by User (Total Hours)")
        st.plotly_chart(fig_line, use_container_width=True)
        
# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("🏆 Leaderboard")
    leaderboard = supabase.table("leaderboard").select("*").order("points", desc=True).execute().data
    if leaderboard:
        st.dataframe(pd.DataFrame(leaderboard), width='stretch')
    
    st.subheader("✅ Daily Challenges")
    challenges_data = supabase.table("challenges").select("*").execute().data
    
    if "prev_selections" not in st.session_state: 
        st.session_state["prev_selections"] = {}

    with st.form("challenges_form"):
        current_selections = {}
        for ch in challenges_data:
            # הצגת האתגר עם אופציית מחיקה בשורה אחת
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                is_checked = st.checkbox(f"{ch['task']} ({ch['points']} pts)", 
                                         key=f"ch_{ch['id']}", 
                                         value=st.session_state["prev_selections"].get(ch['task'], False))
                current_selections[ch['task']] = (is_checked, ch['points'])
            
            with col2:
                # כפתור מחיקה - מופיע רק אם המשתמש הוא היוצר
                if ch.get("created_by") == st.session_state["user_name"]:
                    if st.form_submit_button(f"🗑️", key=f"del_ch_{ch['id']}"):
                        supabase.table("challenges").delete().eq("id", ch['id']).execute()
                        st.rerun()

        if st.form_submit_button("Update Score"):
            user = st.session_state['user_name']
            
            # חישוב שינוי נקודות:
            # נקודות מתווספות אם סומן עכשיו ולא היה מסומן קודם
            # נקודות יורדות אם לא מסומן עכשיו והיה מסומן קודם (Un-check)
            point_change = 0
            for task, (checked, pts) in current_selections.items():
                was_checked = st.session_state["prev_selections"].get(task, False)
                if checked and not was_checked:
                    point_change += pts
                elif not checked and was_checked:
                    point_change -= pts
            
            # עדכון בטבלה
            curr = supabase.table("leaderboard").select("points").eq("user", user).execute().data
            if curr:
                new_total = curr[0]['points'] + point_change
                supabase.table("leaderboard").update({"points": new_total}).eq("user", user).execute()
            else:
                supabase.table("leaderboard").insert({"user": user, "points": point_change}).execute()
            
            st.session_state["prev_selections"] = {k: v[0] for k, v in current_selections.items()}
            st.rerun()
    st.subheader("➕ Suggest a New Challenge")
    with st.form("add_challenge_form", clear_on_submit=True):
        new_task = st.text_input("What is the challenge?")
        new_points = st.number_input("How many points is it worth?", min_value=1, step=1)
        if st.form_submit_button("Submit Suggestion"):
                # שומרים גם את שם המשתמש שיצר את האתגר
            supabase.table("challenges").insert({
                "task": new_task, 
                "points": new_points, 
                "created_by": st.session_state["user_name"]
            }).execute()
            st.rerun()
# --- TAB 3: BLOG ---
with tab3:
    st.header("Squad Feed")
    
    # אזור פרסום פוסט חדש
    with st.form("blog_form", clear_on_submit=True):
        post = st.text_area("שתף מחשבה:")
        if st.form_submit_button("פרסם") and post:
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
        with st.container(border=True):
            # כותרת הפוסט - מיושרת לימין
            st.markdown(f"### {p['user']}")
            st.write(p['post'])
            
            if 'created_at' in p:
                date_str = p['created_at'].replace('T', ' ').split('.')[0]
                st.caption(f"פורסם ב: {date_str}")
            
            # אזור פעולות בשורה אחת
            cols = st.columns([0.2, 0.4, 0.4])
            
            liked_by = p.get('liked_by') if p.get('liked_by') is not None else []
            is_liked = st.session_state["user_name"] in liked_by
            
            with cols[0]:
                if st.button(f"{'❤️' if is_liked else '🤍'} {len(liked_by)}", key=f"post_like_{p['id']}"):
                    if is_liked:
                        liked_by.remove(st.session_state["user_name"])
                    else:
                        liked_by.append(st.session_state["user_name"])
                    supabase.table("blog").update({"liked_by": liked_by}).eq("id", p['id']).execute()
                    st.rerun()
            
            with cols[1]:
                # שימוש ב-Popover לתגובות - הרבה יותר נקי מ-Expander
                comments_resp = supabase.table("comments").select("*").eq("post_id", p['id']).order("created_at").execute()
                comments = comments_resp.data if comments_resp.data else []
                
                with st.popover(f"💬 תגובות ({len(comments)})"):
                    st.subheader("תגובות")
                    if comments:
                        for c in comments:
                            st.markdown(f"**{c.get('user')}**: {c.get('comment')}")
                            if c.get("user") == st.session_state["user_name"]:
                                if st.button("🗑️", key=f"c_del_{c['id']}"):
                                    supabase.table("comments").delete().eq("id", c['id']).execute()
                                    st.rerun()
                    
                    # הוספת תגובה בתוך ה-popover
                    new_comment = st.text_input("הוסף תגובה...", key=f"input_{p['id']}")
                    if st.button("שלח", key=f"btn_{p['id']}"):
                        if new_comment.strip():
                            supabase.table("comments").insert({
                                "post_id": p['id'], 
                                "user": st.session_state["user_name"], 
                                "comment": new_comment.strip()
                            }).execute()
                            st.rerun()

            with cols[2]:
                if p["user"] == st.session_state["user_name"]:
                    if st.button("🗑️ מחק פוסט", key=f"del_{p['id']}"):
                        supabase.table("blog").delete().eq("id", p['id']).execute()
                        st.rerun()