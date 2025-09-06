# app.py
import streamlit as st
import os
from pathlib import Path
# Import the core logic from your logic file
from logic import run_job_application_logic

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="AI Job Application Assistant", layout="wide")

st.title("🤖 AI Job Application Assistant")
st.markdown(
    "Paste a job description below, choose your AI provider, and get a tailored CV and Cover Letter generated for you.")

# --- Sidebar for Configuration ---
with st.sidebar:
    st.header("Configuration")
    ai_provider = st.selectbox("Choose AI Provider", ("gemini", "claude"),
                               help="Select the AI service you want to use.")

    st.markdown("---")
    st.subheader("API Keys")
    st.info("Your API keys are already stored and hence no action is needed.")
    # Get API keys from the user
    # gemini_api_key = st.text_input("Gemini API Key", type="password", help="Required if you choose Gemini.")
    # anthropic_api_key = st.text_input("Anthropic API Key", type="password", help="Required if you choose Claude.")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    # Optional check
    if not anthropic_api_key and not gemini_api_key:
        st.error("API keys not found. Please add them to your .env file.")

# --- Main Area for Input and Generation ---
jd_text = st.text_area("Paste the full Job Description here", height=350)

if st.button("✨ Generate Application Documents"):
    # --- Input Validation ---
    valid_input = True
    if not jd_text.strip():
        st.error("Please paste a job description into the text area.")
        valid_input = False

    if ai_provider == "gemini" and not gemini_api_key:
        st.error("Please enter your Gemini API Key in the sidebar to proceed.")
        valid_input = False
    elif ai_provider == "claude" and not anthropic_api_key:
        st.error("Please enter your Anthropic API Key in the sidebar to proceed.")
        valid_input = False

    if valid_input:
        # Set API keys as environment variables for the logic module to securely access them
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
        if anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

        # Use st.status to show live progress updates from the logic file
        with st.status("Starting the application process...", expanded=True) as status:

            # This callback function allows the logic file to send updates to the UI
            def status_callback(message, status_type="info"):
                if status_type == "success":
                    st.write(f"✅ {message}")
                elif status_type == "error":
                    st.write(f"❌ {message}")
                    status.update(label=f"Error: {message}", state="error")
                elif status_type == "working":
                    st.write(f"⚙️ {message}")
                else:  # info
                    st.write(f"▶️ {message}")


            try:
                # Execute the main logic and get the output path
                output_path = run_job_application_logic(ai_provider, jd_text, status_callback)

                if output_path:
                    status.update(label="Process completed successfully!", state="complete")
                    st.success("All documents have been generated and saved!")
                    # Provide the user with the exact location of their files
                    st.info(f"You can find your files in your home directory here: {output_path}")
                else:
                    # An error was caught and reported by the callback
                    st.error("The process failed. Please check the messages above for details.")
                    status.update(label="Process failed.", state="error")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                status.update(label="An unexpected critical error occurred.", state="error")
