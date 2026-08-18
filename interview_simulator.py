"""
interview_simulator.py — AI Interview Simulator Engine & Scoring Rubric.
Features:
  - score_answer: Evaluates candidate answer across technical clarity, communication,
    structure, and confidence using LLM with graceful per-item fallback.
  - generate_overall_feedback: Computes aggregate scores and executive improvement summary.
  - InterviewSession: State machine managing questions, answers, scoring, and post-interview reports.
"""

import os
import json
import re
import uuid
import datetime
from typing import List, Dict, Any, Optional
from resume_ai import call_llm
from interview_prep import (
    generate_technical_questions,
    generate_hr_questions,
    generate_resume_based_questions,
    SUPPORTED_ROLES
)

SIMULATOR_SESSIONS: Dict[str, 'InterviewSession'] = {}


def score_answer(question: str, answer: str) -> Dict[str, Any]:
    """
    Evaluates a candidate's answer across 4 key dimensions:
      - Technical Clarity (0-10)
      - Communication (0-10)
      - Structure / STAR method (0-10)
      - Textual Confidence (0-10)
      
    NOTE: Confidence and communication are scored from textual phrasing, assertiveness,
    and structure. A future version could incorporate real-time audio and video input.
    
    Handles LLM failures per-answer gracefully so the overall report never fails.
    """
    clean_ans = answer.strip() if answer else ""
    if not clean_ans or clean_ans.lower() in ("(skipped by candidate)", "(no answer provided)", "skip"):
        return {
            "score": 0,
            "overall_10": 0.0,
            "technical_clarity": {"score": 0, "feedback": "Question was skipped by candidate."},
            "communication": {"score": 0, "feedback": "No response provided."},
            "structure": {"score": 0, "feedback": "No response provided."},
            "confidence": {"score": 0, "feedback": "Skipped without attempt."},
            "strengths": [],
            "improvements": ["Attempt an answer using the STAR method even if unsure of the full technical solution."],
            "is_skipped": True
        }

    word_count = len(clean_ans.split())

    prompt = (
        f"You are a principal technical and behavioral interviewer evaluating a candidate's response.\n\n"
        f"QUESTION: {question}\n"
        f"CANDIDATE ANSWER: {clean_ans}\n\n"
        f"Evaluate this answer objectively and return a JSON object with this exact schema:\n"
        f"{{\n"
        f'  "technical_clarity_score": <int 0-10>,\n'
        f'  "technical_clarity_feedback": "<1-2 sentence constructive critique>",\n'
        f'  "communication_score": <int 0-10>,\n'
        f'  "communication_feedback": "<1-2 sentence critique on clarity and vocabulary>",\n'
        f'  "structure_score": <int 0-10>,\n'
        f'  "structure_feedback": "<1-2 sentence critique on STAR flow and logical ordering>",\n'
        f'  "confidence_score": <int 0-10>,\n'
        f'  "confidence_feedback": "<1-2 sentence critique on assertive phrasing and tone>",\n'
        f'  "strengths": ["<strength 1>", "<strength 2>"],\n'
        f'  "improvements": ["<actionable improvement 1>", "<actionable improvement 2>"]\n'
        f"}}\n"
        f"Return ONLY valid raw JSON without markdown code fences."
    )

    try:
        raw_response = call_llm(prompt)
        # Clean potential markdown fences
        clean_json = re.sub(r'^```(?:json)?|```$', '', raw_response.strip(), flags=re.MULTILINE).strip()
        data = json.loads(clean_json)

        tc = int(data.get("technical_clarity_score", 7))
        comm = int(data.get("communication_score", 7))
        struct = int(data.get("structure_score", 7))
        conf = int(data.get("confidence_score", 7))
        avg_10 = round((tc + comm + struct + conf) / 4.0, 1)

        return {
            "score": round(avg_10 * 10),
            "overall_10": avg_10,
            "technical_clarity": {
                "score": tc,
                "feedback": data.get("technical_clarity_feedback", "Sound conceptual explanation.")
            },
            "communication": {
                "score": comm,
                "feedback": data.get("communication_feedback", "Clear expression and technical terms.")
            },
            "structure": {
                "score": struct,
                "feedback": data.get("structure_feedback", "Organized thought progression.")
            },
            "confidence": {
                "score": conf,
                "feedback": data.get("confidence_feedback", "Assertive and professional tone.")
            },
            "strengths": data.get("strengths", ["Addressed the core prompt directly."]),
            "improvements": data.get("improvements", ["Quantify measurable impacts and mention architecture trade-offs."]),
            "is_skipped": False
        }
    except Exception:
        # Graceful heuristic fallback per answer
        if word_count < 15:
            tc, comm, struct, conf = 4, 5, 4, 5
            fb = "Answer is quite brief. Elaborate with specific implementation details and examples."
        elif word_count < 40:
            tc, comm, struct, conf = 7, 7, 7, 7
            fb = "Good direct response. Could benefit from mentioning technical trade-offs or measurable results."
        else:
            tc, comm, struct, conf = 8, 8, 8, 8
            fb = "Comprehensive response covering relevant technologies and logical problem solving."

        avg_10 = round((tc + comm + struct + conf) / 4.0, 1)
        return {
            "score": round(avg_10 * 10),
            "overall_10": avg_10,
            "technical_clarity": {"score": tc, "feedback": fb},
            "communication": {"score": comm, "feedback": "Clear articulation of candidate ideas."},
            "structure": {"score": struct, "feedback": "Structured reasoning followed in response."},
            "confidence": {"score": conf, "feedback": "Good professional phrasing in answer text."},
            "strengths": ["Clear focus on the prompt requirements."],
            "improvements": ["Incorporate the STAR methodology (Situation, Task, Action, Result) to maximize impact."],
            "is_skipped": False
        }


