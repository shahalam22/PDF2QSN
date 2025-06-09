import os
from mistralai import Mistral
from dotenv import load_dotenv
import requests
from io import BytesIO
import fitz  # PyMuPDF
import base64

# Load environment variables
load_dotenv()
api_key = os.environ.get("MISTRAL_API_KEY")
client = Mistral(api_key=api_key)

# Download the PDF
pdf_url = "https://www.testpapersfree.com/pdfs/P4_Science_2024_WA2_aitong.pdf"
# pdf_url = "https://www.testpapersfree.com/pdfs/P5_Maths_2024_WA2_aitong.pdf"
response = requests.get(pdf_url)
pdf_file = BytesIO(response.content)

# Initialize PyMuPDF document
try:
    pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
except Exception as e:
    print(f"Error: Could not open PDF. {str(e)}")
    exit(1)

# Initialize variable to store extracted text
full_text = ""
# Dictionary to store image data (filename: base64 string)
images_dict = {}

# Create a directory for saving images
image_dir = "ocr_images"
os.makedirs(image_dir, exist_ok=True)

# Process each page
for page_num in range(len(pdf_document)):
    try:
        # Load the page
        page = pdf_document[page_num]
        
        # Attempt to extract text directly (for machine-readable PDFs)
        text = page.get_text("text")
        if text and text.strip():
            full_text += f"\nPage {page_num + 1}:\n{text}"
        else:
            # Convert page to image for OCR
            pix = page.get_pixmap(dpi=300)
            
            # Convert pixmap to bytes (PNG format)
            img_byte_arr = pix.tobytes("png")
            
            # Encode image bytes to base64 for Mistral OCR
            img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # Process the page image with Mistral OCR
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "image_url",
                    "image_url": f"data:image/png;base64,{img_base64}"
                },
                include_image_base64=True
            )
            
            # Add OCR-extracted text to full_text
            page_text = ocr_response.pages[0].markdown
            full_text += f"\nPage {page_num + 1}:\n{page_text}"
            
            # Extract and save images from OCR response
            if hasattr(ocr_response.pages[0], 'images') and ocr_response.pages[0].images:
                for img_obj in ocr_response.pages[0].images:
                    img_id = img_obj.id  # e.g., 'img-0.jpeg'
                    img_base64 = img_obj.image_base64  # Base64 string
                    
                    # Decode base64 to bytes
                    img_bytes = base64.b64decode(img_base64)
                    
                    # Save the image to a file
                    img_filename = os.path.join(image_dir, img_id)
                    with open(img_filename, 'wb') as img_file:
                        img_file.write(img_bytes)
                    
                    # Store image info
                    images_dict[img_id] = img_filename
                    # Replace placeholder in text with actual file path
                    page_text = page_text.replace(f"![{img_id}]({img_id})", f"![{img_id}]({img_filename})")
            
            # Update full_text with modified text (including image paths)
            full_text = full_text.rsplit(f"\nPage {page_num + 1}:\n", 1)[0] + f"\nPage {page_num + 1}:\n{page_text}"
    except Exception as e:
        full_text += f"\nPage {page_num + 1}:\n[OCR Error: Could not process page. Error: {str(e)}]"

# Close the PDF document
pdf_document.close()

# Print the full extracted text
print("Full Extracted Text:")
print(full_text)

# Generate a Markdown file from the full_text
try:
    markdown_filename = "OCR_by_Mistral.md"
    with open(markdown_filename, 'w', encoding='utf-8') as md_file:
        md_file.write("# P4 Science 2024 Term 2 Review - OCR Extracted Content\n\n")
        md_file.write("Below is the extracted content from the 'P4_Science_2024_WA2_aitong.pdf' file, processed page by page.\n\n")
        md_file.write(full_text)
    print(f"Markdown file '{markdown_filename}' created successfully.")
except Exception as e:
    print(f"Error: Could not create Markdown file. {str(e)}")

# # Generate answers using a language model
# prompt = f"Here is the content of a P4 Science exam paper:\n{full_text}\n\nProvide answers to all questions in Sections A and B, showing reasoning where necessary."
# try:
#     completion = client.chat.complete(
#         model="mistral-large-latest",  # Or another suitable model
#         messages=[{"role": "user", "content": prompt}]
#     )
#     # Print the generated answers
#     print("Generated Answers:")
#     print(completion.choices[0].message.content)
# except Exception as e:
#     print(f"Error: Could not generate answers. {str(e)}")