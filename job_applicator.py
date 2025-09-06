import os
import sys
import json
import pdfplumber
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

# NEW: Choose your AI provider here. Options: "claude" or "gemini"
AI_PROVIDER = "gemini"

# --- API Key Loading ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Model Selection Dictionary ---
# This makes it easy to manage and swap models
MODELS = {
    "claude": {
        "fast": "claude-3-haiku-20240307",
        "powerful": "claude-3-5-sonnet-20240620"
    },
    "gemini": {
        "fast": "gemini-1.5-flash-latest",
        "powerful": "gemini-1.5-pro-latest"
    }
}

# --- AI Client Initialization ---
try:
    if AI_PROVIDER == "claude":
        if not ANTHROPIC_API_KEY: raise ValueError("ANTHROPIC_API_KEY not found in .env file.")
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    elif AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY not found in .env file.")
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        raise ValueError(f"Invalid AI_PROVIDER: '{AI_PROVIDER}'. Choose 'claude' or 'gemini'.")
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    sys.exit(1)

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
JD_INPUT_DIR = os.path.join(BASE_DIR, "jds_to_process")
OUTPUT_DIR = os.path.join(BASE_DIR, "Job Applications")


# ==============================================================================
# --- HELPER FUNCTIONS ---
# ==============================================================================

def print_status(message, status="info"):
    emojis = {"info": "▶️", "success": "✅", "error": "❌", "working": "⚙️"}
    print(f"{emojis.get(status, '▶️')} {message}")


