"""
github_analyzer.py — GitHub Profile & Repository Evaluation Engine for CareerMate AI.
Features:
  - fetch_profile(username): Fetches GitHub user profile and public repos via GitHub REST API.
  - evaluate_repos(repos, profile): Scores activity recency, documentation completeness,
    and language diversity, identifying repos that need improvement.
  - recommend_repos_to_highlight(repos, target_role, limit):
    Ranks repos most relevant to the target role with specific justification notes.
"""

import os
import datetime
import urllib.request
import urllib.error
import json
from typing import Dict, List, Any, Optional
from skill_gap import ROLE_SKILL_REQUIREMENTS, get_all_roles


def _get_github_headers() -> Dict[str, str]:
    """Builds headers for GitHub API requests, utilizing GITHUB_TOKEN if available."""
    headers = {
        "User-Agent": "CareerMate-AI-Agent/2.0",
        "Accept": "application/vnd.github.v3+json"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token.strip()}"
    return headers


def fetch_profile(username: str) -> Dict[str, Any]:
    """
    Fetches user profile and public repositories from GitHub REST API.
    """
    clean_user = username.strip().lstrip("@")
    if not clean_user:
        raise ValueError("Please provide a valid GitHub username.")

    headers = _get_github_headers()

    # 1. Fetch User Profile
    user_url = f"https://api.github.com/users/{clean_user}"
    user_req = urllib.request.Request(user_url, headers=headers)

    try:
        with urllib.request.urlopen(user_req, timeout=10) as resp:
            user_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"GitHub user '{clean_user}' not found. Please double-check the username.")
        elif e.code in (403, 429):
            raise PermissionError("GitHub API rate limit exceeded. Please wait a few minutes or configure a GITHUB_TOKEN.")
        else:
            raise RuntimeError(f"GitHub API error ({e.code}): {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Could not connect to GitHub API: {str(e)}")

    # 2. Fetch Public Repositories (sorted by recently updated)
    repos_url = f"https://api.github.com/users/{clean_user}/repos?sort=updated&per_page=30&type=owner"
    repos_req = urllib.request.Request(repos_url, headers=headers)
    repos_list = []

    try:
        with urllib.request.urlopen(repos_req, timeout=10) as resp:
            raw_repos = json.loads(resp.read().decode("utf-8"))
            for r in raw_repos:
                if not r.get("fork", False):
                    repos_list.append({
                        "name": r.get("name"),
                        "full_name": r.get("full_name"),
                        "description": r.get("description") or "",
                        "language": r.get("language") or "Plain Text / Other",
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "updated_at": r.get("updated_at", ""),
                        "html_url": r.get("html_url", ""),
                        "has_pages": r.get("has_pages", False),
                        "open_issues": r.get("open_issues_count", 0),
                        "size_kb": r.get("size", 0)
                    })
    except Exception:
        pass

    return {
        "profile": {
            "username": user_data.get("login"),
            "name": user_data.get("name") or user_data.get("login"),
            "avatar_url": user_data.get("avatar_url"),
            "bio": user_data.get("bio") or "No bio provided.",
            "public_repos": user_data.get("public_repos", 0),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "html_url": user_data.get("html_url"),
            "created_at": user_data.get("created_at", "")[:10] if user_data.get("created_at") else "",
            "location": user_data.get("location") or "Not specified",
            "company": user_data.get("company") or "Independent"
        },
        "repos": repos_list
    }


