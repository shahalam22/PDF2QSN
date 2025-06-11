import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
from mistralai import Mistral
import base64
import json
from typing import Dict


app = FastAPI(title="PDF OCR and question Processor")

UPLOAD_FOLDER = "uploads"
IMAGE_DIR = "exported_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

load_dotenv()
client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

def data_uri_to_bytes(data_uri: str) -> bytes:
    _, encoded = data_uri.split(',', 1)
    return base64.b64decode(encoded)

def export_image(image) -> str:
    parsed_image = data_uri_to_bytes(image.image_base64)
    image_path = os.path.join(IMAGE_DIR, image.id)
    with open(image_path, 'wb') as file:
        file.write(parsed_image)
    return image_path

def generate_questions(content):
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

    try:
        completion = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_content = completion.choices[0].message.content
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


async def process_pdf(file_path: str) -> str:
    with open(file_path, "rb") as pdf_file:
        uploaded_file = client.files.upload(
            file={
                "file_name": os.path.basename(file_path),
                "content": pdf_file
            },
            purpose="ocr"
        )

    file_url = client.files.get_signed_url(file_id=uploaded_file.id)

    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": file_url.url
        },
        include_image_base64=True
    )    
    
    content = ""
    for page in response.pages:
        markdown_content = page.markdown
        for image in page.images:
            image_path = export_image(image)
            markdown_content = markdown_content.replace(
                f"![{image.id}]({image.id})",
                f"![{image.id}]({image_path})"
            )
        content += markdown_content
    
    questions = generate_questions(content)
    
    return questions


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)) -> Dict:
    if not file.filename.lower().endswith('.pdf'):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file type. Please upload a PDF"}
        )

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)        
            questions = await process_pdf(file_path)
        
        return {
            "message": "File processed successfully",
            "questions": questions
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)