from flask import Flask, request, render_template, flash, redirect, send_file, url_for, session, Response, render_template_string, jsonify
from subjective import SubjectiveTest
import nltk
from xhtml2pdf import pisa
import fitz
import io
import os
import json
from dotenv import load_dotenv

# Load environment variables (.env file)
load_dotenv()

# Initialize Flask app and configuration
from config import Config
from models import db, User, Resume, ATSScanResult, JobMatchResult, InterviewResult, GeneratedQuestionSet, SkillProgress
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Initialize Database and LoginManager
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please sign in to access this feature."

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# Ensure database tables exist
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Warning: Database initialization error: {e}")

# Register the Resume Builder Blueprint
from resume_builder import resume_bp
app.register_blueprint(resume_bp)

@app.route('/')
def index():
	return render_template('front.html')

# ===== Central Career Dashboard Route =====
from activity_log import log_activity, get_recent_activities

@app.route('/dashboard')
def career_dashboard():
    """Render the central Career Intelligence Dashboard aggregating metrics across active engines."""
    ats_data = session.get('last_ats_result')
    skill_gap_data = session.get('last_skill_gap_results')
    job_match_data = session.get('last_match_results')
    sim_data = session.get('active_sim_data')
    github_data = session.get('last_github_analysis')
    recent_activities = get_recent_activities(session)

    # Hydrate latest records from database if authenticated
    if current_user.is_authenticated:
        if current_user.ats_scans:
            latest_ats = current_user.ats_scans[-1]
            ats_data = latest_ats.get_results_dict()
        if current_user.job_matches:
            latest_jm = current_user.job_matches[-1]
            job_match_data = {
                "match_percentage": latest_jm.match_percent,
                "matching_skills": latest_jm.get_matching_skills(),
                "missing_skills": latest_jm.get_missing_skills(),
                "matched_at": latest_jm.created_at.strftime('%Y-%m-%d')
            }
        if current_user.interview_results:
            latest_ir = current_user.interview_results[-1]
            scores_data = latest_ir.get_scores_dict()
            sim_data = {
                "role": latest_ir.role,
                "report": scores_data.get("report") or {"overall_score": latest_ir.overall_score, "executive_summary": "Recorded performance from saved simulation session."},
                "answers": scores_data.get("answers", [])
            }
        if current_user.skill_progresses:
            latest_sp = current_user.skill_progresses[-1]
            skill_gap_data = {
                "target_role": latest_sp.target_role,
                "coverage_percent": latest_sp.coverage_percent,
                "have": latest_sp.get_known_skills(),
                "missing": [],
                "summary_verdict": f"{latest_sp.coverage_percent}% Readiness for {latest_sp.target_role}"
            }

    return render_template(
        'dashboard.html',
        ats_data=ats_data,
        skill_gap_data=skill_gap_data,
        job_match_data=job_match_data,
        sim_data=sim_data,
        github_data=github_data,
        recent_activities=recent_activities
    )

@app.route('/api/dashboard/metrics')
def api_dashboard_metrics():
    """Asynchronous JSON endpoint for refreshing dashboard metrics and activity feed."""
    ats_data = session.get('last_ats_result')
    skill_gap_data = session.get('last_skill_gap_results')
    job_match_data = session.get('last_match_results')
    sim_data = session.get('active_sim_data')
    github_data = session.get('last_github_analysis')
    recent_activities = get_recent_activities(session)

    return jsonify({
        "status": "success",
        "ats_score": ats_data.get('overall_score') if ats_data else None,
        "skill_gap_coverage": skill_gap_data.get('coverage_percent') if skill_gap_data else None,
        "job_match_percent": job_match_data.get('match_percentage') if job_match_data else None,
        "interview_score": sim_data.get('report', {}).get('overall_score') if sim_data else None,
        "github_score": github_data.get('eval_data', {}).get('overall_score') if github_data else None,
        "recent_activities": recent_activities
    })

# Import Question Predictor 2.0
from question_generator import QuestionGenerator

