import os
import json
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from openai import OpenAI
from docx import Document
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
import uuid
import datetime
import os
from dotenv import load_dotenv


app = FastAPI()
load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")

# ✅ Where to save uploaded files temporarily
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ Load FAQ examples once at startup
JSON_FILE_PATH = "faq_examples.json"
try:
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        faq_examples = json.load(f)
    print(f"✅ Loaded {len(faq_examples)} FAQ examples from '{JSON_FILE_PATH}'")
except Exception as e:
    print(f"❌ Failed to load FAQ examples: {e}")
    faq_examples = []

# 📄 Extract text from PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

# 📄 Extract text from DOCX file
def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return "\n".join(para.text.strip() for para in doc.paragraphs if para.text.strip())

# 🌐 Extract text from URL
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = ' '.join(soup.stripped_strings)
        return text
    except Exception as e:
        print(f"❌ Error fetching URL: {e}")
        return ""

# 🧠 Generate questions and answers using OpenAI
def generate_questions_and_answers(text, question_number,questions):
    examples_text = ""
    for idx, item in enumerate(faq_examples[:5], 1):  # use first 5 examples
        examples_text += f"{idx}. س: {item['question']}\n   ج: {item['answer']}\n"

    prompt = f"""
نمط الأسئلة الشائعة لدينا كالتالي:
{examples_text}

اقرأ النص التالي واستخرج {question_number} سؤالًا شائعًا مع إجابته بطريقهاحترافيه مع الاجابة بشكل كامل .
النص:
\"\"\"
{text}
\"\"\"
 مع الاجابة عن هذه الاسالة {questions}

  اضف فى النهاية 
 ملاحظات إضافية:
يمكن العثور على مزيد من المعلومات عن المنتجات والخدمات على الموقع الإلكتروني 

"""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# ✅ API endpoint: upload file or enter URL → get Q&A
@app.post("/generate-FAQ/{user_id}")
async def generate_faq(
    user_id: str,
    file: UploadFile = None,
    url: str = Form(None),
    question_number: int = Form(10)
):
    extracted_text = ""

    if file:
        original_filename = file.filename
        ext = os.path.splitext(original_filename)[1].lower()   # get .pdf or .docx

        # Generate unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        new_filename = f"{timestamp}_{unique_id}{ext}"

        saved_path = os.path.join(UPLOAD_FOLDER, new_filename)

        # Save file safely
        with open(saved_path, "wb") as f:
            f.write(await file.read())
        print(f"✅ File saved safely at: {saved_path}")

        # Detect extension and extract text
        if ext == ".pdf":
            extracted_text = extract_text_from_pdf(saved_path)
        elif ext == ".docx":
            extracted_text = extract_text_from_docx(saved_path)
        else:
            return JSONResponse({"error": "Unsupported file type."}, status_code=400)
            # ⚠️ Remove file after use (or keep it)
            os.remove(saved_path)

    elif url:
        extracted_text = extract_text_from_url(url)

    else:
        return JSONResponse({"error": "Please upload a file or provide a URL."}, status_code=400)

    if not extracted_text.strip():
        return JSONResponse({"error": "Failed to extract text from input."}, status_code=400)

   # extracted_text = extracted_text[:36000]

    qa_result = generate_questions_and_answers(extracted_text, question_number)
    return {"questions_and_answers": qa_result}


