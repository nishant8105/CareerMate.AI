"""
ats_analyzer.py — ATS Resume Analyzer Engine for CareerMate AI.
Features:
  - extract_text_from_pdf: Extracts plain text using PyMuPDF / pypdf.
  - parse_resume_sections: Segments document into structured sections via regex heuristics.
  - extract_technical_skills: Identifies tech/soft skills using data/skills_taxonomy.json with alias/fuzzy matching.
  - generate_recommendations: Creates specific, actionable, numbered improvements based on score breakdown.
  - compute_ats_score: Calculates overall ATS score (0-100), sub-scores, missing sections, and weak areas.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "skills_taxonomy.json")

ACTION_VERBS = {
    "architected", "engineered", "developed", "spearheaded", "implemented", "optimized", "designed",
    "built", "orchestrated", "deployed", "scaled", "automated", "streamlined", "accelerated", "enhanced",
    "executed", "formulated", "led", "managed", "created", "constructed", "integrated", "produced"
}

WEAK_VERBS = {
    "helped", "worked", "did", "made", "responsible for", "assisted", "tried", "was part of", "handled"
}


def _load_taxonomy() -> Dict[str, Any]:
    """Load the skills taxonomy JSON file with graceful fallback."""
    if os.path.exists(TAXONOMY_PATH):
        try:
            with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "languages": ["Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "SQL", "HTML5", "CSS3"],
        "frameworks": ["React", "Angular", "Vue.js", "Next.js", "Node.js", "Django", "Flask", "FastAPI", "Spring Boot"],
        "tools": ["Git", "GitHub", "Docker", "Kubernetes", "AWS", "GCP", "Linux", "PostgreSQL", "MongoDB"],
        "soft_skills": ["Leadership", "Communication", "Problem Solving", "Team Collaboration", "Agile", "Scrum"],
        "aliases": {}
    }

TAXONOMY_DATA = _load_taxonomy()


def extract_text_from_pdf(pdf_source) -> str:
    """
    Extract raw text from a PDF file object, file path, or bytes.
    Uses PyMuPDF (fitz) with fallback to pypdf.
    """
    text = ""
    try:
        if fitz:
            if hasattr(pdf_source, 'read'):
                stream_bytes = pdf_source.read()
                if hasattr(pdf_source, 'seek'):
                    pdf_source.seek(0)
                doc = fitz.open(stream=stream_bytes, filetype="pdf")
            elif isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                doc = fitz.open(pdf_source)

            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            if text.strip():
                return text.strip()
    except Exception:
        pass

    # Fallback to pypdf
    try:
        if PdfReader:
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
            reader = PdfReader(pdf_source)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception:
        pass

    return text.strip()


def parse_resume_sections(text: str) -> Dict[str, Any]:
    """
    Segments resume text into structured components:
    contact info, summary, education, experience, projects, skills, certifications, achievements.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # 1. Contact Extraction
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', text)
    linkedin_match = re.search(r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', text, re.IGNORECASE)
    github_match = re.search(r'https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+', text, re.IGNORECASE)

    candidate_name = lines[0] if lines and len(lines[0].split()) <= 4 else "Candidate"
    
    contact_info = {
        "name": candidate_name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "linkedin": linkedin_match.group(0) if linkedin_match else "",
        "github": github_match.group(0) if github_match else ""
    }

    # 2. Section Heading Matchers
    section_patterns = {
        "summary": r'(?:summary|professional summary|profile|about me|objective)',
        "education": r'(?:education|academic qualifications?|academic background|academics)',
        "experience": r'(?:experience|work experience|employment history|work history|professional experience|internships?)',
        "projects": r'(?:projects|personal projects|academic projects|key projects)',
        "skills": r'(?:skills|technical skills|core competencies|technologies|tools & technologies|expertise)',
        "certifications": r'(?:certifications?|licenses?|credentials?|courses?|training)',
        "achievements": r'(?:achievements?|awards?|honors?|accomplishments?|extracurricular)'
    }

    sections = {k: [] for k in section_patterns.keys()}
    sections["other"] = []
    
    current_section = "other"
    for line in lines:
        cleaned_lower = line.lower().strip(" :#-_")
        matched_section = None
        
        if len(cleaned_lower.split()) <= 5:
            for sec_key, pattern in section_patterns.items():
                if re.fullmatch(pattern, cleaned_lower):
                    matched_section = sec_key
                    break
        
        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)

    parsed = {
        "raw_text": text,
        "contact_info": contact_info,
        "summary": "\n".join(sections["summary"]),
        "education": "\n".join(sections["education"]),
        "experience": "\n".join(sections["experience"]),
        "projects": "\n".join(sections["projects"]),
        "skills": "\n".join(sections["skills"]),
        "certifications": "\n".join(sections["certifications"]),
        "achievements": "\n".join(sections["achievements"]),
        "other": "\n".join(sections["other"])
    }

    return parsed


