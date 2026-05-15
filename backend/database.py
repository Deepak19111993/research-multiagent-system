import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from urllib.parse import urlparse

DATABASE_URL = os.getenv('DATABASE_URL')

def get_connection():
    if DATABASE_URL:
        # Use PostgreSQL for Production
        return psycopg2.connect(DATABASE_URL)
    else:
        # Use SQLite for Local Development
        return sqlite3.connect('blogs.db')

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        # PostgreSQL Syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blogs (
                id SERIAL PRIMARY KEY,
                user_email TEXT NOT NULL,
                topic TEXT NOT NULL,
                blog_post TEXT NOT NULL,
                critique_report TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite Syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                topic TEXT NOT NULL,
                blog_post TEXT NOT NULL,
                critique_report TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

def save_blog(user_email: str, topic: str, blog_post: str, critique_report: str, score: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        INSERT INTO blogs (user_email, topic, blog_post, critique_report, score)
        VALUES (%s, %s, %s, %s, %s)
    ''' if DATABASE_URL else '''
        INSERT INTO blogs (user_email, topic, blog_post, critique_report, score)
        VALUES (?, ?, ?, ?, ?)
    '''
    
    cursor.execute(query, (user_email, topic, blog_post, critique_report, score))
    conn.commit()
    conn.close()

def get_user_blogs(user_email: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT id, topic, blog_post, critique_report, score, timestamp FROM blogs WHERE user_email = %s ORDER BY id ASC' if DATABASE_URL else 'SELECT id, topic, blog_post, critique_report, score, timestamp FROM blogs WHERE user_email = ? ORDER BY id ASC'
    
    cursor.execute(query, (user_email,))
    rows = cursor.fetchall()
    conn.close()
    
    blogs = []
    for row in rows:
        blogs.append({
            "id": row[0],
            "topic": row[1],
            "blog_post": row[2],
            "critique_report": row[3],
            "score": row[4],
            "timestamp": str(row[5])
        })
        
    return blogs
