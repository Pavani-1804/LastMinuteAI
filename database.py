import sqlite3
import os
import json
import logging
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass

    # Spaces Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            icon_color TEXT DEFAULT '#4f46e5',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Projects Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            space_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            learning_goal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Materials Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'queued', -- queued, processing, ready, failed
            chunk_count INTEGER DEFAULT 0,
            concept_count INTEGER DEFAULT 0,
            error_msg TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Chunks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            page_number INTEGER DEFAULT 1,
            content TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Concepts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'General',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Concept Mastery Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_mastery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            concept_id INTEGER NOT NULL,
            mastery_level REAL DEFAULT 50.0, -- 0 to 100%
            trend TEXT DEFAULT 'stable', -- improving, stable, requires_attention
            total_evaluations INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
            UNIQUE(project_id, concept_id)
        )
    """)

    # Conversations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'Tutor Session',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Messages Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL, -- user, assistant
            content TEXT NOT NULL,
            citations_json TEXT, -- array of {source, page, snippet}
            insufficient_evidence INTEGER DEFAULT 0,
            tokens_used INTEGER DEFAULT 0,
            latency_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    # Quizzes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            quiz_type TEXT DEFAULT 'adaptive', -- adaptive, targeted, custom
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Questions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            concept_id INTEGER,
            question_type TEXT NOT NULL, -- mcq, open_ended
            question_text TEXT NOT NULL,
            options_json TEXT, -- json array for mcq
            correct_answer TEXT NOT NULL,
            rubric_json TEXT, -- json object for open_ended criteria
            explanation TEXT,
            difficulty TEXT DEFAULT 'medium',
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
            FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE SET NULL
        )
    """)

    # Quiz Attempts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            score_percent REAL DEFAULT 0.0,
            total_questions INTEGER DEFAULT 0,
            correct_questions INTEGER DEFAULT 0,
            details_json TEXT, -- detailed user response & AI evaluation per question
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Recommendations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            action_type TEXT DEFAULT 'review_material', -- review_material, retake_quiz, ask_tutor
            action_target TEXT,
            priority TEXT DEFAULT 'medium', -- high, medium, low
            dismissed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Activity Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            space_id INTEGER,
            project_id INTEGER,
            event_type TEXT NOT NULL,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # AI Usage Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            project_id INTEGER,
            feature TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            latency_ms INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            status TEXT DEFAULT 'success',
            error_msg TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # AI Evaluations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            feature TEXT NOT NULL,
            groundedness_score REAL DEFAULT 1.0,
            relevance_score REAL DEFAULT 1.0,
            citation_accuracy REAL DEFAULT 1.0,
            feedback TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Background Jobs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS background_jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT DEFAULT 'queued', -- queued, processing, completed, failed
            retries INTEGER DEFAULT 0,
            error_msg TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed Default Admin Account if not existing
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        import hashlib
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ('admin', 'admin@studycompanion.ai', admin_pass, 'admin')
        )
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = cursor.fetchone()['id']
        
        # Seed initial Space & Project for instant exploration
        cursor.execute(
            "INSERT INTO spaces (user_id, name, description, icon_color) VALUES (?, ?, ?, ?)",
            (admin_id, 'Computer Science & AI', 'Master core AI, Machine Learning, and Software Engineering concepts.', '#6366f1')
        )
        space_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO projects (space_id, user_id, name, description, learning_goal) VALUES (?, ?, ?, ?, ?)",
            (space_id, admin_id, 'Machine Learning Foundations', 'Deep dive into supervised learning, neural networks, and model evaluation.', 'Master ML algorithms, model evaluation, and Python implementation.')
        )
        project_id = cursor.lastrowid
        
        # Seed initial concepts for ML project
        sample_concepts = [
            ("Supervised Learning", "Learning a function that maps an input to an output based on example input-output pairs.", "Machine Learning"),
            ("Neural Networks", "Computing systems inspired by the biological neural networks that constitute animal brains.", "Deep Learning"),
            ("Overfitting & Regularization", "Overfitting happens when a model learns noise; regularization prevents over-complexity.", "Model Evaluation"),
            ("Gradient Descent", "First-order iterative optimization algorithm for finding a local minimum of a differentiable function.", "Optimization")
        ]
        for c_name, c_desc, c_cat in sample_concepts:
            cursor.execute(
                "INSERT INTO concepts (project_id, name, description, category) VALUES (?, ?, ?, ?)",
                (project_id, c_name, c_desc, c_cat)
            )
            c_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO concept_mastery (project_id, concept_id, mastery_level, trend) VALUES (?, ?, ?, ?)",
                (project_id, c_id, 75.0 if c_name=="Supervised Learning" else 45.0, "improving" if c_name=="Supervised Learning" else "requires_attention")
            )
            
        # Seed initial recommendation
        cursor.execute(
            "INSERT INTO recommendations (project_id, user_id, title, description, action_type, priority) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, admin_id, "Practice Overfitting Concepts", "Your mastery of Overfitting & Regularization is currently low (45%). Take a targeted quiz to reinforce key ideas.", "retake_quiz", "high")
        )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
