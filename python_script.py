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
TAVUS_API_KEY = st.secrets["TAVUS_API_KEY"]

#openai.api_key = "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"
#TAVUS_API_KEY = "f79b23d9334b462f81341c010e8f6f59"


import streamlit as st
from openai import OpenAI
from openai import OpenAIError

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("OpenAI API Test")

user_input = st.text_input("Ask something:")

if st.button("Send"):
    if user_input:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": user_input}
                ]
            )
            st.success("Response from GPT:")
            st.write(response.choices[0].message.content)
        except OpenAIError as e:
            st.error(f"OpenAI API error: {e}")
    else:
        st.warning("Please enter a prompt before sending.")




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
    response = client.chat.completions.create(
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
def start_interview(candidate):
    """Trigger Tavus API to start interview and return interview details."""
    url = "https://tavusapi.com/v2/conversations"
    
    payload = {
        "replica_id": "r79e1c033f",
        "persona_id": "p9a95912",
        "callback_url": "https://api.einstellen.ai/api/v1/webapp/candidate/transcript/create-raw-transcript",
        "conversation_name": f"A Interview with {candidate}",
        "custom_greeting": f"Hey {candidate}, nice to meet you! How are you today?",
        "properties": {
            "max_call_duration": 3600,
            "participant_left_timeout": 60,
            "participant_absent_timeout": 300,
            "enable_recording": False,
            "enable_transcription": True,
            "apply_greenscreen": True,
            "language": "english"
        }
    }
    
    headers = {
        "x-api-key": TAVUS_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        
        return response.json()
    else:
        print(f"❌ Failed to start interview. Status Code: {response.status_code}")
        sys.exit(1)

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
            

            meta_script = f"""
            Hi {candidate_info['name']}, this is your AI interviewer.
            Let's dive into your experience of {candidate_info['experience']}.
            We noticed skills like {candidate_info['skills']}.
            Let's go through some interview questions to help you prepare!
            """
            start_interview(candidate_info['name'])