def evaluate_repos(repos: List[Dict[str, Any]], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates repository health, activity recency, documentation quality,
    and language diversity across public repositories.
    """
    if not repos:
        return {
            "overall_score": 30,
            "activity_score": 20,
            "documentation_score": 20,
            "diversity_score": 20,
            "summary_verdict": "Empty or Fork-Only Profile — Create original public repositories",
            "language_distribution": {},
            "evaluated_repos": [],
            "stats": {"total_repos": 0, "documented_count": 0, "missing_desc_count": 0}
        }

    now = datetime.datetime.utcnow()
    total_repos = len(repos)
    documented_count = 0
    missing_desc_count = 0
    recent_activity_count = 0
    lang_counts = {}
    evaluated_repos = []

    for r in repos:
        issues = []
        desc = r.get("description", "").strip()
        lang = r.get("language", "Plain Text / Other")
        updated_str = r.get("updated_at", "")

        # 1. Documentation check
        if desc and len(desc) >= 10:
            documented_count += 1
            has_desc = True
        else:
            missing_desc_count += 1
            has_desc = False
            issues.append("Missing descriptive project summary")

        # 2. Activity recency check
        days_since_update = 999
        if updated_str:
            try:
                dt = datetime.datetime.strptime(updated_str[:10], "%Y-%m-%d")
                days_since_update = (now - dt).days
            except Exception:
                pass

        if days_since_update <= 45:
            recent_activity_count += 1
            activity_badge = "🔥 Actively Maintained"
        elif days_since_update <= 180:
            activity_badge = "🌱 Maintained within 6mo"
        else:
            activity_badge = "⏳ Stale / Inactive"
            issues.append("No commits in over 6 months")

        # 3. Language tracking
        if lang and lang != "Plain Text / Other":
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        evaluated_repos.append({
            **r,
            "has_description": has_desc,
            "days_since_update": days_since_update,
            "activity_badge": activity_badge,
            "issues": issues,
            "needs_improvement": len(issues) > 0
        })

    doc_score = round((documented_count / max(total_repos, 1)) * 100)
    act_pct = (recent_activity_count / max(total_repos, 1))
    act_score = min(100, round(act_pct * 80 + (20 if total_repos >= 3 else 10)))

    unique_langs = len(lang_counts)
    if unique_langs >= 4:
        div_score = 95
    elif unique_langs == 3:
        div_score = 85
    elif unique_langs == 2:
        div_score = 70
    elif unique_langs == 1:
        div_score = 55
    else:
        div_score = 30

    overall = round((act_score * 0.35) + (doc_score * 0.35) + (div_score * 0.30))
    overall = max(10, min(100, overall))

    if overall >= 80:
        verdict = "Exceptional GitHub Portfolio — Strong Activity & Documentation"
    elif overall >= 60:
        verdict = "Solid Developer Presence — Minor Documentation Gaps"
    elif overall >= 40:
        verdict = "Growing Portfolio — Needs Fresh Activity & Project Descriptions"
    else:
        verdict = "Needs Attention — Incomplete Repositories & Inactive History"

    total_lang_repos = sum(lang_counts.values()) or 1
    lang_dist = [
        {"language": l, "count": c, "percent": round((c / total_lang_repos) * 100)}
        for l, c in sorted(lang_counts.items(), key=lambda x: -x[1])
    ]

    return {
        "overall_score": overall,
        "activity_score": act_score,
        "documentation_score": doc_score,
        "diversity_score": div_score,
        "summary_verdict": verdict,
        "language_distribution": lang_dist,
        "evaluated_repos": evaluated_repos,
        "stats": {
            "total_repos": total_repos,
            "documented_count": documented_count,
            "missing_desc_count": missing_desc_count,
            "unique_languages": unique_langs
        }
    }


def recommend_repos_to_highlight(
    repos: List[Dict[str, Any]],
    target_role: str = "Python Developer",
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Picks the repositories most relevant to the target career role and ranks them
    by relevance and repository quality (documentation, stars, recency).
    
    Args:
        repos: List of candidate's public repositories
        target_role: Target career role (e.g. 'Data Scientist', 'Python Developer')
        limit: Number of highlighted repositories to return
        
    Returns:
        List of dicts with repo data, relevance score, and one-line highlight reason.
    """
    if not repos:
        return []

    role_info = ROLE_SKILL_REQUIREMENTS.get(target_role, ROLE_SKILL_REQUIREMENTS.get("Python Developer", {}))
    canonical_role = role_info.get("role", target_role)
    
    # Collect role keywords from skills
    role_skills = set()
    for sk in role_info.get("skills", []):
        role_skills.add(sk["name"].lower())

    scored_repos = []
    for r in repos:
        name_lower = r.get("name", "").lower()
        desc_lower = (r.get("description") or "").lower()
        lang_lower = (r.get("language") or "").lower()

        # Skill keyword matches in repo name, description, or language
        matched_keywords = []
        for sk in role_skills:
            if sk in name_lower or sk in desc_lower or sk in lang_lower:
                matched_keywords.append(sk)

        # Compute Quality Score
        score = 0
        
        # Keyword match weight
        score += len(matched_keywords) * 25
        
        # Documentation bonus
        if r.get("description") and len(r.get("description", "")) >= 15:
            score += 20
            
        # Stars bonus
        score += min(30, r.get("stars", 0) * 6)
        
        # Activity bonus
        days = r.get("days_since_update", 100)
        if days <= 60:
            score += 20
        elif days <= 180:
            score += 10

        # Construct specific one-line rationale
        if matched_keywords and r.get("description"):
            reason = f"High alignment with {canonical_role} skills ({', '.join(matched_keywords[:2]).title()}), well-documented and production-oriented."
        elif r.get("stars", 0) > 0:
            reason = f"Popular public repository with community engagement ({r.get('stars')} stars) demonstrating open-source credibility."
        elif r.get("description"):
            reason = f"Demonstrates clean software engineering and {r.get('language')} implementation relevant to a {canonical_role}."
        else:
            reason = f"Showcases hands-on development in {r.get('language')}; recommend adding a 2-line description before adding to resume."

        scored_repos.append({
            **r,
            "highlight_score": score,
            "matched_keywords": matched_keywords,
            "highlight_reason": reason
        })

    # Sort by highlight score descending
    scored_repos.sort(key=lambda x: -x["highlight_score"])
    return scored_repos[:limit]
