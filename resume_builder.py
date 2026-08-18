"""
Resume Builder Blueprint — Flask routes for the professional resume builder.
Handles form rendering, live preview, PDF download, and AI content generation.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from flask import Blueprint, request, render_template, send_file, jsonify, flash, redirect, url_for
from xhtml2pdf import pisa
from ai_service import generate_project_description, generate_experience_description, suggest_improvements, enhance_text

resume_bp = Blueprint('resume', __name__)

TEMPLATES = {
    'classic': 'resume/classic.html',
    'modern': 'resume/modern.html',
    'minimal': 'resume/minimal.html',
}


# ===== ResumeData Schema =====

@dataclass
class Education:
    degree: str = ""
    university: str = ""
    cgpa: str = ""
    year_start: str = ""
    year_end: str = ""


@dataclass
class Experience:
    title: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


@dataclass
class Project:
    name: str = ""
    tech_stack: str = ""
    description: str = ""
    link: str = ""


@dataclass
class Certification:
    name: str = ""
    issuer: str = ""
    year: str = ""


@dataclass
class PersonalInfo:
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


@dataclass
class Skills:
    technical: List[str] = field(default_factory=list)
    soft: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)


@dataclass
class ResumeData:
    """Full resume data model covering all supported sections."""
    personal: PersonalInfo = field(default_factory=PersonalInfo)
    summary: str = ""
    education: List[Education] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    internships: List[Experience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    skills: Skills = field(default_factory=Skills)
    certifications: List[Certification] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    courses: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convert to a dict for Jinja2 template rendering."""
        return {
            "personal": {
                "name": self.personal.name,
                "email": self.personal.email,
                "phone": self.personal.phone,
                "linkedin": self.personal.linkedin,
                "github": self.personal.github,
                "portfolio": self.personal.portfolio,
            },
            "summary": self.summary,
            "education": [
                {"degree": e.degree, "university": e.university, "cgpa": e.cgpa,
                 "year_start": e.year_start, "year_end": e.year_end}
                for e in self.education
            ],
            "experience": [
                {"title": e.title, "company": e.company, "duration": e.duration,
                 "description": e.description}
                for e in self.experience
            ],
            "internships": [
                {"title": e.title, "company": e.company, "duration": e.duration,
                 "description": e.description}
                for e in self.internships
            ],
            "projects": [
                {"name": p.name, "tech_stack": p.tech_stack,
                 "description": p.description, "link": p.link}
                for p in self.projects
            ],
            "skills": {
                "technical": self.skills.technical,
                "soft": self.skills.soft,
                "tools": self.skills.tools,
            },
            "certifications": [
                {"name": c.name, "issuer": c.issuer, "year": c.year}
                for c in self.certifications
            ],
            "achievements": self.achievements,
            "courses": self.courses,
        }


# ===== Data Parsing & Validation =====

def _parse_resume_data(form_data) -> ResumeData:
    """Parse JSON form data into a validated ResumeData dataclass."""
    try:
        if isinstance(form_data, str):
            raw = json.loads(form_data)
        elif isinstance(form_data, dict):
            raw = form_data
        else:
            raw = {}
    except (json.JSONDecodeError, TypeError):
        raw = {}

    personal_raw = raw.get("personal", {})
    personal = PersonalInfo(
        name=personal_raw.get("name", "").strip(),
        email=personal_raw.get("email", "").strip(),
        phone=personal_raw.get("phone", "").strip(),
        linkedin=personal_raw.get("linkedin", "").strip(),
        github=personal_raw.get("github", "").strip(),
        portfolio=personal_raw.get("portfolio", "").strip(),
    )

    summary = raw.get("summary", "").strip()

    education = [
        Education(**{k: v.strip() if isinstance(v, str) else v for k, v in e.items()
                     if k in Education.__dataclass_fields__})
        for e in raw.get("education", []) if isinstance(e, dict)
    ]

    experience = [
        Experience(**{k: v.strip() if isinstance(v, str) else v for k, v in e.items()
                      if k in Experience.__dataclass_fields__})
        for e in raw.get("experience", []) if isinstance(e, dict)
    ]

    internships = [
        Experience(**{k: v.strip() if isinstance(v, str) else v for k, v in e.items()
                      if k in Experience.__dataclass_fields__})
        for e in raw.get("internships", []) if isinstance(e, dict)
    ]

    projects = [
        Project(**{k: v.strip() if isinstance(v, str) else v for k, v in e.items()
                   if k in Project.__dataclass_fields__})
        for e in raw.get("projects", []) if isinstance(e, dict)
    ]

    skills_raw = raw.get("skills", {})
    skills = Skills(
        technical=[s.strip() for s in skills_raw.get("technical", []) if s.strip()],
        soft=[s.strip() for s in skills_raw.get("soft", []) if s.strip()],
        tools=[s.strip() for s in skills_raw.get("tools", []) if s.strip()],
    )

    certifications = [
        Certification(**{k: v.strip() if isinstance(v, str) else v for k, v in c.items()
                         if k in Certification.__dataclass_fields__})
        for c in raw.get("certifications", []) if isinstance(c, dict)
    ]

    achievements = [a.strip() for a in raw.get("achievements", [])
                    if isinstance(a, str) and a.strip()]

    courses = [c.strip() for c in raw.get("courses", [])
               if isinstance(c, str) and c.strip()]

    return ResumeData(
        personal=personal,
        summary=summary,
        education=education,
        experience=experience,
        internships=internships,
        projects=projects,
        skills=skills,
        certifications=certifications,
        achievements=achievements,
        courses=courses,
    )


