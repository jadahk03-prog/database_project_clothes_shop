import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """PostgreSQL 연결 반환"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "shop_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )

def get_cursor(conn):
    """딕셔너리 형태로 결과 반환하는 커서"""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
