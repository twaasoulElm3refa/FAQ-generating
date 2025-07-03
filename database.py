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

def fetch_faq(user_id: str ):
    connection = get_db_connection()
    if connection is None:
        print("Failed to establish database connection")
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT file_path,url,custom_questions,questions_number
        FROM wpl3_FAQ
        WHERE user_id = %s 
        """
        cursor.execute(query, (user_id,))

        # Fetch the first row
        faq_result = cursor.fetchall()

        return faq_result

    except Error as e:
        print(f"Error fetching data: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()



def update_faq(file_path,FAQ_result):
    connection = get_db_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        query = """
        UPDATE wpl3_FAQ 
        SET FAQ_result = %s 
        WHERE file_path = %s
        """
        cursor.execute(query, (FAQ_result,file_path))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating data: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


