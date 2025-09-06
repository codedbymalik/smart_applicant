# logic.py
import os
import sys
import json
import re
from datetime import datetime
from dotenv import load_dotenv

# --- AI Provider Imports ---
import anthropic
import google.generativeai as genai
from weasyprint import HTML

# ==============================================================================
# --- CONFIGURATION & SETUP ---
# ==============================================================================
load_dotenv()

# --- API Key Loading ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- AI Clients (initialized on demand) ---
claude_client = None
gemini_configured = False

# --- Model Selection Dictionary ---
MODELS = {
    "claude": {"fast": "claude-3-haiku-20240307", "powerful": "claude-3-5-sonnet-20240620"},
    "gemini": {"fast": "gemini-1.5-flash-latest", "powerful": "gemini-1.5-pro-latest"}
}

# --- System Prompt for Consistent AI Behavior ---
SYSTEM_PROMPT = """
You are an expert German-based career assistant named "JobBot".
Your user is Zohaib Malik, a Data Engineer. Your goal is to help him create exceptional, tailored job application documents in Germany.
You must be professional, precise, and follow all instructions meticulously.
Adhere strictly to the requested output format in each prompt (e.g., raw JSON, raw HTML, or plain text).
Do not include any conversational text, apologies, or self-corrections in your final output.
The current date is September 6, 2025.
"""

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_CV_PATH = os.path.join(BASE_DIR, "templates", "cv_template.html")
CORE_INFO_PATH = os.path.join(BASE_DIR, "templates", "core_info.txt")
REFERENCE_CV_PATH = os.path.join(BASE_DIR, "templates", "reference_cv.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "Job Applications")


# ==============================================================================
# --- HELPER FUNCTIONS ---
# ==============================================================================

def initialize_ai_provider(provider, status_callback):
    """Initializes the required AI client if not already done."""
    global claude_client, gemini_configured
    try:
        if provider == "claude" and not claude_client:
            if not ANTHROPIC_API_KEY: raise ValueError("ANTHROPIC_API_KEY is missing from .env")
            claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            status_callback("Claude client initialized.", "info")
        elif provider == "gemini" and not gemini_configured:
            if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY is missing from .env")
            genai.configure(api_key=GEMINI_API_KEY)
            gemini_configured = True
            status_callback("Gemini client initialized.", "info")
    except ValueError as e:
        status_callback(str(e), "error")
        return False
    return True


def call_ai(provider, model_name, prompt, system_prompt, status_callback):
    """Unified function to call the selected AI provider's API."""
    status_callback(f"Calling {provider} model ({model_name})... Please wait.", "working")
    try:
        if provider == "claude":
            message = claude_client.messages.create(
                model=model_name, max_tokens=4096, system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        elif provider == "gemini":
            model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
            # Add a safety setting configuration to be less restrictive
            safety_config = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
            response = model.generate_content(prompt, safety_settings=safety_config)
            return response.text
    except Exception as e:
        status_callback(f"API call to {provider} failed: {e}", "error")
        return None


def read_file_content(file_path, status_callback):
    """Reads content from a file and reports errors via callback."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        status_callback(f"Template file not found: {file_path}", "error")
        return None
    except Exception as e:
        status_callback(f"Error reading file {file_path}: {e}", "error")
        return None


def extract_info_from_jd(provider, model_id, jd_text, system_prompt, status_callback):
    """Uses AI to extract company name and job title from the JD."""
    prompt = f"""
    Analyze the following job description and extract the company name and the job title.
    Return your answer in a clean JSON format, with no other text before or after the JSON block.
    Example: {{"company_name": "Example Corp", "job_title": "Senior Developer"}}

    Job Description:
    ---
    {jd_text}
    ---
    """
    response = call_ai(provider, model_id, prompt, system_prompt, status_callback)
    if not response or not response.strip():
        status_callback("AI returned an empty response for company/role extraction.", "error")
        return "Unknown Company", "Unknown Role"
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            clean_json = json_match.group().strip()
            info = json.loads(clean_json)
            return info.get("company_name"), info.get("job_title")
        else:
            raise json.JSONDecodeError("No JSON object found in the response.", response, 0)
    except Exception as e:
        status_callback(f"Failed to parse company/role from AI response. Error: {e}", "error")
        return "Unknown Company", "Unknown Role"


def create_job_directory(company, role, status_callback):
    """Creates a directory for the application files."""
    safe_company = re.sub(r'[^\w\s-]', '', company).strip()
    safe_role = re.sub(r'[^\w\s-]', '', role).strip()
    dir_name = os.path.join(OUTPUT_DIR, f"{safe_company} - {safe_role}")
    os.makedirs(dir_name, exist_ok=True)
    status_callback(f"Created application folder: {os.path.basename(dir_name)}", "success")
    return dir_name


def tailor_cv(provider, model_id, jd_text, cv_template_html, system_prompt, status_callback):
    prompt = "..." # (Your detailed CV tailoring prompt here)
    return call_ai(provider, model_id, prompt, system_prompt, status_callback)


def generate_anschreiben(provider, model_id, jd_text, tailored_cv_html, core_info, ref_cv_text, system_prompt, status_callback):
    prompt = "..." # (Your detailed Anschreiben generation prompt here)
    return call_ai(provider, model_id, prompt, system_prompt, status_callback)


def save_files(output_dir, company, role, tailored_cv_html, anschreiben_text, status_callback, user_name="ZohaibMalik"):
    """Saves the generated files to the output directory."""
    try:
        safe_role_fn = re.sub(r'[^\w\s-]', '', role).strip().replace(' ', '_')
        html_path = os.path.join(output_dir, f"CV_{user_name}_{safe_role_fn}.html")
        with open(html_path, 'w', encoding='utf-8') as f: f.write(tailored_cv_html)
        status_callback(f"Saved tailored HTML CV to {os.path.basename(html_path)}", "success")

        pdf_path = os.path.join(output_dir, f"CV_{user_name}_{safe_role_fn}.pdf")
        HTML(string=tailored_cv_html).write_pdf(pdf_path)
        status_callback(f"Saved tailored PDF CV to {os.path.basename(pdf_path)}", "success")

        anschreiben_path = os.path.join(output_dir, "Anschreiben.txt")
        with open(anschreiben_path, 'w', encoding='utf-8') as f: f.write(anschreiben_text)
        status_callback(f"Saved Anschreiben to {os.path.basename(anschreiben_path)}", "success")
    except Exception as e:
        status_callback(f"Error saving files: {e}", "error")

# ==============================================================================
# --- MAIN ORCHESTRATOR ---
# ==============================================================================
def run_job_application_logic(provider, jd_text, status_callback):
    """The main logic to be called from any UI (Streamlit, CLI, etc.)."""
    if not initialize_ai_provider(provider, status_callback):
        return

    models = MODELS[provider]
    status_callback(f"Starting Process with '{provider.capitalize()}'...", "info")

    if not jd_text or not jd_text.strip():
        status_callback("Job Description text is empty. Process stopped.", "error")
        return

    company, role = extract_info_from_jd(provider, models["fast"], jd_text, SYSTEM_PROMPT, status_callback)
    if not company or not role:
        status_callback("Could not determine Company and Role. Stopping process.", "error")
        return
    status_callback(f"Identified Role: {role} at {company}", "success")

    job_folder = create_job_directory(company, role, status_callback)

    cv_template_html = read_file_content(TEMPLATE_CV_PATH, status_callback)
    core_info = read_file_content(CORE_INFO_PATH, status_callback)
    reference_cv = read_file_content(REFERENCE_CV_PATH, status_callback)
    if not all([cv_template_html, core_info, reference_cv]): return

    tailored_cv = tailor_cv(provider, models["powerful"], jd_text, cv_template_html, SYSTEM_PROMPT, status_callback)
    # **FIX APPLIED HERE**
    if not tailored_cv or not tailored_cv.strip():
        status_callback("AI failed to generate CV content. Process stopped.", "error")
        return
    status_callback("Successfully tailored CV with AI.", "success")

    anschreiben = generate_anschreiben(provider, models["powerful"], jd_text, tailored_cv, core_info, reference_cv, SYSTEM_PROMPT, status_callback)
    # **FIX APPLIED HERE**
    if not anschreiben or not anschreiben.strip():
        status_callback("AI failed to generate Anschreiben content. Process stopped.", "error")
        return
    status_callback("Successfully generated Anschreiben with AI.", "success")

    save_files(job_folder, company, role, tailored_cv, anschreiben, status_callback)

    status_callback("Automation process completed successfully!", "success")