import random
import string
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client

# --- 1. הגדרת עמוד Streamlit (חייבת להיות הפקודה הראשונה באפליקציה) ---
st.set_page_config(
    page_title="Screen Time Squad",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- 2. פונקציות עזר ואזור זמן (ישראל) ---
def get_local_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


def get_local_today_str():
    return get_local_now().strftime("%Y-%m-%d")


def generate_group_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# --- 3. עיצוב כהה ואלגנטי (Sleek Dark Theme) ---
def apply_sleek_theme():
    custom_css = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    header[data-testid="stHeader"] {
        background: transparent !important;
    }   

    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarExpandButton"] {
        visibility: visible !important;
        display: flex !important;
        color: #FFFFFF !important;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        border: 1px solid #2D3243;
        background-color: #161922;
        color: #EAEEF6;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        border-color: #00C896;
        color: #00C896;
        box-shadow: 0 0 8px rgba(0, 200, 150, 0.2);
    }
    
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px;
        border: 1px solid #222735 !important;
        background-color: #12151D;
    }
    
    .stTextInput input, .stPassword input {
        border-radius: 6px;
        border: 1px solid #2A2F3E;
        background-color: #0D0F14;
        color: #EAEEF6;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


apply_sleek_theme()


# --- 4. חיבור ל-SUPABASE וטעינת COOKIES ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


supabase = init_supabase()

# טעינת מנהל העוגיות באופן ישיר
cookie_manager = stx.CookieManager()
cookies = cookie_manager.get_all()


# --- 5. SESSION RESTORE FROM COOKIE ---
if "user_name" not in st.session_state or not st.session_state["user_name"]:
    saved_access_token = cookies.get("sb_access_token")
    saved_refresh_token = cookies.get("sb_refresh_token")
    saved_username = cookies.get("saved_username")

    if saved_access_token and saved_refresh_token and saved_username:
        try:
            res = supabase.auth.set_session(
                saved_access_token, saved_refresh_token
            )
            if res and res.user:
                st.session_state["user_name"] = saved_username
                st.session_state["auth_user"] = res.user
        except Exception:
            try:
                res = supabase.auth.refresh_session(saved_refresh_token)
                if res and res.user:
                    st.session_state["user_name"] = saved_username
                    st.session_state["auth_user"] = res.user

                    expire_date = datetime.now() + timedelta(days=30)
                    cookie_manager.set(
                        "sb_access_token",
                        res.session.access_token,
                        expires_at=expire_date,
                        key="ref_acc",
                    )
                    cookie_manager.set(
                        "sb_refresh_token",
                        res.session.refresh_token,
                        expires_at=expire_date,
                        key="ref_ref",
                    )
            except Exception:
                st.session_state["user_name"] = None

if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = ["Instagram", "YouTube", "Facebook"]


# --- 6. LOGIN / SIGNUP PAGE ---
if not st.session_state.get("user_name"):

    st.title("Welcome to Screen Time Squad!")
    st.markdown(
        "Track your screen time, compete with friends, and build healthier habits"
        " together."
    )
    st.divider()

    tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

    # ---- כניסה ----
    with tab_login:
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input("Password", type="password")
            submitted_login = st.form_submit_button(
                "Sign In", type="primary", use_container_width=True
            )

        if submitted_login:
            if not login_email or not login_password:
                st.error("Please fill in all fields.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": login_email.strip(),
                        "password": login_password,
                    })
                    if res and res.user:
                        profile = (
                            supabase.table("profiles")
                            .select("username")
                            .eq("id", res.user.id)
                            .execute()
                            .data
                        )
                        username = (
                            profile[0]["username"]
                            if profile
                            else login_email.split("@")[0]
                        )

                        st.session_state["user_name"] = username
                        st.session_state["auth_user"] = res.user

                        expire_date = datetime.now() + timedelta(days=30)
                        cookie_manager.set(
                            "sb_access_token",
                            res.session.access_token,
                            expires_at=expire_date,
                            key="log_acc",
                        )
                        cookie_manager.set(
                            "sb_refresh_token",
                            res.session.refresh_token,
                            expires_at=expire_date,
                            key="log_ref",
                        )
                        cookie_manager.set(
                            "saved_username",
                            username,
                            expires_at=expire_date,
                            key="log_usr",
                        )

                        time.sleep(0.5)
                        st.rerun()
                except Exception as e:
                    err = str(e)
                    if (
                        "Invalid login" in err
                        or "invalid_credentials" in err
                    ):
                        st.error("Incorrect email or password.")
                    else:
                        st.error(f"Sign in failed: {err}")

    # ---- הרשמה ----
    with tab_signup:
        with st.form("signup_form"):
            signup_username = st.text_input(
                "Display Name (shown to your squad)"
            )
            signup_email = st.text_input("Email")
            signup_password = st.text_input(
                "Password (min. 6 characters)", type="password"
            )
            signup_confirm = st.text_input(
                "Confirm Password", type="password"
            )
            submitted_signup = st.form_submit_button(
                "Create Account", type="primary", use_container_width=True
            )

        if submitted_signup:
            if not signup_username or not signup_email or not signup_password:
                st.error("Please fill in all fields.")
            elif signup_password != signup_confirm:
                st.error("Passwords don't match.")
            elif len(signup_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                try:
                    existing = (
                        supabase.table("profiles")
                        .select("username")
                        .eq("username", signup_username.strip())
                        .execute()
                        .data
                    )
                    if existing:
                        st.error(
                            "That display name is already taken. Choose"
                            " another."
                        )
                    else:
                        res = supabase.auth.sign_up({
                            "email": signup_email.strip(),
                            "password": signup_password,
                        })
                        if res and res.user:
                            supabase.table("profiles").insert({
                                "id": res.user.id,
                                "username": signup_username.strip(),
                            }).execute()

                            st.session_state["user_name"] = (
                                signup_username.strip()
                            )
                            st.session_state["auth_user"] = res.user

                            expire_date = datetime.now() + timedelta(days=30)
                            cookie_manager.set(
                                "sb_access_token",
                                res.session.access_token,
                                expires_at=expire_date,
                                key="reg_acc",
                            )
                            cookie_manager.set(
                                "sb_refresh_token",
                                res.session.refresh_token,
                                expires_at=expire_date,
                                key="reg_ref",
                            )
                            cookie_manager.set(
                                "saved_username",
                                signup_username.strip(),
                                expires_at=expire_date,
                                key="reg_usr",
                            )

                            time.sleep(0.5)
                            st.rerun()
                except Exception as e:
                    err = str(e)
                    if (
                        "already registered" in err
                        or "already been registered" in err
                    ):
                        st.error(
                            "An account with this email already exists. Try"
                            " signing in."
                        )
                    else:
                        st.error(f"Sign up failed: {err}")

    st.stop()


# --- LOGOUT FUNCTION ---
def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    cookie_manager.delete("sb_access_token", key="del_acc")
    cookie_manager.delete("sb_refresh_token", key="del_ref")
    cookie_manager.delete("saved_username", key="del_usr")

    for key in ["user_name", "auth_user", "active_group_id", "tracked_apps"]:
        st.session_state.pop(key, None)

    time.sleep(0.5)
    st.rerun()


# --- TOP BAR ---
active_id = st.session_state.get(
    "active_group_id"
) or st.session_state.get("selected_group_id")
current_user = st.session_state["user_name"]

st.title(f"Screen Time Squad | {current_user}")

if active_id:
    try:
        members_data = (
            supabase.table("group_members")
            .select("user")
            .eq("group_id", active_id)
            .execute()
            .data
        )
        if members_data:
            squad_users = [m["user"] for m in members_data]
            st.caption(f"Squad Members: {', '.join(squad_users)}")
        else:
            st.caption(
                "Squad Members: No members found in this database group"
            )
    except Exception:
        st.caption("Squad Members: (Error loading members)")
else:
    st.caption("Squad Members: None (You are not in a squad yet)")


# --- STREAK LOGIC (לפי שעון ישראל) ---
def calculate_streak(user_name, all_logs):
    user_dates = sorted(
        [log["date"] for log in all_logs if log["user"] == user_name],
        reverse=True,
    )
    if not user_dates:
        return 0

    streak = 0
    current_date = get_local_now().date()

    for log_date_str in user_dates:
        log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()
        if (current_date - log_date).days == streak or (
            current_date - log_date
        ).days == (streak + 1):
            streak += 1
        else:
            break
    return streak


user_streak = calculate_streak(
    current_user, supabase.table("logs").select("*").execute().data
)
st.markdown(f"🔥 **{user_streak} days in a row!** Keep it up!")

# משיכת הקבוצות שהמשתמש חבר בהן
user_groups_response = (
    supabase.table("group_members")
    .select("group_id, groups(id, name, code)")
    .eq("user", current_user)
    .execute()
)
user_groups_data = user_groups_response.data
group_options = {}
if user_groups_data:
    group_options = {
        item["group_id"]: {
            "name": item["groups"]["name"],
            "code": item["groups"]["code"],
        }
        for item in user_groups_data
        if item.get("groups")
    }

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        "<h3 style='margin-bottom: 2px;'>SQUADS MANAGEMENT</h3>",
        unsafe_allow_html=True,
    )
    st.caption(f"Logged in as **{current_user}**")

    st.write("")
    if st.button("Sign Out", key="sidebar_signout", use_container_width=True):
        logout()

    st.divider()

    if group_options:
        group_ids = list(group_options.keys())
        default_index = 0
        if (
            "active_group_id" in st.session_state
            and st.session_state["active_group_id"] in group_ids
        ):
            default_index = group_ids.index(st.session_state["active_group_id"])

        selected_group_id = st.selectbox(
            "Active Squad",
            options=group_ids,
            index=default_index,
            format_func=lambda x: group_options[x]["name"],
        )

        if st.session_state.get("active_group_id") != selected_group_id:
            st.session_state["active_group_id"] = selected_group_id
            st.rerun()

        active_code = group_options[selected_group_id]["code"]

        with st.container(border=True):
            st.caption("SQUAD INVITE CODE")
            st.code(active_code, language=None)

            if st.button(
                "Leave Squad", key="btn_leave_squad", use_container_width=True
            ):
                try:
                    supabase.table("group_members").delete().eq(
                        "group_id", selected_group_id
                    ).eq("user", current_user).execute()
                    supabase.table("leaderboard").delete().eq(
                        "group_id", selected_group_id
                    ).eq("user", current_user).execute()
                    st.success("Left squad successfully.")
                    st.session_state["active_group_id"] = None
                    st.rerun()
                except Exception:
                    st.error("Error leaving squad.")

        st.divider()
    else:
        st.info("You are not part of any squad yet.")
        st.divider()

    with st.expander("Manage Squads"):
        tab_choice = st.radio(
            "Action",
            ["Join Squad", "Create Squad"],
            label_visibility="collapsed",
        )
        st.write("")

        if tab_choice == "Join Squad":
            with st.form("join_squad_form", clear_on_submit=True):
                join_code = st.text_input(
                    "Enter 6-Digit Code", placeholder="e.g. AB12CD"
                )
                submit_join = st.form_submit_button(
                    "Join Squad", type="primary", use_container_width=True
                )

                if submit_join and join_code:
                    group_data = (
                        supabase.table("groups")
                        .select("id")
                        .eq("code", join_code.strip().upper())
                        .execute()
                        .data
                    )
                    if group_data:
                        g_id = group_data[0]["id"]
                        existing_member = (
                            supabase.table("group_members")
                            .select("*")
                            .eq("group_id", g_id)
                            .eq("user", current_user)
                            .execute()
                            .data
                        )
                        if not existing_member:
                            supabase.table("group_members").insert({
                                "group_id": g_id,
                                "user": current_user,
                            }).execute()
                            supabase.table("leaderboard").insert({
                                "group_id": g_id,
                                "user": current_user,
                                "points": 0,
                            }).execute()
                            st.success("Successfully joined squad.")
                            st.rerun()
                        else:
                            st.warning("You are already in this squad.")
                    else:
                        st.error("Invalid squad code.")

        else:
            with st.form("create_squad_form", clear_on_submit=True):
                new_name = st.text_input(
                    "New Squad Name", placeholder="e.g. Focus Masters"
                )
                submit_create = st.form_submit_button(
                    "Create Squad", type="primary", use_container_width=True
                )

                if submit_create and new_name:
                    new_code = generate_group_code()
                    new_g = (
                        supabase.table("groups")
                        .insert({
                            "name": new_name.strip(),
                            "code": new_code,
                            "created_by": current_user,
                        })
                        .execute()
                        .data
                    )

                    if new_g:
                        g_id = new_g[0]["id"]
                        supabase.table("group_members").insert({
                            "group_id": g_id,
                            "user": current_user,
                        }).execute()
                        supabase.table("leaderboard").insert({
                            "group_id": g_id,
                            "user": current_user,
                            "points": 0,
                        }).execute()
                        st.success(f"Squad created! Code: {new_code}")
                        st.rerun()


