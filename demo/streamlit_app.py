import streamlit as st
import requests
import json
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="PDF OCR and Question Generator",
    page_icon="📝",
    layout="wide"
)

def display_questions(questions):
    # Display MCQ Questions
    if questions.get("mcq"):
        st.header("Multiple Choice Questions")
        for q in questions["mcq"]:
            with st.expander(f"Question {q['questionNumber']}: {q['questionText'][:100]}..."):
                st.write(q["questionText"])
                if q.get("image") and q["image"].get("path"):
                    st.image(q["image"]["path"], caption=q["image"].get("caption", ""))
                
                # Display options in a cleaner format
                for opt in q["options"]:
                    if opt.get("image") and opt["image"].get("path"):
                        st.image(opt["image"]["path"], caption=opt["image"].get("caption", ""))
                    st.write(f"{opt['id']}. {opt['text']}")
                
                st.success(f"Correct Answer: {q['correctAnswer']}")
                if q.get("explanation"):
                    st.info(f"Explanation: {q['explanation']}")
                st.write(f"Marks: {q['marks']}")

    # Display Short Answer Questions
    if questions.get("short_answer"):
        st.header("Short Answer Questions")
        for q in questions["short_answer"]:
            with st.expander(f"Question {q['questionNumber']}: {q['questionText'][:100]}..."):
                st.write(q["questionText"])
                if q.get("image") and q["image"].get("path"):
                    st.image(q["image"]["path"], caption=q["image"].get("caption", ""))
                
                for sub_q in q.get("subQuestions", []):
                    st.subheader(f"Part {sub_q['id']}")
                    st.write(sub_q["text"])
                    with st.expander("View Answer"):
                        st.write(f"Model Answer: {sub_q['modelAnswer']}")
                        st.write(f"Keywords: {', '.join(sub_q['keywords'])}")
                        st.write(f"Marks: {sub_q['marks']}")
                
                st.write(f"Total Marks: {q['totalMarks']}")

    # Display Fill in the Blanks Questions
    if questions.get("fill_blanks"):
        st.header("Fill in the Blanks Questions")
        for q in questions["fill_blanks"]:
            with st.expander(f"Question {q['questionNumber']}: {q['questionText'][:100]}..."):
                st.write(q["questionText"])
                if q.get("passage"):
                    st.write("Passage:")
                    st.write(q["passage"])
                
                blanks_df = pd.DataFrame(q["blanks"])
                blanks_df = blanks_df.sort_values("position")
                st.write("Answers:")
                st.dataframe(blanks_df[["position", "correctAnswer", "marks"]])
                
                st.write(f"Total Marks: {q['totalMarks']}")

def main():
    st.title("📝 PDF OCR and Question Generator")
    st.write("Upload a PDF file to extract and generate questions automatically!")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        with st.spinner("Processing PDF and generating questions..."):
            try:
                # Make request to FastAPI backend
                files = {"file": uploaded_file}
                response = requests.post("http://localhost:8000/upload/", files=files)
                
                if response.status_code == 200:
                    st.success(response.json()["message"])
                    questions = response.json()["questions"]
                    display_questions(questions)
                else:
                    st.error(f"Error: {response.json().get('error', 'Unknown error occurred')}")
            
            except Exception as e:
                st.error(f"Error connecting to the server: {str(e)}")

if __name__ == "__main__":
    main()
