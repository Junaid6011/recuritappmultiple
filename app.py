import streamlit as st
import requests
import os
import pdfplumber
import docx
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import csv

# ------------------ Azure AI ------------------
ENDPOINT = "https://hire-smart-mvp-resource.cognitiveservices.azure.com/openai/deployments/recruit-ai-gpt4/chat/completions?api-version=2025-01-01-preview"
API_KEY = "E9SGGXsfrRlyY4YsnFH7Qv0VjqHHRehRF3AVHyXpaUgYBvSzD9MWJQQJ99BJACHYHv6XJ3w3AAAAACOGGAHM"
HEADERS = {"Content-Type": "application/json", "api-key": API_KEY}

# ------------------ SMTP Email (Gmail) ------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "linkjune224@gmail.com"
EMAIL_PASSWORD = "ofwm lhxh cibp focw"  # App password

# ------------------ Utility Functions ------------------
def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def read_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def call_ai(prompt):
    try:
        body = {"messages":[{"role":"user","content":prompt}], "temperature":0.7, "max_tokens":600}
        response = requests.post(ENDPOINT, headers=HEADERS, json=body)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling AI: {str(e)}"

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

# ------------------ Streamlit Frontend ------------------
st.set_page_config(page_title="AI Recruitment Assistant", layout="wide")
st.title("🚀 AI Recruitment Assistant (Multi-CV Support)")

# --- Initialize session state ---
if "candidates" not in st.session_state:
    st.session_state.candidates = []  # store multiple candidates with results

# ------------------ Candidate Screening ------------------
st.header("1️⃣ Candidate Screening")
col1, col2 = st.columns(2)
with col1:
    jd_file = st.file_uploader("Upload Job Description (DOCX)", type=["docx"])
with col2:
    resume_files = st.file_uploader("Upload Candidate Resumes (DOCX or PDF)", type=["docx","pdf"], accept_multiple_files=True)

if st.button("Screen Candidates"):
    if not jd_file or not resume_files:
        st.error("Please upload a Job Description and at least one Resume.")
    else:
        # Save JD temp
        jd_path = f"temp_jd.docx"
        with open(jd_path, "wb") as f:
            f.write(jd_file.getbuffer())
        jd_text = read_docx(jd_path)

        # Loop through all resumes
        results = []
        for resume_file in resume_files:
            resume_path = f"temp_resume.{resume_file.name.split('.')[-1]}"
            with open(resume_path, "wb") as f:
                f.write(resume_file.getbuffer())

            if resume_path.endswith(".docx"):
                resume_text = read_docx(resume_path)
            elif resume_path.endswith(".pdf"):
                resume_text = read_pdf(resume_path)
            else:
                resume_text = ""

            prompt = f"""
            You are an expert recruitment AI assistant.
            Compare candidate resume with job description.
            Give match score 0-100, 3 strengths, 3 weaknesses with proper formatting.

            Resume:
            {resume_text}

            Job Description:
            {jd_text}
            """
            ai_result = call_ai(prompt)

            # Store candidate record
            candidate_record = {
                "name": resume_file.name.split('.')[0],  # default name from file
                "email": "",
                "ai_result": ai_result,
                "decision": None,
                "interview_datetime": None
            }
            results.append(candidate_record)

            os.remove(resume_path)

        st.session_state.candidates = results
        os.remove(jd_path)

# ------------------ Show Results ------------------
if st.session_state.candidates:
    st.header("2️⃣ Screening Results & Decisions")
    for idx, candidate in enumerate(st.session_state.candidates):
        with st.expander(f"Candidate: {candidate['name']}"):
            candidate["name"] = st.text_input(f"Candidate Name {idx+1}", value=candidate["name"])
            candidate["email"] = st.text_input(f"Candidate Email {idx+1}", value=candidate["email"])
            st.text_area("AI Evaluation", candidate["ai_result"], height=200)

            candidate["decision"] = st.radio(f"Decision for {candidate['name']}", ("Pending", "Accept", "Reject"), key=f"decision_{idx}")

            if candidate["decision"] == "Accept":
                interview_date = st.date_input(f"Interview Date ({candidate['name']})", datetime.now().date() + timedelta(days=1), key=f"date_{idx}")
                interview_time = st.time_input(f"Interview Time ({candidate['name']})", datetime.now().time(), key=f"time_{idx}")
                candidate["interview_datetime"] = datetime.combine(interview_date, interview_time)

    # Final action
    if st.button("📩 Send Emails & Save Results"):
        csv_file = "candidate_evaluation.csv"
        file_exists = os.path.isfile(csv_file)
        with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Name","Email","Decision","Interview DateTime","AI Evaluation"])

            for c in st.session_state.candidates:
                if c["decision"] == "Accept":
                    email_subject = "Interview Invitation"
                    email_body = f"""
                    Dear {c['name']},<br><br>
                    Congratulations! You have been shortlisted for an interview.<br><br>
                    Interview Date & Time: {c['interview_datetime'].strftime('%Y-%m-%d %H:%M')}<br>
                    Duration: 30 minutes<br><br>
                    <b>AI Evaluation Remarks:</b><br>{c['ai_result'].replace('\n','<br>')}<br><br>
                    Best Regards,<br>Recruitment Team
                    """
                elif c["decision"] == "Reject":
                    email_subject = "Application Update"
                    email_body = f"""
                    Dear {c['name']},<br><br>
                    Thank you for your application. After careful evaluation, we regret to inform you that you have not been selected for the role.<br><br>
                    Best Regards,<br>Recruitment Team
                    """
                else:
                    continue  # Skip pending

                sent, msg = send_email(c["email"], email_subject, email_body)
                if sent:
                    st.success(f"✅ Email sent to {c['name']} ({c['email']})")
                else:
                    st.error(f"❌ Email sending failed for {c['name']}: {msg}")

                writer.writerow([
                    c["name"], c["email"], c["decision"],
                    c["interview_datetime"].strftime('%Y-%m-%d %H:%M') if c["interview_datetime"] else "",
                    c["ai_result"].replace('\n',' | ')
                ])
