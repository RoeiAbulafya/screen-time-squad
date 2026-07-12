import streamlit as st
import pandas as pd 
from datetime import datetime, timezone, timedelta
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
    st.title("👋 Welcome to Screen Time Squad!")
    
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

# --- STREAK LOGIC ---
def calculate_streak(user_name, all_logs):
    user_dates = sorted([log['date'] for log in all_logs if log['user'] == user_name], reverse=True)
    if not user_dates:
        return 0
    
    streak = 0
    current_date = datetime.now().date()
    
    for log_date_str in user_dates:
        log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()
        if (current_date - log_date).days == streak or (current_date - log_date).days == streak + 1:
            streak += 1
        else:
            break
    return streak

user_streak = calculate_streak(st.session_state["user_name"], supabase.table("logs").select("*").execute().data)
st.markdown(f"### Connected as: **{st.session_state['user_name']}** 🔥 {user_streak} days in a row!")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", 
    "🏆 Squad Challenges", 
    "🌐 Squad Feed", 
    "✨ Insights", 
    "🎯 Personal Growth"  
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Log Your Time")
    log_date = st.date_input("Date")
    
    # שליפת נתונים קיימים לתאריך הנבחר
    existing_user_log = supabase.table("logs").select("*").eq("user", st.session_state["user_name"]).eq("date", str(log_date)).execute().data
    
    if existing_user_log:
        current_log = existing_user_log[0]
        default_hours = int(current_log.get('hours', 0))
        default_minutes = int(current_log.get('minutes', 0))
        existing_apps = current_log.get('app_data', {})
        
        # --- הפיצ'ר החדש: הוספת אפליקציות מהעבר לרשימה הנוכחית ---
        for app_name in existing_apps.keys():
            if app_name not in st.session_state["tracked_apps"]:
                st.session_state["tracked_apps"].append(app_name)
        # --------------------------------------------------------
    else:
        default_hours = 0
        default_minutes = 0
        existing_apps = {}

    # 1. קלט זמן מסך כללי
    col_h, col_m = st.columns(2)
    with col_h:
        hours_input = st.number_input("Total Hours:", min_value=0, max_value=24, step=1, value=default_hours, key=f"total_h_{log_date}")
    with col_m:
        minutes_input = st.number_input("Total Minutes:", min_value=0, max_value=59, step=1, value=default_minutes, key=f"total_m_{log_date}")
    
    st.divider()
    st.subheader("App Breakdown")
    
    if "TikTok" in st.session_state["tracked_apps"]:
        st.session_state["tracked_apps"].remove("TikTok")

    # 2. לולאת קלט לאפליקציות (כוללת כעת גם את האפליקציות שנשלפו מההיסטוריה של אותו יום)
    app_logs = {}
    for app in st.session_state["tracked_apps"]:
        st.markdown(f"**{app}**")
        
        app_total_hours = existing_apps.get(app, 0.0)
        app_default_h = int(app_total_hours)
        app_default_m = int(round((app_total_hours - app_default_h) * 60))
        
        c1, c2 = st.columns(2)
        with c1:
            h = st.number_input(f"{app} (Hours):", min_value=0, max_value=24, step=1, value=app_default_h, key=f"{app}_h_{log_date}")
        with c2:
            m = st.number_input(f"{app} (Minutes):", min_value=0, max_value=59, step=1, value=app_default_m, key=f"{app}_m_{log_date}")
        app_logs[app] = h + (m / 60)

    # 3. הוספת אפליקציה חדשה ליום הנוכחי
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
    
    # --- 5. הצגת הגרפים עם בחירת תאריך מותאמת ---
    all_logs = supabase.table("logs").select("*").execute().data

    st.subheader("Daily App Breakdown")

    if all_logs:
        available_dates = sorted(list(set([l['date'] for l in all_logs])), reverse=True)
        selected_date = st.selectbox("Select Date:", options=available_dates)
        
        logs_for_date = [l for l in all_logs if l['date'] == selected_date]

        if logs_for_date:
            for log in logs_for_date:
                user = log['user']
                tot_h = log.get('hours', 0)
                tot_m = log.get('minutes', 0)
                
                # חישוב סך כל זמן המסך שהוזן (ה-100% של הבר)
                total_screen_time = tot_h + (tot_m / 60)
                
                st.markdown(f"**{user}**")
                st.markdown(f"<h1 style='margin-top: -15px; margin-bottom: 0px;'>{tot_h}h {tot_m}m</h1>", unsafe_allow_html=True)

                app_data = log.get('app_data', {})
                
                # 1. בניית רשימת האפליקציות הרגילות שהוזנו
                chart_data = [{"app": app, "duration": duration, "user": ""} for app, duration in app_data.items() if duration > 0]
                
                # חישוב סך הזמן שנאכל על ידי אפליקציות מוגדרות
                total_apps_time = sum(duration for duration in app_data.values() if duration > 0)
                
                # 2. חישוב השארית עבור ה-Other
                other_time = total_screen_time - total_apps_time
                if other_time > 0.01:  # הגנה מפני שברים קטנים של פלואוט
                    chart_data.append({"app": "Other", "duration": other_time, "user": ""})
                
                if chart_data:
                    df_apps = pd.DataFrame(chart_data)
                    
                    # יצירת הגרף עם מיפוי צבעים ספציפי ל-Other כדי שיהיה אפור
                    fig_apps = px.bar(
                        df_apps, 
                        x="duration", 
                        y="user", 
                        color="app", 
                        orientation='h',
                        color_discrete_map={'Other': '#5a5a62'} # צבע אפור כהה ואלגנטי ל-Other
                    )
                    
                    fig_apps.update_traces(width=0.15, marker_line_width=0) 
                    
                    fig_apps.update_layout(
                        height=80, 
                        margin=dict(l=0, r=0, t=10, b=0), 
                        paper_bgcolor="rgba(0,0,0,0)", 
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=""), 
                        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=""), 
                        showlegend=True,
                        legend=dict(
                            orientation="h", 
                            yanchor="top",
                            y=-0.2,
                            xanchor="left",
                            x=0,
                            title="",
                            font=dict(size=11)
                        )
                    )
                    
                    st.plotly_chart(fig_apps, width= 'stretch', config={'displayModeBar': False})
                    
                    # שורת טקסט פירוט מתחת לבר (בלי להציג את Other בטקסט השורתי)
                    breakdown_strs = []
                    for _, row in df_apps.iterrows():
                        if row['app'] != 'Other':
                            mins = int(row['duration'] * 60)
                            breakdown_strs.append(f"{row['app']} {mins}m")
                    
                    if breakdown_strs:
                        st.markdown(f"<div style='font-size: 12px; color: #a0a0a0; margin-top: -15px;'>{' · '.join(breakdown_strs)}</div>", unsafe_allow_html=True)
                    
                st.divider() 
        else:
            st.write("No app data logged for this date.")
        
        # --- 6. הגרף הקווי (Squad Progress Chart) ---
        st.divider()
        st.subheader("Squad Progress Chart") 
        
        df = pd.DataFrame(all_logs)
        df['user'] = df['user'].str.strip()
        df['date'] = pd.to_datetime(df['date'])
        df['total_time'] = df['hours'] + (df['minutes'] / 60)
        df = df.sort_values(by=['user', 'date'])
        
        fig_line = px.line(df, x='date', y='total_time', color='user', 
                        markers=True, title="Screen Time by User (Total Hours)")
        st.plotly_chart(fig_line, width= 'stretch')

    else:
        st.info("No logs available in the system yet.")
        
