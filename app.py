# app.py
import streamlit as st
from logic import run_job_application_logic, MODELS

# --- Page Configuration ---
st.set_page_config(page_title="AI Job Automator", page_icon="🤖", layout="wide")

# --- App UI ---
st.title("🤖 AI Job Application Automator")
st.markdown("Paste a job description, choose your AI provider, and generate tailored application documents.")

col1, col2 = st.columns([2, 1])

with col1:
    jd_text = st.text_area("Paste the Full Job Description Here:", height=450, placeholder="Paste JD here...")

with col2:
    ai_provider = st.radio(
        "Select AI Provider:", options=list(MODELS.keys()), index=0, horizontal=True
    )
    st.info(f"Using **{MODELS[ai_provider]['powerful']}** for content generation.")
    process_button = st.button("✨ Generate Application Documents", type="primary", use_container_width=True)

st.markdown("---")
st.subheader("Live Console Log")
status_placeholder = st.empty()

# --- Processing Logic ---
if process_button:
    st.session_state.status_messages = []
    def status_callback(message, status_type):
        """This function is passed to the logic to report progress to the Streamlit UI."""
        emojis = {"info": "▶️", "success": "✅", "error": "❌", "working": "⚙️"}
        st.session_state.status_messages.append(f"{emojis.get(status_type, '▶️')} {message}")
        messages_string = "\n".join(st.session_state.status_messages)
        status_placeholder.markdown(f"```\n{messages_string}\n```")

    status_placeholder.markdown("```\n \n```") # Clear previous log
    run_job_application_logic(ai_provider, jd_text, status_callback)
else:
    status_placeholder.markdown("```\n▶️ Waiting for a new job to process...\n```")