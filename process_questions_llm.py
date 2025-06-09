import json
import os
from mistralai import Mistral
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.environ.get("MISTRAL_API_KEY")
client = Mistral(api_key=api_key)

def read_markdown_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def generate_questions(content):
    # Construct the prompt for question generation
    prompt = f"""
    Based on the following educational content, extract all the questions following these specific formats:
    1. Multiple Choice Questions (MCQ)
    2. Short Answer Questions
    3. Fill in the Blanks Questions

    Each question must strictly follow these schemas:

    MCQ Schema:
    {{
        "type": "mcq",
        "id": "string",
        "questionNumber": "number",
        "questionText": "string",
        "image": {{
            "path": "string",
            "caption": "string",
            "isOptional": "boolean"
        }},
        "options": [
            {{
                "id": "number",
                "text": "string",
                "image": {{
                    "path": "string",
                    "caption": "string",
                    "isOptional": "boolean"
                }}
            }}
        ],
        "correctAnswer": "number",
        "marks": "number",
        "explanation": "string"
    }}

    Short Answer Schema:
    {{
        "type": "short_answer",
        "id": "string",
        "questionNumber": "number",
        "questionText": "string",
        "image": {{
            "path": "string",
            "caption": "string",
            "isOptional": "boolean"
        }},
        "subQuestions": [
            {{
                "id": "string",
                "text": "string",
                "marks": "number",
                "modelAnswer": "string",
                "keywords": ["string"]
            }}
        ],
        "totalMarks": "number"
    }}

    Fill in the Blanks Schema:
    {{
        "type": "fill_blanks",
        "id": "string",
        "questionNumber": "number",
        "questionText": "string",
        "passage": "string",
        "blanks": [
            {{
                "id": "number",
                "position": "number",
                "correctAnswer": "string",
                "marks": "number",
                "alternatives": ["string"]
            }}
        ],
        "totalMarks": "number"
    }}

    Content:
    {content}

    Format the output as a valid JSON object with three arrays: "mcq", "short_answer", and "fill_blanks".
    Make sure all IDs are unique and sequential (e.g., q1, q2, etc.).
    """

    # Make the API call to generate questions
    try:
        completion = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract and parse the JSON response
        response_content = completion.choices[0].message.content
        # Find the JSON content (assuming it's within the response)
        json_start = response_content.find('{')
        json_end = response_content.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_content = response_content[json_start:json_end]
            return json.loads(json_content)
        else:
            raise ValueError("No valid JSON found in the response")
    
    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        return {
            "mcq": [],
            "short_answer": [],
            "fill_blanks": []
        }

def save_questions(questions, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2)
        print(f"Questions successfully saved to {output_file}")
    except Exception as e:
        print(f"Error saving questions: {str(e)}")

def main():
    # Read the markdown content
    content = read_markdown_file("OCR_by_Mistral.md")
    
    # Generate questions
    questions = generate_questions(content)
    
    # Save questions to llm_questions.json
    save_questions(questions, "llm_questions.json")

if __name__ == "__main__":
    main()
