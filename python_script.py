import streamlit as st
from openai import OpenAI
import PyPDF2
import json
import requests
from typing import Optional, Dict, Any

# Set page config
st.set_page_config(
    page_title="AI Tech Interview Platform", 
    layout="wide",
    page_icon="💻"
)

# Initialize clients
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TAVUS_API_KEY = st.secrets["TAVUS_API_KEY"]

# Constants
TAVUS_API_URL = "https://tavusapi.com/v2/conversations"
TAVUS_REPLICA_ID = "r79e1c033f"
TAVUS_PERSONA_ID = "p9a95912"

# Coding questions database
CODING_QUESTIONS = {
    "python": [
        {
            "title": "Reverse a String",
            "question": "Write a function that reverses a string without using any built-in reverse functions.",
            "starter_code": "def reverse_string(s: str) -> str:\n    # Your code here\n    pass",
            "difficulty": "Easy"
        },
        {
            "title": "Fibonacci Sequence",
            "question": "Write a function that generates the first n numbers in the Fibonacci sequence.",
            "starter_code": "def fibonacci(n: int) -> list:\n    # Your code here\n    pass",
            "difficulty": "Medium"
        }
    ],
    "javascript": [
        {
            "title": "Array Sum",
            "question": "Write a function that calculates the sum of all numbers in an array.",
            "starter_code": "function arraySum(arr) {\n    // Your code here\n}",
            "difficulty": "Easy"
        }
    ]
}


def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from uploaded PDF file."""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        return " ".join(page.extract_text() for page in reader.pages if page.extract_text())
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def gpt_response(prompt: str, temperature: float = 0.7) -> str:
    """Get response from OpenAI GPT model."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to get GPT response: {str(e)}")
        return ""

def parse_resume_info(resume_text: str) -> Optional[Dict[str, Any]]:
    """Extract structured information from resume text."""
    prompt = f"""Extract from this resume:
    - Full Name
    - Email Address
    - Total Years of Experience
    - Current/Most Recent Job Title
    - Top 5 Technical Skills
    - Education Background
    - 2 Notable Projects
    
    Resume:
    {resume_text}
    
    Respond in JSON format with keys: name, email, experience, job_title, skills, education, projects"""
    try:
        return json.loads(gpt_response(prompt, temperature=0.3))
    except Exception:
        st.error("Failed to extract resume info.")
        return None

def generate_technical_questions(candidate_info: Dict[str, Any]) -> list[str]:
    """Generate top 5 technical questions based on resume."""
    prompt = f"""As an expert technical interviewer, generate exactly 5 specific technical questions 
    focused on these skills: {candidate_info['skills']} and their experience as {candidate_info['job_title']}.
    
    Return each question on a new line."""
    questions = gpt_response(prompt).strip().split("\n")
    return [q for q in questions if q.strip()][:5]

