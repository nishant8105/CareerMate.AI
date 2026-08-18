"""
config.py — Configuration settings for CareerMate.AI.
Configures PostgreSQL via DATABASE_URL or individual connection parameters (Supabase / Render / Heroku),
falling back to local SQLite (instance/careermate.db) if not provided.
"""

import os
import urllib.parse
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "career-mate-ai-super-secret-key-2026"

    # Database connection parameters
    db_host = os.environ.get("DB_HOST") or os.environ.get("PGHOST")
    db_port = os.environ.get("DB_PORT") or os.environ.get("PGPORT") or "5432"
    db_name = os.environ.get("DB_NAME") or os.environ.get("PGDATABASE") or "postgres"
    db_user = os.environ.get("DB_USER") or os.environ.get("PGUSER")
    db_pass = os.environ.get("DB_PASSWORD") or os.environ.get("PGPASSWORD")

    database_url = os.environ.get("DATABASE_URL")

    if db_host and db_user and db_pass:
        # Build PostgreSQL URL with URL-encoded password to safely handle special characters like '@'
        encoded_pass = urllib.parse.quote_plus(db_pass)
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"
        )
    elif database_url:
        # Fix legacy postgres:// URL format if provided by Heroku/Render
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Local SQLite database in instance folder
        instance_dir = os.path.join(basedir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'careermate.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
