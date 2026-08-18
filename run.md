# 🚀 CareerMate.AI — Quickstart & Running Guide

Welcome to **CareerMate.AI**! This comprehensive guide walks you through setting up, configuring, and launching the entire platform locally on your machine.

---

## 📋 Table of Contents
- [Prerequisites](#-prerequisites)
- [Quick Setup (Step-by-Step)](#-quick-setup-step-by-step)
- [Environment Configuration (.env)](#-environment-configuration-env)
- [Launching the Server](#-launching-the-server)
- [Feature Directory & URL Sitemap](#-feature-directory--url-sitemap)
- [Running Automated Verification Tests](#-running-automated-verification-tests)
- [Project Architecture & File Map](#-project-architecture--file-map)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 💻 Prerequisites

Ensure you have the following installed on your system:
- **Python 3.10, 3.11, or 3.12**
- **pip** (Python package installer)
- Modern web browser (Chrome, Edge, Firefox, Brave)

---

## ⚡ Quick Setup (Step-by-Step)

### 1. Open Terminal in the Project Directory
```powershell
cd "d:\CareerMate AI"
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> *If you encounter execution policy restrictions on PowerShell, run:*
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install Required Dependencies
```powershell
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the root directory (a default template is provided) with the following optional keys:

```env
# Flask Secret Key for Sessions
SECRET_KEY=career-mate-ai-super-secret-key-2026

# Optional: Google Gemini API Key for dynamic AI question generation & resume bullets
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: GitHub Personal Access Token to raise GitHub API rate limits
GITHUB_TOKEN=your_github_token_here

# Optional: PostgreSQL Database URL (defaults to local SQLite instance/careermate.db if omitted)
# DATABASE_URL=postgresql://user:password@localhost:5432/careermate_db
```

---

## 🎯 Launching the Server

Start the Flask application:

```powershell
python app.py
```
*(Or directly using the virtual environment executable: `.\.venv\Scripts\python.exe app.py`)*

Once launched, open your browser and navigate to:
👉 **[http://localhost:5000](http://localhost:5000)**

---

## 🌐 Feature Directory & URL Sitemap

| Feature | Direct URL | Description |
| :--- | :--- | :--- |
| 🏠 **Landing Page** | [`/`](http://localhost:5000/) | Platform hero, feature showcase, and quick links. |
| 📊 **Career Dashboard** | [`/dashboard`](http://localhost:5000/dashboard) | 6-card executive metric overview & live activity feed. |
| 🛠️ **Resume Builder** | [`/resume/builder`](http://localhost:5000/resume/builder) | Live interactive builder with Modern, Minimal, Technical templates & PDF export. |
| 🎯 **Question Predictor** | [`/predict`](http://localhost:5000/predict) | Predicts multi-format (MCQ/Short/Code) questions from uploaded resumes. |
| 📄 **ATS Resume Analyzer** | [`/ats`](http://localhost:5000/ats) | Checks parsing compatibility, section completeness, and keyword density. |
| 💼 **Job Matcher** | [`/job-match`](http://localhost:5000/job-match) | Matches resume text against job descriptions and computes skill alignment %. |
| 🎙️ **Mock Interview Simulator** | [`/interview-sim`](http://localhost:5000/interview-sim) | Step-by-step interactive mock interview with 4-tier rubric feedback. |
| 📚 **AI Interview Preparation** | [`/interview-prep`](http://localhost:5000/interview-prep) | Technical, HR behavioral, and personalized resume-aware question banks. |
| 📊 **Skill Gap Analyzer** | [`/skill-gap`](http://localhost:5000/skill-gap) | Analyzes skill coverage % and generates prioritized *"Learn Next"* action steps. |
| 🐙 **GitHub Profile Analyzer** | [`/github-analyzer`](http://localhost:5000/github-analyzer) | Audits commit velocity, documentation health, and generates AI resume bullets. |
| 🔐 **Account Authentication** | [`/login`](http://localhost:5000/login) & [`/register`](http://localhost:5000/register) | Persistent user accounts via Flask-Login & password hashing. |
| 📂 **Account History Hub** | [`/history`](http://localhost:5000/history) | Unified viewer for saved resumes, ATS scans, job matches, and interview reports. |

---

## 🧪 Running Automated Verification Tests

You can verify that all routes and database relations are functioning properly with:

```powershell
python -c "import urllib.request; print('Server Status:', urllib.request.urlopen('http://127.0.0.1:5000').getcode())"
```

---

## 🏗️ Project Architecture & File Map

```
CareerMate AI/
├── app.py                      # Central Flask application router & API endpoints
├── config.py                   # Environment & Database configuration (SQLite / PostgreSQL)
├── models.py                   # SQLAlchemy ORM models (User, Resume, ATSScan, JobMatch, etc.)
├── activity_log.py             # Live session activity logger with relative timestamps
├── ats_analyzer.py             # ATS parsing, scoring, and recommendation engine
├── job_matcher.py              # Resume-to-Job-Description similarity & skill matcher
├── question_generator.py       # Multi-format Question Predictor 2.0 engine
├── interview_prep.py           # Technical, HR, and resume-aware question generator
├── interview_simulator.py      # Mock interview state machine & 4-tier rubric scoring
├── skill_gap.py                # Self-contained skill gap comparison & priority ranking engine
├── github_analyzer.py          # GitHub REST API auditor & AI resume bullet generator
├── resume_builder.py           # Resume Builder blueprint & multi-template PDF generator
├── resume_ai.py                # AI STAR bullet point synthesizer & content helper
│
├── data/
│   └── skills_taxonomy.json    # Comprehensive tech skills, tools & alias mappings
│
├── templates/                  # Dark glassmorphic Jinja2 HTML templates
│   ├── front.html              # Landing page & primary navigation
│   ├── dashboard.html          # Executive 6-card Career Dashboard
│   ├── ats.html & ats_results.html
│   ├── job_match.html & job_match_results.html
│   ├── interview_sim.html & interview_sim_results.html
│   ├── skill_gap.html & skill_gap_results.html
│   ├── github_analyzer.html & github_results.html
│   ├── auth/                   # login.html & register.html
│   └── history/                # account_history.html
│
├── static/                     # CSS stylesheets, client JavaScript, and brand assets
│   ├── css/                    # front.css, dashboard styling, animations
│   └── assets/logo.png         # CareerMate AI logo
│
├── instance/
│   └── careermate.db           # Local SQLite relational database (auto-created)
├── requirements.txt            # Python dependencies
└── run.md                      # This running guide
```

---

## ❓ Troubleshooting & FAQs

#### Q: How do I switch to a PostgreSQL database for production?
Simply set the `DATABASE_URL` environment variable in your production environment (e.g. on Render, Heroku, or Railway):
```bash
export DATABASE_URL="postgresql://username:password@hostname:5432/dbname"
```
The application will automatically detect PostgreSQL and use it without code modifications.

#### Q: Can visitors use the tools without signing in?
**Yes!** All analyzer and prediction engines operate seamlessly in **Demo Mode** for visitors. Creating a free account enables permanent database saving, historical comparisons, and custom resume management.

#### Q: What if I don't have a Gemini API key?
The application includes robust built-in fallback generators for all questions, bullet points, and roadmap stages so all features remain functional even without an external API key.

---

*Enjoy building your career with CareerMate AI!* 🚀
