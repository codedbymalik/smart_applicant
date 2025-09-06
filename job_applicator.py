import os
import sys
import json
import pdfplumber
import anthropic
from weasyprint import HTML
from dotenv import load_dotenv
import re
from datetime import datetime  # Added for the date function

# --- CONFIGURATION ---
load_dotenv()

try:
    API_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found in .env file.")
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_CV_PATH = os.path.join(BASE_DIR, "templates", "cv_template.html")
CORE_INFO_PATH = os.path.join(BASE_DIR, "templates", "core_info.txt")
REFERENCE_CV_PATH = os.path.join(BASE_DIR, "templates", "reference_cv.txt")  # NEW: Path to reference CV
JD_INPUT_DIR = os.path.join(BASE_DIR, "jds_to_process")  # NEW: Directory for JDs
OUTPUT_DIR = os.path.join(BASE_DIR, "Job Applications")


# --- HELPER FUNCTIONS ---

def print_status(message, status="info"):
    """Prints a formatted status message."""
    emojis = {"info": "▶️", "success": "✅", "error": "❌", "working": "⚙️"}
    print(f"{emojis.get(status, '▶️')} {message}")


# NEW: Function to find the latest JD file automatically
def find_latest_jd():
    """Finds the most recently modified file in the JD input directory."""
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
    """Reads and returns the content of a given file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print_status(f"File not found: {file_path}", "error")
        return None


def read_jd(file_path):
    """Reads text from a .pdf or .txt file."""
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


def call_ai(prompt, model="claude-sonnet-4-20250514"):
    """Generic function to call the Anthropic API and get a response."""
    print_status(f"Calling AI model ({model})... Please wait.", "working")
    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        print_status(f"API call failed: {e}", "error")
        return None


def extract_info_from_jd(jd_text):
    """Uses AI to extract company name and job title from the JD."""
    prompt = f"""
    Analyze the following job description and extract the company name and the job title.
    Return your answer in a clean JSON format like this:
    {{"company_name": "Example Corp", "job_title": "Senior Developer"}}

    Job Description:
    ---
    {jd_text}
    ---
    """
    response = call_ai(prompt)
    if not response: return None, None

    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            info = json.loads(json_match.group())
            return info.get("company_name"), info.get("job_title")
        else:
            raise json.JSONDecodeError("No JSON object found", response, 0)
    except json.JSONDecodeError:
        print_status("Failed to parse company/role from AI response.", "error")
        return "Unknown Company", "Unknown Role"


def create_job_directory(company, role):
    """Creates a sanitized directory name and the directory itself."""
    safe_company = re.sub(r'[^\w\s-]', '', company).strip()
    safe_role = re.sub(r'[^\w\s-]', '', role).strip()
    dir_name = os.path.join(OUTPUT_DIR, f"{safe_company} - {safe_role}")
    os.makedirs(dir_name, exist_ok=True)
    return dir_name


def tailor_cv(jd_text, cv_template_html):
    """Uses AI to tailor the CV content."""
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
    5. Your final output must be ONLY the full, raw, modified HTML code and nothing else. Do not add explanations.
    """
    return call_ai(prompt)


# MODIFIED: Function now accepts reference_cv_text
def generate_anschreiben(jd_text, tailored_cv_html, core_info, reference_cv_text):
    """Uses AI to generate a German cover letter."""
    # MODIFIED: Prompt is updated to include the full reference CV for better context
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
    return call_ai(prompt)


def save_files(output_dir, company, role, tailored_cv_html, anschreiben_text, user_name="ZohaibMalik"):
    """Saves the generated files to the output directory."""
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


# --- MAIN ORCHESTRATOR ---

# MODIFIED: Main function no longer takes a file path argument
def main():
    """The main function to run the entire workflow."""
    print_status("Starting Job Application Automation Process...", "info")

    # 1. Find and Read JD
    jd_path = find_latest_jd()
    if not jd_path: return
    jd_text = read_jd(jd_path)
    if not jd_text: return

    # 2. Extract Info
    company, role = extract_info_from_jd(jd_text)
    if not company or not role: return
    print_status(f"Identified Role: {role} at {company}", "success")

    # 3. Create Directory
    job_folder = create_job_directory(company, role)
    print_status(f"Created application folder: {job_folder}", "success")

    # 4. Load Templates
    cv_template_html = read_file_content(TEMPLATE_CV_PATH)
    core_info = read_file_content(CORE_INFO_PATH)
    reference_cv = read_file_content(REFERENCE_CV_PATH)  # NEW: Read the reference CV
    if not cv_template_html or not core_info or not reference_cv: return

    # 5. Tailor CV
    tailored_cv = tailor_cv(jd_text, cv_template_html)
    if not tailored_cv: return
    print_status("Successfully tailored CV with AI.", "success")

    # 6. Generate Anschreiben
    # MODIFIED: Pass the reference_cv content to the function
    anschreiben = generate_anschreiben(jd_text, tailored_cv, core_info, reference_cv)
    if not anschreiben: return
    print_status("Successfully generated Anschreiben with AI.", "success")

    # 7. Save all files
    save_files(job_folder, company, role, tailored_cv, anschreiben)

    print_status("Automation process completed successfully!", "success")


# MODIFIED: The execution block is now simpler
if __name__ == "__main__":
    main()