def generate_overall_feedback(all_scores: List[Dict[str, Any]], role: str = "Software Developer") -> Dict[str, Any]:
    """
    Computes aggregate metrics across all answers and synthesizes an executive summary.
    """
    if not all_scores:
        return {
            "overall_score": 0,
            "average_10": 0.0,
            "technical_clarity_avg": 0.0,
            "communication_avg": 0.0,
            "structure_avg": 0.0,
            "confidence_avg": 0.0,
            "executive_summary": "No answers were submitted during this simulation.",
            "top_strengths": [],
            "key_improvement_areas": ["Attempt each interview question to build confidence and muscle memory."]
        }

    valid_items = [s for s in all_scores if not s.get("is_skipped")]
    
    tc_avg = round(sum(s["technical_clarity"]["score"] for s in all_scores) / len(all_scores), 1)
    comm_avg = round(sum(s["communication"]["score"] for s in all_scores) / len(all_scores), 1)
    struct_avg = round(sum(s["structure"]["score"] for s in all_scores) / len(all_scores), 1)
    conf_avg = round(sum(s["confidence"]["score"] for s in all_scores) / len(all_scores), 1)

    overall_10 = round((tc_avg + comm_avg + struct_avg + conf_avg) / 4.0, 1)
    overall_score = round(overall_10 * 10)

    # Collect unique strengths and improvements
    strengths_pool = []
    improvements_pool = []
    for s in all_scores:
        strengths_pool.extend(s.get("strengths", []))
        improvements_pool.extend(s.get("improvements", []))

    top_strengths = list(dict.fromkeys(strengths_pool))[:3]
    key_improvements = list(dict.fromkeys(improvements_pool))[:3]

    if overall_score >= 80:
        summary = f"Outstanding performance! Strong alignment with {role} industry standards, demonstrating deep architectural command and structured communication."
    elif overall_score >= 60:
        summary = f"Solid interview foundation. Good technical grasp for a {role}, with room to enhance metric quantification and STAR framework depth."
    else:
        summary = f"Good initial mock session. Focus on expanding technical detail, framing answers with concrete project examples, and eliminating brief generalizations."

    return {
        "overall_score": overall_score,
        "average_10": overall_10,
        "technical_clarity_avg": tc_avg,
        "communication_avg": comm_avg,
        "structure_avg": struct_avg,
        "confidence_avg": conf_avg,
        "executive_summary": summary,
        "top_strengths": top_strengths if top_strengths else ["Directly tackled technical prompts."],
        "key_improvement_areas": key_improvements if key_improvements else ["Structure answers around measurable outcomes and production trade-offs."]
    }


