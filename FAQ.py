import os
import json
import uuid
import datetime
import fitz  # PyMuPDF
import requests
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from docx import Document
from dotenv import load_dotenv
from typing import Optional
from openai import OpenAI
from database import get_db_connection ,update_faq_result


app = FastAPI()
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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


@app.post("/generate-FAQ/{user_id}")
async def generate_faq(
    user_id: str,
    file: Optional[UploadFile] = None,
    url: Optional[str] = Form(None),
    questions_number: int = Form(...),
    custom_questions: str = Form(""),
    request_id: int = Form(...)
):
    try:
        extracted_text = ""
        saved_path = None
        UPLOAD_FOLDER = "uploads"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        if file and file.filename != "":
            ext = os.path.splitext(file.filename)[1].lower()
            new_filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
            saved_path = os.path.join(UPLOAD_FOLDER, new_filename)
            with open(saved_path, "wb") as f:
                f.write(await file.read())

            if ext == ".pdf":
                extracted_text = extract_text_from_pdf(saved_path)
            elif ext == ".docx":
                extracted_text = extract_text_from_docx(saved_path)
        elif url:
            extracted_text = extract_text_from_url(url)

        if not extracted_text.strip():
            return JSONResponse({"error": "No content found"}, status_code=400)

        with open("faq_examples.json", "r", encoding="utf-8") as f:
            faq_examples = json.load(f)

        faq_result = generate_questions_and_answers(extracted_text, questions_number, custom_questions, faq_examples)

        saved = update_faq_result(request_id, faq_result, saved_path or "")
        if saved:
            return {"questions_and_answers": faq_result}
        else:
            return JSONResponse({"error": "Failed to save result"}, status_code=500)

    except Exception as e:
        print(f"❌ Exception: {e}")
        return JSONResponse({"error": "Server error occurred."}, status_code=500)

        faq_result = generate_questions_and_answers(extracted_text, questions_number, custom_questions, faq_examples)
        saving_data = update_faq_result(request_id, faq_result, saved_path)

        if saving_data:
            print(f"✅ Saved: {saving_data}")
        else:
            print("❌ Failed to update result")

        return {"questions_and_answers": faq_result}

    except Exception as e:
        print(f"❌ Exception: {e}")
        return JSONResponse({"error": "Server error occurred."}, status_code=500)


    return {"questions_and_answers": faq_result}