# NEW: Unified AI call function for both providers
def call_ai(provider, model_name, prompt, system_prompt):
    """Unified function to call the selected AI provider's API."""
    print_status(f"Calling {provider} model ({model_name})... Please wait.", "working")
    try:
        if provider == "claude":
            message = claude_client.messages.create(
                model=model_name,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        elif provider == "gemini":
            model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        print_status(f"API call to {provider} failed: {e}", "error")
        return None


def find_latest_jd():
    # (This function is unchanged)
    print_status(f"Scanning for JDs in '{JD_INPUT_DIR}'...", "info")
    try:
        if not os.path.exists(JD_INPUT_DIR):
            os.makedirs(JD_INPUT_DIR)
            print_status(f"Created JD directory, as it was missing.", "info")
        files = [os.path.join(JD_INPUT_DIR, f) for f in os.listdir(JD_INPUT_DIR) if
                 os.path.isfile(os.path.join(JD_INPUT_DIR, f))]
        if not files:
            print_status(f"No files found in '{JD_INPUT_DIR}'. Please add a JD file.", "error")
            return None
        latest_file = max(files, key=os.path.getmtime)
        print_status(f"Found latest JD: {os.path.basename(latest_file)}", "success")
        return latest_file
    except Exception as e:
        print_status(f"Error finding latest JD file: {e}", "error")
        return None


def read_file_content(file_path):
    # (This function is unchanged)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print_status(f"File not found: {file_path}", "error")
        return None


def read_jd(file_path):
    # (This function is unchanged)
    if not os.path.exists(file_path):
        print_status(f"Job description file not found at {file_path}", "error")
        return None
    text = ""
    try:
        if file_path.lower().endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        else:
            text = read_file_content(file_path)
    except Exception as e:
        print_status(f"Error reading JD file: {e}", "error")
        return None
    return text


def extract_info_from_jd(provider, model_id, jd_text, system_prompt):
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
    response = call_ai(provider, model_id, prompt, system_prompt)
    if not response: return None, None
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            # Clean up potential markdown formatting from Gemini
            clean_json = json_match.group().replace("```json", "").replace("```", "").strip()
            info = json.loads(clean_json)
            return info.get("company_name"), info.get("job_title")
        else:
            raise json.JSONDecodeError("No JSON object found", response, 0)
    except json.JSONDecodeError:
        print_status("Failed to parse company/role from AI response.", "error")
        return "Unknown Company", "Unknown Role"


def create_job_directory(company, role):
    # (This function is unchanged)
    safe_company = re.sub(r'[^\w\s-]', '', company).strip()
    safe_role = re.sub(r'[^\w\s-]', '', role).strip()
    dir_name = os.path.join(OUTPUT_DIR, f"{safe_company} - {safe_role}")
    os.makedirs(dir_name, exist_ok=True)
    return dir_name


def tailor_cv(provider, model_id, jd_text, cv_template_html, system_prompt):
    """Uses AI to tailor the CV content."""
    prompt = f"""
    You are an expert career coach and CV editor. Your task is to meticulously rewrite and optimize a given HTML CV to perfectly match a specific job description, ensuring no content is lost.

    Here is the Job Description (JD):
    <job_description>{jd_text}</job_description>

    Here is the candidate's base HTML CV:
    <cv_html>{cv_template_html}</cv_html>

    **CRITICAL INSTRUCTIONS:**
    1.  **Analyze and Align:** First, analyze the JD for key skills, technologies, and responsibilities. Then, rewrite the CV's "Professional Summary", "Skills", and "Work Experience" bullet points to align with these requirements. Use keywords from the JD naturally.
    2.  **Preserve Structure:** You MUST maintain the original HTML structure and CSS classes perfectly. Only change the text content.
    3.  **No Invention:** Do NOT invent new experiences, skills, or qualifications. Only rephrase and re-prioritize existing information from the base CV to better match the JD.
    4.  **Ensure Completeness:** All original sections and content from the base CV must be present in your final output, unless they are being replaced by tailored content (like the summary). Do not accidentally delete sections like "Education" or "Projects".
    5.  **Final Quality Check:** Before providing the output, mentally perform this check:
        - Did I preserve all original HTML tags and classes?
        - Is every section from the original CV accounted for in my output?
        - Is the new summary tailored specifically to the JD?
        - Does the output contain ONLY the full, raw HTML code?

    Your final output must be ONLY the full, raw, modified HTML code and nothing else.
    """
    return call_ai(provider, model_id, prompt, system_prompt)


def generate_anschreiben(provider, model_id, jd_text, tailored_cv_html, core_info, reference_cv_text, system_prompt):
    """Uses AI to generate a German cover letter."""
    prompt = f"""
    You are a professional German career writer. Your task is to write a compelling, formal "Anschreiben" (cover letter) in German, based in Germany.

    Here is the Job Description (Stellenbeschreibung):
    <job_description>{jd_text}</job_description>

    Here is the candidate's tailored CV for this specific job:
    <tailored_cv_html>{tailored_cv_html}</tailored_cv_html>

    Here is the candidate's full reference CV for detailed background and experience:
    <full_reference_cv>{reference_cv_text}</full_reference_cv>

    Here is the candidate's personal contact information:
    <user_info>{core_info}</user_info>

    Instructions:
    1. Write the entire cover letter in German.
    2. Follow the correct DIN 5008 format for a formal German business letter (Absender, Empfänger, Datum, Betreff, Anrede, Hauptteil, Grußformel, Unterschrift). The current date is {datetime.now().strftime('%d.%m.%Y')}.
    3. In the main body, connect the candidate's strongest qualifications to the job's requirements. Use the full reference CV to pull specific, compelling examples or project details that are not in the tailored summary.
    4. Synthesize information from all provided sources to create the most convincing letter.
    5. Maintain a confident, professional, and enthusiastic tone.
    6. The output should be only the text of the letter, perfectly formatted.
    """
    return call_ai(provider, model_id, prompt, system_prompt)


def save_files(output_dir, company, role, tailored_cv_html, anschreiben_text, user_name="ZohaibMalik"):
    # (This function is unchanged)
    safe_role_fn = re.sub(r'[^\w\s-]', '', role).strip().replace(' ', '_')
    html_path = os.path.join(output_dir, f"CV_{user_name}_{safe_role_fn}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(tailored_cv_html)
    print_status(f"Saved tailored HTML CV to {html_path}", "success")
    pdf_path = os.path.join(output_dir, f"CV_{user_name}_{safe_role_fn}.pdf")
    HTML(string=tailored_cv_html).write_pdf(pdf_path)
    print_status(f"Saved tailored PDF CV to {pdf_path}", "success")
    anschreiben_path = os.path.join(output_dir, "Anschreiben.txt")
    with open(anschreiben_path, 'w', encoding='utf-8') as f:
        f.write(anschreiben_text)
    print_status(f"Saved Anschreiben to {anschreiben_path}", "success")


# ==============================================================================
# --- MAIN ORCHESTRATOR ---
# ==============================================================================

def main():
    """The main function to run the entire workflow."""
    print_status(f"Starting Job Application Automation Process using '{AI_PROVIDER}'...", "info")

    models = MODELS[AI_PROVIDER]

    # 1. Find and Read JD
    jd_path = find_latest_jd()
    if not jd_path: return
    jd_text = read_jd(jd_path)
    if not jd_text: return

    # 2. Extract Info (using the FAST model)
    company, role = extract_info_from_jd(AI_PROVIDER, models["fast"], jd_text, SYSTEM_PROMPT)
    if not company or not role: return
    print_status(f"Identified Role: {role} at {company}", "success")

    # 3. Create Directory
    job_folder = create_job_directory(company, role)
    print_status(f"Created application folder: {job_folder}", "success")

    # 4. Load Templates
    cv_template_html = read_file_content(TEMPLATE_CV_PATH)
    core_info = read_file_content(CORE_INFO_PATH)
    reference_cv = read_file_content(REFERENCE_CV_PATH)
    if not cv_template_html or not core_info or not reference_cv: return

    # 5. Tailor CV (using the POWERFUL model)
    tailored_cv = tailor_cv(AI_PROVIDER, models["powerful"], jd_text, cv_template_html, SYSTEM_PROMPT)
    if not tailored_cv: return
    print_status("Successfully tailored CV with AI.", "success")

    # 6. Generate Anschreiben (using the POWERFUL model)
    anschreiben = generate_anschreiben(AI_PROVIDER, models["powerful"], jd_text, tailored_cv, core_info, reference_cv,
                                       SYSTEM_PROMPT)
    if not anschreiben: return
    print_status("Successfully generated Anschreiben with AI.", "success")

    # 7. Save all files
    save_files(job_folder, company, role, tailored_cv, anschreiben)

    print_status("Automation process completed successfully!", "success")


if __name__ == "__main__":
    main()