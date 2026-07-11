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
                    
                    st.plotly_chart(fig_apps, use_container_width=True, config={'displayModeBar': False})
                    
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
        st.plotly_chart(fig_line, use_container_width=True)

    else:
        st.info("No logs available in the system yet.")
        
# --- TAB 2: Squad Challenges ---
with tab2:
    st.header("🏆 Squad Challenges")
    
    SQUAD_WEEKLY_GOAL = 100.0
    
    total_squad_hours = 0
    for log in all_logs:
        total_squad_hours += log.get('hours', 0) + (log.get('minutes', 0) / 60)
        
    st.subheader("🤝 Group's Co-op Challenge:")
    st.markdown(f"**Weekly goal: Keep the total screen time under {int(SQUAD_WEEKLY_GOAL)} hours**")
    
    progress_val = min(total_squad_hours / SQUAD_WEEKLY_GOAL, 1.0)
    
    if progress_val > 0.8:
        st.warning(f"Watch out! We're getting dangerously close to our weekly limit! We're currently at {int(total_squad_hours)} hours")
        st.progress(progress_val)
    else:
        st.success(f"We're doing fine! We are currently at {int(total_squad_hours)} hours out of {int(SQUAD_WEEKLY_GOAL)}.")
        st.progress(progress_val)
    
    st.divider()
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
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                is_checked = st.checkbox(f"{ch['task']} ({ch['points']} pts)", 
                                         key=f"ch_{ch['id']}", 
                                         value=st.session_state["prev_selections"].get(ch['task'], False))
                current_selections[ch['task']] = (is_checked, ch['points'])
            
            with col2:
                if ch.get("created_by") == st.session_state["user_name"]:
                    if st.form_submit_button(f"🗑️", key=f"del_ch_{ch['id']}"):
                        supabase.table("challenges").delete().eq("id", ch['id']).execute()
                        st.rerun()

        if st.form_submit_button("Update Score"):
            user = st.session_state['user_name']
            point_change = 0
            for task, (checked, pts) in current_selections.items():
                was_checked = st.session_state["prev_selections"].get(task, False)
                if checked and not was_checked:
                    point_change += pts
                elif not checked and was_checked:
                    point_change -= pts
            
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
        
# --- TAB 5: PERSONAL GROWTH (אתגרים אישיים) ---
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
        
        fig_pts.update_traces(textposition='outside')
        fig_pts.update_layout(
            xaxis_title="", 
            yaxis_title="Points",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_pts, use_container_width=True)
        
        # 3. היסטוריית אתגרים (טבלה)
        st.subheader("📜 Challenge History")
        st.dataframe(
            df_c[['date', 'challenge_name', 'difficulty', 'points']].sort_values(by='date', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("You haven't completed any personal challenges yet. Set a goal and get those points!")