# --- Function that calculates when is Sunday ---
def reset_squad_challenges():
    # 1. מחיקת כל הלוגים של השעות (כדי להחזיר את הבר ל-0)
    supabase.table("logs").delete().neq("hours", -1).execute()
    
    # 2. איפוס נקודות הלידרבורד של כולם חזרה ל-0
    users_data = supabase.table("leaderboard").select("user").execute().data
    if users_data:
        for u in users_data:
            supabase.table("leaderboard").update({"points": 0}).eq("user", u['user']).execute()

# --- TAB 2: SQUAD CHALLENGES ---
with tab2:
    st.header("🏆 Squad Challenges")
    
    today = datetime.now()
    
    # --- 1. משיכת נתונים וחישובים ראשוניים (לצורך בדיקת איפוס וצילום מצב) ---
    all_logs = supabase.table("logs").select("*").execute().data
    total_hours_this_week = sum(l.get('hours', 0) + (l.get('minutes', 0) / 60) for l in all_logs)
    
    leaderboard_data = supabase.table("leaderboard").select("*").execute().data
    weekly_squad_points = sum(user.get('points', 0) for user in leaderboard_data)
    
    SQUAD_POINTS_GOAL = 1000

    # --- 2. מנגנון איפוס אוטומטי לחלוטין (עם חגורת בטיחות נגד לולאות) ---
    if "already_reset_this_session" not in st.session_state:
        st.session_state["already_reset_this_session"] = False

    # חישוב מזהה ייחודי לשבוע (מזיזים ביום אחד כדי שיום ראשון ייחשב תחילת השבוע החדש ב-ISO)
    current_week_id = (today + timedelta(days=1)).strftime("%G-%V")
    
    # משיכת נתוני הגדרות מהטבלה החדשה
    settings_data = supabase.table("settings").select("*").execute().data
    settings_dict = {item['key']: item['value'] for item in settings_data}
    
    last_reset_week = settings_dict.get("last_reset_week", "0")
    
    # נכנסים לאיפוס רק אם השבוע התחלף ועדיין לא ניסינו בריצה הנוכחית
    if current_week_id != last_reset_week and not st.session_state["already_reset_this_session"]:
        st.session_state["already_reset_this_session"] = True # נעילת חגורת הבטיחות
        
        try:
            # א. שומרים צילום מצב של ההישגים של השבוע שהסתיים
            supabase.table("settings").upsert({"key": "last_week_hours", "value": f"{total_hours_this_week:.1f}"}).execute()
            supabase.table("settings").upsert({"key": "last_week_points", "value": str(weekly_squad_points)}).execute()
            
            # ב. מפעילים את פונקציית האיפוס שרוקנת את השעות ומאפסת נקודות
            reset_squad_challenges()
            
            # ג. מעדכנים ב-DB שביצענו איפוס עבור השבוע החדש
            supabase.table("settings").upsert({"key": "last_reset_week", "value": current_week_id}).execute()
            
            st.rerun()
        except Exception as e:
            st.error(f"Supabase Sync Error: {e}")

    # --- 3. תצוגת סיכום השבוע שחלף (מופיעה אוטומטית רק ביום ראשון) ---
    if today.weekday() == 6: # יום ראשון
        st.info("📅 **It's Sunday! Reviewing last week's performance...**")
        
        history_hours = float(settings_dict.get("last_week_hours", 0))
        history_points = int(settings_dict.get("last_week_points", 0))
        
        rec_col1, rec_col2 = st.columns(2)
        
        with rec_col1:
            st.write("### ⏱️ Screen Time Result")
            if history_hours < 100:
                st.success(f"🏆 **Success!** The squad stayed under 100 hours! Total: **{history_hours:.1f}** hours. 🎉")
            else:
                st.error(f"❌ **Failed!** The squad exceeded the limit. Total: **{history_hours:.1f}** hours. 📱")
                
        with rec_col2:
            st.write("### 🌟 Squad Points Result")
            if history_points >= SQUAD_POINTS_GOAL:
                st.success(f"🏆 **Success!** Goal crushed! The squad reached **{history_points}** / {SQUAD_POINTS_GOAL} points! 💪")
            else:
                st.error(f"❌ **Failed!** Squad reached only **{history_points}** / {SQUAD_POINTS_GOAL} points.")
        st.divider()

    # --- 4. תצוגת האתגרים הפעילים של השבוע הנוכחי ---
    st.subheader("⏱️ Weekly Screen Time Goal")
    st.progress(min(total_hours_this_week / 100, 1.0))
    st.write(f"Total Squad Screen Time: {total_hours_this_week:.1f} / 100 hours")
    
    st.divider()
    
    st.subheader("🌟 Weekly Squad Points Challenge")
    st.markdown(f"**Weekly Goal:** Reach **{SQUAD_POINTS_GOAL}** total points!")
    
    progress_pts = min(weekly_squad_points / SQUAD_POINTS_GOAL, 1.0)
    st.progress(progress_pts)
    st.write(f"Squad Points: {weekly_squad_points} / {SQUAD_POINTS_GOAL}")
    
    if progress_pts >= 1.0:
        st.success("Squad goal crushed! 🎉")
        
    st.divider()
    st.header("🏆 Leaderboard")
    leaderboard = supabase.table("leaderboard").select("*").order("points", desc=True).execute().data
    
    if leaderboard:
        # בדיקה: אם יש לפחות 3 משתמשים, נציג את הפודיום המשוגע
        if len(leaderboard) >= 3:
            first_place = leaderboard[0]
            second_place = leaderboard[1]
            third_place = leaderboard[2]
            
            # יצירת 3 עמודות שוות
            col1, col2, col3 = st.columns(3)
            
            # עמודה 1 (שמאל) - מקום שלישי (הכי נמוך, נדחף 100 פיקסלים למטה)
            with col1:
                st.markdown(f"""
                <div style='text-align: center; margin-top: 100px; padding: 20px; background-color: #CD7F32; border-radius: 10px; color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
                    <h3>🥉 3rd</h3>
                    <h4>{third_place.get('user', 'Unknown')}</h4>
                    <p><b>{third_place.get('points', 0)}</b> pts</p>
                </div>
                """, unsafe_allow_html=True)
                
            # עמודה 2 (אמצע) - מקום ראשון (הכי גבוה, לא נדחף בכלל)
            with col2:
                st.markdown(f"""
                <div style='text-align: center; margin-top: 0px; padding: 25px; background-color: #FFD700; border-radius: 10px; color: black; box-shadow: 0px 4px 12px rgba(0,0,0,0.5);'>
                    <h1>👑 1st</h1>
                    <h2>{first_place.get('user', 'Unknown')}</h2>
                    <p style='font-size: 20px;'><b>{first_place.get('points', 0)}</b> pts</p>
                </div>
                """, unsafe_allow_html=True)
                
            # עמודה 3 (ימין) - מקום שני (גובה בינוני, נדחף 50 פיקסלים למטה)
            with col3:
                st.markdown(f"""
                <div style='text-align: center; margin-top: 50px; padding: 20px; background-color: #C0C0C0; border-radius: 10px; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
                    <h2>🥈 2nd</h2>
                    <h3>{second_place.get('user', 'Unknown')}</h3>
                    <p><b>{second_place.get('points', 0)}</b> pts</p>
                </div>
                """, unsafe_allow_html=True)
                
            # בונוס: אם בעתיד יצטרפו עוד אנשים לסקוואד (מעבר לטופ 3), נציג אותם בטבלה פשוטה מתחת לפודיום
            if len(leaderboard) > 3:
                st.write("")
                st.write("### Rest of the Squad")
                st.dataframe(pd.DataFrame(leaderboard[3:]), width='stretch')
                
        else:
            # גיבוי: אם יש פחות מ-3 שחקנים רשומים כרגע, נציג טבלה רגילה כדי שלא יישבר העיצוב
            st.dataframe(pd.DataFrame(leaderboard), width='stretch')
    
    st.subheader("✅ Daily Challenges")

    current_user = st.session_state["user_name"]
    now = datetime.now(timezone.utc) # עבודה עם אזורי זמן למניעת באגים

    # שליפת כל האתגרים מהדאטה-בייס
    all_challenges = supabase.table("challenges").select("*").execute().data

    active_challenges = []
    pending_challenges = []

    # מיון ובדיקת פקיעת תוקף (הטריק העצלן)
    for ch in all_challenges:
        created_at = datetime.fromisoformat(ch['created_at'].replace('Z', '+00:00'))
        time_passed = now - created_at
        
        if ch['status'] == 'pending':
            if time_passed.total_seconds() >= 86400: # עברו 24 שעות
                yes_count = len(ch.get('votes_yes', []))
                no_count = len(ch.get('votes_no', []))
                
                if yes_count > no_count:
                    # האתגר אושר! מעדכנים סטטוס
                    supabase.table("challenges").update({"status": "approved"}).eq("id", ch['id']).execute()
                    active_challenges.append(ch)
                else:
                    # האתגר נדחה - מוחקים אותו
                    supabase.table("challenges").delete().eq("id", ch['id']).execute()
            else:
                # עדיין בתוך ה-24 שעות
                pending_challenges.append(ch)
        else:
            active_challenges.append(ch)

    # --- חלק א': אתגרים פעילים (הקוד המקורי שלך, רק על active_challenges) ---
    if active_challenges:
        with st.form("challenges_form"):
            # ... כאן נשאר הלוגיקה של הצ'קבוקסים ועדכון הניקוד שלך ...
            st.form_submit_button("Update Score")
    else:
        st.info("No active challenges yet. Go suggest one below!")

    # --- חלק ב': אתגרים בהצבעה (הפרלמנט) ---
    if pending_challenges:
        st.write("### 🗳️ Challenges Under Review (24h)")
        
        for ch in pending_challenges:
            created_at = datetime.fromisoformat(ch['created_at'].replace('Z', '+00:00'))
            time_left = timedelta(hours=24) - (now - created_at)
            minutes_left = int(time_left.total_seconds() // 60)
            
            # תצוגת כרטיס לכל אתגר בהצבעה
            with st.expander(f"🤔 {ch['task']} ({ch['points']} pts) — {minutes_left // 60}h {minutes_left % 60}m left"):
                
                # 1. מנגנון הצבעה
                yes_votes = ch.get('votes_yes', [])
                no_votes = ch.get('votes_no', [])
                
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    if st.button(f"👍 Approve ({len(yes_votes)})", key=f"yes_{ch['id']}"):
                        if current_user not in yes_votes:
                            new_yes = yes_votes + [current_user]
                            new_no = [u for u in no_votes if u != current_user] # הסרה מהצבעה הפוכה אם הייתה
                            supabase.table("challenges").update({"votes_yes": new_yes, "votes_no": new_no}).eq("id", ch['id']).execute()
                            st.rerun()
                with col_v2:
                    if st.button(f"👎 Reject ({len(no_votes)})", key=f"no_{ch['id']}"):
                        if current_user not in no_votes:
                            new_no = no_votes + [current_user]
                            new_yes = [u for u in yes_votes if u != current_user]
                            supabase.table("challenges").update({"votes_yes": new_yes, "votes_no": new_no}).eq("id", ch['id']).execute()
                            st.rerun()
                
                # 2. מנגנון עריכה (פתוח לכולם במהלך ה-24 שעות)
                st.write("---")
                with st.form(f"edit_form_{ch['id']}"):
                    edit_task = st.text_input("Edit Challenge Name", value=ch['task'])
                    edit_points = st.number_input("Edit Points", min_value=1, value=int(ch['points']))
                    if st.form_submit_button("Suggest Edit Changes"):
                        supabase.table("challenges").update({"task": edit_task, "points": edit_points}).eq("id", ch['id']).execute()
                        st.rerun()
            
    st.subheader("➕ Suggest a New Challenge")
    with st.form("add_challenge_form", clear_on_submit=True):
        new_task = st.text_input("What is the challenge?")
        new_points = st.number_input("How many points is it worth?", min_value=1, step=1)
        if st.form_submit_button("Submit Suggestion"):
            supabase.table("challenges").insert({
                "task": new_task, 
                "points": new_points, 
                "created_by": st.session_state["user_name"]
            }).execute()
            st.rerun()

# --- TAB 3: Squad Feed ---
with tab3:
    st.header("Squad Feed")
    
    with st.form("blog_form", clear_on_submit=True):
        post = st.text_area("Share a thought:")
        if st.form_submit_button("Post") and post:
            supabase.table("blog").insert({
                "user": st.session_state["user_name"], 
                "post": post, 
                "liked_by": [] 
            }).execute()
            st.rerun()

    posts_resp = supabase.table("blog").select("*").order("created_at", desc=True).execute()
    posts = posts_resp.data if posts_resp.data else []

    for p in posts:
        with st.container(border=True):
            st.markdown(f"### {p['user']}")
            st.write(p['post'])
            
            if 'created_at' in p:
                date_str = p['created_at'].replace('T', ' ').split('.')[0]
                st.caption(f"Posted at: {date_str}")
            
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
                comments_resp = supabase.table("comments").select("*").eq("post_id", p['id']).order("created_at").execute()
                comments = comments_resp.data if comments_resp.data else []
                
                with st.popover(f"💬 Comments ({len(comments)})"):
                    st.subheader("Comments")
                    if comments:
                        for c in comments:
                            st.markdown(f"**{c.get('user')}**: {c.get('comment')}")
                            if c.get("user") == st.session_state["user_name"]:
                                if st.button("🗑️", key=f"c_del_{c['id']}"):
                                    supabase.table("comments").delete().eq("id", c['id']).execute()
                                    st.rerun()
                    
                    new_comment = st.text_input("Add a comment...", key=f"input_{p['id']}")
                    if st.button("Send", key=f"btn_{p['id']}"):
                        if new_comment.strip():
                            supabase.table("comments").insert({
                                "post_id": p['id'], 
                                "user": st.session_state["user_name"], 
                                "comment": new_comment.strip()
                            }).execute()
                            st.rerun()

            with cols[2]:
                if p["user"] == st.session_state["user_name"]:
                    if st.button("🗑️ Delete Post", key=f"del_{p['id']}"):
                        supabase.table("blog").delete().eq("id", p['id']).execute()
                        st.rerun()

# --- TAB 4: INSIGHTS ---
with tab4:
    st.header("✨ Personal Insights")
    
    my_logs = [l for l in all_logs if l['user'] == st.session_state["user_name"]]
    
    if len(my_logs) >= 2:
        my_logs_sorted = sorted(my_logs, key=lambda x: x['date'], reverse=True)
        latest_log = my_logs_sorted[0]
        previous_log = my_logs_sorted[1]
        
        latest_time = latest_log.get('hours', 0) + (latest_log.get('minutes', 0) / 60)
        previous_time = previous_log.get('hours', 0) + (previous_log.get('minutes', 0) / 60)
        
        with st.container(border=True):
            st.subheader("📊 Your Trend")
            if latest_time < previous_time:
                diff = previous_time - latest_time
                percent_drop = int((diff / previous_time) * 100) if previous_time > 0 else 0
                st.success(f"Awesome! You decreased your screen time by **{percent_drop}%** compared to your last log. Keep it up!")
            elif latest_time > previous_time:
                st.warning("Your screen time has gone up slightly. Try to notice which app is taking up most of your time today.")
            else:
                st.info("Your screen time is stable. Let's try to shave off half an hour tomorrow!")

        with st.container(border=True):
            st.subheader("⏳ Time Reclaimed")
            daily_goal = 4.0 
            if latest_time < daily_goal:
                saved_time = daily_goal - latest_time
                saved_h = int(saved_time)
                saved_m = int((saved_time - saved_h) * 60)
                
                st.markdown(f"### You managed to save **{saved_h}h {saved_m}m** today! 🎉")
                st.markdown("That's definitely enough time to sit down with the maps and plan your trekking route in Norway, or jump into a focused bouldering session without distractions.")
            else:
                st.markdown("You haven't saved time below your goal (4 hours) today. Tomorrow is a new day!")
    else:
        st.info("We need at least 2 logs to start generating smart insights for you. Keep tracking!")
        
# --- TAB 5: PERSONAL GROWTH  ---
with tab5:
    st.header("🎯 Personal Challenges & Growth")
    
    # טופס הוספת אתגר
    with st.form("add_personal_challenge", clear_on_submit=True):
        st.subheader("Add a New Personal Challenge")
        c_name = st.text_input("What did you achieve today? (e.g., No Instagram for 4 hours)")
        
        # מילון רמות קושי עם הניקוד
        difficulty_map = {
            "Easy (10 pts)": 10, 
            "Medium (25 pts)": 25, 
            "Hard (50 pts)": 50, 
            "Very Hard (100 pts)": 100
        }
        difficulty_choice = st.selectbox("Select Difficulty:", options=list(difficulty_map.keys()))
        
        if st.form_submit_button("Log Challenge 🚀"):
            if c_name:
                points = difficulty_map[difficulty_choice]
                today_str = str(datetime.now().date())
                
                # הזרקה לסופאבייס לטבלה האישית
                supabase.table("personal_challenges").insert({
                    "user": st.session_state["user_name"],
                    "challenge_name": c_name,
                    "difficulty": difficulty_choice.split(" ")[0], 
                    "points": points,
                    "date": today_str
                }).execute()
                
                st.success(f"Awesome! You earned {points} points.")
                st.rerun()

    st.divider()

    # שליפת הנתונים של המשתמש הנוכחי בלבד מ-Supabase
    my_challenges = supabase.table("personal_challenges").select("*").eq("user", st.session_state["user_name"]).execute().data
    
    if my_challenges:
        df_c = pd.DataFrame(my_challenges)
        
        # 1. חישוב סך הכל נקודות אישיות לכל הזמנים
        total_points = df_c['points'].sum()
        st.metric(label="🏆 My Total Lifetime Points", value=total_points)
        
        # 2. גרף השתפרות אישית (נקודות לפי ימים)
        st.subheader("📈 My Daily Progress")
        
        daily_points = df_c.groupby('date')['points'].sum().reset_index()
        daily_points = daily_points.sort_values(by='date')
        
        fig_pts = px.bar(
            daily_points, 
            x="date", 
            y="points", 
            text="points",
            title="Points Earned Per Day",
            color_discrete_sequence=["#4CAF50"] 
        )
        
        if len(daily_points) == 1:
            fig_pts.update_traces(width=0.2, textposition='outside')
        else:
            fig_pts.update_traces(textposition='outside')
            
        fig_pts.update_layout(
            xaxis=dict(type='category'),  
            xaxis_title="", 
            yaxis_title="Points",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_pts, width= 'stretch')
        
        # 3. היסטוריית אתגרים (טבלה)
        st.subheader("📜 Challenge History")
        st.dataframe(
            df_c[['date', 'challenge_name', 'difficulty', 'points']].sort_values(by='date', ascending=False),
            width= 'stretch',
            hide_index=True
        )
    else:
        st.info("You haven't completed any personal challenges yet. Set a goal and get those points!")