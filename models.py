"""
models.py — Database schema & ORM models for CareerMate AI.
Models:
  - User: Authentication, credentials, and relationship roots (UserMixin).
  - Resume: Saved customizable resumes (JSON data payload, template style).
  - ATSScanResult: Historical ATS scans with full score breakdown and weak areas.
  - JobMatchResult: Historical JD alignment scans and skill matches.
  - InterviewResult: Historical mock interview transcripts & scoring reports.
  - GeneratedQuestionSet: Saved question prediction packages.
  - SkillProgress: User's verified skills and career progression per target role.
"""

from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    resumes = db.relationship("Resume", backref="user", lazy=True, cascade="all, delete-orphan")
    ats_scans = db.relationship("ATSScanResult", backref="user", lazy=True, cascade="all, delete-orphan")
    job_matches = db.relationship("JobMatchResult", backref="user", lazy=True, cascade="all, delete-orphan")
    interview_results = db.relationship("InterviewResult", backref="user", lazy=True, cascade="all, delete-orphan")
    question_sets = db.relationship("GeneratedQuestionSet", backref="user", lazy=True, cascade="all, delete-orphan")
    skill_progresses = db.relationship("SkillProgress", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(150), default="My Resume")
    data = db.Column(db.Text, nullable=False)  # JSON payload of ResumeData
    template = db.Column(db.String(50), default="modern")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_data_dict(self) -> dict:
        try:
            return json.loads(self.data)
        except Exception:
            return {}

    def set_data_dict(self, data_dict: dict) -> None:
        self.data = json.dumps(data_dict)


class ATSScanResult(db.Model):
    __tablename__ = "ats_scans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(200), default="Uploaded Resume")
    overall_score = db.Column(db.Integer, default=0)
    data = db.Column(db.Text, nullable=False)  # JSON payload of full results dict
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_results_dict(self) -> dict:
        try:
            return json.loads(self.data)
        except Exception:
            return {}

    def set_results_dict(self, res: dict) -> None:
        self.data = json.dumps(res)


class JobMatchResult(db.Model):
    __tablename__ = "job_matches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(100), default="Software Developer")
    jd_text = db.Column(db.Text, nullable=True)
    resume_snapshot = db.Column(db.Text, nullable=True)
    match_percent = db.Column(db.Integer, default=0)
    matching_skills = db.Column(db.Text, nullable=True)  # JSON list
    missing_skills = db.Column(db.Text, nullable=True)   # JSON list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_matching_skills(self) -> list:
        try:
            return json.loads(self.matching_skills) if self.matching_skills else []
        except Exception:
            return []

    def get_missing_skills(self) -> list:
        try:
            return json.loads(self.missing_skills) if self.missing_skills else []
        except Exception:
            return []


class InterviewResult(db.Model):
    __tablename__ = "interview_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(100), default="Software Developer")
    overall_score = db.Column(db.Integer, default=0)
    scores = db.Column(db.Text, nullable=False)  # JSON payload of full report & QA transcript
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_scores_dict(self) -> dict:
        try:
            return json.loads(self.scores)
        except Exception:
            return {}


class GeneratedQuestionSet(db.Model):
    __tablename__ = "generated_question_sets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    source_filename = db.Column(db.String(200), default="Uploaded Resume")
    role = db.Column(db.String(100), default="Software Developer")
    questions = db.Column(db.Text, nullable=False)  # JSON list of question dicts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_questions_list(self) -> list:
        try:
            return json.loads(self.questions)
        except Exception:
            return []


class SkillProgress(db.Model):
    __tablename__ = "skill_progresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(100), default="Python Developer")
    known_skills = db.Column(db.Text, nullable=False)  # JSON list
    coverage_percent = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_known_skills(self) -> list:
        try:
            return json.loads(self.known_skills) if self.known_skills else []
        except Exception:
            return []

    def set_known_skills(self, skills: list) -> None:
        self.known_skills = json.dumps(skills)
