# OCR Question Parser for Educational Papers

This project is designed to process educational test papers (specifically science papers) using OCR technology and extract structured question data. It uses the Mistral AI API for OCR processing and question parsing.

## Project Overview

The system performs the following functions:
1. Extracts text and images from PDF educational papers using OCR
2. Processes and structures questions into different categories (MCQ, Short Answer, Fill in Blanks)
3. Generates a structured JSON output of all questions with their metadata
4. Preserves images and their relationships to questions

## Project Structure

```
├── app.py                     # Main application for PDF processing and OCR
├── process_questions.py       # Question extraction and structuring logic
├── process_questions_llm.py   # LLM-based question processing
├── OCR_by_Mistral.md         # Markdown output of OCR processed content
├── questions.json            # Structured question data output
├── llm_questions.json        # LLM-processed question data
├── question_schema.txt       # JSON schemas for different question types
└── ocr_images/              # Directory containing extracted images
    └── img-*.jpeg           # Extracted images from the PDF
```

## Features

- PDF Processing
  - Extracts text using PyMuPDF
  - Falls back to OCR for non-machine-readable content
  - Preserves image content and references

- Question Processing
  - Supports multiple question types:
    - Multiple Choice Questions (MCQ)
    - Short Answer Questions
    - Fill in the Blanks
  - Maintains question metadata (marks, images, etc.)
  - Preserves answer keys and model answers

- Data Structure
  - Organized JSON output
  - Standardized question schemas
  - Image linking and management

## Requirements

- Python 3.x
- Required packages:
  - mistralai
  - PyMuPDF (fitz)
  - python-dotenv
  - requests

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install mistralai PyMuPDF python-dotenv requests
   ```
3. Create a `.env` file with your Mistral API key:
   ```
   MISTRAL_API_KEY="your-api-key"
   ```

## Usage

1. Run the main OCR processor:
   ```bash
   python app.py
   ```

2. Process questions from OCR output using LATEX:
   ```bash
   python process_questions.py
   ```

3. Process questions from OCR output using LLM:
   ```bash
   python process_questions_llm.py
   ```

## Output Format

The system produces structured JSON output following these schemas:

### MCQ Questions
```json
{
    "type": "mcq",
    "id": "string",
    "questionNumber": "number",
    "questionText": "string",
    "image": {
        "path": "string",
        "caption": "string",
        "isOptional": "boolean"
    },
    "options": [...],
    "correctAnswer": "number",
    "marks": "number",
    "explanation": "string"
}
```

### Short Answer Questions
```json
{
    "type": "short_answer",
    "id": "string",
    "questionNumber": "number",
    "questionText": "string",
    "image": {...},
    "subQuestions": [...],
    "totalMarks": "number"
}
```

### Fill in the Blanks
```json
{
    "type": "fill_blanks",
    "id": "string",
    "questionNumber": "number",
    "questionText": "string",
    "passage": "string",
    "blanks": [...],
    "totalMarks": "number"
}
```