def extract_technical_skills(text: str) -> List[str]:
    """
    Extracts all technical and soft skills present in the text using
    the data/skills_taxonomy.json dictionary and alias/fuzzy normalization.
    
    Returns:
        Deduplicated list of canonical skill names (e.g. ['Python', 'React', 'Docker', 'PostgreSQL'])
    """
    taxonomy = _load_taxonomy()
    text_lower = text.lower()
    
    found_skills = set()
    
    # 1. Direct and category lookup
    all_categories = ["languages", "frameworks", "tools", "soft_skills"]
    for cat in all_categories:
        for skill in taxonomy.get(cat, []):
            pattern = r'(?<![a-zA-Z0-9])' + re.escape(skill.lower()) + r'(?![a-zA-Z0-9])'
            if re.search(pattern, text_lower):
                found_skills.add(skill)

    # 2. Aliases & Fuzzy Variants (e.g. "React.js" -> "React", "K8s" -> "Kubernetes", "Postgres" -> "PostgreSQL")
    aliases = taxonomy.get("aliases", {})
    for alias_key, canonical in aliases.items():
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias_key.lower()) + r'(?![a-zA-Z0-9])'
        if re.search(pattern, text_lower):
            found_skills.add(canonical)

    return sorted(list(found_skills))


def generate_recommendations(parsed_resume: Dict[str, Any], score_breakdown: Dict[str, Any]) -> List[str]:
    """
    Generates specific, actionable, numbered recommendations to improve the resume ATS score.
    
    Args:
        parsed_resume: The output of parse_resume_sections
        score_breakdown: Dictionary containing overall_score and sub_scores
        
    Returns:
        List of actionable recommendation strings
    """
    recs = []
    text_lower = parsed_resume.get("raw_text", "").lower()
    contact = parsed_resume.get("contact_info", {})
    sub_scores = score_breakdown.get("sub_scores", {})
    
    # 1. Contact & Links Recommendations
    if not contact.get("email"):
        recs.append("Add a clear email address at the top of your resume so recruiters can contact you.")
    if not contact.get("phone"):
        recs.append("Include your phone number in standard international or local format.")
    if not contact.get("linkedin"):
        recs.append("Add your customized LinkedIn profile URL to verify your professional background.")
    if not contact.get("github"):
        recs.append("Include your GitHub profile or live portfolio link to showcase code and projects.")

    # 2. Section Completeness Recommendations
    if not parsed_resume.get("skills"):
        recs.append("Add a dedicated 'Skills' or 'Technical Skills' section — none was detected.")
    elif len(extract_technical_skills(parsed_resume.get("skills", ""))) < 5:
        recs.append("Expand your Skills section to include at least 6-10 specific technologies, languages, and tools.")

    if not parsed_resume.get("experience") and not parsed_resume.get("projects"):
        recs.append("Add a 'Work Experience' or 'Projects' section detailing your hands-on achievements.")

    if not parsed_resume.get("summary"):
        recs.append("Include a 2-3 sentence Professional Summary at the top highlighting your core value proposition.")

    if not parsed_resume.get("certifications"):
        recs.append("Add a 'Certifications' section (e.g., AWS, Coursera, HackerRank) to demonstrate continuous learning.")

    # 3. Formatting & Word Count Recommendations
    word_count = len(parsed_resume.get("raw_text", "").split())
    if word_count < 250:
        recs.append(f"Your resume is relatively brief ({word_count} words). Aim for 350-700 words to provide adequate depth.")
    elif word_count > 1100:
        recs.append(f"Your resume is {word_count} words. Condense it to 1-2 pages to ensure high readability.")

    # 4. Metrics & Impact Recommendations
    metrics = re.findall(r'\b(?:\d+%(?:\.\d+)?|\$\d+|\d+\+|\d+k|\d+m|\d+\s*(?:users|clients|projects|ms|seconds|x))\b', text_lower)
    if len(metrics) < 2:
        recs.append("Quantify at least 2 to 3 bullet points in your Experience or Projects section (e.g., 'boosted speed by 35%', 'handled 5k+ daily requests').")

    # 5. Action Verbs Recommendations
    words_in_doc = set(re.findall(r'\b[a-zA-Z]+\b', text_lower))
    has_weak = bool(words_in_doc.intersection(WEAK_VERBS))
    strong_verb_count = len(words_in_doc.intersection(ACTION_VERBS))
    
    if has_weak or strong_verb_count < 3:
        recs.append("Replace passive phrases ('worked on', 'helped with') with powerful action verbs ('Architected', 'Engineered', 'Optimized', 'Delivered').")

    # 6. Fallback general recommendation if resume is already high scoring
    if not recs:
        recs.append("Tailor your technical keywords directly to specific job descriptions before each application.")
        recs.append("Ensure consistent bullet point punctuation and chronological order across all roles.")

    return recs[:7]


