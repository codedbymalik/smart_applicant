# logic.py
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# --- AI Provider and File Conversion Imports ---
import anthropic
import google.generativeai as genai
from weasyprint import HTML

# ==============================================================================
# --- CONFIGURATION & SETUP ---
# ==============================================================================
# Use Pathlib for modern, OS-agnostic path handling
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # Load environment variables from .env file

# --- Template and Output Paths ---
TEMPLATE_CV_PATH = BASE_DIR / "templates" / "cv_template.html"
CORE_INFO_PATH = BASE_DIR / "templates" / "core_info.txt"
REFERENCE_CV_PATH = BASE_DIR / "templates" / "reference_cv.txt"
# Save generated applications to a consistent folder in the user's home directory
OUTPUT_DIR = Path("/Users/zohaibmalik/DATA ENGINEERING/Job_Automator/Job Applications")

# --- API Key Loading ---
# These will be read from environment variables set by the UI (Streamlit/CLI)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- AI Model Selection ---
MODELS = {
    "claude": {"fast": "claude-3-5-haiku-20241022", "powerful": "claude-3-5-haiku-20241022"},
    "gemini": {"fast": "gemini-1.5-flash-latest", "powerful": "gemini-1.5-pro-latest"}
}

# --- System Prompt for Consistent AI Behavior ---
# Removed hardcoded date to ensure timeliness
SYSTEM_PROMPT = """
You are an expert German-based career assistant named "JobBot".
Your user is Zohaib Malik, a Data Engineer. Your goal is to help him create exceptional, tailored job application documents in Germany.
You must be professional, precise, and follow all instructions meticulously.
Adhere strictly to the requested output format in each prompt (e.g., raw JSON, raw HTML, or plain text).
Do not include any conversational text, apologies, or self-corrections in your final output.
"""

# --- Global AI Clients (initialized on demand to save resources) ---
claude_client = None
gemini_configured = False


# ==============================================================================
# --- HELPER FUNCTIONS ---
# ==============================================================================

def initialize_ai_provider(provider, status_callback):
    """Initializes the required AI client if not already done."""
    global claude_client, gemini_configured, ANTHROPIC_API_KEY, GEMINI_API_KEY

    # Refresh API keys from environment in case they were updated
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    try:
        if provider == "claude" and not claude_client:
            if not ANTHROPIC_API_KEY: raise ValueError("ANTHROPIC_API_KEY is not set.")
            claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            status_callback("Claude client initialized.", "info")
        elif provider == "gemini" and not gemini_configured:
            if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY is not set.")
            genai.configure(api_key=GEMINI_API_KEY)
            gemini_configured = True
            status_callback("Gemini client initialized.", "info")
    except ValueError as e:
        status_callback(str(e), "error")
        return False
    return True


