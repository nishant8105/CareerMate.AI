"""
AI Service Module — Google Gemini API wrapper for CareerMate AI.
Provides functions for generating and enhancing resume content.
Uses the google-genai SDK (latest, non-deprecated).
"""

import os
from google import genai


def _get_client():
    """Initialize and return a Gemini client instance."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        return None
    return genai.Client(api_key=api_key)


def generate_project_description(name, tech_stack, brief):
    """
    Generate a polished 2-3 sentence project description.

    Args:
        name: Project name
        tech_stack: Technologies used
        brief: A short rough description from the user

    Returns:
        str: Professional project description, or fallback text if API unavailable
    """
    client = _get_client()
    if not client:
        return brief or f"Developed {name} using {tech_stack}."

    prompt = f"""You are a professional resume writer. Write a concise, impactful 2-3 sentence 
project description for a resume. Focus on what was built, technologies used, and the impact/outcome.
Do NOT use first person pronouns. Use action verbs. Keep it under 60 words.

Project Name: {name}
Technologies: {tech_stack}
Brief Description: {brief}

Return ONLY the description text, no labels or formatting."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return brief or f"Developed {name} using {tech_stack}."


def generate_experience_description(title, company, brief):
    """
    Generate professional bullet points for work/internship experience.

    Args:
        title: Job title
        company: Company name
        brief: Rough description of responsibilities

    Returns:
        str: Professional experience description with bullet points
    """
    client = _get_client()
    if not client:
        return brief or f"Worked as {title} at {company}."

    prompt = f"""You are a professional resume writer. Write 3-4 concise bullet points 
for a resume work experience entry. Use strong action verbs, quantify achievements where possible.
Do NOT use first person pronouns. Each bullet should be one line, under 20 words.

Job Title: {title}
Company: {company}
Brief Description: {brief}

Return ONLY the bullet points, each on a new line starting with •. No other text."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return brief or f"Worked as {title} at {company}."


def suggest_improvements(section_name, content):
    """
    Provide actionable suggestions to improve a resume section.

    Args:
        section_name: Name of the section (e.g., "Skills", "Projects")
        content: Current content of the section

    Returns:
        str: Improvement suggestions
    """
    client = _get_client()
    if not client:
        return "AI suggestions require a valid Gemini API key. Please add your key to the .env file."

    prompt = f"""You are an expert resume reviewer. Analyze this resume section and provide 
3-4 specific, actionable suggestions to improve it. Be concise and practical.
Focus on: clarity, impact, relevance, and professional tone.

Section: {section_name}
Content: {content}

Return suggestions as a numbered list. Keep each suggestion under 25 words."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return "Unable to generate suggestions at this time. Please try again."


def enhance_text(text, context="resume"):
    """
    Rewrite text to be more professional and impactful.

    Args:
        text: Text to enhance
        context: Context for enhancement (e.g., "resume", "cover letter")

    Returns:
        str: Enhanced text
    """
    client = _get_client()
    if not client:
        return text

    prompt = f"""You are a professional resume writer. Rewrite the following text to be more 
professional, impactful, and suitable for a {context}. Keep the same meaning but improve
the language, tone, and clarity. Keep it concise.

Text: {text}

Return ONLY the rewritten text, nothing else."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return text
