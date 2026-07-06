import uuid
from datetime import date, datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Screen Time Squad", layout="centered")

# --- INITIALIZE SESSION STATE ---
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

if "custom_challenges" not in st.session_state:
    st.session_state["custom_challenges"] = [
        {"text": "🚫 No Social Media Before Noon", "points": 50},
        {"text": "⏳ Under 3 Hours Total Screen Time Today", "points": 100},
        {"text": "🌳 Walk without your phone for 30 mins", "points": 40},
    ]

if "tracked_apps" not in st.session_state:
    st.session_state["tracked_apps"] = [
        "Instagram",
        "YouTube",
        "Facebook",
        "TikTok",
    ]


# --- WELCOME SCREEN ---
def welcome_screen():
    st.title("👋 Welcome to Screen Time Squad!")
    st.write("Enter your name to access the synchronized squad app.")
    with st.form("login_form"):
        name_input = st.text_input("Your Name:", placeholder="e.g., Alex")
        if st.form_submit_button("Enter Squad App", type="primary"):
            if name_input.strip():
                st.session_state["user_name"] = name_input.strip().capitalize()
                st.rerun()
            else:
                st.error("Please enter a valid name!")


if not st.session_state["user_name"]:
    welcome_screen()
    st.stop()

# --- APP HEADER ---
st.title("📱 Screen Time Squad")
col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"Logged in as: **{st.session_state['user_name']}**")
with col2:
    if st.button("Switch User"):
        st.session_state["user_name"] = None
        st.rerun()

st.divider()

# --- DATABASE CONNECTIONS ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    logs_df = conn.read(worksheet="Logs", ttl=0)
except Exception:
    logs_df = pd.DataFrame(
        columns=["Date", "User", "Total Hours"]
        + st.session_state["tracked_apps"]
    )

try:
    leaderboard_df = conn.read(worksheet="Leaderboard", ttl=0)
except Exception:
    leaderboard_df = pd.DataFrame(columns=["User", "Points"])

try:
    blog_df = conn.read(worksheet="Blog", ttl=0)
except Exception:
    blog_df = pd.DataFrame(
        columns=["PostID", "Timestamp", "User", "Post", "Likes"]
    )

try:
    comments_df = conn.read(worksheet="Comments", ttl=0)
except Exception:
    comments_df = pd.DataFrame(columns=["PostID", "User", "Comment"])


# --- TABS SETUP ---
tab1, tab2, tab3 = st.tabs(
    ["📊 Dashboard & Logging", "🏆 Challenges", "📝 Squad Blog"]
)


# --- TAB 1: DASHBOARD & LOGGING ---
with tab1:
    st.header("Squad Weekly Progress")
    if not logs_df.empty and "Date" in logs_df.columns:
        try:
            pivot_data = logs_df.pivot(
                index="Date", columns="User", values="Total Hours"
            )
            st.line_chart(pivot_data)
        except Exception:
            st.info("Log your daily data below to initialize the line chart.")
    else:
        st.info("No logs found. Submit your time below to start the graph!")

    st.divider()

    st.subheader("Log Today's Screen Time")
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
        new_row = {
            "Date": str(log_date),
            "User": st.session_state["user_name"],
            "Total Hours": manual_total_hours,
        }
        new_row.update(app_logs)

        if not logs_df.empty:
            logs_df = logs_df[
                ~(
                    (logs_df["Date"] == str(log_date))
                    & (logs_df["User"] == st.session_state["user_name"])
                )
            ]

        updated_logs = pd.concat(
            [logs_df, pd.DataFrame([new_row])], ignore_index=True
        )
        conn.update(data=updated_logs, worksheet="Logs")
        st.success("Stats successfully uploaded!")
        st.rerun()


