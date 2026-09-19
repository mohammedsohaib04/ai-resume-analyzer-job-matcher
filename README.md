# 🤖 ResumeAI — AI Career Copilot

A SaaS-ready resume analyzer that compares a resume with a target job, saves analysis history per user, and enforces a free usage limit.

## Live Demo
https://ai-resume-analyzer-job-matcher-re2k.onrender.com

## Current SaaS features
- Account signup/login with hashed passwords
- Per-user dashboard
- Saved analysis history
- PDF resume upload up to 5 MB
- Resume/job skill matching
- Match score and missing skills
- Free plan: 3 analyses
- Pro plan foundation
- SQLite locally or PostgreSQL through DATABASE_URL
- Gunicorn production server

## Production environment variables
Set:
- SECRET_KEY = a long random secret
- DATABASE_URL = PostgreSQL connection string

## Run locally
```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Roadmap
1. PostgreSQL production database
2. Stripe/Razorpay subscriptions
3. LLM semantic resume analysis
4. AI resume rewriting
5. Cover-letter generator
6. Job application tracker
7. Interview preparation
8. Usage analytics and admin dashboard
