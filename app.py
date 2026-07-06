from datetime import date
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Screen Time Squad", layout="centered")

# --- INITIALIZE SESSION STATE ---
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

if "custom_challenges" not in st.session_state:
    st.session_state["custom_challenges"] = [
        "🚫 No Social Media Before Noon (50 pts)",
        "⏳ Under 3 Hours Total Screen Time Today (100 pts)",
        "🌳 Walk without your phone for 30 mins (40 pts)",
    ]

if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = [
        "Instagram",
        "YouTube",
        "Facebook",
        "TikTok",
    ]


# --- WELCOME SCREEN (Identity Gate) ---
def welcome_screen():
    st.title("👋 Welcome to Screen Time Squad!")
    st.write(
        "Enter your name below to jump into the squad dashboard and log your stats."
    )

    with st.form("login_form"):
        name_input = st.text_input("Your Name:", placeholder="e.g., Alex")
        submitted = st.form_submit_button("Enter Squad App", type="primary")

        if submitted:
            if name_input.strip() != "":
                st.session_state["user_name"] = name_input.strip()
                st.rerun()
            else:
                st.error("Please enter your name to continue!")


# If the user hasn't entered their name yet, show only the welcome screen!
if not st.session_state["user_name"]:
    welcome_screen()
    st.stop()  # Stop running the rest of the app until they log in

# --- MAIN APP HEADER (Once Logged In) ---
st.title("📱 Screen Time Squad")
col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"Logged in as: **{st.session_state['user_name']}**")
with col2:
    if st.button("Switch User"):
        st.session_state["user_name"] = None
        st.rerun()

st.divider()

# --- DATABASE CONNECTION ---
# Connects to your Google Sheet using Streamlit's built-in secrets engine
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    existing_data = conn.read(ttl=0)  # Read fresh data without caching delay
except Exception:
    # Fallback mock dataframe if Google Sheet is not configured yet
    existing_data = pd.DataFrame(
        columns=["Date", "User", "Total Hours"]
        + st.session_state["tracked_apps"]
    )

# --- TABS SETUP ---
tab1, tab2, tab3 = st.tabs(
    ["📊 Dashboard & Logging", "🏆 Challenges", "📝 Mini-Blog"]
)

# --- TAB 1: DASHBOARD & LOGGING ---
with tab1:
    st.header("Squad Weekly Progress")

    # 1. RENDER MULTI-LINE GRAPH
    if not existing_data.empty and "Date" in existing_data.columns:
        # Pivot table so Dates are rows, Users are columns, and values are Total Hours
        try:
            pivot_data = existing_data.pivot(
                index="Date", columns="User", values="Total Hours"
            )
            st.line_chart(pivot_data)
        except Exception:
            st.info("Log some data below to generate the squad line chart!")
    else:
        st.info(
            "No data logged yet! Be the first to add your screen time below."
        )

    st.divider()

    # 2. LOGGING FORM
    st.subheader(f"Log Today's Time for {st.session_state['user_name']}")
    log_date = st.date_input("Date:", value=date.today())

    manual_total_hours = st.number_input(
        "Total Phone Screen Time Today (hrs):",
        min_value=0.0,
        max_value=24.0,
        step=0.1,
    )

    st.write("Specific App Breakdown:")
    app_logs = {}
    cols = st.columns(2)
    for i, app in enumerate(st.session_state["tracked_apps"]):
        with cols[i % 2]:
            app_logs[app] = st.number_input(
                f"**{app}** (hrs):", min_value=0.0, max_value=24.0, step=0.1
            )

    if st.button("Save Today's Log to Cloud", type="primary"):
        # Create a dictionary for the new row
        new_row = {
            "Date": str(log_date),
            "User": st.session_state["user_name"],
            "Total Hours": manual_total_hours,
        }
        new_row.update(app_logs)

        # Append new row to existing dataframe
        updated_data = pd.concat(
            [existing_data, pd.DataFrame([new_row])], ignore_index=True
        )

        try:
            # Update the Google Sheet!
            conn.update(data=updated_data)
            st.success("Successfully saved to your group's Google Sheet!")
            st.rerun()  # Refresh immediately to update the line chart
        except Exception as e:
            st.error(
                "Could not save to Google Sheets. Check your Secrets configuration!"
            )

# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("Active Challenges")
    with st.expander("⚡ Create a New Squad Challenge"):
        with st.form("new_challenge_form"):
            new_challenge_text = st.text_input("Challenge Description")
            new_challenge_pts = st.number_input(
                "Reward Points", min_value=10, max_value=500, step=10, value=50
            )
            if (
                st.form_submit_button("Add Challenge for Squad")
                and new_challenge_text
            ):
                st.session_state["custom_challenges"].append(
                    f"🎯 {new_challenge_text} ({new_challenge_pts} pts)"
                )
                st.rerun()

    for idx, challenge in enumerate(st.session_state["custom_challenges"]):
        st.checkbox(challenge, key=f"challenge_{idx}")

# --- TAB 3: MINI-BLOG ---
with tab3:
    st.header("Squad Reflections")
    with st.form("blog_form"):
        entry_text = st.text_area("How did your digital detox go today?")
        if st.form_submit_button("Post to Blog") and entry_text:
            st.success(f"Posted as {st.session_state['user_name']}!")