import os
import json
#import uuid
#import datetime
import fitz  # PyMuPDF
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from docx import Document
from dotenv import load_dotenv
from openai import OpenAI
from database import get_data_by_request_id, update_faq_result
from pydantic import BaseModel
import pymysql

app = FastAPI()
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
UPLOAD_DIR = "./uploads"  # تأكد من أن المجلد موجود ولديه صلاحيات كتابة
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return ' '.join(soup.stripped_strings)
    except Exception as e:
        return ""

def generate_questions_and_answers(text, question_number, questions, faq_examples):
    examples_text = ""
    for idx, item in enumerate(faq_examples[:5], 1):
        examples_text += f"{idx}. س: {item['question']}\n   ج: {item['answer']}\n"

    prompt = f"""
نمط الأسئلة الشائعة لدينا كالتالي:
{examples_text}

اقرأ النص التالي واستخرج {question_number} سؤالًا شائعًا مع إجابته بطريقة احترافية:

\"\"\"
{text}
\"\"\"

مع الإجابة عن هذه الأسئلة:
{questions}
"""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content


#@app.get("/generate-FAQ/{request_id}")
#async def generate_faq(request_id: int):

class FAQRequest(BaseModel):
    request_id: int
    user_id: int
    url: str
    question_number: int
    custom_questions: str


@app.get("/process-faq/{record_id}")
def process_faq(record_id: int):
    try:
        data = get_data_by_request_id(request_id)
        if not data:
            return JSONResponse({"error": "No data found for this ID."}, status_code=404)
            
        file_path = data.get("file_path")
        url = data.get("url")
        questions_number = data.get("questions_number", 10)
        custom_questions = data.get("custom_questions", "")

        extracted_text = ""

        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".pdf":
                extracted_text = extract_text_from_pdf(file_path)
            elif ext in [".doc", ".docx"]:
                extracted_text = extract_text_from_docx(file_path)
        elif url:
            extracted_text = extract_text_from_url(url)

        if not extracted_text.strip():
            return JSONResponse({"error": "No content found."}, status_code=400)

        with open("faq_examples.json", "r", encoding="utf-8") as f:
            faq_examples = json.load(f)

        faq_result = generate_questions_and_answers(extracted_text, questions_number, custom_questions, faq_examples)
        saved = update_faq_result(record_id, faq_result)
        #data.request_id
        if saved:
            # 🗑️ حذف الملف بعد الاستخدام
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️ Deleted file: {file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to delete file: {e}")

            return JSONResponse(content={"questions_and_answers": faq_result})
        else:
            return JSONResponse({"error": "Failed to save result"}, status_code=500)

    except Exception as e:
        print(f"❌ Exception: {e}")
        return JSONResponse({"error": "Server error occurred."}, status_code=500)
#, file_path or ""
