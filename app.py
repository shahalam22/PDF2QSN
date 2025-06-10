import os

from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

file_name = "P4_Science_2024_WA2_aitong.pdf"

uploaded_file = client.files.upload(
    file = {
        "file_name": file_name,
        "content": open(file_name, "rb")
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
    include_image_base64 = True
)

# print(response)

import base64

def data_uri_to_bytes(data_uri):
    _, encoded = data_uri.split(',', 1)
    return base64.b64decode(encoded)


image_dir = "exported_images"
os.makedirs(image_dir, exist_ok=True)

def export_image(image):
    parsed_image = data_uri_to_bytes(image.image_base64)
    # Create file path using os.path.join
    image_path = os.path.join(image_dir, image.id)
    with open(image_path, 'wb') as file:
        file.write(parsed_image)
    return image_path

with open("OCR_by_Mistral.md", "w") as f:
    for page in response.pages:
        markdown_content = page.markdown
        for image in page.images:
            # Export image and get the path
            image_path = export_image(image)
            # Update image reference in markdown
            markdown_content = markdown_content.replace(
                f"![{image.id}]({image.id})", 
                f"![{image.id}]({image_path})"
            )
        f.write(markdown_content)