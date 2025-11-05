# database.py
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT") or 3306)

TABLE = "wpl3_FAQ"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            charset="utf8mb4",
            use_unicode=True,
        )
        return conn
    except Error as e:
        print(f"❌ DB connect error: {e}")
        return None

def get_data_by_request_id(request_id: int):
    """Return row by id (or None). Keeps API imports happy."""
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"SELECT * FROM `{TABLE}` WHERE `id` = %s", (request_id,))
        row = cur.fetchone()
        return row or None
    except Error as e:
        print(f"❌ get_data_by_request_id error: {e}")
        return None
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

def update_faq_result(record_id: int, FAQ_result: str):
    conn = get_db_connection()
    if not conn:
        print("❌ Failed DB connection")
        return False
    cur = conn.cursor()
    try:
        FAQ_result = FAQ_result or "لا توجد نتيجة تم إنشاؤها"
        sql = f"""
            UPDATE `{TABLE}`
               SET `FAQ_result` = %s,
                   `updated_at` = NOW()
             WHERE `id` = %s
        """
        cur.execute(sql, (FAQ_result, record_id))
        conn.commit()
        return True
    except Error as e:
        print(f"❌ update_faq_result error: {e}")
        try: conn.rollback()
        except: pass
        return False
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

def insert_full_record(user_id, file_path, url, written_data, questions_number, custom_questions, faq_result):
    """
    Safe parameterized INSERT matching the API payload.
    Adjust columns if your table differs.
    """
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")

    file_path        = file_path or None
    url              = url or None
    written_data     = written_data or None
    custom_questions = custom_questions or None
    questions_number = int(questions_number) if questions_number is not None else None
    faq_result       = faq_result or ""

    cur = conn.cursor()
    try:
        sql = f"""
            INSERT INTO `{TABLE}`
                (`user_id`, `file_path`, `url`, `written_data`,
                 `questions_number`, `custom_questions`, `FAQ_result`,
                 `date_time`, `updated_at`)
            VALUES
                (%s, %s, %s, %s,
                 %s, %s, %s,
                 NOW(), NOW())
        """
        cur.execute(sql, (
            user_id, file_path, url, written_data,
            questions_number, custom_questions, faq_result
        ))
        conn.commit()
        return True
    except Error as e:
        print(f"❌ insert_full_record error: {e}")
        try: conn.rollback()
        except: pass
        raise
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
