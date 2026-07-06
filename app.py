import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Screen Time Squad", layout="centered")
st.title("📱 Screen Time Squad")
st.write("Track stats, smash challenges, and log your digital detox journey.")

# --- INITIALIZE SESSION STATE (For dynamic challenges & custom apps) ---
if "custom_challenges" not in st.session_state:
    st.session_state["custom_challenges"] = [
        "🚫 No Social Media Before Noon (50 pts)",
        "⏳ Under 3 Hours Total Screen Time Today (100 pts)",
        "🌳 Walk without your phone for 30 mins (40 pts)"
    ]

if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = ["Instagram", "YouTube", "Facebook", "TikTok"]

# --- TABS SETUP ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Logging", "🏆 Challenges", "📝 Mini-Blog"])

# --- TAB 1: DASHBOARD & LOGGING ---
with tab1:
    st.header("Weekly Progress")
    
    # Mock chart data
    chart_data = pd.DataFrame(
        {
            "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "Your Time (hrs)": [4.2, 3.8, 5.1, 2.9, 4.5, 6.2, 3.5],
            "Squad Avg (hrs)": [4.5, 4.1, 4.8, 3.5, 4.0, 5.5, 4.2]
        }
    ).set_index("Day")
    st.line_chart(chart_data)
    
    st.divider()
    
    # --- SPECIFIC APP TIME LOGGING ---
    st.subheader("Log Today's App Breakdown")
    st.write("Enter hours spent on specific apps today:")
    
    # Option to add a new custom app to the tracking list
    with st.expander("➕ Add another app to track"):
        new_app_name = st.text_input("App Name (e.g., Reddit, Netflix, Games):")
        if st.button("Add App Category"):
            if new_app_name and new_app_name not in st.session_state["tracked_apps"]:
                st.session_state["tracked_apps"].append(new_app_name)
                st.rerun() # Refresh app to show the new field immediately
    
    # Create input fields for every app currently in our list
    app_logs = {}
    cols = st.columns(2) # Organize inputs neatly into two columns
    for i, app in enumerate(st.session_state["tracked_apps"]):
        with cols[i % 2]:
            app_logs[app] = st.number_input(f"**{app}** (hrs):", min_value=0.0, max_value=24.0, step=0.1, key=f"app_{app}")
            
    total_logged = sum(app_logs.values())
    st.info(f"**Total Screen Time Logged Today:** {total_logged:.1f} hours")
    
    if st.button("Submit Today's Breakdown", type="primary"):
        st.success("App breakdown logged successfully!")

# --- TAB 2: CHALLENGES ---
with tab2:
    st.header("Active Challenges")
    
    # --- ADD A CUSTOM CHALLENGE ---
    with st.expander("⚡ Create a New Squad Challenge"):
        with st.form("new_challenge_form"):
            new_challenge_text = st.text_input("Challenge Description", placeholder="e.g., Keep phone in another room during dinner")
            new_challenge_pts = st.number_input("Reward Points", min_value=10, max_value=500, step=10, value=50)
            submitted_challenge = st.form_submit_button("Add Challenge for Squad")
            
            if submitted_challenge and new_challenge_text:
                full_challenge_str = f"🎯 {new_challenge_text} ({new_challenge_pts} pts)"
                st.session_state["custom_challenges"].append(full_challenge_str)
                st.rerun() # Refresh to show the new checkbox below!
    
    st.write("Check off the challenges you completed today:")
    
    # Render checkboxes for all challenges dynamically
    for idx, challenge in enumerate(st.session_state["custom_challenges"]):
        st.checkbox(challenge, key=f"challenge_{idx}")
    
    st.divider()
    
    st.subheader("Leaderboard")
    leaderboard = pd.DataFrame({
        "Friend": ["Alex", "You", "Sam", "Jordan"],
        "Points": [240, 190, 150, 90]
    })
    st.table(leaderboard)

# --- TAB 3: MINI-BLOG ---
with tab3:
    st.header("Squad Reflections")
    
    with st.form("blog_form"):
        user_name = st.text_input("Your Name")
        entry_text = st.text_area("How did your digital detox go today?")
        submitted = st.form_submit_button("Post to Blog")
        if submitted and user_name and entry_text:
            st.success(f"Posted by {user_name}!")

    st.divider()
    
    st.markdown("**Alex** *• 2 hours ago*")
    st.caption("Left my phone in the kitchen while studying. Honestly felt great, highly recommend.")
    
    st.markdown("**Sam** *• Yesterday*")
    st.caption("Failed the 'Under 3 hours' challenge because of a long FaceTime call, but trying again tomorrow!")