@app.route('/predict')
def index1():
    """Render the Question Predictor 2.0 configuration and upload page."""
    has_last_resume = bool(session.get('last_resume_text'))
    return render_template('predict.html', has_last_resume=has_last_resume)

@app.route('/test_generate', methods=["POST"])
def test_generate():
    """Generate multi-format, multi-difficulty interview questions from resume."""
    text = ""
    use_last_resume = request.form.get('use_last_resume') == 'yes'

    if use_last_resume and session.get('last_resume_text'):
        text = session['last_resume_text']
    elif 'pdf_file' in request.files and request.files['pdf_file'].filename != '':
        pdf_file = request.files['pdf_file']
        try:
            pdf_bytes = pdf_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            if text.strip():
                session['last_resume_text'] = text.strip()
        except Exception:
            pass
    elif session.get('last_resume_text'):
        text = session['last_resume_text']

    if not text or len(text.strip()) < 30:
        flash('Please upload a valid resume PDF with readable text.')
        return redirect(url_for('index1'))

    question_type = request.form.get('question_type', 'long').lower()
    difficulty = request.form.get('difficulty', 'medium').lower()
    no_of_questions = int(request.form.get('no_of_questions', 10))

    try:
        generator = QuestionGenerator(text, no_of_questions=no_of_questions, difficulty=difficulty)
        results = generator.generate(question_type=question_type)
        session['last_question_results'] = results
        has_last_resume = bool(session.get('last_resume_text'))

        return render_template(
            'predict.html',
            qdata=results,
            grouped_questions=results.get("grouped_questions", {}),
            cresults=results.get("flat_questions", []),
            question_type=question_type,
            difficulty=difficulty,
            has_last_resume=has_last_resume
        )
    except Exception as e:
        flash('Error generating questions. Please try again.')
        return redirect(url_for('index1'))

@app.route('/predict/download-pdf', methods=['GET', 'POST'])
def predict_download_pdf():
    """Export the generated interview questions as a downloadable PDF."""
    results = session.get('last_question_results')
    if not results:
        flash('No generated questions found to export. Please generate questions first.')
        return redirect(url_for('index1'))

    try:
        html_content = render_template('questions_pdf.html', data=results)
        pdf_filename = "predicted_interview_questions.pdf"
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), pdf_filename)

        with open(pdf_path, 'wb') as f:
            pisa_status = pisa.CreatePDF(html_content, dest=f)

        if pisa_status.err:
            flash('Failed to export PDF.')
            return redirect(url_for('index1'))

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'An error occurred exporting PDF: {str(e)}')
        return redirect(url_for('index1'))

# ===== ATS Resume Analyzer Routes =====
from ats_analyzer import extract_text_from_pdf, parse_resume_sections, compute_ats_score, extract_technical_skills

@app.route('/ats')
def ats_page():
    """Render the ATS Resume Analyzer upload page."""
    return render_template('ats.html')

@app.route('/ats/analyze', methods=['POST'])
def ats_analyze():
    """Analyze uploaded resume PDF and compute ATS score."""
    if 'pdf_file' not in request.files:
        flash('Please select a PDF file to upload.')
        return redirect(url_for('ats_page'))

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        flash('No file selected. Please choose a resume PDF.')
        return redirect(url_for('ats_page'))

    try:
        raw_text = extract_text_from_pdf(pdf_file)
        if not raw_text or len(raw_text.strip()) < 30:
            flash('Could not extract text from this PDF. Please ensure it is not scanned/image-only.')
            return redirect(url_for('ats_page'))

        parsed_sections = parse_resume_sections(raw_text)
        ats_results = compute_ats_score(parsed_sections)
        session['last_resume_text'] = raw_text
        session['last_ats_result'] = ats_results
        log_activity(session, 'ats_scan', f"ATS Resume Scan completed ({ats_results.get('overall_score', 0)}% score)")

        # Database persistence if user is authenticated
        if current_user.is_authenticated:
            try:
                ats_scan_record = ATSScanResult(
                    user_id=current_user.id,
                    filename=getattr(pdf_file, 'filename', 'Uploaded Resume'),
                    overall_score=ats_results.get('overall_score', 0),
                    data=json.dumps(ats_results)
                )
                db.session.add(ats_scan_record)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return render_template('ats_results.html', results=ats_results)

    except Exception as e:
        flash('An error occurred while analyzing the resume. Please try again.')
        return redirect(url_for('ats_page'))

