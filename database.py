import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()

db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_port = int(os.getenv("DB_PORT") or 3306)

TABLE = "wpl3_FAQ"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port,
            charset="utf8mb4",   # ensure Arabic/emoji safe
            use_unicode=True
        )
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def update_faq_result(record_id, FAQ_result):
    conn = get_db_connection()
    if not conn:
        print("Failed to establish database connection")
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
        print(f"❌ Error updating data: {e}")
        return False
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

def insert_full_record(user_id, file_path, url, written_data, questions_number, custom_questions, faq_result):
    """
    Safe parameterized INSERT. Matches columns you’re passing from FastAPI.
    If your table doesn’t have `written_data` or `date_time`, comment them out accordingly.
    """
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")

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
            user_id,
            file_path or None,
            url or None,
            written_data or None,
            int(questions_number) if questions_number is not None else None,
            custom_questions or None,
            faq_result or ""
        ))
        conn.commit()
        return True
    except Error as e:
        # Log full error for diagnostics
        print(f"❌ Insert error: {e}")
        conn.rollback()
        raise
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

