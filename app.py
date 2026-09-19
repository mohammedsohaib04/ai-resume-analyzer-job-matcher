import os
import re
import json
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from pypdf import PdfReader

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-in-production")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
database_url = os.environ.get("DATABASE_URL", "sqlite:///resumeai.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(30), default="free", nullable=False)
    analyses = db.relationship("Analysis", backref="user", lazy=True, cascade="all, delete-orphan")

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_title = db.Column(db.String(200), default="Untitled job")
    score = db.Column(db.Integer, nullable=False)
    result_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

SKILLS = ["python","java","javascript","typescript","c","c++","c#","html","css","react","angular","vue","node.js","express","flask","django","fastapi","sql","mysql","postgresql","mongodb","firebase","git","github","docker","aws","azure","gcp","machine learning","deep learning","nlp","natural language processing","pandas","numpy","scikit-learn","tensorflow","pytorch","power bi","tableau","excel","data analysis","data visualization","rest api","api","linux","kubernetes","spring boot","figma","ui/ux","cybersecurity","iot","arduino","raspberry pi","agile","scrum","communication","problem solving","leadership"]

def extract_pdf(file):
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()

def find_skills(text):
    t = normalize(text)
    return sorted(set(s for s in SKILLS if re.search(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])", t)))

def analyze(resume, job):
    rs, js = find_skills(resume), find_skills(job)
    matched = sorted(set(rs) & set(js))
    missing = sorted(set(js) - set(rs))
    score = round(len(matched) / len(js) * 100) if js else 0
    suggestions = []
    if missing:
        suggestions.append("Consider adding genuine experience or projects for: " + ", ".join(missing[:8]) + ".")
    if score < 50:
        suggestions.append("Tailor your summary and project bullets to keywords and responsibilities in the target job.")
    if not re.search(r"\b(project|experience|internship)\b", normalize(resume)):
        suggestions.append("Add relevant project or internship achievements.")
    if not re.search(r"\b\d+%|\b\d+\+|\b\d+\b", resume):
        suggestions.append("Use measurable achievements where possible, such as users, performance, time saved, or percentages.")
    if not suggestions:
        suggestions.append("The main detected job skills are represented. Keep bullets concise and achievement-focused.")
    return {"score": min(score,100), "resume_skills": rs, "job_skills": js, "matched": matched, "missing": missing, "suggestions": suggestions}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "error")
        else:
            session["user_id"] = user.id
            return redirect(request.args.get("next") or url_for("dashboard"))
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    analyses = Analysis.query.filter_by(user_id=user.id).order_by(Analysis.created_at.desc()).limit(20).all()
    return render_template("dashboard.html", analyses=analyses)

@app.route("/analyze", methods=["POST"])
@login_required
def analyze_route():
    user = current_user()
    if user.plan == "free" and Analysis.query.filter_by(user_id=user.id).count() >= 3:
        return jsonify(error="Free plan limit reached. Upgrade to Pro for unlimited analyses."), 402

    f = request.files.get("resume")
    text = request.form.get("resume_text", "").strip()
    job = request.form.get("job_description", "").strip()
    job_title = request.form.get("job_title", "").strip() or "Untitled job"
    if f and f.filename:
        if not f.filename.lower().endswith(".pdf"):
            return jsonify(error="Please upload a PDF resume."), 400
        try:
            text = extract_pdf(f)
        except Exception:
            return jsonify(error="Could not read this PDF. Please try another PDF."), 400
    if not text:
        return jsonify(error="Upload a PDF resume or paste resume text."), 400
    if not job:
        return jsonify(error="Please paste the job description."), 400

    result = analyze(text, job)
    record = Analysis(user_id=user.id, job_title=job_title[:200], score=result["score"], result_json=json.dumps(result))
    db.session.add(record)
    db.session.commit()
    result["analysis_id"] = record.id
    return jsonify(result)

@app.route("/analysis/<int:analysis_id>")
@login_required
def analysis_detail(analysis_id):
    record = Analysis.query.filter_by(id=analysis_id, user_id=session["user_id"]).first_or_404()
    return render_template("analysis.html", analysis=record, result=json.loads(record.result_json))

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="File is too large. Maximum size is 5 MB."), 413

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=False)