# ===== Job Description Matcher Routes =====
from job_matcher import match_resume_to_jd

@app.route('/job-match')
def job_match_page():
    """Render the Job Description Matcher page."""
    has_last_resume = bool(session.get('last_resume_text'))
    has_last_match = bool(session.get('last_match_results'))
    last_jd_text = session.get('last_jd_text', '')
    return render_template(
        'job_match.html',
        has_last_resume=has_last_resume,
        has_last_match=has_last_match,
        last_jd_text=last_jd_text
    )

@app.route('/job-match/results')
def job_match_saved_results():
    """View the last saved Job Description match results without re-uploading."""
    results = session.get('last_match_results')
    if not results:
        flash('No recent match results found. Please analyze a Job Description first.')
        return redirect(url_for('job_match_page'))
    return render_template('job_match_results.html', results=results)

@app.route('/job-match/analyze', methods=['POST'])
def job_match_analyze():
    """Analyze resume against Job Description and compute match percentage."""
    jd_text = request.form.get('jd_text', '').strip()
    if not jd_text or len(jd_text) < 20:
        flash('Please provide a valid Job Description with required skills and responsibilities.')
        return redirect(url_for('job_match_page'))

    use_last_resume = request.form.get('use_last_resume') == 'yes'
    resume_text = ""

    if use_last_resume and session.get('last_resume_text'):
        resume_text = session['last_resume_text']
    elif 'resume_file' in request.files and request.files['resume_file'].filename != '':
        pdf_file = request.files['resume_file']
        resume_text = extract_text_from_pdf(pdf_file)
        if resume_text:
            session['last_resume_text'] = resume_text
    elif session.get('last_resume_text'):
        resume_text = session['last_resume_text']

    if not resume_text or len(resume_text.strip()) < 30:
        flash('Please upload a resume PDF or select "Use previously uploaded resume".')
        return redirect(url_for('job_match_page'))

    try:
        results = match_resume_to_jd(resume_text, jd_text)
        session['last_match_results'] = results
        session['last_jd_text'] = jd_text
        log_activity(session, 'job_match', f"Matched resume against Job Description ({results.get('match_percentage', 0)}% alignment)")

        # Database persistence if user is authenticated
        if current_user.is_authenticated:
            try:
                job_match_record = JobMatchResult(
                    user_id=current_user.id,
                    target_role="Target Job",
                    jd_text=jd_text[:1000],
                    match_percent=results.get('match_percentage', 0),
                    matching_skills=json.dumps(results.get('matching_skills', [])),
                    missing_skills=json.dumps(results.get('missing_skills', []))
                )
                db.session.add(job_match_record)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return render_template('job_match_results.html', results=results)
    except Exception as e:
        flash('Failed to match resume against Job Description. Please try again.')
        return redirect(url_for('job_match_page'))

# ===== AI Interview Preparation Routes =====
import datetime
from interview_prep import (
    generate_technical_questions,
    generate_hr_questions,
    generate_resume_based_questions,
    SUPPORTED_ROLES
)

@app.route('/interview-prep')
def interview_prep_page():
    """Render the AI Interview Preparation role selection page."""
    has_last_resume = bool(session.get('last_resume_text'))
    return render_template(
        'interview_prep.html',
        selected_role="Python Developer",
        supported_roles=SUPPORTED_ROLES,
        technical_questions=[],
        hr_questions=[],
        resume_questions=[],
        has_last_resume=has_last_resume
    )

