"""
job_matcher.py — Job Description Matcher Engine for CareerMate AI.
Features:
  - match_resume_to_jd: Computes match percentage and extracts matching/missing skills.
  - recommend_skills_to_learn: Ranks missing skills by frequency in the JD with "why it matters" notes.
  - highlight_jd_keywords: Generates formatted HTML with highlighted matched and missing keywords in context.
"""

import os
import json
import re
import html
from urllib.parse import quote_plus
from collections import Counter
from typing import Dict, List, Any, Optional
from ats_analyzer import extract_technical_skills

SKILL_NOTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "skill_notes.json")

try:
    import nltk
    from nltk.corpus import stopwords
    try:
        STOPWORDS = set(stopwords.words('english'))
    except Exception:
        nltk.download('stopwords', quiet=True)
        STOPWORDS = set(stopwords.words('english'))
except Exception:
    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
        "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
        "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
        "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
        "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
        "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
        "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
        "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
        "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
        "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
        "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
        "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
        "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
        "you're", "you've", "your", "yours", "yourself", "yourselves", "experience", "role", "work",
        "candidate", "job", "responsibilities", "requirements", "team", "skills", "years", "working"
    }


def _load_skill_notes() -> Dict[str, str]:
    """Load skill explanation notes from data/skill_notes.json."""
    if os.path.exists(SKILL_NOTES_PATH):
        try:
            with open(SKILL_NOTES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def extract_top_jd_keywords(jd_text: str, top_n: int = 12) -> List[str]:
    """
    Extract top domain keywords from a Job Description using frequency analysis
    and stopword filtering.
    """
    words = re.findall(r'\b[a-zA-Z]{3,}\b', jd_text.lower())
    filtered_words = [
        w.capitalize() for w in words
        if w not in STOPWORDS and len(w) > 2 and not w.isdigit()
    ]
    word_counts = Counter(filtered_words)
    return [word for word, count in word_counts.most_common(top_n)]


def recommend_skills_to_learn(missing_skills: List[str], target_role: Optional[str] = None, jd_text: str = "") -> List[Dict[str, Any]]:
    """
    Ranks missing skills by how often they appear in the JD and returns them
    with a short "why it matters" explanation and a link to the Career Roadmap route.
    
    Args:
        missing_skills: List of skills required by JD but missing from the resume
        target_role: Optional name of the target job title
        jd_text: Raw text of the job description for frequency weighting
        
    Returns:
        List of dicts: [{"skill": "...", "frequency": N, "why_it_matters": "...", "roadmap_url": "..."}, ...]
    """
    if not missing_skills:
        return []

    skill_notes = _load_skill_notes()
    jd_lower = jd_text.lower() if jd_text else ""

    ranked = []
    for skill in missing_skills:
        # Count frequency in the JD text
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(skill.lower()) + r'(?![a-zA-Z0-9])'
        freq = len(re.findall(pattern, jd_lower)) if jd_lower else 1
        
        # Get "why it matters" note or build a sensible fallback
        note = skill_notes.get(skill)
        if not note:
            # Check lowercase variant
            note = skill_notes.get(skill.lower())
        if not note:
            role_ctx = target_role if target_role else "this target role"
            note = f"Core industry capability frequently requested in {role_ctx} to ensure production readiness."

        ranked.append({
            "skill": skill,
            "frequency": max(1, freq),
            "why_it_matters": note,
            "roadmap_url": f"/roadmap?focus={quote_plus(skill)}"
        })

    # Sort primarily by frequency descending, secondarily by skill name
    ranked.sort(key=lambda x: (-x["frequency"], x["skill"]))
    return ranked


def highlight_jd_keywords(jd_text: str, matching_skills: List[str], missing_skills: List[str]) -> str:
    """
    Renders the original Job Description text with matching keywords and missing keywords
    highlighted in context using <mark> spans.
    
    - Matches are wrapped in: <mark class="jd-mark match" title="Skill matched in your resume">...</mark>
    - Missing skills are wrapped in: <mark class="jd-mark missing" title="Skill missing from your resume">...</mark>
    """
    if not jd_text:
        return ""

    escaped_text = html.escape(jd_text)
    
    # Sort skills by length descending to match multi-word phrases first (e.g. 'Spring Boot' before 'Spring')
    all_matched = sorted(matching_skills, key=len, reverse=True)
    all_missing = sorted(missing_skills, key=len, reverse=True)

    # Replace matched skills with placeholder tokens to avoid nested replacements
    replacements = {}
    counter = 0

    for s in all_matched:
        pattern = re.compile(r'(?<![a-zA-Z0-9])(' + re.escape(html.escape(s)) + r')(?![a-zA-Z0-9])', re.IGNORECASE)
        for match in pattern.finditer(escaped_text):
            original = match.group(1)
            token = f"__MATCH_TOKEN_{counter}__"
            replacements[token] = f'<mark class="jd-mark match" title="Matched in your resume: {original}">{original}</mark>'
            counter += 1
        escaped_text = pattern.sub(lambda m: f"__MATCH_TOKEN_{counter-1}__", escaped_text)

    for s in all_missing:
        pattern = re.compile(r'(?<![a-zA-Z0-9])(' + re.escape(html.escape(s)) + r')(?![a-zA-Z0-9])', re.IGNORECASE)
        for match in pattern.finditer(escaped_text):
            original = match.group(1)
            token = f"__MISSING_TOKEN_{counter}__"
            replacements[token] = f'<mark class="jd-mark missing" title="Missing in your resume: {original}">{original}</mark>'
            counter += 1
        escaped_text = pattern.sub(lambda m: f"__MISSING_TOKEN_{counter-1}__", escaped_text)

    # Restore placeholders
    for token, replacement in replacements.items():
        escaped_text = escaped_text.replace(token, replacement)

    # Format newlines into HTML paragraphs/breaks
    formatted_html = escaped_text.replace("\n", "<br>")
    return formatted_html


def match_resume_to_jd(resume_text: str, jd_text: str, target_role: Optional[str] = None) -> Dict[str, Any]:
    """
    Matches candidate resume against a job description.
    
    Args:
        resume_text: Extracted plain text of the resume
        jd_text: Text of the target job description
        target_role: Optional target role title
        
    Returns:
        dict containing:
          - match_percentage: int (0-100)
          - matching_skills: list of skills present in both JD and resume
          - missing_skills: list of skills required by JD but missing in resume
          - all_jd_skills: list of all skills identified in JD
          - resume_skills: list of all skills detected in resume
          - jd_keywords: list of top domain keywords from the JD
          - recommended_skills: ranked list of missing skills with "why it matters" notes
          - highlighted_jd_html: original JD text with <mark> tags for contextual highlighting
          - summary_verdict: string (e.g. "Strong Match — Highly Qualified")
    """
    # 1. Extract Skills
    jd_skills = extract_technical_skills(jd_text)
    resume_skills = extract_technical_skills(resume_text)
    
    resume_skills_set = set(s.lower() for s in resume_skills)

    # 2. Map canonical skill names
    matching_skills = [s for s in jd_skills if s.lower() in resume_skills_set]
    missing_skills = [s for s in jd_skills if s.lower() not in resume_skills_set]

    # 3. Compute Match Percentage
    if jd_skills:
        skill_match_ratio = len(matching_skills) / len(jd_skills)
    else:
        skill_match_ratio = 0.5

    jd_tokens = set(w for w in re.findall(r'\b[a-zA-Z]{3,}\b', jd_text.lower()) if w not in STOPWORDS)
    res_tokens = set(w for w in re.findall(r'\b[a-zA-Z]{3,}\b', resume_text.lower()) if w not in STOPWORDS)
    
    token_overlap_ratio = len(jd_tokens.intersection(res_tokens)) / max(len(jd_tokens), 1)

    raw_score = (0.70 * skill_match_ratio + 0.30 * token_overlap_ratio) * 100
    match_percentage = round(raw_score)
    match_percentage = max(10, min(99, match_percentage))

    # 4. Determine Verdict
    if match_percentage >= 80:
        verdict = "Strong Match — Highly Qualified"
    elif match_percentage >= 60:
        verdict = "Good Match — Minor Skill Gaps"
    elif match_percentage >= 40:
        verdict = "Moderate Match — Skill Gaps Identified"
    else:
        verdict = "Low Match — Significant Skills Missing"

    # 5. Extract top JD keywords
    jd_keywords = extract_top_jd_keywords(jd_text, top_n=10)

    # 6. Rank missing skills with "why it matters" notes
    recommended_skills = recommend_skills_to_learn(missing_skills, target_role=target_role, jd_text=jd_text)

    # 7. Highlight keywords in JD text
    highlighted_jd_html = highlight_jd_keywords(jd_text, matching_skills, missing_skills)

    return {
        "match_percentage": match_percentage,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "all_jd_skills": jd_skills,
        "resume_skills": resume_skills,
        "jd_keywords": jd_keywords,
        "recommended_skills": recommended_skills,
        "highlighted_jd_html": highlighted_jd_html,
        "summary_verdict": verdict,
        "stats": {
            "total_jd_skills": len(jd_skills),
            "matched_count": len(matching_skills),
            "missing_count": len(missing_skills)
        }
    }