# --- TABS NAVIGATION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard",
    "Squad Challenges",
    "Squad Feed",
    "Insights",
    "Personal Growth",
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("LOG YOUR TIME")
    st.caption("Track your daily digital habits and monitor your screen time")
    st.divider()

    # דיפולט לתאריך מקומי של ישראל
    log_date = st.date_input("Select Date", value=get_local_now().date())

    active_id = st.session_state.get("active_group_id")
    current_user = st.session_state["user_name"]

    existing_user_log = (
        supabase.table("logs")
        .select("*")
        .eq("user", current_user)
        .eq("date", str(log_date))
        .execute()
        .data
    )

    if existing_user_log:
        current_log = existing_user_log[0]
        default_hours = int(current_log.get("hours", 0))
        default_minutes = int(current_log.get("minutes", 0))
        existing_apps = current_log.get("app_data", {})

        for app_name in existing_apps.keys():
            if app_name not in st.session_state["tracked_apps"]:
                st.session_state["tracked_apps"].append(app_name)
    else:
        default_hours = 0
        default_minutes = 0
        existing_apps = {}

    with st.container(border=True):
        st.markdown("**TOTAL SCREEN TIME**")
        col_h, col_m = st.columns(2)
        with col_h:
            hours_input = st.number_input(
                "Total Hours",
                min_value=0,
                max_value=24,
                step=1,
                value=default_hours,
                key=f"total_h_{log_date}",
            )
        with col_m:
            minutes_input = st.number_input(
                "Total Minutes",
                min_value=0,
                max_value=59,
                step=1,
                value=default_minutes,
                key=f"total_m_{log_date}",
            )

        st.write("")
        st.markdown("**APP BREAKDOWN**")

        if "TikTok" in st.session_state["tracked_apps"]:
            st.session_state["tracked_apps"].remove("TikTok")

        app_logs = {}
        for app in st.session_state["tracked_apps"]:
            app_total_hours = existing_apps.get(app, 0.0)
            app_default_h = int(app_total_hours)
            app_default_m = int(round((app_total_hours - app_default_h) * 60))

            col_name, col_app_h, col_app_m = st.columns([2, 1, 1])
            with col_name:
                st.markdown(
                    f"<div style='padding-top: 35px; font-weight:"
                    f" 500;'>{app}</div>",
                    unsafe_allow_html=True,
                )
            with col_app_h:
                h = st.number_input(
                    "Hours",
                    min_value=0,
                    max_value=24,
                    step=1,
                    value=app_default_h,
                    key=f"{app}_h_{log_date}",
                )
            with col_app_m:
                m = st.number_input(
                    "Minutes",
                    min_value=0,
                    max_value=59,
                    step=1,
                    value=app_default_m,
                    key=f"{app}_m_{log_date}",
                )

            app_logs[app] = h + (m / 60)

        st.divider()

        st.caption("ADD TRACKED APP")
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            new_app = st.text_input(
                "New App Name",
                label_visibility="collapsed",
                placeholder="Enter app name (e.g. Instagram, YouTube)...",
            )
        with col_btn:
            if st.button("Add App", use_container_width=True):
                if (
                    new_app
                    and new_app not in st.session_state["tracked_apps"]
                ):
                    st.session_state["tracked_apps"].append(new_app)
                    st.rerun()

    st.write("")

    if st.button("Save Daily Log", type="primary", use_container_width=True):
        existing_log = (
            supabase.table("logs")
            .select("id")
            .eq("user", current_user)
            .eq("date", str(log_date))
            .execute()
            .data
        )
        if existing_log:
            supabase.table("logs").delete().eq(
                "id", existing_log[0]["id"]
            ).execute()

        data_to_insert = {
            "date": str(log_date),
            "user": current_user,
            "hours": hours_input,
            "minutes": minutes_input,
            "app_data": app_logs,
            "created_at": get_local_now().isoformat(),  # שמירה עם שעון ישראל
        }
        supabase.table("logs").insert(data_to_insert).execute()
        st.success("Log saved successfully!")
        st.rerun()

    st.divider()

    # --- הצגת הגרפים ---
    all_logs = supabase.table("logs").select("*").execute().data

    if not active_id:
        allowed_users = [current_user]
    else:
        members_data = (
            supabase.table("group_members")
            .select("user")
            .eq("group_id", active_id)
            .execute()
            .data
        )
        allowed_users = (
            [m["user"] for m in members_data]
            if members_data
            else [current_user]
        )

    filtered_logs = (
        [l for l in all_logs if l["user"] in allowed_users] if all_logs else []
    )

    st.subheader("DAILY BREAKDOWN")
    st.caption("Compare app usage distribution among your squad")

    if filtered_logs:
        available_dates = sorted(
            list(set([l["date"] for l in filtered_logs])), reverse=True
        )
        selected_date = st.selectbox(
            "Select Date for Analysis", options=available_dates
        )

        logs_for_date = [
            l for l in filtered_logs if l["date"] == selected_date
        ]

        if logs_for_date:
            for log in logs_for_date:
                user = log["user"]
                tot_h = log.get("hours", 0)
                tot_m = log.get("minutes", 0)
                total_screen_time = tot_h + (tot_m / 60)

                with st.container(border=True):
                    col_u1, col_u2 = st.columns([1, 4])
                    with col_u1:
                        st.caption(f"USER: {user.upper()}")
                        st.metric(
                            label="Total Time", value=f"{tot_h}h {tot_m}m"
                        )

                    with col_u2:
                        app_data = log.get("app_data", {})
                        chart_data = [
                            {"app": app, "duration": duration, "user": ""}
                            for app, duration in app_data.items()
                            if duration > 0
                        ]
                        total_apps_time = sum(
                            duration
                            for duration in app_data.values()
                            if duration > 0
                        )

                        other_time = total_screen_time - total_apps_time
                        if other_time > 0.01:
                            chart_data.append({
                                "app": "Other",
                                "duration": other_time,
                                "user": "",
                            })

                        if chart_data:
                            df_apps = pd.DataFrame(chart_data)

                            fig_apps = px.bar(
                                df_apps,
                                x="duration",
                                y="user",
                                color="app",
                                orientation="h",
                                color_discrete_map={"Other": "#3A3F50"},
                            )

                            fig_apps.update_traces(
                                width=0.3, marker_line_width=0
                            )
                            fig_apps.update_layout(
                                height=80,
                                margin=dict(l=0, r=0, t=0, b=0),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                xaxis=dict(
                                    showgrid=False,
                                    showticklabels=False,
                                    zeroline=False,
                                    title="",
                                ),
                                yaxis=dict(
                                    showgrid=False,
                                    showticklabels=False,
                                    zeroline=False,
                                    title="",
                                ),
                                showlegend=True,
                                legend=dict(
                                    orientation="h",
                                    yanchor="top",
                                    y=-0.5,
                                    xanchor="left",
                                    x=0,
                                    title="",
                                    font=dict(size=11, color="#EAEEF6"),
                                ),
                            )

                            st.plotly_chart(
                                fig_apps,
                                use_container_width=True,
                                config={"displayModeBar": False},
                            )

                            breakdown_strs = []
                            for _, row in df_apps.iterrows():
                                if row["app"] != "Other":
                                    mins = int(row["duration"] * 60)
                                    breakdown_strs.append(
                                        f"{row['app']} {mins}m"
                                    )

                            if breakdown_strs:
                                st.markdown(
                                    "<div style='font-size: 12px; color:"
                                    " #8A92A6; margin-top:"
                                    f" -10px;'>{' · '.join(breakdown_strs)}</div>",
                                    unsafe_allow_html=True,
                                )
        else:
            st.info("No app data logged for this date.")

        # --- 6. הגרף הקווי (Squad Progress Chart) עם סינון 7 ימים ---
        st.write("")
        st.subheader("SQUAD PROGRESS")
        st.caption("Screen time trends over time")

        df = pd.DataFrame(filtered_logs)
        df["user"] = df["user"].str.strip()
        df["date"] = pd.to_datetime(df["date"])
        df["total_time"] = df["hours"] + (df["minutes"] / 60)
        df = df.sort_values(by=["user", "date"])

        time_frame = st.radio(
            "Select range:",
            options=["Last 7 Days", "Last 14 Days", "All Time"],
            horizontal=True,
            key="squad_progress_range",
        )

        max_date = df["date"].max()

        if time_frame == "Last 7 Days":
            df_chart = df[df["date"] >= (max_date - pd.Timedelta(days=6))]
        elif time_frame == "Last 14 Days":
            df_chart = df[df["date"] >= (max_date - pd.Timedelta(days=13))]
        else:
            df_chart = df

        fig_line = px.line(
            df_chart,
            x="date",
            y="total_time",
            color="user",
            markers=True,
            template="plotly_dark",
        )

        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(22, 25, 34, 0.5)",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Date",
            yaxis_title="Total Hours",
            legend_title="Squad Members",
        )
        fig_line.update_xaxes(
            showgrid=True, gridwidth=1, gridcolor="#222735"
        )
        fig_line.update_yaxes(
            showgrid=True, gridwidth=1, gridcolor="#222735"
        )

        st.plotly_chart(fig_line, use_container_width=True)


