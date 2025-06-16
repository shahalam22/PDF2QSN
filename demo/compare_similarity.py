from transformers import BertTokenizer, BertModel
import torch
import json
import re
from bs4 import BeautifulSoup
import markdown

def clean_text(text):
    """Clean text by removing special characters, latex expressions and normalizing whitespace"""
    # Remove LaTeX expressions
    text = re.sub(r'\$.*?\$', '', text)
    # Remove special characters but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text.lower().strip()

def extract_text_from_markdown(md_file):
    """Extract all text content from markdown file"""
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML then to text
    html = markdown.markdown(md_content)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Get all text content
    text = soup.get_text()
    return clean_text(text)

def extract_text_from_json(json_file):
    """Extract all question text from JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions_text = []
    
    # Extract MCQ questions
    for q in data['questions'].get('mcq', []):
        questions_text.append(q['questionText'])
        # Include options if they exist
        if 'options' in q:
            for opt in q['options']:
                if 'text' in opt:
                    questions_text.append(opt['text'])
    
    # Extract short answer questions
    for q in data['questions'].get('short_answer', []):
        questions_text.append(q['questionText'])
    
    return clean_text(' '.join(questions_text))

def get_bert_embedding(text, model, tokenizer):
    """Get BERT embedding for a text"""
    # Tokenize and get model output
    with torch.no_grad():
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        outputs = model(**inputs)
        # Use [CLS] token embedding as the text embedding
        return outputs.last_hidden_state[:, 0, :].numpy()

def calculate_similarity(text1, text2):
    """Calculate cosine similarity between two texts using BERT"""
    # Initialize BERT
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertModel.from_pretrained('bert-base-uncased')
    model.eval()
    
    # Get embeddings
    emb1 = get_bert_embedding(text1, model, tokenizer)
    emb2 = get_bert_embedding(text2, model, tokenizer)
    
    # Calculate cosine similarity
    similarity = torch.nn.functional.cosine_similarity(
        torch.tensor(emb1), 
        torch.tensor(emb2)
    )[0].item()
    
    return similarity

def main():
    # File paths
    md_file = 'OCR_by_Mistral.md'
    json_file = 'validation/response_P4_Maths_2023_SA1_Raffles.json'
    
    # Extract text from both files
    print("Extracting text from files...")
    md_text = extract_text_from_markdown(md_file)
    json_text = extract_text_from_json(json_file)
    
    # Calculate similarity
    print("Calculating similarity...")
    similarity = calculate_similarity(md_text, json_text)
    
    print(f"\nResults:")
    print(f"Similarity score: {similarity:.4f}")
    print(f"Percentage match: {similarity * 100:.2f}%")
    
    # Print text length comparison
    print(f"\nText length comparison:")
    print(f"Markdown text length: {len(md_text)} characters")
    print(f"JSON text length: {len(json_text)} characters")
    
    if similarity >= 0.8:
        print("\nInterpretation: High similarity - The OCR output matches well with the JSON content")
    elif similarity >= 0.6:
        print("\nInterpretation: Moderate similarity - Most content is captured but there may be some differences")
    else:
        print("\nInterpretation: Low similarity - Significant differences between OCR and JSON content")

if __name__ == "__main__":
    main()







# import json
# import re
# import torch
# from transformers import BertTokenizer, BertModel
# import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity

# # Load BERT model and tokenizer
# tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
# model = BertModel.from_pretrained('bert-base-uncased')
# model.eval()

# # Function to get BERT embeddings for a given text
# def get_bert_embedding(text):
#     inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
#     with torch.no_grad():
#         outputs = model(**inputs)
#     # Use the [CLS] token embedding
#     embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
#     return embedding

# # Function to compute cosine similarity between two texts
# def compute_similarity(text1, text2):
#     emb1 = get_bert_embedding(text1)
#     emb2 = get_bert_embedding(text2)
#     similarity = cosine_similarity([emb1], [emb2])[0][0]
#     return similarity

# # Load the JSON file
# with open('response_P4_Maths_2023_SA1_Raffles.json', 'r', encoding='utf-8') as f:
#     json_data = json.load(f)

# # Extract questions from JSON
# json_questions = {}
# for q_type in ['mcq', 'short_answer']:
#     for q in json_data['questions'][q_type]:
#         question_number = q['questionNumber']
#         question_text = q['questionText']
#         json_questions[question_number] = question_text

# # Load and parse the OCR markdown file
# with open('OCR_response_P4_Maths_2023_SA1_Raffles.md', 'r', encoding='utf-8') as f:
#     ocr_content = f.read()

# # Function to clean question text
# def clean_text(text):
#     # Remove LaTeX, special characters, and extra whitespace
#     text = re.sub(r'\$[^\$]+\$', '', text)  # Remove LaTeX
#     text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
#     text = text.strip()
#     return text

# # Extract questions from OCR markdown
# ocr_questions = {}
# section_a_pattern = r'(\d+)\.\s+([^\n]+?)(?=\s+\(\d+\)|$|\n\n)'
# section_b_pattern = r'(\d+)\.\s+([^\n]+?)(?=\s+Ans:|\n\n)'
# section_c_pattern = r'(\d+)\.\s+([^\n]+?)(?=\s+\[|\n\n)'

# # Section A (MCQs)
# for match in re.finditer(section_a_pattern, ocr_content):
#     q_num = int(match.group(1))
#     q_text = clean_text(match.group(2))
#     if q_num <= 15:  # Section A questions 1-15
#         ocr_questions[q_num] = q_text

# # Section B (Short Answer)
# for match in re.finditer(section_b_pattern, ocr_content):
#     q_num = int(match.group(1))
#     q_text = clean_text(match.group(2))
#     if 16 <= q_num <= 35:  # Section B questions 16-35
#         ocr_questions[q_num] = q_text

# # Section C (Long Answer)
# for match in re.finditer(section_c_pattern, ocr_content):
#     q_num = int(match.group(1))
#     q_text = clean_text(match.group(2))
#     if 36 <= q_num <= 44:  # Section C questions 36-44
#         ocr_questions[q_num] = q_text

# # Validate that all OCR questions are present in JSON
# missing_questions = []
# similarity_threshold = 0.9  # Threshold for considering questions as matching

# for ocr_q_num, ocr_q_text in ocr_questions.items():
#     if ocr_q_num not in json_questions:
#         missing_questions.append((ocr_q_num, ocr_q_text, "Not found in JSON"))
#     else:
#         json_q_text = clean_text(json_questions[ocr_q_num])
#         similarity = compute_similarity(ocr_q_text, json_q_text)
#         if similarity < similarity_threshold:
#             missing_questions.append((ocr_q_num, ocr_q_text, f"Low similarity ({similarity:.2f}) with JSON text: {json_q_text}"))

# # Report results
# print("Validation Results:")
# if not missing_questions:
#     print("All OCR questions are present in the JSON file with high similarity.")
# else:
#     print("Issues found:")
#     for q_num, q_text, issue in missing_questions:
#         print(f"Question {q_num}: {q_text}")
#         print(f"Issue: {issue}\n")

# # Print total questions checked
# print(f"Total OCR questions checked: {len(ocr_questions)}")
# print(f"Total JSON questions: {len(json_questions)}")