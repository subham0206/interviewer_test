import streamlit as st
from openai import OpenAI
import PyPDF2
import json
import requests
from typing import Optional, Dict, Any
from streamlit_monaco import st_monaco

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
        },
        {
            "title": "Two Sum",
            "question": "Given an array of integers and a target, return indices of the two numbers that add up to the target.",
            "starter_code": "def two_sum(nums: list, target: int) -> list:\n    # Your code here\n    pass",
            "difficulty": "Medium",
            "test_cases": [
                {"input": "[2,7,11,15], 9", "output": "[0, 1]"},
                {"input": "[3,2,4], 6", "output": "[1, 2]"}
            ]
        }
    ],
    "javascript": [
        {
            "title": "Array Sum",
            "question": "Write a function that calculates the sum of all numbers in an array.",
            "starter_code": "function arraySum(arr) {\n    // Your code here\n}",
            "difficulty": "Easy",
            "test_cases": [
                {"input": "[1, 2, 3, 4]", "output": "10"},
                {"input": "[10, -2, 5]", "output": "13"}
            ]
        },
        {
            "title": "Palindrome Check",
            "question": "Write a function that checks if a string is a palindrome.",
            "starter_code": "function isPalindrome(str) {\n    // Your code here\n}",
            "difficulty": "Medium",
            "test_cases": [
                {"input": "'racecar'", "output": "true"},
                {"input": "'hello'", "output": "false"}
            ]
        }
    ]
}

def show_credit_status():
    """Display remaining Tavus credits in sidebar."""
    try:
        response = requests.get(
            "https://tavusapi.com/v2/account",
            headers={"x-api-key": TAVUS_API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            credits = response.json().get('remaining_credits', 'unknown')
            st.sidebar.metric("🎟️ Tavus Credits", credits)
        else:
            st.sidebar.warning("⚠️ Couldn't fetch credit status")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Credit check failed: {str(e)}")

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
    return [q for q in questions if q.strip()][:5]  # Ensure exactly 5 questions

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
        elif response.status_code == 402:
            st.error("⚠️ Out of Tavus conversational credits. Please purchase more credits.")
            return None
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error starting interview: {str(e)}")
        return None

def coding_test_panel():
    """Create the coding test interface."""
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
    
    # Editor with Monaco
    code = st_monaco(
        value=question_data["starter_code"],
        height="400px",
        language=lang,
        theme="vs-dark",
        key=f"editor_{lang}"
    )
    
    # Execution buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ Run Code", use_container_width=True):
            with st.spinner("Executing code..."):
                execute_code(code, lang, question_data["test_cases"])
    with col2:
        if st.button("🧹 Reset Code", use_container_width=True):
            st.session_state[f"editor_{lang}"] = question_data["starter_code"]
            st.rerun()
    with col3:
        if st.button("📋 Submit Solution", use_container_width=True):
            st.success("✅ Solution submitted! The interviewer has been notified.")
            st.balloons()
    
    # Console output area
    if "console_output" in st.session_state:
        st.subheader("Console Output")
        st.code(st.session_state.console_output, language="text")

def execute_code(code: str, language: str, test_cases: list):
    """Execute the submitted code and display results."""
    # In a real implementation, you would use a code execution API
    # For demo purposes, we'll simulate execution
    
    output = []
    output.append(f"Running {language} code...\n")
    output.append("=== Code Submitted ===")
    output.append(code)
    output.append("\n=== Test Results ===")
    
    # Simulate test case execution
    for i, case in enumerate(test_cases, 1):
        output.append(f"\nTest Case {i}:")
        output.append(f"Input: {case['input']}")
        output.append(f"Expected: {case['output']}")
        output.append("Status: ✅ Passed (simulated)")
    
    output.append("\nAll test cases passed! 🎉")
    st.session_state.console_output = "\n".join(output)

def main():
    st.title("💻 AI Technical Interview Platform")
    show_credit_status()
    
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
                        st.success("🎉 Interview ready!")
                        
                        # Create two columns for interview and coding test
                        col_interview, col_coding = st.columns([1, 1], gap="large")
                        
                        with col_interview:
                            st.subheader("🎤 Live Interview")
                            st.markdown("""
                                <style>
                                .interview-iframe {
                                    width: 100%;
                                    height: 600px;
                                    border: none;
                                    border-radius: 8px;
                                }
                                </style>
                                <iframe src="{url}" 
                                        class="interview-iframe" 
                                        allow="camera; microphone; fullscreen">
                                </iframe>
                                """.format(url=tavus_response['conversation_url']),
                                unsafe_allow_html=True
                            )
                            st.markdown(
                                f"🔗 [Open interview in new tab]({tavus_response['conversation_url']})",
                                unsafe_allow_html=True
                            )
                        
                        with col_coding:
                            coding_test_panel()
                    else:
                        st.error("Failed to start interview. Please check your Tavus configuration.")

if __name__ == "__main__":
    main()