# --- TAB 2: CHALLENGES & LEADERBOARD ---
with tab2:
    st.header("Squad Leaderboard")
    if not leaderboard_df.empty:
        sorted_leaderboard = leaderboard_df.sort_values(
            by="Points", ascending=False
        ).reset_index(drop=True)
        st.dataframe(sorted_leaderboard, use_container_width=True)
    else:
        st.info("The leaderboard is currently empty. Claim points below!")

    st.divider()
    st.subheader("Daily Challenges")

    score_earned = 0
    for idx, ch in enumerate(st.session_state["custom_challenges"]):
        if st.checkbox(
            f"{ch['text']} (+{ch['points']} pts)", key=f"ch_{idx}"
        ):
            score_earned += ch["points"]

    if st.button("Submit Completed Challenges", type="primary"):
        current_user = st.session_state["user_name"]

        if (
            not leaderboard_df.empty
            and current_user in leaderboard_df["User"].values
        ):
            idx = leaderboard_df[
                leaderboard_df["User"] == current_user
            ].index[0]
            leaderboard_df.at[idx, "Points"] = (
                int(leaderboard_df.at[idx, "Points"]) + score_earned
            )
        else:
            new_score_row = {"User": current_user, "Points": score_earned}
            leaderboard_df = pd.concat(
                [leaderboard_df, pd.DataFrame([new_score_row])],
                ignore_index=True,
            )

        conn.update(data=leaderboard_df, worksheet="Leaderboard")
        st.success(f"Added {score_earned} points to your total!")
        st.rerun()


# --- TAB 3: SQUAD BLOG (WITH LIKES & COMMENTS) ---
with tab3:
    st.header("Squad Feed")

    # Write a Post Form
    with st.form("blog_form", clear_on_submit=True):
        entry_text = st.text_area(
            "Share a tip, milestone, or reflection on your detox today:",
            placeholder="Type here...",
        )
        if st.form_submit_button("Post to Squad Feed") and entry_text.strip():
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            unique_id = str(uuid.uuid4())[:8]  # Simple brief ID
            new_post = {
                "PostID": unique_id,
                "Timestamp": now_str,
                "User": st.session_state["user_name"],
                "Post": entry_text.strip(),
                "Likes": "",  # Stores comma-separated names of users who liked
            }

            updated_blog = pd.concat(
                [blog_df, pd.DataFrame([new_post])], ignore_index=True
            )
            conn.update(data=updated_blog, worksheet="Blog")
            st.success("Post published to squad feed!")
            st.rerun()

    st.divider()

    # Display Feed
    if not blog_df.empty:
        # Fill NaN values to avoid string split errors
        blog_df["Likes"] = blog_df["Likes"].fillna("").astype(str)
        sorted_blog = blog_df.iloc[::-1]  # Show newest first

        for _, row in sorted_blog.iterrows():
            pid = row["PostID"]

            # Parse likes list
            likes_list = (
                [x.strip() for x in row["Likes"].split(",") if x.strip()]
                if row["Likes"]
                else []
            )
            likes_count = len(likes_list)
            has_liked = st.session_state["user_name"] in likes_list

            # Render Post Card
            st.markdown(f"**{row['User']}** *• {row['Timestamp']}*")
            st.info(row["Post"])

            # Likes & Comments Row Layout
            l_col, c_col = st.columns([1, 4])

            # Like Button Logic
            with l_col:
                like_label = f"❤️ {likes_count}" if has_liked else f"🤍 {likes_count}"
                if st.button(like_label, key=f"like_{pid}"):
                    if has_liked:
                        likes_list.remove(st.session_state["user_name"])
                    else:
                        likes_list.append(st.session_state["user_name"])

                    # Update specific row in dataframe
                    blog_df.loc[blog_df["PostID"] == pid, "Likes"] = (
                        ",".join(likes_list)
                    )
                    conn.update(data=blog_df, worksheet="Blog")
                    st.rerun()

            # Comments Section
            with st.expander("💬 View/Write Comments"):
                # Filter comments for this specific post
                post_comments = pd.DataFrame()
                if not comments_df.empty and "PostID" in comments_df.columns:
                    post_comments = comments_df[comments_df["PostID"] == pid]

                if not post_comments.empty:
                    for _, c_row in post_comments.iterrows():
                        st.markdown(
                            f"**{c_row['User']}:** {c_row['Comment']}"
                        )
                else:
                    st.caption("No comments yet.")

                # Inline Comment Form
                with st.form(key=f"c_form_{pid}", clear_on_submit=True):
                    new_comment = st.text_input(
                        "Add a comment...", key=f"in_{pid}"
                    )
                    if (
                        st.form_submit_button("Reply")
                        and new_comment.strip()
                    ):
                        new_c_row = {
                            "PostID": pid,
                            "User": st.session_state["user_name"],
                            "Comment": new_comment.strip(),
                        }
                        comments_df = pd.concat(
                            [comments_df, pd.DataFrame([new_c_row])],
                            ignore_index=True,
                        )
                        conn.update(data=comments_df, worksheet="Comments")
                        st.rerun()
            st.markdown("---")
    else:
        st.caption("No reflections posted yet.")