import sqlite3
import json
import os

DB_NAME = 'blogs.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
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
    cursor.execute('''
        INSERT INTO blogs (user_email, topic, blog_post, critique_report, score)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_email, topic, blog_post, critique_report, score))
    conn.commit()
    conn.close()

def get_user_blogs(user_email: str):
    """Returns a list of dictionaries containing the user's generated blogs, ordered by newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, topic, blog_post, critique_report, score, timestamp 
        FROM blogs 
        WHERE user_email = ?
        ORDER BY id ASC
    ''', (user_email,))
    
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
            "timestamp": row[5]
        })
        
    return blogs
