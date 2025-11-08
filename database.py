import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_port = int(os.getenv("DB_PORT", "3306"))

TABLE = "wpl3_FAQ"

def get_db_connection():
    return mysql.connector.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )

def insert_full_record(user_id, file_path, url, written_data, questions_number, custom_questions, faq_result):
    """
    يُرجع الـ insert_id (int).
    الأعمدة في جدولك:
    id, user_id, file_path(text), url(text), written_data(longtext),
    custom_questions(longtext), questions_number(int), FAQ_result(longtext),
    edited_faq_result(longtext), date_time(datetime default current_timestamp), updated_at(datetime)
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = f"""
            INSERT INTO {TABLE}
            (user_id, file_path, url, written_data, custom_questions, questions_number, FAQ_result, edited_faq_result, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        # نحفظ نفس الناتج كنسخة أولية في edited_faq_result
        cur.execute(sql, (
            user_id,
            file_path,
            url,
            written_data,
            custom_questions,
            int(questions_number),
            faq_result,
            faq_result
        ))
        conn.commit()
        insert_id = cur.lastrowid
        return insert_id
    except Error as e:
        # ارفع الاستثناء للـ API ليرجعه في JSON
        raise
    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

def get_data_by_request_id(request_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM {TABLE} WHERE id=%s LIMIT 1", (request_id,))
        row = cur.fetchone()
        return row
    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

def update_faq_result(record_id, FAQ_result):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {TABLE} SET FAQ_result=%s, updated_at=NOW() WHERE id=%s",
            (FAQ_result, record_id)
        )
        conn.commit()
        return True
    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass
