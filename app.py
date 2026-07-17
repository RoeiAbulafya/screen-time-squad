import streamlit as st
import pandas as pd 
from datetime import datetime, timezone, timedelta
from supabase import create_client
import plotly.express as px
import random
import string
def generate_group_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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
active_id = st.session_state.get("active_group_id")
current_user = st.session_state["user_name"]

# 1. שליפת ה-ID של הקבוצה הפעילה (נוודא שאנחנו מנסים את המפתחות הנפוצים)
active_id = st.session_state.get("active_group_id") or st.session_state.get("selected_group_id")
current_user = st.session_state["user_name"]

st.title(f"📱 Screen Time Squad | {current_user}")

# 2. מציגים חברי קבוצה רק אם נמצאה קבוצה פעילה ב-session_state
if active_id:
    try:
        # שליפת חברי הקבוצה מה-DB לפי ה-active_id
        members_data = supabase.table("group_members").select("user").eq("group_id", active_id).execute().data
        if members_data:
            squad_users = [m['user'] for m in members_data]
            st.caption(f"Squad Members: {', '.join(squad_users)}")
        else:
            st.caption("Squad Members: No members found in this database group")
    except Exception as e:
        # הגנה במקרה של שגיאת תקשורת או מבנה טבלה
        st.caption("Squad Members: (Error loading members)")
else:
    st.caption("Squad Members: None (You are not in a squad yet)")

st.subheader(f"Connected as: {current_user} 🔥 {st.session_state.get('streak', 0)} days in a row!")

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
# --- ודא שהמשתמש מחובר ---
if "user_name" in st.session_state:
    current_user = st.session_state["user_name"]
    
    # משיכת הקבוצות שהמשתמש חבר בהן מתוך טבלת הקשר, כולל פרטי הקבוצה
    user_groups_response = supabase.table("group_members").select("group_id, groups(id, name, code)").eq("user", current_user).execute()
    user_groups_data = user_groups_response.data
    
    if user_groups_data:
        # יצירת מילון שממפה את ה-ID של הקבוצה לשם ולמספר הקוד שלה
        # חשוב: אנחנו מוודאים ש-'groups' לא ריק במקרה של חוסר סנכרון בדאטה-בייס
        group_options = {
            item['group_id']: {
                "name": item['groups']['name'],
                "code": item['groups']['code']
            }
            for item in user_groups_data if item.get('groups')
        }
        
        # כותרת הסיידבר
        st.sidebar.title("👥 My Squads")
        
        # יצירת רשימה של ה-IDs עבור ה-selectbox
        group_ids = list(group_options.keys())
        
        # תיבה נפתחת לבחירת קבוצה. ה-format_func גורם לזה להציג את השם היפה ולא את המספר ID
        selected_group_id = st.sidebar.selectbox(
            "Select Active Squad:", 
            options=group_ids, 
            format_func=lambda x: group_options[x]["name"]
        )
        
        # שומרים את ה-ID של הקבוצה הפעילה ב-Session State כדי שכל הטאבים יכירו אותו
        st.session_state["active_group_id"] = selected_group_id
        
        # שולפים את הקוד של הקבוצה הפעילה ומציגים אותו למטה בסיידבר
        active_code = group_options[selected_group_id]["code"]
        st.sidebar.info(f"🔑 Invite Code: **{active_code}**\n\nShare this with friends to let them join!")
        
    else:
        # אם המשתמש לא חבר באף קבוצה
        st.session_state["active_group_id"] = None
        st.sidebar.title("👥 My Squads")
        st.sidebar.warning("You are not part of any squad yet.")
        st.sidebar.info("Go to the 'Home' tab to create or join a squad!")
        
# --- כאן מתחילים הטאבים שלך (tab1, tab2...) ---
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
    
    # משתנים כלליים לשמוש בהמשך
    active_id = st.session_state.get("active_group_id")
    current_user = st.session_state["user_name"]
    
    # שליפת נתונים קיימים לתאריך הנבחר
    existing_user_log = supabase.table("logs").select("*").eq("user", current_user).eq("date", str(log_date)).execute().data
    
    if existing_user_log:
        current_log = existing_user_log[0]
        default_hours = int(current_log.get('hours', 0))
        default_minutes = int(current_log.get('minutes', 0))
        existing_apps = current_log.get('app_data', {})
        
        # --- הפיצ'ר החדש: הוספת אפליקציות מהעבר לרשימה הנוכחית ---
        for app_name in existing_apps.keys():
            if app_name not in st.session_state["tracked_apps"]:
                st.session_state["tracked_apps"].append(app_name)
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

    # 2. לולאת קלט לאפליקציות
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
        existing_log = supabase.table("logs").select("id").eq("user", current_user).eq("date", str(log_date)).execute().data
        if existing_log:
            supabase.table("logs").delete().eq("id", existing_log[0]['id']).execute()
            
        data_to_insert = {
            "date": str(log_date), 
            "user": current_user, 
            "hours": hours_input, 
            "minutes": minutes_input, 
            "app_data": app_logs
        }
        supabase.table("logs").insert(data_to_insert).execute()
        st.success("Log saved!")
        st.rerun()

    st.divider()
    
    # =========================================================
    # --- 5. הצגת הגרפים (מוגנים ומסוננים לפי לוגיקת קבוצות) ---
    # =========================================================
    all_logs = supabase.table("logs").select("*").execute().data

    # לוגיקת סינון: קביעה אילו משתמשים מותר לראות בגרפים
    if not active_id:
        # משתמש ללא קבוצה רואה רק את עצמו
        allowed_users = [current_user]
    else:
        # משתמש בקבוצה רואה את כל חברי הקבוצה שלו בלבד
        members_data = supabase.table("group_members").select("user").eq("group_id", active_id).execute().data
        allowed_users = [m['user'] for m in members_data] if members_data else [current_user]

    # סינון כל רשומות הדאטה-בייס רק למשתמשים המורשים
    filtered_logs = [l for l in all_logs if l['user'] in allowed_users] if all_logs else []

    st.subheader("Daily App Breakdown")

    if filtered_logs:
        available_dates = sorted(list(set([l['date'] for l in filtered_logs])), reverse=True)
        selected_date = st.selectbox("Select Date:", options=available_dates)
        
        logs_for_date = [l for l in filtered_logs if l['date'] == selected_date]

        if logs_for_date:
            for log in logs_for_date:
                user = log['user']
                tot_h = log.get('hours', 0)
                tot_m = log.get('minutes', 0)
                
                total_screen_time = tot_h + (tot_m / 60)
                
                st.markdown(f"**{user}**")
                st.markdown(f"<h1 style='margin-top: -15px; margin-bottom: 0px;'>{tot_h}h {tot_m}m</h1>", unsafe_allow_html=True)

                app_data = log.get('app_data', {})
                
                chart_data = [{"app": app, "duration": duration, "user": ""} for app, duration in app_data.items() if duration > 0]
                total_apps_time = sum(duration for duration in app_data.values() if duration > 0)
                
                other_time = total_screen_time - total_apps_time
                if other_time > 0.01:
                    chart_data.append({"app": "Other", "duration": other_time, "user": ""})
                
                if chart_data:
                    df_apps = pd.DataFrame(chart_data)
                    
                    fig_apps = px.bar(
                        df_apps, 
                        x="duration", 
                        y="user", 
                        color="app", 
                        orientation='h',
                        color_discrete_map={'Other': '#5a5a62'}
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
                    
                    st.plotly_chart(fig_apps, width='stretch', config={'displayModeBar': False})
                    
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
        
        # --- 6. הגרף הקווי (Squad Progress Chart) המסונן ---
        st.divider()
        st.subheader("Squad Progress Chart") 
        
        df = pd.DataFrame(filtered_logs)
        df['user'] = df['user'].str.strip()
        df['date'] = pd.to_datetime(df['date'])
        df['total_time'] = df['hours'] + (df['minutes'] / 60)
        df = df.sort_values(by=['user', 'date'])
        
        fig_line = px.line(df, x='date', y='total_time', color='user', 
                           markers=True, title="Screen Time by User (Total Hours)")
        st.plotly_chart(fig_line, width='stretch')

    else:
        st.info("No logs available in the system yet.")
        
    # =========================================================
    # --- 7. ניהול קבוצות (Squad Management) ---
    # =========================================================
    st.divider()
    st.subheader("🤝 Squad Management")

    col_join, col_create = st.columns(2)

    with col_join:
        with st.form("join_squad_form", clear_on_submit=True):
            st.write("**Join an Existing Squad**")
            join_code = st.text_input("Enter 6-Digit Invite Code:")
            if st.form_submit_button("Join Squad"):
                if join_code:
                    group_check = supabase.table("groups").select("id, name").eq("code", join_code.upper()).execute().data
                    if group_check:
                        new_group_id = group_check[0]['id']
                        group_name = group_check[0]['name']
                        
                        try:
                            supabase.table("group_members").insert({"group_id": new_group_id, "user": current_user}).execute()
                            supabase.table("leaderboard").insert({"group_id": new_group_id, "user": current_user, "points": 0}).execute()
                            
                            st.success(f"Successfully joined '{group_name}'! 🎉")
                            st.rerun()
                        except Exception as e:
                            st.error("You are already a member of this squad!")
                    else:
                        st.error("Invalid Code. Squad not found.")

    with col_create:
        with st.form("create_squad_form", clear_on_submit=True):
            st.write("**Create a New Squad**")
            new_squad_name = st.text_input("New Squad Name:")
            if st.form_submit_button("Create Squad"):
                if new_squad_name:
                    new_code = generate_group_code()
                    try:
                        new_group = supabase.table("groups").insert({
                            "name": new_squad_name, 
                            "code": new_code, 
                            "created_by": current_user
                        }).execute().data
                        
                        if new_group:
                            new_group_id = new_group[0]['id']
                            supabase.table("group_members").insert({"group_id": new_group_id, "user": current_user}).execute()
                            supabase.table("leaderboard").insert({"group_id": new_group_id, "user": current_user, "points": 0}).execute()
                            
                            st.success(f"Squad created! Your invite code is {new_code} 🚀")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error creating squad: {e}")
 #reset group challenge points (sunday or a button)       
def reset_squad_challenges(group_id):
    if group_id:
        # מאפסים את הניקוד ל-0 רק עבור חברי הקבוצה הספציפית הזו
        supabase.table("leaderboard").update({"points": 0}).eq("group_id", group_id).execute()

# --- TAB 2: SQUAD CHALLENGES ---
with tab2:
    active_id = st.session_state.get("active_group_id")
    
    if not active_id:
        st.warning("⚠️ You need to select or join a squad first! Go to the Dashboard tab.")
    else:
        st.header("🏆 Squad Challenges")
        
        # --- 1. משיכת חברי הקבוצה הפעילה הנוכחית ---
        members_data = supabase.table("group_members").select("user").eq("group_id", active_id).execute().data
        squad_users = [m['user'] for m in members_data] if members_data else []
        
        # --- 2. משיכת נתונים מסוננת ומסודרת לפי הקבוצה הפעילה ---
        all_logs = supabase.table("logs").select("*").execute().data
        # הלידרבורד נשלף מסונן לקבוצה הנוכחית ומסודר מהגבוה לנמוך עבור הפודיום
        leaderboard_data = supabase.table("leaderboard").select("*").eq("group_id", active_id).order("points", desc=True).execute().data
        challenges_data = supabase.table("challenges").select("*").eq("group_id", active_id).execute().data
        settings_data = supabase.table("settings").select("*").execute().data 
        
        # סינון שעות מסך: סופרים רק את הלוגים של חברי הקבוצה הזו
        group_logs = [log for log in all_logs if log['user'] in squad_users]
        
        settings_dict = {item['key']: item['value'] for item in settings_data}
        last_reset_time = settings_dict.get("last_reset_time", "1970-01-01T00:00:00")
        last_reset_clean = last_reset_time[:19].replace(" ", "T")
        
        SQUAD_POINTS_GOAL = 1000

        # --- 3. חישוב שעות מסך קבוצתיות לשבוע הנוכחי ---
        total_hours_this_week = 0
        for l in group_logs:
            c_at = l.get('created_at')
            if c_at:
                c_at_clean = c_at[:19].replace(" ", "T")
                if c_at_clean > last_reset_clean:
                    total_hours_this_week += l.get('hours', 0) + (l.get('minutes', 0) / 60)
                
        weekly_squad_points = sum(user.get('points', 0) for user in leaderboard_data)

        # --- 4. תצוגת אתגר שעות המסך השבועי ---
        st.subheader("⏱️ Weekly Screen Time Goal")
        st.progress(min(total_hours_this_week / 100, 1.0))
        st.write(f"Total Squad Screen Time: {total_hours_this_week:.1f} / 100 hours")
        
        st.divider()
        
        # --- 5. תצוגת אתגר הנקודות הקבוצתי ---
        st.subheader("🌟 Weekly Squad Points Challenge")
        st.markdown(f"**Weekly Goal:** Reach **{SQUAD_POINTS_GOAL}** total points!")
        
        progress_pts = min(weekly_squad_points / SQUAD_POINTS_GOAL, 1.0)
        st.progress(progress_pts)
        st.write(f"Squad Points: {weekly_squad_points} / {SQUAD_POINTS_GOAL}")
        
        if progress_pts >= 1.0:
            st.success("Squad goal crushed! 🎉")
            
        st.divider()
        
        # --- 6. כפתור איפוס ידני קבוצתי ---
        st.subheader("⚙️ Management")
        if st.button("🔄 Reset All Squad Challenges Now", use_container_width=True):
            try:
                now_utc_str = datetime.now(timezone.utc).isoformat()
                supabase.table("settings").upsert({"key": "last_reset_time", "value": now_utc_str}).execute()
                reset_squad_challenges(active_id)
                st.success("All challenges for this squad have been reset successfully! 🚀")
                st.rerun()
            except Exception as e:
                st.error(f"Reset failed: {e}")
                
        st.divider()

        # --- 7. הלידרבורד והפודיום המעוצב (מסונן לקבוצה) ---
        st.header("🏆 Leaderboard")
        if leaderboard_data:
            if len(leaderboard_data) >= 3:
                first_place = leaderboard_data[0]
                second_place = leaderboard_data[1]
                third_place = leaderboard_data[2]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div style='text-align: center; margin-top: 100px; padding: 20px; background-color: #CD7F32; border-radius: 10px; color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
                        <h3>🥉 3rd</h3>
                        <h4>{third_place.get('user', 'Unknown')}</h4>
                        <p><b>{third_place.get('points', 0)}</b> pts</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col2:
                    st.markdown(f"""
                    <div style='text-align: center; margin-top: 0px; padding: 25px; background-color: #FFD700; border-radius: 10px; color: black; box-shadow: 0px 4px 12px rgba(0,0,0,0.5);'>
                        <h1>👑 1st</h1>
                        <h2>{first_place.get('user', 'Unknown')}</h2>
                        <p style='font-size: 20px;'><b>{first_place.get('points', 0)}</b> pts</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col3:
                    st.markdown(f"""
                    <div style='text-align: center; margin-top: 50px; padding: 20px; background-color: #C0C0C0; border-radius: 10px; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
                        <h2>🥈 2nd</h2>
                        <h3>{second_place.get('user', 'Unknown')}</h3>
                        <p><b>{second_place.get('points', 0)}</b> pts</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                if len(leaderboard_data) > 3:
                    st.write("")
                    st.write("### Rest of the Squad")
                    st.dataframe(pd.DataFrame(leaderboard_data[3:]), width='stretch')
            else:
                st.dataframe(pd.DataFrame(leaderboard_data), width='stretch')
        
        st.divider()

        # --- 8. לוגיקת האתגרים היומיים (הפרלמנט והפעילים) ---
        st.subheader("✅ Daily Challenges")
        current_user = st.session_state["user_name"]
        now = datetime.now(timezone.utc)
        
        active_challenges = []
        pending_challenges = []
        
        for ch in challenges_data:
            created_at = datetime.fromisoformat(ch['created_at'].replace('Z', '+00:00'))
            time_passed = now - created_at
            
            if ch.get('status') == 'pending':
                yes_votes = ch.get('votes_yes') or []
                no_votes = ch.get('votes_no') or []
                yes_count = len(yes_votes)
                no_count = len(no_votes)
                
                # חישוב רוב דינמי חכם: מבוסס על כמות החברים הנוכחית בקבוצה הזו!
                required_votes = max(2, (len(squad_users) // 2) + 1)
                
                if yes_count >= required_votes:
                    supabase.table("challenges").update({"status": "approved"}).eq("id", ch['id']).execute()
                    ch['status'] = 'approved'
                    active_challenges.append(ch)
                elif time_passed.total_seconds() >= 86400:
                    if yes_count > no_count:
                        supabase.table("challenges").update({"status": "approved"}).eq("id", ch['id']).execute()
                        active_challenges.append(ch)
                    else:
                        supabase.table("challenges").delete().eq("id", ch['id']).execute()
                else:
                    pending_challenges.append(ch)
            else:
                active_challenges.append(ch)
                
        # --- חלק א': אתגרים פעילים ---
        if active_challenges:
            st.write("### 🎯 Active Challenges")
            with st.form("challenges_form"):
                newly_completed = {}
                for ch in active_challenges:
                    completed_by = ch.get('completed_by') or []
                    if current_user in completed_by:
                        st.checkbox(f"✅ {ch['task']} ({ch['points']} pts) - Completed!", value=True, disabled=True, key=f"chk_{ch['id']}")
                    else:
                        newly_completed[ch['id']] = st.checkbox(f"⬜ {ch['task']} ({ch['points']} pts)", key=f"chk_{ch['id']}")
                        
                submit_btn = st.form_submit_button("Update Score")
                if submit_btn:
                    points_to_add = 0
                    for ch_id, is_checked in newly_completed.items():
                        if is_checked:
                            ch_data = next(c for c in active_challenges if c['id'] == ch_id)
                            points_to_add += ch_data['points']
                            updated_completed_by = (ch_data.get('completed_by') or []) + [current_user]
                            supabase.table("challenges").update({"completed_by": updated_completed_by}).eq("id", ch_id).execute()
                    
                    if points_to_add > 0:
                        # עדכון ניקוד בלידרבורד תחת הקבוצה הספציפית בלבד
                        user_record = supabase.table("leaderboard").select("points").eq("group_id", active_id).eq("user", current_user).execute().data
                        if user_record:
                            current_points = user_record[0].get("points", 0)
                            supabase.table("leaderboard").update({"points": current_points + points_to_add}).eq("group_id", active_id).eq("user", current_user).execute()
                            st.success(f"Awesome! You earned {points_to_add} points! 🎉")
                            st.rerun()
                        else:
                            st.error("Could not find your user in this squad's leaderboard.")
                    else:
                        st.warning("You didn't check any new challenges.")
        else:
            st.info("No active challenges yet. Go suggest one below!")
            
        # --- חלק ב': אתגרים בהצבעה (הפרלמנט כולל טופס עריכה המקורית שלך) ---
        if pending_challenges:
            st.write("### 🗳️ Challenges Under Review (24h)")
            for ch in pending_challenges:
                created_at = datetime.fromisoformat(ch['created_at'].replace('Z', '+00:00'))
                time_left = timedelta(hours=24) - (now - created_at)
                minutes_left = int(time_left.total_seconds() // 60)
                
                with st.expander(f"🤔 {ch['task']} ({ch['points']} pts) — {max(0, minutes_left // 60)}h {max(0, minutes_left % 60)}m left"):
                    yes_votes = ch.get('votes_yes') or []
                    no_votes = ch.get('votes_no') or []
                    
                    # כפתורי הצבעה
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        if st.button(f"👍 Approve ({len(yes_votes)})", key=f"yes_{ch['id']}"):
                            if current_user not in yes_votes:
                                new_yes = yes_votes + [current_user]
                                new_no = [u for u in no_votes if u != current_user]
                                supabase.table("challenges").update({"votes_yes": new_yes, "votes_no": new_no}).eq("id", ch['id']).execute()
                                st.rerun()
                    with col_v2:
                        if st.button(f"👎 Reject ({len(no_votes)})", key=f"no_{ch['id']}"):
                            if current_user not in no_votes:
                                new_no = no_votes + [current_user]
                                new_yes = [u for u in yes_votes if u != current_user]
                                supabase.table("challenges").update({"votes_yes": new_yes, "votes_no": new_no}).eq("id", ch['id']).execute()
                                st.rerun()
                                
                    # טופס עריכה מקורי (נשמר במלואו!)
                    st.write("---")
                    with st.form(f"edit_form_{ch['id']}"):
                        edit_task = st.text_input("Edit Challenge Name", value=ch['task'])
                        edit_points = st.number_input("Edit Points", min_value=1, value=int(ch['points']))
                        if st.form_submit_button("Suggest Edit Changes"):
                            supabase.table("challenges").update({"task": edit_task, "points": edit_points}).eq("id", ch['id']).execute()
                            st.rerun()
        
        # --- חלק ג': הצעת אתגר חדש (מוצמד אוטומטית לקבוצה הפעילה) ---
        st.subheader("➕ Suggest a New Challenge")
        with st.form("add_challenge_form", clear_on_submit=True):
            new_task = st.text_input("What is the challenge?")
            new_points = st.number_input("How many points is it worth?", min_value=1, step=1)
            if st.form_submit_button("Submit Suggestion"):
                if new_task:
                    supabase.table("challenges").insert({
                        "task": new_task, 
                        "points": new_points, 
                        "created_by": current_user,
                        "group_id": active_id  # שיוך לקבוצה
                    }).execute()
                    st.rerun()

# --- TAB 3: Squad Feed ---
with tab3:
    active_id = st.session_state.get("active_group_id")
    
    if not active_id:
        st.warning("⚠️ You need to select or join a squad first! Go to the Dashboard tab.")
    else:
        st.header("Squad Feed")
        
        # --- יצירת פוסט חדש (משויך לקבוצה הפעילה) ---
        with st.form("blog_form", clear_on_submit=True):
            post = st.text_area("Share a thought:")
            if st.form_submit_button("Post") and post:
                supabase.table("blog").insert({
                    "user": st.session_state["user_name"], 
                    "post": post, 
                    "liked_by": [],
                    "group_id": active_id  # שיוך הפוסט לקבוצה הנוכחית
                }).execute()
                st.rerun()

        # --- שליפת הפוסטים - מסוננים רק לקבוצה הפעילה ---
        posts_resp = supabase.table("blog").select("*").eq("group_id", active_id).order("created_at", desc=True).execute()
        posts = posts_resp.data if posts_resp.data else []

        # --- הצגת הפוסטים ---
        for p in posts:
            with st.container(border=True):
                st.markdown(f"### {p['user']}")
                st.write(p['post'])
                
                if 'created_at' in p:
                    date_str = p['created_at'].replace('T', ' ').split('.')[0]
                    st.caption(f"Posted at: {date_str}")
                
                cols = st.columns([0.2, 0.4, 0.4])
                
                # --- מנגנון לייקים ---
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
                
                # --- מנגנון תגובות (בתוך Popover) ---
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

                # --- מחיקת פוסט ---
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