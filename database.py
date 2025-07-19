import mysql.connector
from mysql.connector import Error
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # يبحث عن .env في مجلد المشروع الحالي

api_key = os.getenv("OPENAI_API_KEY")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_port = os.getenv("DB_PORT")


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        if connection.is_connected():
            print("Connected to MySQL successfully!")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def update_faq_result(request_id, FAQ_result, pdf_file_name):
    connection = get_db_connection()
    if connection is None:
        print("Failed to establish database connection")
        return False
    try:
        if not FAQ_result:
            FAQ_result = "لا توجد نتيجة تم إنشاؤها"
        if not pdf_file_name:
            pdf_file_name = ""
        cursor = connection.cursor()
        query = """
        INSERT INTO wpl3_FAQ_result (request_id, FAQ_result, pdf_file_name)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (request_id, FAQ_result, pdf_file_name))
        connection.commit()
        print("✅ Data inserted successfully into wpl3_FAQ_result")
        return True
    except Error as e:
        print(f"❌ Error updating data: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()




