import json
import re

def clean_text(text):
    """Clean text by removing page markers, extra whitespace, and other artifacts"""
    # Remove page markers
    text = re.sub(r'Page \d+:', '', text)
    # Remove "Go on to the next page" markers
    text = re.sub(r'\(?\s*Go on to the next page\s*\)?', '', text)
    # Remove multiple newlines and spaces
    text = re.sub(r'\s+', ' ', text)
    # Clean up any remaining artifacts
    text = re.sub(r'\(\s*\)', '', text)
    return text.strip()

def read_answers_from_text(text):
    """Extract answers from the answer template section"""
    answers = {}
    answer_pattern = r'(\d+)\)(\d+)'
    matches = re.finditer(answer_pattern, text)
    for match in matches:
        q_num = match.group(1)
        ans = match.group(2)
        answers[f"q{q_num}"] = int(ans)
    
    # Extract short answer model answers
    model_answers = {}
    pattern = r'Q(\d+[a-z])\s*\|\s*([^\|]+)'
    matches = re.finditer(pattern, text)
    for match in matches:
        q_id = match.group(1)
        answer = match.group(2).strip()
        model_answers[f"q{q_id}"] = answer
    
    return answers, model_answers

def extract_mcq_questions(text, answers):
    """Extract MCQ questions from Section A"""
    questions = []
    
    # Find Section A content
    section_match = re.search(r'Section A.*?(?=Section B|$)', text, re.DOTALL)
    if not section_match:
        return questions
    
    section_text = section_match.group()
    
    # Remove the section header and instructions
    section_text = re.sub(r'^Section A.*?marks\)', '', section_text, flags=re.DOTALL).strip()
    
    # Split into individual questions using number at start of line
    question_blocks = re.split(r'\n(?=\d+[\.|\s])', section_text)
    
    for block in question_blocks:
        # Extract question number
        num_match = re.match(r'(\d+)[\.\s]+(.*)', block.strip(), re.DOTALL)
        if not num_match:
            continue
            
        q_num = int(num_match.group(1))
        q_text = num_match.group(2).strip()
        
        # Extract image if present
        image_info = None
        img_match = re.search(r'!\[(.*?)\]\((.*?)\)', q_text)
        if img_match:
            image_info = {
                "path": img_match.group(2).replace('\\', '/'),
                "caption": "Question illustration",
                "isOptional": False
            }
            q_text = re.sub(r'!\[.*?\]\(.*?\)', '', q_text).strip()
        
        # Split question text and options
        parts = re.split(r'\s*\(1\)', q_text, maxsplit=1)
        if len(parts) != 2:
            continue
            
        question_text = clean_text(parts[0])
        options_text = '(1)' + parts[1]
        
        # Extract options using a more precise pattern
        options = []
        option_pattern = r'\((\d)\)\s*((?:(?!\(\d\)|Page \d+:).)*)'
        for opt_match in re.finditer(option_pattern, options_text, re.DOTALL):
            opt_num = int(opt_match.group(1))
            opt_text = clean_text(opt_match.group(2))
            
            # Check for option image
            opt_img_match = re.search(r'!\[(.*?)\]\((.*?)\)', opt_text)
            option = {
                "id": opt_num,
                "text": re.sub(r'!\[.*?\]\(.*?\)', '', opt_text).strip()
            }
            
            if opt_img_match:
                option["image"] = {
                    "path": opt_img_match.group(2).replace('\\', '/'),
                    "caption": f"Option {opt_num} illustration",
                    "isOptional": False
                }
            
            options.append(option)
        
        # Only add complete questions
        if options and len(options) == 4:  # MCQ should have exactly 4 options
            mcq = {
                "type": "mcq",
                "id": f"q{q_num}",
                "questionNumber": q_num,
                "questionText": question_text,
                "options": options,
                "correctAnswer": answers.get(f"q{q_num}"),
                "marks": 2
            }
            
            if image_info:
                mcq["image"] = image_info
                
            questions.append(mcq)
    
    return questions

def clean_model_answer(text):
    """Clean model answer text by removing LaTeX markers and normalizing blanks"""
    # Replace LaTeX qquad with a standard blank
    text = re.sub(r'\$\\qquad\$', '___', text)
    # Normalize other types of blanks
    text = re.sub(r'_{2,}|\.\.\.', '___', text)
    return clean_text(text)