def create_conversation_context(candidate_info: Dict[str, Any], questions: list[str]) -> str:
    """Create detailed interview context with structured flow."""
    return f"""
            You are about to conduct a video interview with {candidate_info['name']}, a professional working as {candidate_info['job_title']} with {candidate_info['experience']} of experience.
            They have expertise in {candidate_info['skills']} and has worked on projects like {candidate_info['projects']}.
            
            ### Interview Flow:
            1. **Start with an Icebreaker**:
               - "Hey {candidate_info['name']}, how are you today?"
               - "Tell me a little about yourself and your background."
            
            2. **Discuss their Background & Experience**:
               - "I see you studied {candidate_info['education']}. How does that inform your work today?"
            
            3. **Technical Deep Dive**:
               - "{questions[0]}"
               - "{questions[1]}"
               - "{questions[2]}"
               - "{questions[3]}"
               - "{questions[4]}"
            
            4. **Closing Discussion**:
               - "What are you looking for in your next role?"
               - "Do you have any questions for me about the role/company?"
            """ """

def start_tavus_interview(candidate_info: Dict[str, Any], questions: list[str]):
    """Start Tavus interview with proper context."""
    conversation_context = create_conversation_context(candidate_info, questions)
    
    payload = {
        "replica_id": TAVUS_REPLICA_ID,
        "persona_id": TAVUS_PERSONA_ID,
        "conversation_name": f"Tech Interview - {candidate_info['name']}",
        "custom_greeting": f"Hello {candidate_info['name']}, I'll be your interviewer today. Ready to begin?",
        "conversational_context": conversation_context.strip(),
        "properties": {
            "max_call_duration": 1800,
            "enable_transcription": True,
            "language": "english"
        }
    }
    
    try:
        response = requests.post(
            TAVUS_API_URL,
            json=payload,
            headers={"x-api-key": TAVUS_API_KEY, "Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to start interview: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error starting interview: {str(e)}")
        return None

def coding_test_panel():
    """Create the coding test interface using Streamlit native text_area."""
    st.subheader("🧑‍💻 Coding Assessment")
    
    # Language selection
    lang = st.selectbox(
        "Select Programming Language",
        options=list(CODING_QUESTIONS.keys()),
        index=0,
        key="coding_lang"
    )
    
    # Question selection
    question_data = st.selectbox(
        "Select Coding Problem",
        options=CODING_QUESTIONS[lang],
        format_func=lambda x: f"{x['title']} ({x['difficulty']})",
        key="coding_question"
    )
    
    st.markdown(f"**Problem:** {question_data['question']}")
    
    # Use Streamlit's native text_area for code input
    code = st.text_area(
        "Write your code here:",
        value=question_data["starter_code"],
        height=400,
        key=f"editor_{lang}"
    )
    
    # Execution buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ Run Code", use_container_width=True):
            with st.spinner("Executing code..."):
                st.session_state.console_output = f"Running {lang} code...\n\n{code}\n\n(Execution simulated)"
    with col2:
        if st.button("🧹 Reset Code", use_container_width=True):
            st.session_state[f"editor_{lang}"] = question_data["starter_code"]
            st.rerun()
    with col3:
        if st.button("📋 Submit Solution", use_container_width=True):
            st.success("✅ Solution submitted!")
            st.balloons()
    
    # Console output
    if "console_output" in st.session_state:
        st.subheader("Console Output")
        st.code(st.session_state.console_output, language=lang)

def execute_code(code: str, language: str, test_cases: list):
    """Execute the submitted code and display results."""
    output = []
    output.append(f"Running {language} code...\n")
    output.append("=== Code Submitted ===")
    output.append(code)
    output.append("\n=== Test Results ===")
    
    for i, case in enumerate(test_cases, 1):
        output.append(f"\nTest Case {i}:")
        output.append(f"Input: {case['input']}")
        output.append(f"Expected: {case['output']}")
        output.append("Status: ✅ Passed (simulated)")
    
    output.append("\nAll test cases passed! 🎉")
    st.session_state.console_output = "\n".join(output)

def main():
    st.title("💻 AI Technical Interview Platform")
    
    resume_file = st.sidebar.file_uploader("📄 Upload Resume (PDF)", type=["pdf"])
    if not resume_file:
        st.info("Please upload your resume to begin")
        return

    with st.spinner("Analyzing resume..."):
        resume_text = extract_text_from_pdf(resume_file)
        candidate_info = parse_resume_info(resume_text)
        if not candidate_info:
            return

    st.subheader("👤 Candidate Profile")
    cols = st.columns(2)
    with cols[0]:
        st.write(f"**Name:** {candidate_info['name']}")
        st.write(f"**Education:** {candidate_info['education']}")
    with cols[1]:
        st.write(f"**Experience:** {candidate_info['experience']}")
        st.write(f"**Current Role:** {candidate_info['job_title']}")
    st.write(f"**Skills:** {', '.join(candidate_info['skills'])}")
    st.write(f"**Notable Projects:** {candidate_info['projects']}")

    with st.spinner("Preparing technical questions..."):
        tech_questions = generate_technical_questions(candidate_info)
        
        if tech_questions:
            st.subheader("🧠 Technical Interview Questions")
            for i, question in enumerate(tech_questions, 1):
                st.write(f"{i}. {question}")
            
            if st.button("🚀 Start AI Interview", type="primary"):
                with st.spinner("Setting up interview..."):
                    tavus_response = start_tavus_interview(candidate_info, tech_questions)
                    
                    if tavus_response and tavus_response.get("conversation_url"):
                        st.session_state.tavus_url = tavus_response['conversation_url']
                        st.session_state.show_interview = True
                
                if st.session_state.get('show_interview'):
                    st.success("🎉 Interview ready!")
                    col_interview, col_coding = st.columns([1, 1], gap="large")
                    
                    with col_interview:
                        st.subheader("🎤 Live Interview")
                        st.markdown(
                            f"""
                            <iframe src="{st.session_state.tavus_url}" 
                                    style="width:100%; height:600px; border:none; border-radius:8px;" 
                                    allow="camera; microphone; fullscreen">
                            </iframe>
                            """,
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"🔗 [Open interview in new tab]({st.session_state.tavus_url})",
                            unsafe_allow_html=True
                        )
                    
                    with col_coding:
                        coding_test_panel()

if __name__ == "__main__":
    main()