@app.route('/interview-prep/generate', methods=['POST'])
def interview_prep_generate():
    """Generate categorized technical, HR, and resume-aware questions."""
    role = request.form.get('role', 'Python Developer')
    use_last_resume = request.form.get('use_last_resume') == 'yes'
    resume_text = ""

    if use_last_resume and session.get('last_resume_text'):
        resume_text = session['last_resume_text']
    elif 'resume_file' in request.files and request.files['resume_file'].filename != '':
        pdf_file = request.files['resume_file']
        extracted = extract_text_from_pdf(pdf_file)
        if extracted:
            resume_text = extracted
            session['last_resume_text'] = resume_text
    elif session.get('last_resume_text'):
        resume_text = session['last_resume_text']

    try:
        tech_questions = generate_technical_questions(role=role, n=10)
        hr_questions = generate_hr_questions(n=10)
        resume_questions = []

        if resume_text:
            resume_questions = generate_resume_based_questions(resume_text=resume_text, role=role, n=8)

        # Cache active set in session
        session['active_interview_set'] = {
            "role": role,
            "tech": tech_questions,
            "hr": hr_questions,
            "resume": resume_questions
        }

        has_last_resume = bool(session.get('last_resume_text'))

        return render_template(
            'interview_prep.html',
            selected_role=role,
            supported_roles=SUPPORTED_ROLES,
            technical_questions=tech_questions,
            hr_questions=hr_questions,
            resume_questions=resume_questions,
            has_last_resume=has_last_resume
        )
    except Exception as e:
        flash('Could not generate interview questions. Please try again.')
        return redirect(url_for('interview_prep_page'))