def extract_fill_blanks(text, model_answers):
    """Extract fill in the blanks questions with both traditional blanks and $\qquad$ patterns"""
    questions = []
    
    # Look for paragraphs containing either $\qquad$ or traditional blank patterns
    text_blocks = text.split('\n\n')
    
    for block in text_blocks:
        # Check for any type of blank marker
        if not re.search(r'\$\\qquad\$|_{2,}|\.\.\.', block):
            continue
            
        # Extract question number if present
        num_match = re.match(r'.*?(\d+)[a-z]?[\.\s]', block)
        if not num_match:
            continue
            
        q_num = int(num_match.group(1))
        
        # Find all blanks (marked by $\qquad$ or traditional patterns)
        blank_pattern = r'\$\\qquad\$|_{2,}|\.\.\.'
        blank_positions = list(re.finditer(blank_pattern, block))
        if not blank_positions:
            continue
            
        # Split text into segments
        segments = re.split(blank_pattern, block)
        passage = ''
        blanks = []
        
        for i, blank in enumerate(blank_positions, 1):
            q_id = f"q{q_num}{chr(96+i)}"  # a, b, c, etc.
            model_answer = clean_model_answer(model_answers.get(q_id, ""))
            
            blank_obj = {
                "id": i,
                "position": i,
                "correctAnswer": model_answer,
                "marks": 1,
                "alternatives": [model_answer] if model_answer else []
            }
            blanks.append(blank_obj)
            
            # Build passage with underscores for blanks
            if i <= len(segments):
                passage += clean_text(segments[i-1]) + "___"
        
        # Complete the passage with the last segment
        if len(segments) > len(blanks):
            passage += clean_text(segments[-1])
        
        # Create question object
        question = {
            "type": "fill_blanks",
            "id": f"q{q_num}",
            "questionNumber": q_num,
            "questionText": clean_text(segments[0]),
            "passage": passage,
            "blanks": blanks,
            "totalMarks": len(blanks)
        }
        
        # Extract image if present
        img_match = re.search(r'!\[(.*?)\]\((.*?)\)', block)
        if img_match:
            question["image"] = {
                "path": img_match.group(2).replace('\\', '/'),
                "caption": "Question illustration",
                "isOptional": False
            }
        
        questions.append(question)
    
    return questions

def extract_short_answer_questions(text, model_answers):
    """Extract short answer questions from Section B"""
    questions = []
    
    # Find Section B content
    section_match = re.search(r'Section B.*?(?=End of Paper|$)', text, re.DOTALL)
    if not section_match:
        return questions
    
    section_text = section_match.group()
    
    # Remove the section header and instructions
    section_text = re.sub(r'^Section B.*?marks\]', '', section_text, flags=re.DOTALL).strip()
    
    # Split into individual questions using number at start of line
    question_blocks = re.split(r'\n(?=\d+[\.|\s])', section_text)
    
    for block in question_blocks:
        # Extract question number
        num_match = re.match(r'(\d+)[\.\s]+(.*)', block.strip(), re.DOTALL)
        if not num_match:
            continue
            
        q_num = int(num_match.group(1))
        q_text = num_match.group(2).strip()
        
        # Extract image if present
        image_info = None
        img_match = re.search(r'!\[(.*?)\]\((.*?)\)', q_text)
        if img_match:
            image_info = {
                "path": img_match.group(2).replace('\\', '/'),
                "caption": "Question illustration",
                "isOptional": False
            }
            q_text = re.sub(r'!\[.*?\]\(.*?\)', '', q_text).strip()
        
        # Get main question text (before any sub-questions)
        main_text = re.split(r'\s*\([a-z]\)', q_text)[0].strip()
        
        # Extract sub-questions
        sub_questions = []
        sub_pattern = r'\(([a-z])\)\s*((?:(?!\([a-z]\)|Page \d+:).)*)'
        for sub_match in re.finditer(sub_pattern, q_text, re.DOTALL):
            sub_letter = sub_match.group(1)
            sub_text = clean_text(sub_match.group(2))
            q_id = f"q{q_num}{sub_letter}"
            
            # Get model answer and extract keywords, cleaning any LaTeX markers
            model_answer = clean_model_answer(model_answers.get(q_id, ""))
            keywords = [clean_model_answer(word.strip()) for word in model_answer.split() if len(word.strip()) > 3]
            keywords = [k for k in keywords if k and k != '___']  # Remove blank markers from keywords
            
            sub_q = {
                "id": q_id,
                "text": sub_text,
                "marks": 1,
                "modelAnswer": model_answer,
                "keywords": keywords[:5]  # Take up to 5 significant keywords
            }
            
            sub_questions.append(sub_q)
        
        # Only add if we have a valid question
        if main_text and main_text != "marks)":
            question = {
                "type": "short_answer",
                "id": f"q{q_num}",
                "questionNumber": q_num,
                "questionText": clean_text(main_text),
                "subQuestions": sub_questions,
                "totalMarks": len(sub_questions) or 1  # At least 1 mark
            }
            
            if image_info:
                question["image"] = image_info
                
            questions.append(question)
    
    return questions

def process_questions(markdown_file):
    """Main function to process questions from the OCR output"""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract answers and model answers from the correction template
    answers, model_answers = read_answers_from_text(content)
    
    # Process each type of question
    mcq_questions = extract_mcq_questions(content, answers)
    short_answer_questions = extract_short_answer_questions(content, model_answers)
    fill_blanks_questions = extract_fill_blanks(content, model_answers)
    
    # Combine all questions
    all_questions = {
        "mcq": mcq_questions,
        "short_answer": short_answer_questions,
        "fill_blanks": fill_blanks_questions
    }
    
    # Save to JSON file
    output_file = 'questions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)
    
    return all_questions

if __name__ == "__main__":
    # Process the OCR output file
    markdown_file = "OCR_by_Mistral.md"
    questions = process_questions(markdown_file)
    
    # Print summary
    print(f"Questions processed and saved to questions.json")
    print(f"Summary:")
    print(f"MCQ questions: {len(questions['mcq'])}")
    print(f"Short answer questions: {len(questions['short_answer'])}")
    print(f"Fill in the blanks questions: {len(questions['fill_blanks'])}")