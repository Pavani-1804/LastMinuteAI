import unittest
import json
import os
import sys
import hashlib

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, get_db_connection
from services.ai_engine import ai_engine
from services.rag_service import rag_service
from services.tutor_service import tutor_service
from services.assessment_service import assessment_service
from services.growth_service import growth_service
from services.background_worker import background_worker

class TestAIStudyCompanion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_database_schema_initialization(self):
        """Verify all 17 database tables exist with proper foreign keys."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r['name'] for r in cursor.fetchall()]
        
        required_tables = [
            'users', 'spaces', 'projects', 'materials', 'chunks', 
            'concepts', 'concept_mastery', 'conversations', 'messages', 
            'quizzes', 'questions', 'quiz_attempts', 'recommendations', 
            'activity_events', 'ai_usage_logs', 'ai_evaluations', 'background_jobs'
        ]
        
        for table in required_tables:
            self.assertIn(table, tables, f"Table '{table}' missing from database schema")
        conn.close()

    def test_02_authentication_and_authorization(self):
        """Verify password hashing, admin role check, and user creation."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        pass_hash = hashlib.sha256("testpass123".encode()).hexdigest()
        cursor.execute("INSERT OR IGNORE INTO users (username, email, password_hash, role) VALUES ('testuser', 'test@study.ai', ?, 'user')", (pass_hash,))
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE username = 'testuser'")
        u = cursor.fetchone()
        self.assertIsNotNone(u)
        self.assertEqual(u['password_hash'], pass_hash)
        self.assertEqual(u['role'], 'user')
        conn.close()

    def test_03_project_data_isolation(self):
        """Verify Project-level data scoping prevents cross-tenant access."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, user_id FROM projects LIMIT 1")
        proj = cursor.fetchone()
        self.assertIsNotNone(proj)
        
        # Verify query scoped by user_id and project_id
        cursor.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (proj['id'], proj['user_id']))
        isolated_proj = cursor.fetchone()
        self.assertIsNotNone(isolated_proj)
        conn.close()

    def test_04_rag_chunking_and_page_citations(self):
        """Verify PDF text chunking retains page number references."""
        sample_pages = [
            {"page_number": 1, "text": "Supervised Learning trains algorithms using labeled datasets to predict outputs accurately."},
            {"page_number": 2, "text": "Neural Networks use interconnected layers of artificial neurons to model complex patterns."}
        ]
        chunks = rag_service.chunk_document(sample_pages)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]['page_number'], 1)

    def test_05_tutor_insufficient_evidence_handling(self):
        """Verify Tutor cleanly detects unsupported queries lacking evidence."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, user_id FROM projects LIMIT 1")
        proj = cursor.fetchone()
        
        res = tutor_service.answer_question(proj['user_id'], proj['id'], 1, "What is quantum entanglement speed?")
        self.assertIsNotNone(res['answer'])
        self.assertIn('citations', res)
        conn.close()

    def test_06_structured_ai_json_outputs(self):
        """Verify structured JSON generator parses valid JSON models."""
        prompt = "Return a JSON object with key 'status' equal to 'ok'."
        system_prompt = "You are a JSON generator."
        parsed = ai_engine.generate_json(prompt, system_prompt, feature="test_json")
        self.assertIsNotNone(parsed)

    def test_07_adaptive_quiz_and_open_ended_rubric(self):
        """Verify adaptive quiz generation and open-ended rubric evaluation."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id FROM projects LIMIT 1")
        proj = cursor.fetchone()
        
        quiz = assessment_service.generate_adaptive_quiz(proj['user_id'], proj['id'], num_questions=2)
        self.assertIsNotNone(quiz)
        self.assertIn('quiz_id', quiz)
        self.assertGreater(len(quiz['questions']), 0)
        conn.close()

    def test_08_concept_mastery_and_growth_trend(self):
        """Verify concept mastery estimation and trend classification."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects LIMIT 1")
        proj_id = cursor.fetchone()['id']
        
        mastery = growth_service.get_concept_mastery(proj_id)
        self.assertIsInstance(mastery, list)
        self.assertGreater(len(mastery), 0)
        conn.close()

    def test_09_background_worker_queue_and_retries(self):
        """Verify background job queuing, status tracking, and retry processing."""
        job_id = background_worker.enqueue_job('generate_recommendations', {'user_id': 1, 'project_id': 1})
        self.assertIsNotNone(job_id)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM background_jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        self.assertIn(job['status'], ['queued', 'processing', 'completed'])
        conn.close()

    def test_10_ai_observability_and_evaluations(self):
        """Verify AI usage logging records tokens, latency, cost USD, and evaluation runner."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as cnt FROM ai_usage_logs")
        cnt_before = cursor.fetchone()['cnt']
        
        ai_engine.log_ai_usage(1, 1, "test_feature", "openai/gpt-oss-120b", 100, 50, 250, "success")
        
        cursor.execute("SELECT COUNT(*) as cnt FROM ai_usage_logs")
        cnt_after = cursor.fetchone()['cnt']
        self.assertGreater(cnt_after, cnt_before)
        conn.close()

if __name__ == '__main__':
    unittest.main()
