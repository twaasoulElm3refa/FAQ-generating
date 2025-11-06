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
    return mysql.connector.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        charset="utf8mb4",
        use_unicode=True,
    )

def insert_full_record(user_id, file_path, url, written_data, questions_number, custom_questions, faq_result):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sql = f"""
            INSERT INTO `{TABLE}`
                (`user_id`,`file_path`,`url`,`written_data`,
                 `custom_questions`,`questions_number`,
                 `FAQ_result`,`edited_faq_result`,
                 `date_time`,`updated_at`)
            VALUES
                (%s,%s,%s,%s,
                 %s,%s,
                 %s,%s,
                 NOW(),NOW())
        """
        cur.execute(sql, (
            user_id,
            file_path or None,
            url or None,
            written_data or None,
            custom_questions or None,
            int(questions_number) if questions_number is not None else 10,
            faq_result or "",
            faq_result or "",
        ))
        conn.commit()
        return True
    except Error as e:
        try: conn.rollback()
        except: pass
        print(f"❌ insert_full_record error: {e}")
        raise
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