def _validate_resume_data(data: ResumeData) -> List[str]:
    """
    Validate required fields and return a list of error messages.
    Returns an empty list if all validations pass.
    """
    errors = []

    if not data.personal.name:
        errors.append("Full name is required.")
    if not data.personal.email:
        errors.append("Email address is required.")
    elif "@" not in data.personal.email or "." not in data.personal.email:
        errors.append("Please enter a valid email address.")

    # At least one education entry with a degree
    has_education = any(e.degree for e in data.education)
    if not has_education:
        errors.append("At least one education entry with a degree is required.")

    # Warn if no skills at all
    all_skills = data.skills.technical + data.skills.soft + data.skills.tools
    if not all_skills:
        errors.append("Adding at least a few skills is strongly recommended.")

    return errors


# ===== Routes =====

@resume_bp.route('/resume/builder')
def builder():
    """Render the resume builder form page."""
    return render_template('resume_builder.html')


@resume_bp.route('/resume/preview', methods=['POST'])
def preview():
    """
    AJAX endpoint — returns rendered HTML for the selected resume template.
    Expects JSON body: { "template": "classic|modern|minimal", "data": {...} }
    """
    try:
        payload = request.get_json(force=True)
        template_name = payload.get('template', 'classic')
        resume_data = _parse_resume_data(payload.get('data', {}))

        # Validate and include warnings (non-blocking for preview)
        validation_errors = _validate_resume_data(resume_data)

        template_file = TEMPLATES.get(template_name, TEMPLATES['classic'])
        html = render_template(template_file, data=resume_data.to_dict())
        return jsonify({
            "html": html,
            "warnings": validation_errors if validation_errors else None
        })
    except Exception as e:
        return jsonify({"error": f"Preview rendering failed: {str(e)}"}), 400


