"""
interview_prep.py — AI Interview Preparation Module for CareerMate AI.
Features:
  - generate_technical_questions(role, n)
  - generate_hr_questions(n)
  - generate_resume_based_questions(resume_text, role, n)
  - Uses call_llm() with prompt templates, ATS section parsing, and fallback generation.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from resume_ai import call_llm
from ats_analyzer import parse_resume_sections, extract_technical_skills

QUESTIONS_BANK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "interview_questions.json")

SUPPORTED_ROLES = [
    "Python Developer",
    "Data Scientist",
    "ML Engineer",
    "Web Developer",
    "Data Analyst",
    "Software Developer"
]


def _load_fallback_bank() -> Dict[str, List[str]]:
    """Load static fallback question bank from data/interview_questions.json."""
    if os.path.exists(QUESTIONS_BANK_PATH):
        try:
            with open(QUESTIONS_BANK_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _parse_llm_question_lines(text: str, limit: int = 10) -> List[str]:
    """Clean and parse numbered/bulleted question lines from LLM response."""
    lines = text.strip().split("\n")
    questions = []
    for line in lines:
        cleaned = re.sub(r'^\s*(?:\d+[\.\)]|\-|\*|Q\d+:?)\s*', '', line).strip()
        cleaned = re.sub(r'^[\"\']|[\"\']$', '', cleaned).strip()
        if len(cleaned) > 15 and ('?' in cleaned or cleaned.startswith(('Explain', 'Describe', 'Tell', 'How', 'What', 'Discuss', 'Why', 'Walk', 'Given'))):
            if not cleaned.endswith('?') and not cleaned.endswith('.'):
                cleaned += '?'
            questions.append(cleaned)
            if len(questions) >= limit:
                break
    return questions


def generate_technical_questions(role: str, n: int = 10) -> List[str]:
    """
    Generate role-specific technical interview questions using LLM with static fallback.
    """
    role_clean = role if role in SUPPORTED_ROLES else "Software Developer"
    prompt = (
        f"You are an expert technical hiring manager interviewing candidates for a '{role_clean}' position. "
        f"Generate {n} challenging, realistic, and insightful technical interview questions covering core architecture, "
        f"frameworks, best practices, debugging, and real-world system design scenarios for this role. "
        f"Do not include introductory text or markdown commentary. Return ONLY the questions numbered 1 to {n}."
    )

    try:
        raw_response = call_llm(prompt)
        parsed = _parse_llm_question_lines(raw_response, limit=n)
        if len(parsed) >= min(3, n):
            return parsed[:n]
    except Exception:
        pass

    # Static Fallback
    bank = _load_fallback_bank()
    role_questions = bank.get(role_clean, bank.get("Software Developer", []))
    if role_questions:
        return role_questions[:n]

    return [
        f"Explain the end-to-end architecture of a major system you built as a {role_clean}.",
        "How do you optimize performance and identify bottlenecks in your code?",
        "Describe how you design modular, maintainable, and well-tested services.",
        "What debugging strategies do you employ when resolving production incidents?",
        "How do you evaluate and integrate third-party APIs and libraries into your application?"
    ][:n]


def generate_hr_questions(n: int = 10) -> List[str]:
    """
    Generate behavioral and HR interview questions (STAR methodology, leadership, conflict).
    """
    prompt = (
        f"You are an experienced HR Director conducting behavioral and culture-fit interviews for engineering talent. "
        f"Generate {n} high-impact behavioral interview questions evaluating the STAR method (Situation, Task, Action, Result), "
        f"teamwork, handling tight deadlines, conflict resolution, failure recovery, and professional growth. "
        f"Return ONLY the questions numbered 1 to {n} without conversational filler."
    )

    try:
        raw_response = call_llm(prompt)
        parsed = _parse_llm_question_lines(raw_response, limit=n)
        if len(parsed) >= min(3, n):
            return parsed[:n]
    except Exception:
        pass

    # Static Fallback
    bank = _load_fallback_bank()
    hr_questions = bank.get("HR_Behavioral", [])
    if hr_questions:
        return hr_questions[:n]

    return [
        "Tell me about a time you had to deliver a critical project under a tight deadline. How did you prioritize?",
        "Describe a situation where you had a technical disagreement with a colleague. How was it resolved?",
        "Give an example of a mistake you made in a past project and the lessons you learned from it.",
        "How do you stay motivated and continuously upskill with emerging technologies?",
        "Tell me about a time you went above and beyond your assigned responsibilities to help your team succeed."
    ][:n]


def generate_resume_based_questions(resume_text: str, role: str = "Software Developer", n: int = 8) -> List[str]:
    """
    Builds personalized interview questions that reference the candidate's actual
    projects, experience, and technologies extracted from their resume.
    """
    if not resume_text or len(resume_text.strip()) < 30:
        return []

    # Parse resume sections
    parsed = parse_resume_sections(resume_text)
    detected_skills = extract_technical_skills(resume_text)
    
    projects_text = parsed.get("sections", {}).get("projects", "")
    experience_text = parsed.get("sections", {}).get("experience", "")
    skills_text = ", ".join(detected_skills[:12]) if detected_skills else "Software Engineering Tools"

    resume_summary_context = (
        f"Candidate Target Role: {role}\n"
        f"Extracted Skills: {skills_text}\n"
        f"Experience Highlights: {experience_text[:500]}\n"
        f"Project Highlights: {projects_text[:500]}\n"
    )

    prompt = (
        f"You are a principal interviewer conducting a deep technical interview for a '{role}' candidate. "
        f"Here are excerpts from the candidate's resume:\n\n"
        f"{resume_summary_context}\n\n"
        f"Generate {n} personalized, probing interview questions directly referencing their specific projects, "
        f"tools, architecture choices, and claimed accomplishments (e.g. 'Walk me through the architecture of <project>', "
        f"'How did you handle scaling/state in <project>?', 'Why did you select <tool> over alternatives?'). "
        f"Return ONLY the numbered questions 1 to {n}."
    )

    try:
        raw_response = call_llm(prompt)
        parsed_questions = _parse_llm_question_lines(raw_response, limit=n)
        if len(parsed_questions) >= min(3, n):
            return parsed_questions[:n]
    except Exception:
        pass

    # Heuristic Fallback based on extracted resume skills and projects
    fallback_questions = []
    
    # 1. Project questions
    project_matches = re.findall(r'(?:Project|System|App|Platform|Engine|API|Dashboard|Model):\s*([A-Za-z0-9\s-]+)', projects_text)
    if not project_matches:
        project_matches = re.findall(r'\b([A-Z][a-zA-Z0-9\s]{3,25}(?:App|System|Project|Platform|API|Classifier))\b', projects_text + " " + experience_text)

    for p in project_matches[:3]:
        p_clean = p.strip()
        if len(p_clean) > 3:
            fallback_questions.append(f"Walk me through the end-to-end architecture of your '{p_clean}' project.")
            fallback_questions.append(f"What was the most challenging technical roadblock you encountered while building '{p_clean}' and how did you resolve it?")

    # 2. Skill questions
    for skill in detected_skills[:4]:
        fallback_questions.append(f"In your recent projects, how did you leverage {skill}, and what architectural trade-offs did you consider?")

    # 3. General accomplishments
    if len(fallback_questions) < n:
        fallback_questions.extend([
            f"Looking at your experience, how did you ensure test automation and CI/CD quality in your past team deliverables?",
            f"Describe a specific metric or performance optimization you achieved in your highlighted projects.",
            f"If you were to re-architect your most complex project today for 10x scale, what would you change?"
        ])

    return list(dict.fromkeys(fallback_questions))[:n]
