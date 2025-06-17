import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
from mistralai import Mistral
import base64
import json
import re
import torch
from transformers import BertTokenizer, BertModel
from bs4 import BeautifulSoup
import markdown
from typing import Dict, Tuple


app = FastAPI(title="PDF OCR and question Processor")

UPLOAD_FOLDER = "uploads"
IMAGE_DIR = "exported_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

load_dotenv()
client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

# BERT model and tokenizer for similarity comparison
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')
model.eval()


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


def clean_text(text):
    """Clean text by removing special characters, latex expressions and normalizing whitespace"""
    # Remove LaTeX expressions
    text = re.sub(r'\$.*?\$', '', text)
    # Remove special characters but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text.lower().strip()


def extract_text_from_json(questions_json):
    """Extract all question text from questions JSON"""
    questions_text = []
    
    # Extract MCQ questions
    for q in questions_json.get('mcq', []):
        questions_text.append(q['questionText'])
        # Include options if they exist
        if 'options' in q:
            for opt in q['options']:
                if 'text' in opt:
                    questions_text.append(opt['text'])
    
    # Extract short answer questions
    for q in questions_json.get('short_answer', []):
        questions_text.append(q['questionText'])
    
    # Extract fill in the blanks questions
    for q in questions_json.get('fill_blanks', []):
        questions_text.append(q['questionText'])
        if 'passage' in q:
            questions_text.append(q['passage'])
    
    return clean_text(' '.join(questions_text))


def get_bert_embedding(text, model, tokenizer):
    """Get BERT embedding for a text"""
    # Tokenize and get model output
    with torch.no_grad():
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        outputs = model(**inputs)
        # Use [CLS] token embedding as the text embedding
        return outputs.last_hidden_state[:, 0, :].numpy()


def calculate_similarity(markdown_content, questions_json):
    """Calculate cosine similarity between markdown content and extracted questions"""
    # Clean the markdown content
    md_text = clean_text(markdown_content)
    
    # Extract and clean the question text from JSON
    json_text = extract_text_from_json(questions_json)
    
    # Get embeddings
    emb1 = get_bert_embedding(md_text, model, tokenizer)
    emb2 = get_bert_embedding(json_text, model, tokenizer)
    
    # Calculate cosine similarity
    similarity = torch.nn.functional.cosine_similarity(
        torch.tensor(emb1), 
        torch.tensor(emb2)
    )[0].item()
    
    # Create similarity result
    result = {
        "similarity_score": similarity,
        "percentage_match": similarity * 100,
        "text_length": {
            "markdown_text_length": len(md_text),
            "json_text_length": len(json_text)
        },
        "interpretation": ""
    }
    
    # Add interpretation
    if similarity >= 0.8:
        result["interpretation"] = "High similarity - The OCR output matches well with the extracted questions"
    elif similarity >= 0.6:
        result["interpretation"] = "Moderate similarity - Most content is captured but there may be some differences"
    else:
        result["interpretation"] = "Low similarity - Significant differences between OCR and extracted questions"
    
    return result


async def process_pdf(file_path: str) -> Tuple[str, Dict]:
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
    
    # Return both content and questions
    return content, questions


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
            
        # Get both content and questions from process_pdf
        markdown_content, questions = await process_pdf(file_path)
        
        # Calculate similarity between OCR content and extracted questions
        similarity_result = calculate_similarity(markdown_content, questions)
        
        return {
            "message": "File processed successfully",
            "questions": questions,
            "similarity": similarity_result
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)