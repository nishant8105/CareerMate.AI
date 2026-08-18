"""
resume_ai.py — AI-assisted content helper for CareerMate AI.
Provides:
  - call_llm: Provider-agnostic LLM caller (Google Gemini / OpenAI / mock fallback)
  - generate_bullet_points: Transforms rough notes into polished resume bullet points
  - suggest_improvements: Comprehensive resume review for weak verbs, missing metrics, etc.
"""

import os
import re
from typing import List, Dict, Any


def get_api_key() -> str:
    """Retrieve the LLM API key from environment variables."""
    return os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY", "")


def call_llm(prompt: str) -> str:
    """
    Simple provider-agnostic wrapper to execute an LLM prompt.
    Uses google-genai (Gemini 2.0 Flash) if available and configured.
    Falls back gracefully if the API key is missing or call fails.
    """
    api_key = get_api_key()
    if not api_key or api_key in ("your_api_key_here", "your_gemini_api_key_here"):
        return ""

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return (response.text or "").strip()
    except Exception as e:
        # Fallback without raising unhandled exceptions
        return ""


def _fallback_bullets(role_or_project: str, raw_notes: str) -> List[str]:
    """Generate smart, professional fallback bullet points when LLM is unavailable."""
    notes = raw_notes.strip() if raw_notes else ""
    target = role_or_project.strip() if role_or_project else "Role/Project"

    if not notes:
        return [
            f"Spearheaded development and implementation of key features for {target}.",
            f"Collaborated with cross-functional teams to optimize performance and code maintainability.",
            f"Engineered robust solutions adhering to modern software engineering best practices."
        ]

    # Split notes by lines or sentences
    chunks = [c.strip(" -•*") for c in re.split(r'[\n;.]+', notes) if len(c.strip(" -•*")) > 5]
    action_verbs = ["Architected", "Engineered", "Implemented", "Spearheaded", "Optimized", "Designed"]
    
    bullets = []
    for i, chunk in enumerate(chunks[:3]):
        verb = action_verbs[i % len(action_verbs)]
        # If chunk already starts with an action verb, keep it
        first_word = chunk.split()[0] if chunk.split() else ""
        if first_word.capitalize() in action_verbs:
            bullets.append(f"{chunk[0].upper()}{chunk[1:]}.")
        else:
            bullets.append(f"{verb} {chunk[0].lower()}{chunk[1:]} to deliver high-quality outcomes.")

    while len(bullets) < 2:
        bullets.append(f"Successfully contributed to {target} while ensuring high quality standards.")

    return bullets[:4]


def generate_bullet_points(role_or_project: str, raw_notes: str) -> List[str]:
    """
    Transforms rough project or experience notes into 2 to 4 polished resume bullet points.
    
    Args:
        role_or_project: Name of the role (e.g. 'Software Engineer at ABC') or project name
        raw_notes: User's unstructured or rough description
        
    Returns:
        List of 2-4 formatted bullet points (without leading bullet characters)
    """
    prompt = f"""You are an elite resume consultant.
Convert the following rough notes about a role or project into 2 to 4 high-impact resume bullet points.

Rules:
1. Start each bullet point with a strong action verb (e.g., Architected, Spearheaded, Engineered, Streamlined, Accelerated).
2. Quantify results, metrics, or technologies where possible.
3. Keep each bullet concise (under 25 words).
4. Do NOT use first-person pronouns (I, me, my, we).
5. Output ONLY the bullet points, one per line, starting with a dash (- ).

Target Role / Project: {role_or_project}
User Notes: {raw_notes}
"""
    llm_output = call_llm(prompt)
    if llm_output:
        lines = [
            line.strip(" -•*–\t\r") 
            for line in llm_output.split("\n") 
            if line.strip(" -•*–\t\r")
        ]
        if lines:
            return lines[:4]

    # Offline / graceful fallback
    return _fallback_bullets(role_or_project, raw_notes)


