import os
import json
import uuid
import datetime
import fitz  # PyMuPDF
import requests
import pymysql
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from docx import Document
from dotenv import load_dotenv
from typing import Optional
from openai import OpenAI
from database import get_db_connection ,fetch_faq ,update_faq

app = FastAPI()
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# MySQL connection settings from .env
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

JSON_FILE_PATH = "faq_examples.json"
try:
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        faq_examples = json.load(f)
except Exception as e:
    print(f"❌ Failed to load FAQ examples: {e}")
    faq_examples = []

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return "\n".join(para.text.strip() for para in doc.paragraphs if para.text.strip())

def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return ' '.join(soup.stripped_strings)
    except Exception as e:
        return ""

def generate_questions_and_answers(text, question_number, questions):
    examples_text = ""
    for idx, item in enumerate(faq_examples[:5], 1):
        examples_text += f"{idx}. س: {item['question']}\n   ج: {item['answer']}\n"

    prompt = f"""
نمط الأسئلة الشائعة لدينا كالتالي:
{examples_text}

اقرأ النص التالي واستخرج {question_number} سؤالًا شائعًا مع إجابته بطريقه احترافية:

\"\"\"
{text}
\"\"\"

مع الاجابة عن هذه الأسئلة:
{questions}

ملاحظات إضافية:
يمكن العثور على مزيد من المعلومات عن المنتجات والخدمات على الموقع الإلكتروني.
"""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content


        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ DB Error: {e}")

@app.post("/generate-FAQ/{user_id}")
async def generate_faq(
    user_id: str,
    file: Optional[UploadFile] = None,
    url: Optional[str] = Form(None),
    question_number: int = Form(10),
    custom_questions: str = Form("")
):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    user_session_id = user_id

    faq_release = fetch_faq(user_session_id)
    
    extracted_text = ""
    file_path = None

    if file:
        ext = os.path.splitext(file.filename)[1].lower()
        new_filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        if ext == ".pdf":
            extracted_text = extract_text_from_pdf(file_path)
        elif ext == ".docx":
            extracted_text = extract_text_from_docx(file_path)
        else:
            return JSONResponse({"error": "Unsupported file type."}, status_code=400)
    elif url:
        extracted_text = extract_text_from_url(url)
    else:
        return JSONResponse({"error": "Please upload a file or provide a URL."}, status_code=400)

    if not extracted_text.strip():
        return JSONResponse({"error": "Failed to extract text from input."}, status_code=400)

    faq_result = generate_questions_and_answers(extracted_text, question_number, custom_questions)
    update_data= update_faq(user_id,faq_result)

    connection.commit()
    cursor.close()
    connection.close()

    return {"questions_and_answers": faq_result}
