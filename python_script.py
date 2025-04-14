import streamlit as st
import openai
import PyPDF2
import os
import requests
from pydantic import BaseModel
import pandas as pd

# Set page config
st.set_page_config(page_title="AI Resume Analyzer & Interview Prep", layout="wide")

# Securely load API keys from Streamlit secrets
#openai.api_key = st.secrets["OPENAI_API_KEY"]
#TAVUS_API_KEY = st.secrets["TAVUS_API_KEY"]

openai.api_key = "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"
TAVUS_API_KEY = "f79b23d9334b462f81341c010e8f6f59"

# Title
st.title("💼 AI Resume Analyzer & Interview Coach")

# Sidebar file uploader
resume_file = st.sidebar.file_uploader("📄 Upload your Resume (PDF)", type=["pdf"])

# Helper: Extract text from PDF
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    return " ".join(page.extract_text() for page in reader.pages if page.extract_text())

# Helper: OpenAI GPT call
def gpt_response(prompt, temperature=0.7):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature
    )
    return response.choices[0].message.content.strip()

# Helper: Parse Resume Info
def parse_resume_info(resume_text):
    prompt = f"""
    Extract the following details from the resume text below:
    - Full Name
    - Email Address
    - Total Years of Experience
    - Key Skills (comma separated)
    
    Resume:
    {resume_text}
    
    Respond in JSON format with keys: name, email, experience, skills
    """
    try:
        import json
        return json.loads(gpt_response(prompt))
    except Exception as e:
        st.error("Failed to extract resume info.")
        return None

# Resume processing
if resume_file:
    with st.spinner("Reading and analyzing your resume..."):
        resume_text = extract_text_from_pdf(resume_file)
        candidate_info = parse_resume_info(resume_text)

    if candidate_info:
        st.subheader("📊 Candidate Summary")
        st.write(candidate_info)

        # Interview Question Generation
        with st.spinner("Generating interview questions..."):
            interview_prompt = f"""
            You are an AI interviewer. Generate 5 technical and 3 behavioral questions for a candidate with the following profile:

            Name: {candidate_info['name']}
            Experience: {candidate_info['experience']}
            Skills: {candidate_info['skills']}

            Return each question on a new line.
            """
            interview_questions = gpt_response(interview_prompt)
        
        st.subheader("🧠 Interview Questions")
        st.text(interview_questions)

        # Generate Tavus Meta Human Video
        with st.spinner("Creating AI Interviewer video (Tavus)..."):
            tavus_api = "https://api.tavus.io/video"
            headers = {
                "Authorization": f"Bearer {TAVUS_API_KEY}",
                "Content-Type": "application/json"
            }

            meta_script = f"""
            Hi {candidate_info['name']}, this is your AI interviewer.
            Let's dive into your experience of {candidate_info['experience']}.
            We noticed skills like {candidate_info['skills']}.
            Let's go through some interview questions to help you prepare!
            """

            payload = {
                "video_template_id": "tpl_cwzAvUdq5FjDf1baGzk13",  # Replace with your own template ID
                "payload": {
                    "Script": meta_script
                }
            }

            response = requests.post(tavus_api, json=payload, headers=headers)

            if response.status_code == 201:
                video_url = response.json().get("video_url", "URL not available")
                st.success("AI Interviewer video generated!")
                st.video(video_url)
            else:
                st.error("Failed to create Tavus video.")
