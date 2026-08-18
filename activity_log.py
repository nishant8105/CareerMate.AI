"""
activity_log.py — Lightweight Activity Feed Logger for CareerMate AI.
Features:
  - log_activity: Appends timestamped events to session['recent_activities'] (capped at 10).
  - get_recent_activities: Returns activities with human-friendly relative time strings.
"""

import datetime
from typing import List, Dict, Any, Optional

ACTIVITY_ICONS = {
    "ats_scan": "📄",
    "job_match": "💼",
    "mock_interview": "🎙️",
    "skill_gap": "📊",
    "project_status": "🚀",
    "github_audit": "🐙",
    "resume_build": "🛠️",
    "question_gen": "🎯",
    "general": "⚡"
}


def _format_relative_time(iso_str: str) -> str:
    """Computes a human-readable relative time string (e.g. 'Just now', '5 minutes ago')."""
    if not iso_str:
        return "Recently"
    try:
        past = datetime.datetime.fromisoformat(iso_str)
        now = datetime.datetime.utcnow()
        diff = now - past
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            mins = max(1, seconds // 60)
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif seconds < 172800:
            return "Yesterday"
        else:
            days = seconds // 86400
            return f"{days} days ago"
    except Exception:
        return "Recently"


def log_activity(
    session_obj: Any,
    activity_type: str,
    summary: str,
    icon: Optional[str] = None
) -> None:
    """
    Appends a new activity log entry to the Flask session, capping at 10 entries.
    
    Args:
        session_obj: Flask session object
        activity_type: Identifier key (e.g. 'ats_scan', 'job_match')
        summary: Short descriptive text
        icon: Optional emoji icon override
    """
    if 'recent_activities' not in session_obj or not isinstance(session_obj['recent_activities'], list):
        session_obj['recent_activities'] = []

    chosen_icon = icon or ACTIVITY_ICONS.get(activity_type, "⚡")
    now_utc = datetime.datetime.utcnow().isoformat()
    now_local_str = datetime.datetime.now().strftime("%I:%M %p")

    new_entry = {
        "type": activity_type,
        "summary": summary,
        "icon": chosen_icon,
        "timestamp": now_utc,
        "time_str": now_local_str
    }

    # Prepend new entry so newest is at index 0
    session_obj['recent_activities'].insert(0, new_entry)

    # Keep only the last 10 entries
    session_obj['recent_activities'] = session_obj['recent_activities'][:10]
    session_obj.modified = True


def get_recent_activities(session_obj: Any) -> List[Dict[str, Any]]:
    """
    Retrieves and formats all recent activities from the session with relative timestamps.
    """
    raw_list = session_obj.get('recent_activities', [])
    formatted = []

    for item in raw_list:
        formatted.append({
            "type": item.get("type", "general"),
            "summary": item.get("summary", ""),
            "icon": item.get("icon", "⚡"),
            "relative_time": _format_relative_time(item.get("timestamp", "")),
            "time_str": item.get("time_str", "")
        })

    return formatted
