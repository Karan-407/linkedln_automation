import streamlit as st
import time
import requests

BACKEND_INPUT_URL="http://localhost:8000/generate"
BACKEND_EDIT_URL="http://localhost:8000/edit"
BACKEND_POST_URL="http://localhost:8000/post"

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(page_title="LinkedIn Post Automator", layout="centered")

# ----------------------------
# Session State Setup
# ----------------------------
if "generated_post" not in st.session_state:
    st.session_state.generated_post = None
if "step" not in st.session_state:
    st.session_state.step = "input"   # steps: input → processing → result

# ----------------------------
# Step 1: Input Page
# ----------------------------
if st.session_state.step == "input":
    st.title("🤖 LinkedIn Post Automator")
    st.write("Automate your LinkedIn posts with AI 🚀")

    query = st.text_area("Enter your post idea or query:")
    url = st.text_input("Enter URL (optional):")
    temperature = st.slider("Set LLM Temperature (Creativity)", 0.0, 1.0, 0.7)

    if st.button("✨ Generate LinkedIn Post"):
        if not query.strip():
            st.error("Please provide a query to generate the post.")
        else:
            # Call backend API
            
            response = requests.post(BACKEND_INPUT_URL, json={
                "query": query,
                "url": url,
                "temperature": temperature
            })

            if response.status_code == 200:
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.logs = data["logs"]
                st.session_state.generated_post = data["generated_post"]
                st.session_state.step = "result"
                st.rerun()
            else:
                st.error("Error connecting to backend API")

# ----------------------------
# Step 2: Processing Page
# ----------------------------
elif st.session_state.step == "processing":
    st.title("⚙️ Processing... Please wait")

    logs = st.empty()

    fake_logs = [
        "🔍 Analyzing input query...",
        f"🌐 Processing URL: {st.session_state.url}" if st.session_state.url else "🌐 No URL provided, skipping...",
        f"⚙️ Running LLM with temperature {st.session_state.temperature}...",
        "✍️ Drafting LinkedIn post...",
        "✅ Post generated successfully!"
    ]

    for log in fake_logs:
        logs.write(log)
        time.sleep(1)

    # Simulated LLM output
    st.session_state.generated_post = f"""
    🚀 **Your LinkedIn Post Draft** 🚀  

    {st.session_state.query}  

    {"🔗 Source: " + st.session_state.url if st.session_state.url else ""}
    """
    st.session_state.step = "result"
    st.rerun()

elif st.session_state.step == "edit":
    st.title("🤖 Suggest the changes")
    st.write("Automate your LinkedIn posts with AI 🚀")

    user_feedback = st.text_area("Enter your post idea or query:")

    if st.button("✨ Edit LinkedIn Post"):
        if not user_feedback.strip():
            st.error("Please provide a query to generate the post.")
        else:
            # Call backend API
            # if user_feedback.lower() == "exit":
            #     print("Exiting workflow.")
            #     st.session_state.step = "exit"
            #     st.rerun()
            response = requests.post(BACKEND_EDIT_URL, json={
                    "user_feedback": user_feedback,
                    "session_id": st.session_state.session_id,
                })
            data = response.json()
            if data["state"] == "Posted to linkedin":
                st.success("✅ The post has been posted to LinkedIn")
                st.session_state.state = "exit"
                st.rerun()
            elif data["state"] == "result":
                st.session_state.step = "result"
                st.session_state.generated_post = data["generated_post"]
                st.rerun()


elif st.session_state.step == "post":
    st.title("🤖 Suggest the changes")
    st.write("Automate your LinkedIn posts with AI 🚀")

    response = requests.post(BACKEND_POST_URL, json={
                    "user_feedback": "approve",
                    "session_id": st.session_state.session_id,
                })
    if response.status_code == 200:
        data = response.json()
        st.write(data)
        if data["state"] == "Posted":
            st.success("✅ The post has been posted to LinkedIn")
            st.session_state.step = "exit"
            st.rerun()

# ----------------------------
# Step 3: Result Page
# ----------------------------
elif st.session_state.step == "result":
    st.title("✅ Generated LinkedIn Post")
    st.success(st.session_state.generated_post)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Accept"):
            st.success("Post accepted and ready for LinkedIn 🚀")
            st.session_state.step = "post"
            st.rerun()
    with col2:
        if st.button("✍️ Suggest Changes"):
            st.info("You can now edit your query and try again.")
            st.session_state.step = "edit"
            st.rerun()

    with col3:
        if st.button("❌ Exit"):
            st.warning("Exiting session.")
            st.session_state.step = "exit"
            st.session_state.generated_post = None
            st.rerun()


elif st.session_state.step == "exit":
    # Clear all workflow-related session state
    keys_to_clear = ["generated_post", "logs", "query", "url", "temperature", "session_id"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Reset step to input so UI is clean for next session
    st.session_state.step = "input"
    st.empty()  # clears previous elements
    st.title("✅ Thank You!")
    st.info("Your LinkedIn post session has ended. You can start a new session now.")
    timer_placeholder = st.empty()

    # Countdown from 1 to 3
    for timer in range(1, 4):
     # Update the same placeholder text
        timer_placeholder.text(f"Redirecting to new page in {timer}")
        time.sleep(2)
    timer_placeholder.text("Redirecting now 🚀")
    # Clear the page (rerun will redraw only input page)
    st.rerun()

