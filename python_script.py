import streamlit as st
from openai import OpenAI
import PyPDF2
import json
import requests
from io import StringIO
import sys
from typing import Optional, Dict, Any

# Set page config
st.set_page_config(
    page_title="HumaneAI", 
    layout="wide",
    page_icon="🤖"
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
            "difficulty": "Easy",
            "test_cases": [
                {"input": "'hello'", "output": "'olleh'"},
                {"input": "'python'", "output": "'nohtyp'"}
            ]
        },
        {
            "title": "Fibonacci Sequence",
            "question": "Write a function that generates the first n numbers in the Fibonacci sequence.",
            "starter_code": "def fibonacci(n: int) -> list:\n    # Your code here\n    pass",
            "difficulty": "Medium",
            "test_cases": [
                {"input": "5", "output": "[0, 1, 1, 2, 3]"},
                {"input": "8", "output": "[0, 1, 1, 2, 3, 5, 8, 13]"}
            ]
        }
    ]
}

# Initialize all session state variables
if 'candidate_info' not in st.session_state:
    st.session_state.candidate_info = None
if 'tech_questions' not in st.session_state:
    st.session_state.tech_questions = []
if 'tavus_url' not in st.session_state:
    st.session_state.tavus_url = ""
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = ""
if 'show_interview' not in st.session_state:
    st.session_state.show_interview = False
if 'show_coding' not in st.session_state:
    st.session_state.show_coding = False
if 'console_output' not in st.session_state:
    st.session_state.console_output = ""

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from uploaded PDF file."""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        return " ".join(page.extract_text() for page in reader.pages if page.extract_text())
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""



def parse_resume_info(resume_text: str) -> Optional[Dict[str, Any]]:
    """Extract structured information from resume text."""

    prompt = f"""
Extract the following information from this resume.

Return ONLY valid JSON.
Do NOT add explanation.
Do NOT wrap in markdown.

Required format:
{{
    "name": "string",
    "email": "string",
    "experience": "string",
    "job_title": "string",
    "skills": ["skill1", "skill2"],
    "education": "string",
    "projects": ["project1", "project2"]
}}