@resume_bp.route('/resume/download', methods=['POST'])
def download():
    """
    Generate a PDF from resume data and return it as a downloadable file.
    Validates required fields before generation.
    Expects JSON body: { "template": "classic|modern|minimal", "data": {...} }
    """
    try:
        payload = request.get_json(force=True)
        template_name = payload.get('template', 'classic')
        resume_data = _parse_resume_data(payload.get('data', {}))

        # Server-side validation — block download if critical fields missing
        validation_errors = _validate_resume_data(resume_data)
        critical_errors = [e for e in validation_errors if "required" in e.lower()]
        if critical_errors:
            return jsonify({
                "error": "Validation failed",
                "details": critical_errors
            }), 422

        template_file = TEMPLATES.get(template_name, TEMPLATES['classic'])
        html = render_template(template_file, data=resume_data.to_dict())

        # Generate unique filename
        safe_name = "".join(
            c for c in resume_data.personal.name
            if c.isalnum() or c in (' ', '-', '_')
        ).strip() or "resume"
        pdf_filename = f"{safe_name}_resume.pdf"
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), pdf_filename)

        # Generate PDF
        with open(pdf_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return jsonify({"error": "PDF generation failed. Please try a different template."}), 500

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# ===== Legacy Form-Based Download (preserves downloadpdf.html / cantdownload.html) =====

@resume_bp.route('/resume/download-legacy', methods=['POST'])
def download_legacy():
    """
    Traditional form-POST download route that preserves the original
    downloadpdf.html / cantdownload.html error flow with flash messages.
    """
    try:
        # Accept form data or JSON
        if request.is_json:
            raw_data = request.get_json(force=True).get('data', {})
        else:
            raw_data = json.loads(request.form.get('resume_data', '{}'))

        template_name = request.form.get('template', 'classic')
        resume_data = _parse_resume_data(raw_data)

        # Validate
        validation_errors = _validate_resume_data(resume_data)
        critical_errors = [e for e in validation_errors if "required" in e.lower()]
        if critical_errors:
            for err in critical_errors:
                flash(err, 'error')
            return redirect(url_for('resume.builder'))

        template_file = TEMPLATES.get(template_name, TEMPLATES['classic'])
        html = render_template(template_file, data=resume_data.to_dict())

        safe_name = "".join(
            c for c in resume_data.personal.name
            if c.isalnum() or c in (' ', '-', '_')
        ).strip() or "resume"
        pdf_filename = f"{safe_name}_resume.pdf"
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), pdf_filename)

        with open(pdf_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            flash('PDF generation failed. Please try a different template or check your data.', 'error')
            return render_template('cantdownload.html')

        return render_template('downloadpdf.html', pdf_path=pdf_path)

    except json.JSONDecodeError:
        flash('Invalid form data. Please fill in the resume builder form.', 'error')
        return redirect(url_for('resume.builder'))
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        return render_template('cantdownload.html')


# ===== AI Routes =====

from resume_ai import generate_bullet_points, suggest_improvements as review_resume_improvements

@resume_bp.route('/resume/ai/bullet-points', methods=['POST'])
def ai_bullet_points():
    """
    Transform rough notes about a project or role into 2-4 professional resume bullet points.
    Expects JSON: { "role_or_project": "...", "raw_notes": "..." }
    Returns JSON: { "bullets": [...], "text": "• ...\n• ..." }
    """
    try:
        payload = request.get_json(force=True) or {}
        role_or_project = payload.get('role_or_project') or payload.get('name') or payload.get('title') or ''
        raw_notes = payload.get('raw_notes') or payload.get('description') or payload.get('brief') or ''

        bullets = generate_bullet_points(role_or_project, raw_notes)
        formatted_text = "\n".join(f"• {b}" for b in bullets)

        return jsonify({
            "bullets": bullets,
            "text": formatted_text,
            "result": formatted_text
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to generate bullet points. Please try again.",
            "bullets": [
                f"Contributed to {role_or_project or 'project'} with focus on quality and reliability.",
                "Collaborated on technical design and feature implementation."
            ]
        }), 200


@resume_bp.route('/resume/ai/suggestions', methods=['POST'])
def ai_suggestions():
    """
    Review full resume data and return a list of actionable improvement strings.
    Expects JSON: { "resume_data": {...} } or { "data": {...} }
    Returns JSON: { "suggestions": [...] }
    """
    try:
        payload = request.get_json(force=True) or {}
        raw_data = payload.get('resume_data') or payload.get('data') or payload

        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        suggestions = review_resume_improvements(raw_data)
        return jsonify({
            "suggestions": suggestions,
            "result": "\n".join(f"• {s}" for s in suggestions)
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to analyze resume. Please verify your entries.",
            "suggestions": [
                "Ensure every bullet point begins with a strong action verb.",
                "Include measurable metrics (%, numbers, timelines) where possible.",
                "Add your LinkedIn and GitHub links to complete your profile."
            ]
        }), 200


@resume_bp.route('/resume/ai/generate', methods=['POST'])
def ai_generate():
    """
    Generate AI-powered content for a resume section.
    Expects JSON: { "type": "project|experience|internship|summary", "data": {...} }
    """
    try:
        payload = request.get_json(force=True)
        gen_type = payload.get('type', '')
        data = payload.get('data', {})

        if gen_type in ('project', 'experience', 'internship'):
            role_or_project = data.get('name') or data.get('title') or ''
            raw_notes = data.get('description') or data.get('brief') or ''
            bullets = generate_bullet_points(role_or_project, raw_notes)
            result = "\n".join(f"• {b}" for b in bullets)
        elif gen_type == 'summary':
            result = enhance_text(
                data.get('text', ''),
                context='professional resume summary'
            )
        else:
            result = enhance_text(data.get('text', ''), context='resume')

        return jsonify({"result": result, "text": result})
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500


@resume_bp.route('/resume/ai/suggest', methods=['POST'])
def ai_suggest():
    """
    Get AI suggestions for improving a resume section or full resume.
    Expects JSON: { "section": "...", "content": "..." } or { "resume_data": {...} }
    """
    try:
        payload = request.get_json(force=True) or {}
        section = payload.get('section', 'General')
        content = payload.get('content', '')

        if not content or content in ('{}', '[]'):
            return jsonify({"result": f"Add some content to your {section} section first, then ask for suggestions."})

        # Try full review if dict or JSON string
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
            if isinstance(parsed, dict) and any(k in parsed for k in ('personal', 'skills', 'education')):
                suggestions = review_resume_improvements(parsed)
                return jsonify({"result": "\n".join(f"• {s}" for s in suggestions), "suggestions": suggestions})
        except Exception:
            pass

        result = suggest_improvements(section, str(content))
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": f"AI suggestion failed: {str(e)}"}), 500