def reset_squad_challenges(group_id):
    if group_id:
        supabase.table("leaderboard").update({"points": 0}).eq(
            "group_id", group_id
        ).execute()


# --- TAB 2: SQUAD CHALLENGES ---
with tab2:
    active_id = st.session_state.get("active_group_id")

    if not active_id:
        st.warning(
            "You need to select or join a squad first. Please navigate to the"
            " Dashboard tab."
        )
    else:
        st.subheader("SQUAD CHALLENGES")
        st.caption(
            "Compete with your team, complete daily tasks, and climb the"
            " leaderboard"
        )
        st.divider()

        members_data = (
            supabase.table("group_members")
            .select("user")
            .eq("group_id", active_id)
            .execute()
            .data
        )
        squad_users = [m["user"] for m in members_data] if members_data else []

        all_logs = supabase.table("logs").select("*").execute().data
        leaderboard_data = (
            supabase.table("leaderboard")
            .select("*")
            .eq("group_id", active_id)
            .order("points", desc=True)
            .execute()
            .data
        )
        challenges_data = (
            supabase.table("challenges")
            .select("*")
            .eq("group_id", active_id)
            .execute()
            .data
        )
        settings_data = supabase.table("settings").select("*").execute().data

        group_logs = [log for log in all_logs if log["user"] in squad_users]

        settings_dict = {item["key"]: item["value"] for item in settings_data}
        last_reset_time = settings_dict.get(
            "last_reset_time", "1970-01-01T00:00:00"
        )
        last_reset_clean = last_reset_time[:19].replace(" ", "T")

        SQUAD_POINTS_GOAL = 1000

        total_hours_this_week = 0
        for l in group_logs:
            c_at = l.get("created_at")
            if c_at:
                c_at_clean = c_at[:19].replace(" ", "T")
                if c_at_clean > last_reset_clean:
                    total_hours_this_week += l.get("hours", 0) + (
                        l.get("minutes", 0) / 60
                    )

        weekly_squad_points = sum(
            user.get("points", 0) for user in leaderboard_data
        )

        with st.container(border=True):
            col_goal1, col_goal2 = st.columns(2)

            with col_goal1:
                st.caption("WEEKLY SCREEN TIME GOAL")
                st.metric(
                    label="Squad Total",
                    value=f"{total_hours_this_week:.1f}h",
                    delta="Goal: 100h",
                    delta_color="off",
                )
                st.progress(min(total_hours_this_week / 100, 1.0))

            with col_goal2:
                st.caption("WEEKLY POINTS CHALLENGE")
                st.metric(
                    label="Squad Points",
                    value=f"{weekly_squad_points}",
                    delta=f"Goal: {SQUAD_POINTS_GOAL}",
                    delta_color="off",
                )
                progress_pts = min(
                    weekly_squad_points / SQUAD_POINTS_GOAL, 1.0
                )
                st.progress(progress_pts)

        if progress_pts >= 1.0:
            st.success("Squad points goal successfully achieved!")

        st.write("")

        st.subheader("LEADERBOARD")
        st.caption("Current squad rankings and top performers")

        if leaderboard_data:
            if len(leaderboard_data) >= 3:
                first_place = leaderboard_data[0]
                second_place = leaderboard_data[1]
                third_place = leaderboard_data[2]

                col_2nd, col_1st, col_3rd = st.columns([1, 1.1, 1])

                with col_1st:
                    with st.container(border=True):
                        st.markdown(
                            "<div style='text-align: center; color: #E5C07B;"
                            " font-weight: 600; font-size: 14px;"
                            " letter-spacing: 1px;'>1ST PLACE</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<div style='text-align: center; font-size: 22px;"
                            " font-weight: bold; margin: 10px"
                            f" 0;'>{first_place.get('user', 'Unknown')}</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            "<div style='text-align: center; color: #8A92A6;"
                            f" font-size: 16px;'><b>{first_place.get('points', 0)}</b>"
                            " pts</div>",
                            unsafe_allow_html=True,
                        )

                with col_2nd:
                    with st.container(border=True):
                        st.markdown(
                            "<div style='text-align: center; color: #ABB2BF;"
                            " font-weight: 600; font-size: 13px;"
                            " letter-spacing: 1px;'>2ND PLACE</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<div style='text-align: center; font-size: 18px;"
                            " font-weight: bold; margin: 10px"
                            f" 0;'>{second_place.get('user', 'Unknown')}</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            "<div style='text-align: center; color: #8A92A6;"
                            f" font-size: 14px;'><b>{second_place.get('points', 0)}</b>"
                            " pts</div>",
                            unsafe_allow_html=True,
                        )

                with col_3rd:
                    with st.container(border=True):
                        st.markdown(
                            "<div style='text-align: center; color: #D19A66;"
                            " font-weight: 600; font-size: 13px;"
                            " letter-spacing: 1px;'>3RD PLACE</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<div style='text-align: center; font-size: 18px;"
                            " font-weight: bold; margin: 10px"
                            f" 0;'>{third_place.get('user', 'Unknown')}</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            "<div style='text-align: center; color: #8A92A6;"
                            f" font-size: 14px;'><b>{third_place.get('points', 0)}</b>"
                            " pts</div>",
                            unsafe_allow_html=True,
                        )

                if len(leaderboard_data) > 3:
                    st.write("")
                    st.caption("OTHER SQUAD MEMBERS")
                    st.dataframe(
                        pd.DataFrame(leaderboard_data[3:]),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.dataframe(
                    pd.DataFrame(leaderboard_data),
                    use_container_width=True,
                    hide_index=True,
                )

        st.divider()

        st.subheader("DAILY CHALLENGES")
        st.caption("Complete approved tasks to earn points for your squad")

        current_user = st.session_state["user_name"]
        now = datetime.now(timezone.utc)

        active_challenges = []
        pending_challenges = []

        for ch in challenges_data:
            created_at = datetime.fromisoformat(
                ch["created_at"].replace("Z", "+00:00")
            )
            time_passed = now - created_at

            if ch.get("status") == "pending":
                yes_votes = ch.get("votes_yes") or []
                no_votes = ch.get("votes_no") or []
                yes_count = len(yes_votes)
                no_count = len(no_votes)

                required_votes = max(2, (len(squad_users) // 2) + 1)

                if yes_count >= required_votes:
                    supabase.table("challenges").update(
                        {"status": "approved"}
                    ).eq("id", ch["id"]).execute()
                    ch["status"] = "approved"
                    active_challenges.append(ch)
                elif time_passed.total_seconds() >= 86400:
                    if yes_count > no_count:
                        supabase.table("challenges").update(
                            {"status": "approved"}
                        ).eq("id", ch["id"]).execute()
                        active_challenges.append(ch)
                    else:
                        supabase.table("challenges").delete().eq(
                            "id", ch["id"]
                        ).execute()
                else:
                    pending_challenges.append(ch)
            else:
                active_challenges.append(ch)

        if active_challenges:
            today_str = get_local_today_str()
            completions_response = (
                supabase.table("challenge_completions")
                .select("challenge_name")
                .eq("user_name", current_user)
                .eq("completion_date", today_str)
                .execute()
            )
            completed_today_ids = [
                record["challenge_name"] for record in completions_response.data
            ]

            with st.container(border=True):
                with st.form("challenges_form"):
                    newly_completed = {}
                    for ch in active_challenges:
                        if ch["id"] in completed_today_ids:
                            st.checkbox(
                                f"[COMPLETED] {ch['task']} ({ch['points']} pts)",
                                value=True,
                                disabled=True,
                                key=f"chk_{ch['id']}",
                            )
                        else:
                            newly_completed[ch["id"]] = st.checkbox(
                                f"{ch['task']} ({ch['points']} pts)",
                                key=f"chk_{ch['id']}",
                            )

                    st.write("")
                    submit_btn = st.form_submit_button(
                        "Update My Score",
                        type="primary",
                        use_container_width=True,
                    )

                    if submit_btn:
                        points_to_add = 0
                        for ch_id, is_checked in newly_completed.items():
                            if is_checked:
                                ch_data = next(
                                    c for c in active_challenges if c["id"] == ch_id
                                )
                                points_to_add += ch_data["points"]

                                data_to_insert = {
                                    "user_name": current_user,
                                    "challenge_name": ch_id,
                                    "completion_date": today_str,
                                    "points": ch_data["points"],
                                }
                                supabase.table("challenge_completions").insert(
                                    data_to_insert
                                ).execute()

                        if points_to_add > 0:
                            user_record = (
                                supabase.table("leaderboard")
                                .select("points")
                                .eq("group_id", active_id)
                                .eq("user", current_user)
                                .execute()
                                .data
                            )
                            if user_record:
                                current_points = user_record[0].get("points", 0)
                                supabase.table("leaderboard").update({
                                    "points": current_points + points_to_add
                                }).eq("group_id", active_id).eq(
                                    "user", current_user
                                ).execute()
                                st.success(
                                    f"Score updated! You earned {points_to_add}"
                                    " points."
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "Could not find your user in this squad's"
                                    " leaderboard."
                                )
                        else:
                            st.warning("No new challenges were selected.")
        else:
            st.info("No active challenges available. Suggest a new one below.")

        st.write("")

        if pending_challenges:
            st.caption("CHALLENGES UNDER REVIEW (24H VOTING WINDOW)")
            for ch in pending_challenges:
                created_at = datetime.fromisoformat(
                    ch["created_at"].replace("Z", "+00:00")
                )
                time_left = timedelta(hours=24) - (now - created_at)
                minutes_left = int(time_left.total_seconds() // 60)

                with st.expander(
                    f"PROPOSED: {ch['task']} ({ch['points']} pts) —"
                    f" {max(0, minutes_left // 60)}h"
                    f" {max(0, minutes_left % 60)}m remaining"
                ):
                    yes_votes = ch.get("votes_yes") or []
                    no_votes = ch.get("votes_no") or []

                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        if st.button(
                            f"Approve ({len(yes_votes)})",
                            key=f"yes_{ch['id']}",
                            use_container_width=True,
                        ):
                            if current_user not in yes_votes:
                                new_yes = yes_votes + [current_user]
                                new_no = [
                                    u for u in no_votes if u != current_user
                                ]
                                supabase.table("challenges").update({
                                    "votes_yes": new_yes,
                                    "votes_no": new_no,
                                }).eq("id", ch["id"]).execute()
                                st.rerun()
                    with col_v2:
                        if st.button(
                            f"Reject ({len(no_votes)})",
                            key=f"no_{ch['id']}",
                            use_container_width=True,
                        ):
                            if current_user not in no_votes:
                                new_no = no_votes + [current_user]
                                new_yes = [
                                    u for u in yes_votes if u != current_user
                                ]
                                supabase.table("challenges").update({
                                    "votes_yes": new_yes,
                                    "votes_no": new_no,
                                }).eq("id", ch["id"]).execute()
                                st.rerun()

                    st.divider()
                    st.caption("SUGGEST MODIFICATIONS")
                    with st.form(f"edit_form_{ch['id']}"):
                        col_e1, col_e2 = st.columns([3, 1])
                        with col_e1:
                            edit_task = st.text_input(
                                "Challenge Name",
                                value=ch["task"],
                                label_visibility="collapsed",
                            )
                        with col_e2:
                            edit_points = st.number_input(
                                "Points",
                                min_value=1,
                                value=int(ch["points"]),
                                label_visibility="collapsed",
                            )

                        if st.form_submit_button(
                            "Update Suggestion", use_container_width=True
                        ):
                            supabase.table("challenges").update({
                                "task": edit_task,
                                "points": edit_points,
                            }).eq("id", ch["id"]).execute()
                            st.rerun()

        st.write("")

        with st.container(border=True):
            st.caption("SUGGEST A NEW CHALLENGE")
            with st.form("add_challenge_form", clear_on_submit=True):
                col_t, col_p, col_btn = st.columns([3, 1, 1.2])
                with col_t:
                    new_task = st.text_input(
                        "Task Description",
                        placeholder="e.g., No social media after 10 PM...",
                        label_visibility="collapsed",
                    )
                with col_p:
                    new_points = st.number_input(
                        "Points Worth",
                        min_value=1,
                        step=1,
                        value=10,
                        label_visibility="collapsed",
                    )
                with col_btn:
                    submitted = st.form_submit_button(
                        "Submit Suggestion", use_container_width=True
                    )

                if submitted:
                    if new_task:
                        supabase.table("challenges").insert({
                            "task": new_task,
                            "points": new_points,
                            "created_by": current_user,
                            "group_id": active_id,
                        }).execute()
                        st.rerun()

        st.divider()

        with st.expander("SQUAD MANAGEMENT & RESET"):
            st.caption(
                "Warning: Resetting challenges will clear the progress for"
                " the current week."
            )
            if st.button("Reset All Squad Challenges", use_container_width=True):
                try:
                    now_utc_str = datetime.now(timezone.utc).isoformat()
                    supabase.table("settings").upsert({
                        "key": "last_reset_time",
                        "value": now_utc_str,
                    }).execute()
                    reset_squad_challenges(active_id)
                    st.success(
                        "All challenges for this squad have been reset"
                        " successfully."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Reset failed: {e}")

# --- TAB 3: Squad Feed ---
with tab3:
    active_id = st.session_state.get("active_group_id")

    if not active_id:
        st.warning(
            "You need to select or join a squad first. Please navigate to the"
            " Dashboard tab."
        )
    else:
        st.subheader("SQUAD FEED")
        st.caption(
            "Share updates, thoughts, and stay connected with your squad"
            " members"
        )
        st.divider()

        with st.container(border=True):
            st.caption("CREATE NEW POST")
            with st.form("blog_form", clear_on_submit=True):
                post = st.text_area(
                    "Share a thought",
                    placeholder=(
                        "What's on your mind? Share your progress or"
                        " thoughts..."
                    ),
                    label_visibility="collapsed",
                )

                col_spacer, col_btn = st.columns([4, 1])
                with col_btn:
                    submitted = st.form_submit_button(
                        "Publish Post", type="primary", use_container_width=True
                    )

                if submitted and post:
                    supabase.table("blog").insert({
                        "user": st.session_state["user_name"],
                        "post": post,
                        "liked_by": [],
                        "group_id": active_id,
                    }).execute()
                    st.rerun()

        st.write("")

        posts_resp = (
            supabase.table("blog")
            .select("*")
            .eq("group_id", active_id)
            .order("created_at", desc=True)
            .execute()
        )
        posts = posts_resp.data if posts_resp.data else []

        if posts:
            for p in posts:
                with st.container(border=True):
                    col_user, col_date = st.columns([2, 1])
                    with col_user:
                        st.markdown(
                            f"<div style='font-size: 16px; font-weight: 600;"
                            f" color: #E5C07B;'>{p['user']}</div>",
                            unsafe_allow_html=True,
                        )
                    with col_date:
                        if "created_at" in p:
                            date_str = (
                                p["created_at"]
                                .replace("T", " ")
                                .split(".")[0]
                            )
                            st.markdown(
                                "<div style='text-align: right; font-size:"
                                f" 12px; color: #8A92A6;'>{date_str}</div>",
                                unsafe_allow_html=True,
                            )

                    st.markdown(
                        "<div style='margin: 15px 0; font-size: 15px;"
                        f" line-height: 1.5;'>{p['post']}</div>",
                        unsafe_allow_html=True,
                    )
                    st.divider()

                    cols = st.columns([1.2, 1.5, 1.5, 2])

                    liked_by = (
                        p.get("liked_by") if p.get("liked_by") is not None else []
                    )
                    is_liked = st.session_state["user_name"] in liked_by

                    with cols[0]:
                        like_label = (
                            f"Liked ({len(liked_by)})"
                            if is_liked
                            else f"Like ({len(liked_by)})"
                        )
                        btn_type = "primary" if is_liked else "secondary"

                        if st.button(
                            like_label,
                            key=f"post_like_{p['id']}",
                            type=btn_type,
                            use_container_width=True,
                        ):
                            if is_liked:
                                liked_by.remove(st.session_state["user_name"])
                            else:
                                liked_by.append(st.session_state["user_name"])
                            supabase.table("blog").update(
                                {"liked_by": liked_by}
                            ).eq("id", p["id"]).execute()
                            st.rerun()

                    with cols[1]:
                        comments_resp = (
                            supabase.table("comments")
                            .select("*")
                            .eq("post_id", p["id"])
                            .order("created_at")
                            .execute()
                        )
                        comments = (
                            comments_resp.data if comments_resp.data else []
                        )

                        with st.popover(
                            f"Comments ({len(comments)})",
                            use_container_width=True,
                        ):
                            st.markdown("**DISCUSSION**")
                            st.divider()

                            if comments:
                                for c in comments:
                                    col_comm_text, col_comm_del = st.columns([
                                        4,
                                        1,
                                    ])
                                    with col_comm_text:
                                        st.markdown(
                                            "<div style='font-size:"
                                            f" 13px;'><b>{c.get('user')}:</b>"
                                            f" {c.get('comment')}</div>",
                                            unsafe_allow_html=True,
                                        )
                                    with col_comm_del:
                                        if (
                                            c.get("user")
                                            == st.session_state["user_name"]
                                        ):
                                            if st.button(
                                                "Remove",
                                                key=f"c_del_{c['id']}",
                                                use_container_width=True,
                                            ):
                                                supabase.table(
                                                    "comments"
                                                ).delete().eq(
                                                    "id", c["id"]
                                                ).execute()
                                                st.rerun()
                                    st.write("")
                            else:
                                st.caption(
                                    "No comments yet. Be the first to reply."
                                )

                            st.write("")
                            new_comment = st.text_input(
                                "Write a comment...",
                                key=f"input_{p['id']}",
                                label_visibility="collapsed",
                                placeholder="Write a reply...",
                            )
                            if st.button(
                                "Send Reply",
                                key=f"btn_{p['id']}",
                                use_container_width=True,
                            ):
                                if new_comment.strip():
                                    supabase.table("comments").insert({
                                        "post_id": p["id"],
                                        "user": st.session_state["user_name"],
                                        "comment": new_comment.strip(),
                                    }).execute()
                                    st.rerun()

                    with cols[2]:
                        if p["user"] == st.session_state["user_name"]:
                            if st.button(
                                "Delete Post",
                                key=f"del_{p['id']}",
                                use_container_width=True,
                            ):
                                supabase.table("blog").delete().eq(
                                    "id", p["id"]
                                ).execute()
                                st.rerun()
        else:
            st.info(
                "No posts in the feed yet. Start the conversation by sharing a"
                " thought above."
            )

# --- TAB 4: INSIGHTS ---
with tab4:
    st.subheader("PERSONAL INSIGHTS & GOALS")
    st.caption(
        "Analyze your screen time habits, track performance, and set daily"
        " target goals"
    )
    st.divider()

    current_user = st.session_state["user_name"]

    user_logs = (
        supabase.table("logs")
        .select("*")
        .eq("user", current_user)
        .execute()
        .data
    )

    if not user_logs:
        st.info(
            "No logged data found. Start logging your daily screen time to"
            " unlock personal insights."
        )
    else:
        df = pd.DataFrame(user_logs)
        df["date"] = pd.to_datetime(df["date"])
        df["total_hours"] = df["hours"] + (df["minutes"] / 60)
        df = df.sort_values("date", ascending=False)

        last_7_logs = df.head(7)
        weekly_avg = last_7_logs["total_hours"].mean()

        latest_log = df.iloc[0]
        latest_time = latest_log["total_hours"]
        latest_date_str = latest_log["date"].strftime("%b %d")

        recommended_goal = max(0.5, round((weekly_avg * 0.9) * 2) / 2)

        if "daily_goal" not in st.session_state:
            st.session_state["daily_goal"] = recommended_goal

        with st.container(border=True):
            st.caption("DAILY TARGET GOAL")
            col_goal1, col_goal2 = st.columns([1, 1])

            with col_goal1:
                user_goal = st.number_input(
                    "My Screen Time Goal (Hours)",
                    min_value=0.5,
                    max_value=24.0,
                    step=0.5,
                    value=float(st.session_state["daily_goal"]),
                )
                st.session_state["daily_goal"] = user_goal

            with col_goal2:
                st.markdown(
                    "<div style='padding-top: 25px; color: #8A92A6; font-size:"
                    " 13px; line-height: 1.4;'><b>RECOMMENDED"
                    f" TARGET:</b><br/>Based on your 7-day average ({weekly_avg:.1f}h),"
                    f" aiming for <b>{recommended_goal}h</b> is optimal for"
                    " gradual reduction.</div>",
                    unsafe_allow_html=True,
                )

        st.write("")

        st.subheader("PERFORMANCE SUMMARY")
        st.caption(
            "Comparison between your daily targets and actual screen time"
        )

        def format_hm(hours_float):
            h = int(hours_float)
            m = int(round((hours_float - h) * 60))
            return f"{h}h {m}m"

        delta_val = latest_time - user_goal

        with st.container(border=True):
            m1, m2, m3 = st.columns(3)

            m1.metric(
                label=f"Latest Log ({latest_date_str})",
                value=format_hm(latest_time),
                delta=f"{round(delta_val, 1)}h vs Goal",
                delta_color="inverse",
            )

            m2.metric(label="7-Day Average", value=format_hm(weekly_avg))

            m3.metric(label="Daily Goal Target", value=f"{user_goal}h")

        st.write("")

        st.subheader("HABIT ANALYSIS")

        if latest_time <= user_goal:
            st.success(
                "Target Achieved: Your latest screen time remained within your"
                " daily goal."
            )
        else:
            st.warning(
                "Goal Exceeded: Your screen time was"
                f" {round(delta_val, 1)} hours over your daily target."
            )

        if latest_time < weekly_avg:
            st.info(
                "Positive Trend: Your latest logged screen time is lower than"
                " your 7-day average."
            )
        elif latest_time > weekly_avg:
            st.info(
                "Attention: Your latest screen time exceeded your recent"
                " average."
            )

# --- TAB 5: PERSONAL GROWTH ---
with tab5:
    st.subheader("PERSONAL CHALLENGES & GROWTH")
    st.caption(
        "Log personal milestones, earn points, and track your self-improvement"
        " progress"
    )
    st.divider()

    with st.container(border=True):
        st.caption("ADD NEW CHALLENGE")
        with st.form("add_personal_challenge", clear_on_submit=True):
            c_name = st.text_input(
                "Achievement Description",
                placeholder=(
                    "e.g., Kept screen time under 3 hours, No Instagram for 4"
                    " hours..."
                ),
            )

            difficulty_map = {
                "Easy (10 pts)": 10,
                "Medium (25 pts)": 25,
                "Hard (50 pts)": 50,
                "Very Hard (100 pts)": 100,
            }
            difficulty_choice = st.selectbox(
                "Difficulty Level", options=list(difficulty_map.keys())
            )

            col_space, col_btn = st.columns([3, 1])
            with col_btn:
                submitted = st.form_submit_button(
                    "Log Challenge", type="primary", use_container_width=True
                )

            if submitted:
                if c_name:
                    points = difficulty_map[difficulty_choice]
                    today_str = get_local_today_str()

                    supabase.table("personal_challenges").insert({
                        "user": st.session_state["user_name"],
                        "challenge_name": c_name,
                        "difficulty": difficulty_choice.split(" ")[0],
                        "points": points,
                        "date": today_str,
                    }).execute()

                    st.success(
                        f"Challenge logged successfully. Earned {points}"
                        " points."
                    )
                    st.rerun()

    st.write("")

    my_challenges = (
        supabase.table("personal_challenges")
        .select("*")
        .eq("user", st.session_state["user_name"])
        .execute()
        .data
    )

    if my_challenges:
        df_c = pd.DataFrame(my_challenges)
        total_points = df_c["points"].sum()
        with st.container(border=True):
            st.metric(
                label="Total Lifetime Points", value=f"{total_points:,} pts"
            )

        st.write("")

        st.subheader("DAILY PROGRESS")
        st.caption("Overview of points earned over time")

        daily_points = df_c.groupby("date")["points"].sum().reset_index()
        daily_points = daily_points.sort_values(by="date")

        fig_pts = px.bar(
            daily_points,
            x="date",
            y="points",
            text="points",
            color_discrete_sequence=["#61AFEF"],
        )

        if len(daily_points) == 1:
            fig_pts.update_traces(
                width=0.2,
                textposition="outside",
                textfont=dict(color="#8A92A6"),
            )
        else:
            fig_pts.update_traces(
                textposition="outside", textfont=dict(color="#8A92A6")
            )

        fig_pts.update_layout(
            xaxis=dict(
                type="category",
                title="",
                showgrid=False,
                tickfont=dict(color="#8A92A6"),
            ),
            yaxis=dict(
                title="Points",
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(color="#8A92A6"),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20),
            font=dict(color="#8A92A6"),
        )
        st.plotly_chart(fig_pts, use_container_width=True)

        st.write("")

        st.subheader("CHALLENGE HISTORY")
        st.caption("Complete log of completed personal goals")

        df_display = df_c[
            ["date", "challenge_name", "difficulty", "points"]
        ].sort_values(by="date", ascending=False)
        df_display.columns = ["Date", "Challenge", "Difficulty", "Points"]

        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No personal challenges logged yet. Complete a challenge above to"
            " start earning points."
        )