def compute_ats_score(parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a parsed resume and computes:
      - Overall ATS Score (0 - 100)
      - Sub-scores for Formatting, Section Completeness, and Keyword Density
      - List of missing sections
      - List of weak areas
      - Detected technical & soft skills
      - Specific, numbered recommendations
    """
    raw_text = parsed_resume.get("raw_text", "")
    text_lower = raw_text.lower()
    contact = parsed_resume.get("contact_info", {})
    
    # -------------------------------------------------------------
    # 1. Section Completeness Sub-Score (0-100)
    # -------------------------------------------------------------
    completeness_score = 0
    missing_sections = []
    strengths = []
    weak_areas = []

    # Contact Info
    if contact.get("email") and contact.get("phone"):
        completeness_score += 20
        strengths.append("Complete contact details (Email & Phone detected).")
    else:
        if not contact.get("email"):
            weak_areas.append("Missing or unreadable email address.")
        if not contact.get("phone"):
            weak_areas.append("Missing or unreadable phone number.")

    # Education
    if parsed_resume.get("education") or any(deg in text_lower for deg in ["bachelor", "master", "b.tech", "b.e", "b.s", "m.s", "university", "college", "cgpa", "gpa"]):
        completeness_score += 25
        strengths.append("Education section clearly recognized.")
    else:
        missing_sections.append("Education")
        weak_areas.append("No clear Education section found.")

    # Experience or Projects
    has_exp = bool(parsed_resume.get("experience"))
    has_proj = bool(parsed_resume.get("projects"))
    if has_exp and has_proj:
        completeness_score += 30
        strengths.append("Both Work Experience and Projects sections present.")
    elif has_exp or has_proj:
        completeness_score += 22
        strengths.append("Practical experience or project work detected.")
    else:
        missing_sections.append("Work Experience / Projects")
        weak_areas.append("Missing Work Experience and Projects sections.")

    # Skills
    extracted_skills = extract_technical_skills(raw_text)
    if parsed_resume.get("skills") or len(extracted_skills) >= 3:
        completeness_score += 20
        strengths.append(f"Identified {len(extracted_skills)} technical and domain skills.")
    else:
        missing_sections.append("Skills")
        weak_areas.append("Missing a dedicated Skills section.")

    # Summary or Certifications
    if parsed_resume.get("summary"):
        completeness_score += 5
    else:
        missing_sections.append("Professional Summary")

    if not parsed_resume.get("certifications"):
        missing_sections.append("Certifications / Courses")

    completeness_score = min(100, completeness_score)

    # -------------------------------------------------------------
    # 2. Formatting Sub-Score (0-100)
    # -------------------------------------------------------------
    formatting_score = 40  # baseline

    if contact.get("email"):
        formatting_score += 15
    if contact.get("phone"):
        formatting_score += 15
    if contact.get("linkedin"):
        formatting_score += 15
        strengths.append("LinkedIn profile link included for recruiter verification.")
    else:
        weak_areas.append("No LinkedIn profile link detected.")

    if contact.get("github"):
        formatting_score += 15
        strengths.append("GitHub or Portfolio link included.")

    word_count = len(raw_text.split())
    if 250 <= word_count <= 1000:
        formatting_score = min(100, formatting_score)
    elif word_count < 200:
        formatting_score = max(30, formatting_score - 20)
        weak_areas.append("Resume is too brief (less than 200 words). Add more details.")
    elif word_count > 1200:
        formatting_score = max(50, formatting_score - 10)
        weak_areas.append("Resume may be too lengthy. Aim for a concise 1 to 2 page format.")

    formatting_score = min(100, max(20, formatting_score))

    # -------------------------------------------------------------
    # 3. Keyword Density & Action Verbs Sub-Score (0-100)
    # -------------------------------------------------------------
    keyword_score = 0
    words_in_doc = set(re.findall(r'\b[a-zA-Z0-9+#.-]+\b', text_lower))
    
    # Check tech keywords
    tech_count = len(extracted_skills)
    if tech_count >= 10:
        keyword_score += 40
        strengths.append(f"Strong industry keyword presence ({tech_count}+ skills detected).")
    elif tech_count >= 5:
        keyword_score += 25
    elif tech_count >= 2:
        keyword_score += 15
    else:
        weak_areas.append("Low technical keyword density. Include relevant industry tools & languages.")

    # Check strong action verbs
    matched_verbs = ACTION_VERBS.intersection(words_in_doc)
    verb_count = len(matched_verbs)
    if verb_count >= 5:
        keyword_score += 30
        strengths.append("Effective use of strong action verbs (e.g., Developed, Architected, Engineered).")
    elif verb_count >= 2:
        keyword_score += 18
    else:
        weak_areas.append("Lacks strong action verbs. Replace passive phrasing with impact verbs.")

    # Check for quantifiable metrics
    metrics = re.findall(r'\b(?:\d+%(?:\.\d+)?|\$\d+|\d+\+|\d+k|\d+m|\d+\s*(?:users|clients|projects|ms|seconds|x))\b', text_lower)
    if len(metrics) >= 3:
        keyword_score += 30
        strengths.append("Well-quantified accomplishments with numbers and metrics.")
    elif len(metrics) >= 1:
        keyword_score += 15
    else:
        weak_areas.append("Missing quantifiable metrics (e.g., 'improved by 25%', 'served 10k+ users').")

    keyword_score = min(100, max(20, keyword_score))

    # -------------------------------------------------------------
    # Overall Score Calculation
    # -------------------------------------------------------------
    overall_score = round(0.30 * formatting_score + 0.35 * completeness_score + 0.35 * keyword_score)
    overall_score = max(10, min(99, overall_score))

    # Clean duplicates
    missing_sections = list(dict.fromkeys(missing_sections))
    weak_areas = list(dict.fromkeys(weak_areas))
    strengths = list(dict.fromkeys(strengths))

    score_breakdown = {
        "overall_score": overall_score,
        "sub_scores": {
            "formatting": formatting_score,
            "section_completeness": completeness_score,
            "keyword_density": keyword_score
        }
    }

    # Generate specific numbered recommendations
    recommendations = generate_recommendations(parsed_resume, score_breakdown)

    return {
        "overall_score": overall_score,
        "sub_scores": score_breakdown["sub_scores"],
        "missing_sections": missing_sections,
        "weak_areas": weak_areas,
        "strengths": strengths,
        "detected_skills": extracted_skills,
        "recommendations": recommendations,
        "parsed_data": {
            "name": contact.get("name", "Candidate"),
            "email": contact.get("email", "Not found"),
            "phone": contact.get("phone", "Not found"),
            "tech_keywords_found": extracted_skills[:15],
            "word_count": word_count
        }
    }
