# job_applicator.py
import os
import sys
import argparse
import pdfplumber

# Import the core logic from the single source of truth
from logic import run_job_application_logic

# --- CLI-Specific File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JD_INPUT_DIR = os.path.join(BASE_DIR, "jds_to_process")


# ==============================================================================
# --- CLI-SPECIFIC HELPER FUNCTIONS ---
# ==============================================================================

def print_status(message, status_type="info"):
    """A callback function to print status updates to the console."""
    emojis = {"info": "▶️", "success": "✅", "error": "❌", "working": "⚙️"}
    print(f"{emojis.get(status_type, '▶️')} {message}")


def find_latest_jd():
    """Finds the most recently modified file in the JD input directory."""
    print_status(f"Scanning for JDs in '{os.path.basename(JD_INPUT_DIR)}'...")
    if not os.path.exists(JD_INPUT_DIR):
        os.makedirs(JD_INPUT_DIR)
        print_status(f"Created JD directory, as it was missing. Please add a JD file.", "error")
        return None

    files = [os.path.join(JD_INPUT_DIR, f) for f in os.listdir(JD_INPUT_DIR) if
             os.path.isfile(os.path.join(JD_INPUT_DIR, f))]
    if not files:
        print_status(f"No files found in '{os.path.basename(JD_INPUT_DIR)}'. Please add a JD file.", "error")
        return None

    latest_file = max(files, key=os.path.getmtime)
    print_status(f"Found latest JD: {os.path.basename(latest_file)}", "success")
    return latest_file


def read_jd_text(file_path):
    """Reads text from a .txt or .pdf file."""
    if not file_path: return None
    text = ""
    try:
        if file_path.lower().endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        else:  # Assume text file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        print_status(f"Error reading JD file '{os.path.basename(file_path)}': {e}", "error")
        return None
    return text


# ==============================================================================
# --- MAIN CLI ORCHESTRATOR ---
# ==============================================================================

def main():
    """The main function to run the CLI workflow."""
    parser = argparse.ArgumentParser(description="AI Job Application Automator (CLI)")
    parser.add_argument(
        '--provider',
        choices=['gemini', 'claude'],
        default='gemini',
        help='The AI provider to use for the generation process.'
    )
    args = parser.parse_args()

    # 1. Find and read the latest job description
    jd_file_path = find_latest_jd()
    jd_text = read_jd_text(jd_file_path)

    # 2. If JD is found, run the core logic, passing the CLI-specific 'print_status' as the callback
    if jd_text:
        run_job_application_logic(args.provider, jd_text, print_status)
    else:
        print_status("Could not read job description. Exiting.", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()