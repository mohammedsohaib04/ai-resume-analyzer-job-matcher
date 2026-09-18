import os
import re
from flask import Flask, render_template, request, jsonify
from pypdf import PdfReader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

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
    if missing: suggestions.append("Consider adding genuine experience or projects for: " + ", ".join(missing[:8]) + ".")
    if score < 50: suggestions.append("Tailor your summary and project bullets to keywords and responsibilities in the target job.")
    if not re.search(r"\b(project|experience|internship)\b", normalize(resume)): suggestions.append("Add relevant project or internship achievements.")
    if not re.search(r"\b\d+%|\b\d+\+|\b\d+\b", resume): suggestions.append("Use measurable achievements where possible, such as users, performance, time saved, or percentages.")
    if not suggestions: suggestions.append("The main detected job skills are represented. Keep bullets concise and achievement-focused.")
    return {"score": min(score,100), "resume_skills": rs, "job_skills": js, "matched": matched, "missing": missing, "suggestions": suggestions}

@app.route("/")
def index(): return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze_route():
    f = request.files.get("resume")
    text = request.form.get("resume_text", "").strip()
    job = request.form.get("job_description", "").strip()
    if f and f.filename:
        if not f.filename.lower().endswith(".pdf"): return jsonify(error="Please upload a PDF resume."), 400
        try: text = extract_pdf(f)
        except Exception: return jsonify(error="Could not read this PDF. Please try another PDF."), 400
    if not text: return jsonify(error="Upload a PDF resume or paste resume text."), 400
    if not job: return jsonify(error="Please paste the job description."), 400
    return jsonify(analyze(text, job))

@app.errorhandler(413)
def too_large(_): return jsonify(error="File is too large. Maximum size is 5 MB."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