Resume:
{resume_text}
"""

    try:
        raw_response = gpt_response(prompt, temperature=0.2)

        if not raw_response:
            st.error("Empty response from GPT.")
            return None

        cleaned = raw_response.strip()

        # Remove markdown if present
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        # Attempt JSON parsing
        parsed = json.loads(cleaned)

        # Validate required keys exist
        required_keys = ["name", "email", "experience", "job_title", "skills", "education", "projects"]

        for key in required_keys:
            if key not in parsed:
                st.error(f"Missing key in response: {key}")
                return None

        return parsed

    except json.JSONDecodeError:
        st.error("GPT returned invalid JSON. Showing raw response below:")
        st.code(raw_response)
        return None

    except Exception as e:
        st.error(f"Resume extraction failed: {str(e)}")
        return None


    except Exception as e:
        st.error(f"Resume extraction failed: {str(e)}")
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
"""

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
    """Create the coding test interface with actual code execution."""
    st.subheader("🧑‍💻 Coding Assessment")
    
    # Language selection
    lang = st.selectbox(
        "Select Programming Language",
        options=["python"],
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
    
    # Code editor
    code = st.text_area(
        "Write your code here:",
        value=question_data["starter_code"],
        height=300,
        key=f"editor_{lang}"
    )
    
    # Execution buttons
    if st.button("▶️ Run Code", key="run_code"):
        with st.spinner("Executing code..."):
            try:
                old_stdout = sys.stdout
                sys.stdout = mystdout = StringIO()
                
                exec_globals = {}
                exec(code, exec_globals)
                
                sys.stdout = old_stdout
                output = mystdout.getvalue()
                
                st.session_state.console_output = f"=== Execution Output ===\n{output}"
            except Exception as e:
                st.session_state.console_output = f"=== Error ===\n{str(e)}"
    
    if st.button("📋 Submit Solution", key="submit_code"):
        st.success("✅ Solution submitted!")
        st.balloons()
    
    # Console output
    if st.session_state.console_output:
        st.subheader("Execution Results")
        st.code(st.session_state.console_output, language="text")

def candidate_profile_panel():
    """Top panel showing candidate profile that won't refresh"""
    with st.container(border=True):
        if st.session_state.candidate_info:
            st.subheader("👤 Candidate Profile")
            
            # Candidate profile columns
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Name:** {st.session_state.candidate_info['name']}")
                st.write(f"**Education:** {st.session_state.candidate_info['education']}")
            with col2:
                st.write(f"**Experience:** {st.session_state.candidate_info['experience']}")
                st.write(f"**Current Role:** {st.session_state.candidate_info['job_title']}")
            st.write(f"**Skills:** {', '.join(st.session_state.candidate_info['skills'])}")
            st.write(f"**Notable Projects:** {st.session_state.candidate_info['projects']}")

def technical_questions_panel():
    """Panel for technical questions that won't refresh"""
    with st.container(border=True):
        st.subheader("🧠 Technical Questions")
        
        if st.session_state.tech_questions:
            for question in st.session_state.tech_questions:
                st.write(question)  # Just display the question as-is

def interview_panel():
    """Panel for the interview interface"""
    with st.container(border=True):
        st.subheader("👨‍🏫 Live Interview")
        
        if st.button("Start Interview", key="start_interview"):
            with st.spinner("Setting up interview..."):
                tavus_response = start_tavus_interview(st.session_state.candidate_info, st.session_state.tech_questions)
                if tavus_response:
                    st.session_state.tavus_url = tavus_response['conversation_url']
                    st.session_state.conversation_id = tavus_response['conversation_url'].split('/')[-1]
                    st.session_state.show_interview = True
        
        if st.session_state.show_interview and st.session_state.tavus_url:
            st.markdown(f"""
                <iframe src="{st.session_state.tavus_url}" 
                        style="width:100%; height:500px; border:none; border-radius:8px;" 
                        allow="camera; microphone">
                </iframe>
                """, unsafe_allow_html=True)
            
            if st.button("End Interview", key="end_interview"):
                with st.spinner("Ending interview..."):
                    try:
                        url = f"https://tavusapi.com/v2/conversations/{st.session_state.conversation_id}/end"
                        headers = {"x-api-key": TAVUS_API_KEY}
                        response = requests.post(url, headers=headers)
                        
                        if response.status_code == 200:
                            st.success("Interview ended successfully!")
                        else:
                            st.error(f"Failed to end interview: {response.text}")
                    except Exception as e:
                        st.error(f"Error ending interview: {str(e)}")
                    
                    st.session_state.show_interview = False
                    st.session_state.tavus_url = ""
                    st.session_state.conversation_id = ""
                    st.rerun()

def coding_panel():
    """Panel for the coding test"""
    with st.container(border=True):
        st.subheader("💻 Coding Evaluation")
        
        if st.button("Start Coding Test", key="start_coding"):
            st.session_state.show_coding = True
        
        if st.session_state.show_coding:
            coding_test_panel()
            
            if st.button("Close Coding Test", key="close_coding"):
                st.session_state.show_coding = False

def main():
    st.title("🤖 HumaneAI")
    
    # Resume upload and analysis
    resume_file = st.sidebar.file_uploader("📄 Upload Resume (PDF)", type=["pdf"])
    if not resume_file:
        st.info("Please upload your resume to begin")
        return

    # Only analyze resume if we haven't already
    if st.session_state.candidate_info is None:
        with st.spinner("Analyzing resume..."):
            resume_text = extract_text_from_pdf(resume_file)
            candidate_info = parse_resume_info(resume_text)
            if candidate_info:
                st.session_state.candidate_info = candidate_info
                st.session_state.tech_questions = generate_technical_questions(candidate_info)
            else:
                return

    # Top panel - Candidate Profile & Technical Questions
    col1, col2 = st.columns([1, 1])
    with col1:
        candidate_profile_panel()
    with col2:
        technical_questions_panel()
    
    st.divider()
    
    # Bottom panels - Interview and Coding (60:40 ratio)
    col_interview, col_coding = st.columns([6, 4], gap="large")
    
    with col_interview:
        interview_panel()
    
    with col_coding:
        coding_panel()

if __name__ == "__main__":
    main()






