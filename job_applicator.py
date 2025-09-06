# job_applicator.py
import argparse
import sys
from pathlib import Path
import pdfplumber

# Import the core logic from the single source of truth
from logic import run_job_application_logic

# --- CLI-Specific File Paths ---
BASE_DIR = Path(__file__).resolve().parent
JD_INPUT_DIR = BASE_DIR / "jds_to_process"


# ==============================================================================
# --- CLI-SPECIFIC HELPER FUNCTIONS ---
# ==============================================================================

def print_status(message, status_type="info"):
    """A callback function to print colorful status updates to the console."""
    emojis = {"info": "▶️", "success": "✅", "error": "❌", "working": "⚙️"}
    print(f"{emojis.get(status_type, '▶️')} {message}")


def find_latest_jd():
    """Finds the most recently modified file in the JD input directory."""
    print_status(f"Scanning for JDs in '{JD_INPUT_DIR.name}'...")
    if not JD_INPUT_DIR.exists():
        JD_INPUT_DIR.mkdir()
        print_status(f"Created JD directory, as it was missing. Please add a JD file to it.", "error")
        return None

    # Find all files, ignoring directories
    files = [f for f in JD_INPUT_DIR.iterdir() if f.is_file()]
    if not files:
        print_status(f"No files found in '{JD_INPUT_DIR.name}'. Please add a JD file.", "error")
        return None

    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print_status(f"Found latest JD: {latest_file.name}", "success")
    return latest_file


def read_jd_text(file_path: Path):
    """Reads text from a .txt or .pdf file."""
    if not file_path: return None
    text = ""
    try:
        if file_path.suffix.lower() == '.pdf':
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:  # Assume text file for any other extension
            text = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print_status(f"Error reading JD file '{file_path.name}': {e}", "error")
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
        default='gemini',  # Default to Gemini as it's often more accessible
        help='The AI provider to use for the generation process.'
    )
    args = parser.parse_args()

    # 1. Find and read the latest job description file
    jd_file_path = find_latest_jd()
    if not jd_file_path:
        sys.exit(1)

    jd_text = read_jd_text(jd_file_path)

    # 2. If JD text is successfully read, run the core logic
    if jd_text:
        # Pass the CLI-specific 'print_status' function as the callback
        run_job_application_logic(args.provider, jd_text, print_status)
    else:
        print_status("Could not read content from the job description file. Exiting.", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