def suggest_improvements(resume_data: Dict[str, Any]) -> List[str]:
    """
    Reviews the full resume data to identify weak verbs, missing metrics,
    short skills list, missing sections, and suggests actionable enhancements.
    
    Args:
        resume_data: Dictionary containing resume fields (personal, education,
                     experience, internships, projects, skills, certifications, etc.)
                     
    Returns:
        List of actionable improvement suggestion strings
    """
    heuristic_suggestions = []
    
    # 1. Check Personal / Links
    personal = resume_data.get("personal", {}) if isinstance(resume_data.get("personal"), dict) else {}
    if not personal.get("linkedin") and not resume_data.get("LinkedIn"):
        heuristic_suggestions.append("Add your LinkedIn profile URL to boost recruiter visibility and credibility.")
    if not personal.get("github") and not resume_data.get("GitHub"):
        heuristic_suggestions.append("Include your GitHub URL or portfolio link to showcase code samples.")
    if not resume_data.get("summary"):
        heuristic_suggestions.append("Add a 2-3 sentence Professional Summary at the top to highlight your core strengths.")

    # 2. Check Skills Count
    skills = resume_data.get("skills", {})
    if isinstance(skills, dict):
        tech_skills = skills.get("technical", [])
        tools = skills.get("tools", [])
        total_skills = len(tech_skills) + len(tools) + len(skills.get("soft", []))
    elif isinstance(skills, list):
        total_skills = len(skills)
    elif isinstance(skills, str):
        total_skills = len([s for s in re.split(r'[,;\n]+', skills) if s.strip()])
    else:
        total_skills = 0

    if total_skills < 5:
        heuristic_suggestions.append("Expand your Skills section (target at least 6-10 technical skills & tools relevant to target roles).")

    # 3. Check Experience / Projects for missing metrics & weak action verbs
    weak_verbs = {"helped", "worked", "did", "made", "responsible", "handled", "assisted", "tried", "was part"}
    has_metrics = False
    has_weak_verb = False
    
    combined_texts = []
    
    # Check experience & internships
    for section_key in ("experience", "internships", "projects"):
        items = resume_data.get(section_key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    desc = item.get("description", "")
                    combined_texts.append(desc)
                elif isinstance(item, str):
                    combined_texts.append(item)
        elif isinstance(items, str):
            combined_texts.append(items)

    for text in combined_texts:
        if any(char.isdigit() or char in "%$" for char in text):
            has_metrics = True
        words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
        if words.intersection(weak_verbs):
            has_weak_verb = True

    if not has_metrics and combined_texts:
        heuristic_suggestions.append("Quantify your achievements (e.g., 'improved performance by 30%', 'managed 5+ microservices', '10K+ active users').")
    
    if has_weak_verb:
        heuristic_suggestions.append("Replace passive verbs (like 'helped', 'worked on') with powerful action verbs (e.g., 'Architected', 'Optimized', 'Delivered').")

    # 4. Check Certifications & Achievements
    certs = resume_data.get("certifications", [])
    if not certs or (isinstance(certs, list) and len(certs) == 0):
        heuristic_suggestions.append("Include relevant Certifications (e.g., AWS, GCP, Coursera, HackerRank) to validate your technical skills.")

    # 5. If LLM is available, combine with deep AI review
    prompt = f"""You are a senior tech recruiter and resume evaluator.
Review this candidate's resume data and provide 3-4 highly specific, actionable suggestions for improvement.

Focus on:
1. Impact and metric quantification
2. Strong action verbs
3. Skill relevancy and keyword optimization
4. Missing high-value sections

Resume Data:
{resume_data}

Output format:
Return ONLY the suggestions, one per line starting with a dash (- ). Keep each under 25 words.
"""
    llm_output = call_llm(prompt)
    if llm_output:
        ai_lines = [
            line.strip(" -•*–\t\r") 
            for line in llm_output.split("\n") 
            if line.strip(" -•*–\t\r")
        ]
        if ai_lines:
            # Combine unique suggestions
            merged = []
            for s in ai_lines + heuristic_suggestions:
                if s and s not in merged:
                    merged.append(s)
            return merged[:5]

    # Return curated heuristic suggestions
    return heuristic_suggestions[:5] if heuristic_suggestions else [
        "Include measurable impact with percentages, throughput, or user metrics.",
        "Ensure every bullet point starts with a strong past-tense action verb.",
        "Tailor technical skills and keywords directly to your target job descriptions."
    ]