@app.route('/interview-prep/ajax/regenerate', methods=['POST'])
def interview_prep_ajax_regenerate():
    """AJAX endpoint to regenerate a single question section without page reload."""
    data = request.get_json() or {}
    section = data.get('section', 'tech')
    role = data.get('role', 'Python Developer')
    resume_text = session.get('last_resume_text', '')

    try:
        if section == 'tech':
            questions = generate_technical_questions(role=role, n=10)
        elif section == 'hr':
            questions = generate_hr_questions(n=10)
        elif section == 'resume':
            if not resume_text:
                return jsonify({"status": "error", "message": "No resume available to regenerate resume-based questions."}), 400
            questions = generate_resume_based_questions(resume_text=resume_text, role=role, n=8)
        else:
            return jsonify({"status": "error", "message": "Invalid section specified."}), 400

        # Update active set in session
        if 'active_interview_set' in session:
            session['active_interview_set'][section] = questions
            session.modified = True

        return jsonify({
            "status": "success",
            "section": section,
            "questions": questions
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/interview-prep/save', methods=['POST'])
def interview_prep_save():
    """
    Save the current question set into database (if logged in) or session fallback.
    """
    data = request.get_json() or {}
    role = data.get('role', 'Software Developer')
    tech = data.get('tech_questions', [])
    hr = data.get('hr_questions', [])
    resume_q = data.get('resume_questions', [])

    saved_set = {
        "id": int(datetime.datetime.now().timestamp()),
        "role": role,
        "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tech_questions": tech,
        "hr_questions": hr,
        "resume_questions": resume_q
    }

    # 1. Database persistence if user is authenticated
    if current_user.is_authenticated:
        try:
            q_set_record = GeneratedQuestionSet(
                user_id=current_user.id,
                source_filename="AI Interview Preparation",
                role=role,
                questions=json.dumps(saved_set)
            )
            db.session.add(q_set_record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()

    # 2. Session cache fallback
    if 'saved_interview_sets' not in session:
        session['saved_interview_sets'] = []

    session['saved_interview_sets'].append(saved_set)
    session.modified = True
    log_activity(session, 'question_gen', f"Saved Interview Question Bank for {role}")

    return jsonify({
        "status": "success",
        "message": f"Successfully saved question set for {role}!"
    })

# ===== AI Interview Simulator Routes =====
from interview_simulator import InterviewSession, SIMULATOR_SESSIONS

@app.route('/interview-sim')
def interview_sim_setup():
    """Render the mock interview simulation configuration and launcher."""
    has_last_resume = bool(session.get('last_resume_text'))
    return render_template('interview_sim_setup.html', has_last_resume=has_last_resume)

@app.route('/interview-sim/start', methods=['POST'])
def interview_sim_start():
    """Start an interactive mock interview simulation session."""
    role = request.form.get('role', 'Software Developer')
    mode = request.form.get('mode', 'mixed')
    total_q = int(request.form.get('total_questions', 5))
    use_last_resume = request.form.get('use_last_resume') == 'yes'
    resume_text = session.get('last_resume_text', '') if use_last_resume else None

    sim_session = InterviewSession.create(
        role=role,
        mode=mode,
        total_questions=total_q,
        resume_text=resume_text
    )

    session['active_sim_data'] = sim_session.to_dict()

    return render_template(
        'interview_sim.html',
        session_data=sim_session.to_dict(),
        current_question=sim_session.get_current_question(),
        progress=sim_session.get_progress()
    )

@app.route('/interview-sim/answer', methods=['POST'])
def interview_sim_answer():
    """Submit candidate's answer for active question and advance simulation state."""
    session_id = request.form.get('session_id')
    answer_text = request.form.get('answer_text', '')

    sim_session = SIMULATOR_SESSIONS.get(session_id)
    if not sim_session and session.get('active_sim_data'):
        sim_session = InterviewSession.from_dict(session['active_sim_data'])
        SIMULATOR_SESSIONS[sim_session.session_id] = sim_session

    if not sim_session:
        flash('Interview session expired or not found. Please start a new session.')
        return redirect(url_for('interview_sim_setup'))

    sim_session.submit_answer(answer_text)

    if sim_session.is_complete():
        report = sim_session.evaluate_all_answers()
        session['active_sim_data'] = sim_session.to_dict()
        log_activity(session, 'mock_interview', f"Completed {sim_session.role} Mock Interview ({report.get('overall_score', 0)}% score)")

        # Database persistence if user is authenticated
        if current_user.is_authenticated:
            try:
                res_record = InterviewResult(
                    user_id=current_user.id,
                    role=sim_session.role,
                    overall_score=report.get('overall_score', 0),
                    scores=json.dumps({"report": report, "answers": sim_session.answers})
                )
                db.session.add(res_record)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return render_template(
            'interview_sim_results.html',
            session_data=sim_session.to_dict(),
            report=report
        )

    session['active_sim_data'] = sim_session.to_dict()

    return render_template(
        'interview_sim.html',
        session_data=sim_session.to_dict(),
        current_question=sim_session.get_current_question(),
        progress=sim_session.get_progress()
    )

@app.route('/interview-sim/results')
def interview_sim_results_view():
    """View the last completed simulation results transcript and feedback report."""
    sim_data = session.get('active_sim_data')
    if not sim_data:
        flash('No recent interview simulation found.')
        return redirect(url_for('interview_sim_setup'))
    report = sim_data.get('report') or {}
    return render_template('interview_sim_results.html', session_data=sim_data, report=report)

# ===== Skill Gap Analyzer Routes =====
from skill_gap import analyze_skill_gap, get_all_roles

@app.route('/skill-gap')
def skill_gap_page():
    """Render the Skill Gap Analyzer input page."""
    has_last_resume = bool(session.get('last_resume_text'))
    all_roles = get_all_roles()
    return render_template(
        'skill_gap.html',
        all_roles=all_roles,
        selected_role='Python Developer',
        has_last_resume=has_last_resume
    )

@app.route('/skill-gap/analyze', methods=['POST'])
def skill_gap_analyze():
    """Analyze candidate skill gaps against target career requirements."""
    target_role = request.form.get('target_role', 'Python Developer')
    manual_skills = request.form.get('manual_skills', '').strip()
    use_last_resume = request.form.get('use_last_resume') == 'yes'

    current_skills = []

    # 1. Manual skills input
    if manual_skills:
        current_skills.extend([s.strip() for s in manual_skills.split(',') if s.strip()])

    # 2. Resume PDF extraction
    if 'resume_file' in request.files and request.files['resume_file'].filename != '':
        pdf_file = request.files['resume_file']
        extracted_text = extract_text_from_pdf(pdf_file)
        if extracted_text:
            session['last_resume_text'] = extracted_text
            extracted_skills = extract_technical_skills(extracted_text)
            current_skills.extend(extracted_skills)
    elif use_last_resume and session.get('last_resume_text'):
        extracted_skills = extract_technical_skills(session['last_resume_text'])
        current_skills.extend(extracted_skills)

    if not current_skills:
        flash('Please enter at least one skill or upload your resume to analyze gaps.')
        return redirect(url_for('skill_gap_page'))

    results = analyze_skill_gap(current_skills=current_skills, target_role=target_role)
    session['last_skill_gap_results'] = results
    log_activity(session, 'skill_gap', f"Skill Gap Analyzed for {target_role} ({results.get('coverage_percent', 0)}% coverage)")

    return render_template('skill_gap_results.html', results=results)

# ===== GitHub Analyzer Routes =====
from github_analyzer import fetch_profile, evaluate_repos, recommend_repos_to_highlight
from resume_ai import generate_bullet_points

@app.route('/github-analyzer')
def github_analyzer_page():
    """Render the GitHub Profile Analyzer username input page."""
    all_roles = get_all_roles()
    return render_template('github_analyzer.html', all_roles=all_roles, default_role='Python Developer')

@app.route('/github-analyzer/analyze', methods=['POST'])
def github_analyzer_analyze():
    """Fetch and evaluate public repositories for the provided GitHub handle."""
    username = request.form.get('username', '').strip()
    target_role = request.form.get('target_role', 'Python Developer')

    if not username:
        flash('Please enter a valid GitHub username.')
        return redirect(url_for('github_analyzer_page'))

    try:
        data = fetch_profile(username)
        eval_data = evaluate_repos(data['repos'], data['profile'])
        highlighted_repos = recommend_repos_to_highlight(
            eval_data['evaluated_repos'],
            target_role=target_role,
            limit=3
        )
        all_roles = get_all_roles()

        session['last_github_analysis'] = {
            "profile": data['profile'],
            "eval_data": eval_data,
            "target_role": target_role
        }
        log_activity(session, 'github_audit', f"Audited GitHub profile @{username} ({eval_data.get('overall_score', 0)}% health)")

        return render_template(
            'github_results.html',
            profile=data['profile'],
            eval_data=eval_data,
            highlighted_repos=highlighted_repos,
            target_role=target_role,
            all_roles=all_roles
        )
    except ValueError as e:
        flash(str(e))
        return redirect(url_for('github_analyzer_page'))
    except PermissionError as e:
        flash(str(e))
        return redirect(url_for('github_analyzer_page'))
    except Exception as e:
        flash(f"Could not analyze GitHub profile: {str(e)}")
        return redirect(url_for('github_analyzer_page'))

@app.route('/github-analyzer/generate-bullet', methods=['POST'])
def github_generate_bullet():
    """Generate high-impact resume bullet points from repository metadata using AI."""
    repo_name = request.form.get('repo_name', 'Open Source Project')
    repo_desc = request.form.get('repo_desc', '')
    repo_lang = request.form.get('repo_lang', 'Software')
    target_role = request.form.get('target_role', 'Software Developer')

    prompt_text = f"Project: {repo_name}. Description: {repo_desc}. Primary Stack: {repo_lang}."
    bullets = generate_bullet_points(target_role, prompt_text)
    return jsonify({"bullets": bullets})

# ===== Authentication Routes =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Sign in existing user."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f"Welcome back, {user.name or user.email}!")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for('login'))

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user account."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please sign in.")
            return redirect(url_for('login'))

        new_user = User(email=email, name=name)
        new_user.set_password(password)
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash("Account created successfully! Welcome to CareerMate AI.")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Could not create account: {str(e)}")
            return redirect(url_for('register'))

    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    """Sign out the current user."""
    logout_user()
    flash("You've been signed out.")
    return redirect(url_for('index'))

# ===== History & Saved Records Routes =====

@app.route('/history')
@login_required
def account_history_hub():
    """Unified history hub displaying all saved records across engines."""
    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.updated_at.desc()).all()
    ats_scans = ATSScanResult.query.filter_by(user_id=current_user.id).order_by(ATSScanResult.created_at.desc()).all()
    job_matches = JobMatchResult.query.filter_by(user_id=current_user.id).order_by(JobMatchResult.created_at.desc()).all()
    interview_results = InterviewResult.query.filter_by(user_id=current_user.id).order_by(InterviewResult.created_at.desc()).all()
    question_sets = GeneratedQuestionSet.query.filter_by(user_id=current_user.id).order_by(GeneratedQuestionSet.created_at.desc()).all()
    skill_progresses = SkillProgress.query.filter_by(user_id=current_user.id).order_by(SkillProgress.updated_at.desc()).all()

    return render_template(
        'history/account_history.html',
        resumes=resumes,
        ats_scans=ats_scans,
        job_matches=job_matches,
        interview_results=interview_results,
        question_sets=question_sets,
        skill_progresses=skill_progresses
    )

@app.route('/resume/history')
@login_required
def resume_history():
    """List all saved customizable resumes for the logged-in user."""
    return redirect(url_for('account_history_hub'))

@app.route('/ats/history')
@login_required
def ats_history():
    """List historical ATS scans for current user."""
    return redirect(url_for('account_history_hub'))

@app.route('/ats/history/<int:scan_id>')
@login_required
def ats_history_view(scan_id):
    """View stored full ATS report from historical scan."""
    scan = ATSScanResult.query.get_or_404(scan_id)
    if scan.user_id != current_user.id:
        flash("Unauthorized access to this scan record.")
        return redirect(url_for('account_history_hub'))
    return render_template('ats_results.html', results=scan.get_results_dict())

@app.route('/job-match/history')
@login_required
def job_match_history():
    """List historical job matches for current user."""
    return redirect(url_for('account_history_hub'))

@app.route('/job-match/history/<int:match_id>')
@login_required
def job_match_history_view(match_id):
    """View stored job description match analysis."""
    match = JobMatchResult.query.get_or_404(match_id)
    if match.user_id != current_user.id:
        flash("Unauthorized access to this match record.")
        return redirect(url_for('account_history_hub'))

    results = {
        "match_percentage": match.match_percent,
        "matching_skills": match.get_matching_skills(),
        "missing_skills": match.get_missing_skills(),
        "total_required": len(match.get_matching_skills()) + len(match.get_missing_skills())
    }
    return render_template('job_match_results.html', results=results)

@app.route('/interview-sim/history')
@login_required
def interview_sim_history():
    """List historical mock interviews for current user."""
    return redirect(url_for('account_history_hub'))

@app.route('/interview-sim/history/<int:result_id>')
@login_required
def interview_sim_history_view(result_id):
    """View stored mock interview QA transcript and rubric feedback report."""
    record = InterviewResult.query.get_or_404(result_id)
    if record.user_id != current_user.id:
        flash("Unauthorized access to this interview record.")
        return redirect(url_for('account_history_hub'))

    scores_data = record.get_scores_dict()
    sim_data = {
        "role": record.role,
        "report": scores_data.get("report") or {"overall_score": record.overall_score, "executive_summary": "Historical saved session."},
        "answers": scores_data.get("answers", [])
    }
    return render_template('interview_sim_results.html', session_data=sim_data, report=sim_data['report'])

@app.route("/generate")
def gen():
     return redirect(url_for('resume.builder'))

@app.route("/generatepdf", methods=['POST', 'GET'])
def generate():
    """Legacy route — redirect to the new resume builder."""
    return redirect(url_for('resume.builder'))

if __name__ == "__main__":
	debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
	app.run(debug=debug_mode)







    
