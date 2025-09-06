# 🤖 Job Application Automator

Tired of manually tweaking your CV for every job?  
**This project automates the grind** — tailored CVs, German-standard Anschreiben, and neatly organized application folders, all generated with AI. Just feed it a Job Description (JD) and let the automator do its magic. ⚡

---

## ✨ Features

- 📂 **Smart Foldering**  
  Creates a dedicated application folder for each job with company & role names.  

- 📝 **AI-Tailored CV**  
  Reads your HTML CV template and rewrites the summary, skills, and experience sections to match the JD.  

- 💌 **DIN 5008 Anschreiben (Cover Letter)**  
  Automatically generates a German-format cover letter — polished, professional, and JD-specific.  

- 🖨 **Multi-Format Output**  
  Saves your CV as both `.html` and `.pdf`, plus the Anschreiben as `.txt`.  

- 🖥 **Dual Modes**  
  - **CLI mode**: quick runs from the terminal.  
  - **Streamlit UI**: paste your JD text, hit run, and download your tailored files instantly.  

---

## 🛠 Tech Stack

- **Python 3.10+**  
- [Anthropic Claude](https://www.anthropic.com/) & [Google Gemini](https://ai.google.dev/) (AI brains 🧠)  
- [WeasyPrint](https://weasyprint.org/) (HTML → PDF)  
- [pdfplumber](https://pypi.org/project/pdfplumber/) (extract JD text from PDFs)  
- [Streamlit](https://streamlit.io/) (beautiful UI on top of CLI logic)  

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/codedbymalik/smart_applicant.git
cd smart_applicant
```
### TO BE CONTINUED . . . 