class InterviewSession:
    """
    State machine holding the state of a single interactive interview simulation.
    """

    def __init__(
        self,
        role: str = "Software Developer",
        questions: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        current_index: int = 0,
        answers: Optional[List[Dict[str, Any]]] = None,
        report: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.role = role if role in SUPPORTED_ROLES else "Software Developer"
        self.questions = questions or []
        self.current_index = current_index
        self.answers = answers or []
        self.report = report or {}
        self.created_at = created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def create(
        cls,
        role: str = "Python Developer",
        mode: str = "mixed",
        total_questions: int = 5,
        resume_text: Optional[str] = None
    ) -> 'InterviewSession':
        questions = []
        n = max(3, min(10, int(total_questions)))

        if mode == "tech":
            questions = generate_technical_questions(role=role, n=n)
        elif mode == "hr":
            questions = generate_hr_questions(n=n)
        elif mode == "resume" and resume_text:
            resume_q = generate_resume_based_questions(resume_text=resume_text, role=role, n=n)
            tech_q = generate_technical_questions(role=role, n=n)
            questions = resume_q + tech_q
        else:
            tech_count = max(2, int(n * 0.6))
            hr_count = max(1, n - tech_count)
            tech_q = generate_technical_questions(role=role, n=tech_count)
            hr_q = generate_hr_questions(n=hr_count)
            questions = tech_q + hr_q

        deduped = []
        for q in questions:
            if q not in deduped:
                deduped.append(q)
            if len(deduped) >= n:
                break

        if not deduped:
            deduped = [
                f"Explain the architectural design of a core system you built as a {role}.",
                "Tell me about a time you resolved a difficult production issue or bottleneck.",
                "How do you approach team collaboration and technical decision making?"
            ]

        session = cls(role=role, questions=deduped)
        SIMULATOR_SESSIONS[session.session_id] = session
        return session

    def get_current_question(self) -> Optional[str]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def submit_answer(self, answer_text: str) -> None:
        current_q = self.get_current_question()
        if current_q:
            self.answers.append({
                "question_index": self.current_index + 1,
                "question": current_q,
                "answer": answer_text.strip() if answer_text else "(No answer provided)",
                "submitted_at": datetime.datetime.now().strftime("%H:%M:%S"),
                "evaluation": {}
            })
            self.current_index += 1

    def next_question(self) -> Optional[str]:
        return self.get_current_question()

    def is_complete(self) -> bool:
        return self.current_index >= len(self.questions)

    def evaluate_all_answers(self) -> Dict[str, Any]:
        """
        Runs rubric scoring on all recorded answers and compiles the post-interview report.
        """
        all_evaluations = []
        for item in self.answers:
            if not item.get("evaluation"):
                eval_result = score_answer(item["question"], item["answer"])
                item["evaluation"] = eval_result
            all_evaluations.append(item["evaluation"])

        self.report = generate_overall_feedback(all_evaluations, role=self.role)
        return self.report

    def get_progress(self) -> Dict[str, Any]:
        total = len(self.questions)
        current = min(self.current_index + 1, total)
        percent = round((self.current_index / max(total, 1)) * 100) if total else 0
        return {
            "current": current,
            "total": total,
            "percent": percent,
            "is_last": (self.current_index == total - 1)
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "role": self.role,
            "questions": self.questions,
            "current_index": self.current_index,
            "answers": self.answers,
            "report": self.report,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterviewSession':
        return cls(
            role=data.get("role", "Software Developer"),
            questions=data.get("questions", []),
            session_id=data.get("session_id"),
            current_index=data.get("current_index", 0),
            answers=data.get("answers", []),
            report=data.get("report", {}),
            created_at=data.get("created_at")
        )
