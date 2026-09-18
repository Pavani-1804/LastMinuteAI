import json
import logging
from database import get_db_connection
from services.ai_engine import ai_engine

class GrowthService:
    def get_concept_mastery(self, project_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.id, c.name, c.description, c.category, cm.mastery_level, cm.trend, cm.last_updated
            FROM concepts c
            LEFT JOIN concept_mastery cm ON c.id = cm.concept_id AND cm.project_id = ?
            WHERE c.project_id = ?
            ORDER BY cm.mastery_level ASC
        """, (project_id, project_id))
        
        rows = cursor.fetchall()
        conn.close()

        mastery_data = []
        for r in rows:
            mastery_data.append({
                "concept_id": r['id'],
                "name": r['name'],
                "category": r['category'] or "General",
                "mastery_level": r['mastery_level'] if r['mastery_level'] is not None else 50.0,
                "trend": r['trend'] or "stable",
                "last_updated": r['last_updated']
            })
        return mastery_data

    def generate_recommendations(self, user_id, project_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch weak concepts
        cursor.execute("""
            SELECT c.name, cm.mastery_level, cm.trend
            FROM concept_mastery cm
            JOIN concepts c ON cm.concept_id = c.id
            WHERE cm.project_id = ? AND cm.mastery_level < 65.0
            ORDER BY cm.mastery_level ASC
        """, (project_id,))
        weak_concepts = [dict(r) for r in cursor.fetchall()]

        # 2. Fetch recent quiz performance
        cursor.execute("SELECT score_percent, completed_at FROM quiz_attempts WHERE project_id = ? ORDER BY completed_at DESC LIMIT 3", (project_id,))
        recent_quizzes = [dict(r) for r in cursor.fetchall()]

        # Generate intelligent recommendation using AI Engine
        system_prompt = """You are a Learning Growth Advisor for an AI Study Companion.
Analyze the user's concept mastery levels and recent quiz attempts to output 1 or 2 targeted, actionable recommendations.

OUTPUT SCHEMA (JSON ONLY):
[
  {
    "title": "Short Title",
    "description": "Specific action guidance on what to review or practice.",
    "action_type": "review_material", // "review_material", "retake_quiz", "ask_tutor"
    "priority": "high" // "high", "medium", "low"
  }
]
"""
        prompt = f"WEAK CONCEPTS: {json.dumps(weak_concepts)}\nRECENT QUIZZES: {json.dumps(recent_quizzes)}"
        
        recs = ai_engine.generate_json(prompt, system_prompt, feature="recommendations", user_id=user_id, project_id=project_id)

        if not recs or not isinstance(recs, list):
            recs = [
                {
                    "title": "Review Weak Concepts",
                    "description": "Your mastery level in key concepts is currently under 65%. Ask the AI Tutor for simpler explanations and targeted examples.",
                    "action_type": "ask_tutor",
                    "priority": "high"
                }
            ]

        # Save recommendations to database
        for rec in recs:
            cursor.execute("""
                INSERT INTO recommendations (project_id, user_id, title, description, action_type, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, user_id, rec['title'], rec['description'], rec.get('action_type', 'review_material'), rec.get('priority', 'medium')))

        conn.commit()
        conn.close()
        return recs

    def get_active_recommendations(self, user_id, project_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, description, action_type, priority, created_at
            FROM recommendations
            WHERE project_id = ? AND user_id = ? AND dismissed = 0
            ORDER BY priority DESC, created_at DESC
            LIMIT 5
        """, (project_id, user_id))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

growth_service = GrowthService()