def call_ai(provider, model_name, prompt, system_prompt, status_callback):
    """Unified function to call the selected AI provider's API."""
    status_callback(f"Calling {provider} model ({model_name})... This may take a moment.", "working")
    try:
        if provider == "claude":
            message = claude_client.messages.create(
                model=model_name, max_tokens=4096, system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        elif provider == "gemini":
            model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
            # Safety settings to reduce chances of blocking legitimate content
            safety_config = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE', 'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
            response = model.generate_content(prompt, safety_settings=safety_config)
            return response.text
    except Exception as e:
        status_callback(f"API call to {provider} failed: {e}", "error")
        return None


def read_file_content(file_path, status_callback):
    """Reads content from a file and reports errors via callback."""
    try:
        return file_path.read_text(encoding='utf-8')
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
    Example: {{"company_name": "Innovate GmbH", "job_title": "Senior Data Engineer"}}

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
        # Robustly find the JSON blob in the AI's response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            info = json.loads(json_match.group())
            return info.get("company_name", "Unknown Company"), info.get("job_title", "Unknown Role")
        else:
            raise json.JSONDecodeError("No JSON object found in the response.", response, 0)
    except Exception as e:
        status_callback(f"Failed to parse company/role from AI response. Error: {e}", "error")
        return "Unknown Company", "Unknown Role"


def create_job_directory(company, role, status_callback):
    """Creates a sanitized directory for the application files."""
    try:
        safe_company = re.sub(r'[^\w\s-]', '', company).strip()
        safe_role = re.sub(r'[^\w\s-]', '', role).strip()
        dir_name = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')} - {safe_company} - {safe_role}"
        dir_name.mkdir(parents=True, exist_ok=True)
        status_callback(f"Created application folder: {dir_name.name}", "success")
        return dir_name
    except Exception as e:
        status_callback(f"Failed to create directory. Error: {e}", "error")
        return None


def tailor_cv(provider, model_id, jd_text, cv_template_html, system_prompt, status_callback):
    """Generates the tailored CV using the detailed prompt."""
    prompt = f"""
    You are an expert career coach. Your task is to rewrite and optimize a given HTML CV to perfectly match a specific job description.

    Here is the Job Description (JD):
    <job_description>{jd_text}</job_description>

    Here is the candidate's base HTML CV:
    <cv_html>{cv_template_html}</cv_html>

    Instructions:
    1. Analyze the JD for key skills, technologies, and responsibilities.
    2. Rewrite the CV's "Professional Summary", "Skills", and "Work Experience" bullet points to align with the JD's requirements. Use keywords from the JD naturally.
    3. Do NOT invent new experiences. Only rephrase and re-prioritize existing information.
    4. Maintain the original HTML structure and CSS classes. Only change the text content.
    5. Your final output must be ONLY the full, raw, modified HTML code and nothing else. Do not add explanations or markdown backticks.
    """
    return call_ai(provider, model_id, prompt, system_prompt, status_callback)


def generate_anschreiben(provider, model_id, jd_text, tailored_cv_html, core_info, ref_cv_text, system_prompt,
                         status_callback):
    """Generates the Anschreiben (cover letter) using the detailed prompt."""
    current_date = datetime.now().strftime('%d.%m.%Y')
    prompt = f"""
    You are a professional German career writer. Your task is to write a compelling, formal "Anschreiben" (cover letter) in German.

    Here is the Job Description (Stellenbeschreibung):
    <job_description>{jd_text}</job_description>

    Here is the candidate's tailored CV for this specific job:
    <tailored_cv_html>{tailored_cv_html}</tailored_cv_html>

    Here is the candidate's full reference CV for detailed background and experience:
    <full_reference_cv>{ref_cv_text}</full_reference_cv>

    Here is the candidate's personal contact information:
    <user_info>{core_info}</user_info>

    Instructions:
    1. Write the entire cover letter in German.
    2. Follow the correct DIN 5008 format for a formal German business letter (Absender, Empfänger, Datum, Betreff, Anrede, Hauptteil, Grußformel, Unterschrift). The current date is {current_date}.
    3. In the main body, connect the candidate's strongest qualifications to the job's requirements. Use the full reference CV to pull specific, compelling examples.
    4. Synthesize information from all sources to create the most convincing letter.
    5. Maintain a confident, professional, and enthusiastic tone.
    6. The output must be ONLY the plain text of the letter, perfectly formatted. Do not add explanations.
    """
    return call_ai(provider, model_id, prompt, system_prompt, status_callback)


def save_files(output_dir, company, role, tailored_cv_html, anschreiben_text, status_callback, user_name="ZohaibMalik"):
    """Saves the generated CV (HTML/PDF) and Anschreiben (TXT) to the output directory."""
    try:
        safe_role_fn = re.sub(r'[^\w\s-]', '', role).strip().replace(' ', '_')

        # Save HTML CV
        html_path = output_dir / f"CV_{user_name}_{safe_role_fn}.html"
        html_path.write_text(tailored_cv_html, encoding='utf-8')
        status_callback(f"Saved tailored HTML CV to {html_path.name}", "success")

        # Convert HTML to PDF and save
        pdf_path = output_dir / f"CV_{user_name}_{safe_role_fn}.pdf"
        HTML(string=tailored_cv_html).write_pdf(pdf_path)
        status_callback(f"Saved tailored PDF CV to {pdf_path.name}", "success")

        # Save Anschreiben
        anschreiben_path = output_dir / "Anschreiben.txt"
        anschreiben_path.write_text(anschreiben_text, encoding='utf-8')
        status_callback(f"Saved Anschreiben to {anschreiben_path.name}", "success")
    except Exception as e:
        status_callback(f"Error saving files: {e}", "error")


# ==============================================================================
# --- MAIN ORCHESTRATOR ---
# ==============================================================================

def run_job_application_logic(provider, jd_text, status_callback):
    """The main logic orchestrator, callable from any UI (Streamlit, CLI, etc.)."""
    if not initialize_ai_provider(provider, status_callback):
        return None

    models = MODELS[provider]
    status_callback(f"Starting Process with '{provider.capitalize()}'...", "info")

    if not jd_text or not jd_text.strip():
        status_callback("Job Description text is empty. Process stopped.", "error")
        return None

    # Step 1: Extract Company and Role
    company, role = extract_info_from_jd(provider, models["fast"], jd_text, SYSTEM_PROMPT, status_callback)
    status_callback(f"Identified Role: {role} at {company}", "success")

    # Step 2: Create Output Directory
    job_folder = create_job_directory(company, role, status_callback)
    if not job_folder: return None

    # Step 3: Load Template Files
    cv_template_html = read_file_content(TEMPLATE_CV_PATH, status_callback)
    core_info = read_file_content(CORE_INFO_PATH, status_callback)
    reference_cv = read_file_content(REFERENCE_CV_PATH, status_callback)
    if not all([cv_template_html, core_info, reference_cv]): return None

    # Step 4: Tailor CV
    tailored_cv = tailor_cv(provider, models["powerful"], jd_text, cv_template_html, SYSTEM_PROMPT, status_callback)
    if not tailored_cv or not tailored_cv.strip():
        status_callback("AI failed to generate CV content. Process stopped.", "error")
        return None
    status_callback("Successfully tailored CV with AI.", "success")

    # Step 5: Generate Anschreiben
    anschreiben = generate_anschreiben(provider, models["powerful"], jd_text, tailored_cv, core_info, reference_cv,
                                       SYSTEM_PROMPT, status_callback)
    if not anschreiben or not anschreiben.strip():
        status_callback("AI failed to generate Anschreiben content. Process stopped.", "error")
        return None
    status_callback("Successfully generated Anschreiben with AI.", "success")

    # Step 6: Save All Files
    save_files(job_folder, company, role, tailored_cv, anschreiben, status_callback)

    # Return the path to the output folder on success
    return job_folder
