"""
skill_gap.py — Skill Gap Analyzer Engine for CareerMate AI.
Compares candidate current skills against target role required skills using fuzzy taxonomy matching.
Computes coverage percentage, strengths, and ranked 'Learn Next' action priorities.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from ats_analyzer import extract_technical_skills, TAXONOMY_DATA

ROLE_SKILL_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "Python Developer": {
        "role": "Python Developer",
        "overview": "Backend engineering, APIs, data manipulation, and scalable web architectures using Python.",
        "skills": [
            {"name": "Python", "priority": "P1 — Highest Priority (Core Foundation)", "tier": 1},
            {"name": "Git", "priority": "P1 — Highest Priority (Core Foundation)", "tier": 1},
            {"name": "SQL", "priority": "P1 — Highest Priority (Core Foundation)", "tier": 1},
            {"name": "Django", "priority": "P2 — High Priority (Frameworks)", "tier": 2},
            {"name": "Flask", "priority": "P2 — High Priority (Frameworks)", "tier": 2},
            {"name": "FastAPI", "priority": "P2 — High Priority (Frameworks)", "tier": 2},
            {"name": "PostgreSQL", "priority": "P2 — High Priority (Databases)", "tier": 2},
            {"name": "REST APIs", "priority": "P2 — High Priority (APIs)", "tier": 2},
            {"name": "Docker", "priority": "P3 — Medium Priority (DevOps & Scale)", "tier": 3},
            {"name": "Redis", "priority": "P3 — Medium Priority (Caching)", "tier": 3},
            {"name": "Celery", "priority": "P3 — Medium Priority (Async Queues)", "tier": 3},
            {"name": "CI/CD", "priority": "P4 — Advanced Priority (Deployment)", "tier": 4},
            {"name": "AWS", "priority": "P4 — Advanced Priority (Cloud)", "tier": 4},
            {"name": "Kubernetes", "priority": "P4 — Advanced Priority (Orchestration)", "tier": 4}
        ]
    },
    "Data Scientist": {
        "role": "Data Scientist",
        "overview": "Statistical modeling, exploratory data analysis, machine learning algorithms, and data storytelling.",
        "skills": [
            {"name": "Python", "priority": "P1 — Highest Priority (Core Foundation)", "tier": 1},
            {"name": "SQL", "priority": "P1 — Highest Priority (Data Extraction)", "tier": 1},
            {"name": "Statistics", "priority": "P1 — Highest Priority (Math & Analytics)", "tier": 1},
            {"name": "Pandas", "priority": "P2 — High Priority (Data Manipulation)", "tier": 2},
            {"name": "NumPy", "priority": "P2 — High Priority (Numerical Computing)", "tier": 2},
            {"name": "Scikit-Learn", "priority": "P2 — High Priority (Machine Learning)", "tier": 2},
            {"name": "Data Visualization", "priority": "P2 — High Priority (Visualization)", "tier": 2},
            {"name": "Matplotlib", "priority": "P2 — High Priority (Visualization)", "tier": 2},
            {"name": "Deep Learning", "priority": "P3 — Medium Priority (Advanced Modeling)", "tier": 3},
            {"name": "PyTorch", "priority": "P3 — Medium Priority (Deep Learning)", "tier": 3},
            {"name": "TensorFlow", "priority": "P3 — Medium Priority (Deep Learning)", "tier": 3},
            {"name": "A/B Testing", "priority": "P3 — Medium Priority (Experimentation)", "tier": 3},
            {"name": "Feature Engineering", "priority": "P4 — Advanced Priority (Optimization)", "tier": 4},
            {"name": "AWS", "priority": "P4 — Advanced Priority (Cloud Deployment)", "tier": 4}
        ]
    },
    "ML Engineer": {
        "role": "ML Engineer",
        "overview": "Production ML systems, scalable training pipelines, MLOps, model deployment, and optimization.",
        "skills": [
            {"name": "Python", "priority": "P1 — Highest Priority (Core Foundation)", "tier": 1},
            {"name": "PyTorch", "priority": "P1 — Highest Priority (Model Building)", "tier": 1},
            {"name": "Git", "priority": "P1 — Highest Priority (Version Control)", "tier": 1},
            {"name": "Docker", "priority": "P2 — High Priority (Containerization)", "tier": 2},
            {"name": "FastAPI", "priority": "P2 — High Priority (Model Serving)", "tier": 2},
            {"name": "MLOps", "priority": "P2 — High Priority (Pipelines)", "tier": 2},
            {"name": "Model Deployment", "priority": "P2 — High Priority (Inference)", "tier": 2},
            {"name": "Kubernetes", "priority": "P3 — Medium Priority (Orchestration)", "tier": 3},
            {"name": "MLflow", "priority": "P3 — Medium Priority (Tracking)", "tier": 3},
            {"name": "Distributed Training", "priority": "P4 — Advanced Priority (Scale)", "tier": 4},
            {"name": "AWS", "priority": "P4 — Advanced Priority (Cloud Infra)", "tier": 4}
        ]
    },
    "Web Developer": {
        "role": "Web Developer",
        "overview": "Full-stack modern web application development, responsive UI, microservices, and databases.",
        "skills": [
            {"name": "HTML5", "priority": "P1 — Highest Priority (Markup)", "tier": 1},
            {"name": "CSS3", "priority": "P1 — Highest Priority (Styling)", "tier": 1},
            {"name": "JavaScript", "priority": "P1 — Highest Priority (Core Language)", "tier": 1},
            {"name": "Git", "priority": "P1 — Highest Priority (Version Control)", "tier": 1},
            {"name": "React", "priority": "P2 — High Priority (Frontend Framework)", "tier": 2},
            {"name": "TypeScript", "priority": "P2 — High Priority (Type Safety)", "tier": 2},
            {"name": "Node.js", "priority": "P2 — High Priority (Backend Runtime)", "tier": 2},
            {"name": "REST APIs", "priority": "P2 — High Priority (API Design)", "tier": 2},
            {"name": "Next.js", "priority": "P3 — Medium Priority (SSR / Fullstack)", "tier": 3},
            {"name": "PostgreSQL", "priority": "P3 — Medium Priority (Database)", "tier": 3},
            {"name": "MongoDB", "priority": "P3 — Medium Priority (NoSQL)", "tier": 3},
            {"name": "Docker", "priority": "P4 — Advanced Priority (DevOps)", "tier": 4},
            {"name": "CI/CD", "priority": "P4 — Advanced Priority (Deployment)", "tier": 4}
        ]
    },
    "Data Analyst": {
        "role": "Data Analyst",
        "overview": "Business intelligence, SQL querying, data cleaning, dashboarding, and actionable insights.",
        "skills": [
            {"name": "SQL", "priority": "P1 — Highest Priority (Querying)", "tier": 1},
            {"name": "Excel", "priority": "P1 — Highest Priority (Spreadsheets)", "tier": 1},
            {"name": "Python", "priority": "P2 — High Priority (Analytics)", "tier": 2},
            {"name": "Pandas", "priority": "P2 — High Priority (Data Manipulation)", "tier": 2},
            {"name": "Tableau", "priority": "P2 — High Priority (BI & Visualization)", "tier": 2},
            {"name": "Power BI", "priority": "P2 — High Priority (Dashboards)", "tier": 2},
            {"name": "Data Cleaning", "priority": "P3 — Medium Priority (ETL)", "tier": 3},
            {"name": "Data Warehousing", "priority": "P4 — Advanced Priority (Infrastructure)", "tier": 4}
        ]
    },
    "Software Developer": {
        "role": "Software Developer",
        "overview": "Core software engineering, algorithms, system design, object-oriented programming, and clean code.",
        "skills": [
            {"name": "Data Structures", "priority": "P1 — Highest Priority (CS Fundamentals)", "tier": 1},
            {"name": "Algorithms", "priority": "P1 — Highest Priority (CS Fundamentals)", "tier": 1},
            {"name": "Git", "priority": "P1 — Highest Priority (Version Control)", "tier": 1},
            {"name": "Java", "priority": "P2 — High Priority (OOP)", "tier": 2},
            {"name": "Python", "priority": "P2 — High Priority (Languages)", "tier": 2},
            {"name": "SQL", "priority": "P2 — High Priority (Databases)", "tier": 2},
            {"name": "System Design", "priority": "P3 — Medium Priority (Architecture)", "tier": 3},
            {"name": "Docker", "priority": "P3 — Medium Priority (Containers)", "tier": 3},
            {"name": "Linux", "priority": "P4 — Advanced Priority (Environment)", "tier": 4},
            {"name": "CI/CD", "priority": "P4 — Advanced Priority (Deployment)", "tier": 4}
        ]
    }
}


def get_all_roles() -> List[str]:
    """Returns list of supported engineering roles for skill analysis."""
    return list(ROLE_SKILL_REQUIREMENTS.keys())


def _normalize_skill_set(skills: List[str]) -> List[str]:
    """Normalizes a list of skills into canonical names using aliases from taxonomy."""
    if not skills:
        return []

    aliases = TAXONOMY_DATA.get("aliases", {})
    normalized = []
    seen = set()

    for s in skills:
        s_clean = s.strip()
        if not s_clean:
            continue

        canonical = aliases.get(s_clean.lower(), s_clean)
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            normalized.append(canonical)

    return normalized


def rank_missing_skills_by_priority(missing: List[str], target_role: str = "Python Developer") -> List[Dict[str, Any]]:
    """
    Orders missing skills by learning priority tier.
    """
    if not missing:
        return []

    role_info = ROLE_SKILL_REQUIREMENTS.get(target_role, ROLE_SKILL_REQUIREMENTS["Python Developer"])
    role_skills = role_info.get("skills", [])
    skill_priority_map = {sk["name"].lower(): sk for sk in role_skills}

    missing_set = set(s.strip().lower() for s in missing if s)
    ranked = []
    assigned = set()

    for sk_data in role_skills:
        name_lower = sk_data["name"].lower()
        if name_lower in missing_set and name_lower not in assigned:
            assigned.add(name_lower)
            ranked.append({
                "skill": sk_data["name"],
                "tier": sk_data["tier"],
                "priority_label": sk_data["priority"]
            })

    for sk in missing:
        if sk.lower() not in assigned:
            assigned.add(sk.lower())
            ranked.append({
                "skill": sk,
                "tier": 4,
                "priority_label": "Domain Competency Priority"
            })

    ranked.sort(key=lambda x: (x["tier"], x["skill"]))
    return ranked


def analyze_skill_gap(current_skills: List[str], target_role: str = "Python Developer") -> Dict[str, Any]:
    """
    Analyzes candidate skill gaps against industry requirements for a target role.
    """
    role_info = ROLE_SKILL_REQUIREMENTS.get(target_role, ROLE_SKILL_REQUIREMENTS["Python Developer"])
    canonical_role = role_info["role"]
    role_skills = role_info.get("skills", [])

    norm_current = _normalize_skill_set(current_skills)
    current_set = set(s.lower() for s in norm_current)

    all_required_skills = [sk["name"] for sk in role_skills]
    have_skills = [sk for sk in all_required_skills if sk.lower() in current_set]
    missing_skills = [sk for sk in all_required_skills if sk.lower() not in current_set]

    total_req = len(all_required_skills)
    coverage_pct = round((len(have_skills) / max(total_req, 1)) * 100) if total_req else 0
    coverage_pct = min(100, max(0, coverage_pct))

    ranked_learn_next = rank_missing_skills_by_priority(missing_skills, target_role=canonical_role)

    if coverage_pct >= 80:
        verdict = "Industry Ready — Excellent Skill Coverage"
    elif coverage_pct >= 55:
        verdict = "Competitive Candidate — Moderate Skill Gaps"
    elif coverage_pct >= 30:
        verdict = "Foundational Match — Core Gaps to Address"
    else:
        verdict = "Early Career / Transitioning — Significant Upskilling Needed"

    return {
        "target_role": canonical_role,
        "overview": role_info.get("overview", ""),
        "coverage_percent": coverage_pct,
        "have": have_skills,
        "missing": missing_skills,
        "ranked_learn_next": ranked_learn_next,
        "all_required": all_required_skills,
        "current_skills": norm_current,
        "summary_verdict": verdict,
        "stats": {
            "total_required": total_req,
            "have_count": len(have_skills),
            "missing_count": len(missing_skills)
        }
    }
