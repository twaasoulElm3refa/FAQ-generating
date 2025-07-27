import os
import json
import fitz  # PDF
import requests
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
from docx import Document
from pptx import Presentation
from openai import OpenAI
from dotenv import load_dotenv
from database import get_data_by_request_id, update_faq_result
from datetime import datetime

# تحميل المتغيرات البيئية
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # غيّر إلى دومينك الفعلي
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# استخراج النص من PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

# استخراج النص من DOCX
def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return "\n".join(para.text.strip() for para in doc.paragraphs if para.text.strip())

# استخراج النص من PPTX
def extract_text_from_pptx(pptx_path):
    text = ""
    prs = Presentation(pptx_path)
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

# استخراج النص من رابط
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return ' '.join(soup.stripped_strings)
    except Exception:
        return ""

# توليد الأسئلة من OpenAI
def generate_questions_and_answers(text, question_number, questions, faq_examples):
    examples_text = ""
    for idx, item in enumerate(faq_examples[:5], 1):
        examples_text += f"{idx}. س: {item['question']}\n   ج: {item['answer']}\n"

    prompt = f"""
نمط الأسئلة الشائعة لدينا كالتالي:
{examples_text}

اقرأ النص التالي واستخرج {question_number} سؤالًا شائعًا مع إجابته بطريقة احترافية:

\"\"\"{text}\"\"\"

مع الإجابة عن هذه الأسئلة:
{questions}
"""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# واجهة المعالجة عبر record_id
@app.get("/process-faq/{record_id}")
def process_faq(record_id: int):
    try:
        # جلب البيانات من قاعدة البيانات
        data = get_data_by_request_id(record_id)
        if not data:
            return JSONResponse({"error": "No data found for this ID."}, status_code=404)

        file_path = data.get("file_path")
        url = data.get("url")
        questions_number = data.get("questions_number", 10)
        custom_questions = data.get("custom_questions", "")

        extracted_text = ""

        # استخراج النص من الملف
        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".pdf":
                extracted_text = extract_text_from_pdf(file_path)
            elif ext in [".doc", ".docx"]:
                extracted_text = extract_text_from_docx(file_path)
            elif ext in [".pptx"]:
                extracted_text = extract_text_from_pptx(file_path)

        # أو من الرابط
        elif url:
            extracted_text = extract_text_from_url(url)

        if not extracted_text.strip():
            return JSONResponse({"error": "تعذر استخراج نص من الرابط أو الملف."}, status_code=400)

        with open("faq_examples.json", "r", encoding="utf-8") as f:
            faq_examples = json.load(f)

        # توليد الأسئلة
        faq_result = generate_questions_and_answers(
            extracted_text, questions_number, custom_questions, faq_examples
        )

        # تحديث السجل بالنتيجة
        saved = update_faq_result(record_id, faq_result)

        # حذف الملف بعد المعالجة
        if saved and file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return JSONResponse(content={"questions_and_answers": faq_result})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)
