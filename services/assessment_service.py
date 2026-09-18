import json
import logging
from database import get_db_connection
from services.ai_engine import ai_engine

class AssessmentService:
    def generate_adaptive_quiz(self, user_id, project_id, num_questions=4):
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Project Concepts and current mastery
        cursor.execute("""
            SELECT c.id, c.name, c.description, cm.mastery_level, cm.trend
            FROM concepts c
            LEFT JOIN concept_mastery cm ON c.id = cm.concept_id AND cm.project_id = ?
            WHERE c.project_id = ?
        """, (project_id, project_id))
        concepts = cursor.fetchall()

        if not concepts:
            # Seed default fallback concepts if none exist
            cursor.execute("INSERT INTO concepts (project_id, name, description) VALUES (?, 'General Principles', 'Core concepts for this project')", (project_id,))
            c_id = cursor.lastrowid
            cursor.execute("INSERT INTO concept_mastery (project_id, concept_id, mastery_level) VALUES (?, ?, 50.0)", (project_id, c_id))
            conn.commit()
            cursor.execute("SELECT c.id, c.name, c.description, 50.0 as mastery_level, 'stable' as trend FROM concepts c WHERE c.id = ?", (c_id,))
            concepts = cursor.fetchall()

        # Prioritize concepts with low mastery (requiring practice)
        concept_list = []
        for c in concepts:
            concept_list.append({
                "id": c['id'],
                "name": c['name'],
                "description": c['description'] or c['name'],
                "mastery": c['mastery_level'] if c['mastery_level'] is not None else 50.0
            })
        concept_list.sort(key=lambda x: x['mastery'])

        # 2. Retrieve recent project chunk excerpts for context
        cursor.execute("SELECT content FROM chunks WHERE project_id = ? ORDER BY RANDOM() LIMIT 3", (project_id,))
        chunk_excerpts = [r['content'] for r in cursor.fetchall()]
        excerpt_str = "\n---\n".join(chunk_excerpts) if chunk_excerpts else "General domain knowledge."

        # Prompt for structured quiz JSON
        system_prompt = """You are an Adaptive Assessment Generator for an AI Study Companion.
Create a balanced quiz with a mix of Multiple-Choice Questions (MCQs) and Open-Ended Questions targeted at the learner's current mastery levels.

OUTPUT SCHEMA (JSON ONLY):
{
  "title": "Adaptive Quiz: Project Mastery Check",
  "questions": [
    {
      "concept_id": 1,
      "concept_name": "Concept Name",
      "question_type": "mcq",
      "difficulty": "medium",
      "question_text": "Question prompt?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Why Option A is correct."
    },
    {
      "concept_id": 2,
      "concept_name": "Concept Name",
      "question_type": "open_ended",
      "difficulty": "hard",
      "question_text": "Explain how...",
      "correct_answer": "Key points required in a correct explanation.",
      "rubric": {
        "key_concepts": ["Concept 1", "Concept 2"],
        "scoring_criteria": "Full credit if key concepts and reasoning are explained."
      },
      "explanation": "Sample model response."
    }
  ]
}
"""
        prompt = f"TARGET CONCEPTS FOR QUIZ:\n{json.dumps(concept_list)}\n\nDOCUMENT EXCERPTS FOR QUIZ GROUNDING:\n{excerpt_str}\n\nGenerate {num_questions} questions."
        
        quiz_data = ai_engine.generate_json(prompt, system_prompt, feature="quiz_generation", user_id=user_id, project_id=project_id)
        
        if not quiz_data or "questions" not in quiz_data:
            # Simple fallback quiz if API formatting fails
            c_target = concept_list[0]
            quiz_data = {
                "title": f"Practice Quiz: {c_target['name']}",
                "questions": [
                    {
                        "concept_id": c_target['id'],
                        "concept_name": c_target['name'],
                        "question_type": "mcq",
                        "difficulty": "medium",
                        "question_text": f"Which statement best describes {c_target['name']}?",
                        "options": [
                            f"A fundamental concept related to {c_target['description']}",
                            "An unrelated database index algorithm",
                            "A hardware peripheral interface",
                            "None of the above"
                        ],
                        "correct_answer": f"A fundamental concept related to {c_target['description']}",
                        "explanation": f"{c_target['name']} is defined as: {c_target['description']}"
                    }
                ]
            }

        # Save Quiz & Questions to DB
        cursor.execute("INSERT INTO quizzes (project_id, title, quiz_type) VALUES (?, ?, 'adaptive')", (project_id, quiz_data.get('title', 'Adaptive Assessment')))
        quiz_id = cursor.lastrowid

        saved_questions = []
        for q in quiz_data['questions']:
            c_id = q.get('concept_id') or concept_list[0]['id']
            q_type = q.get('question_type', 'mcq')
            opts_json = json.dumps(q.get('options')) if q_type == 'mcq' else None
            rubric_json = json.dumps(q.get('rubric')) if q_type == 'open_ended' else None
            
            cursor.execute("""
                INSERT INTO questions (quiz_id, concept_id, question_type, question_text, options_json, correct_answer, rubric_json, explanation, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (quiz_id, c_id, q_type, q['question_text'], opts_json, q['correct_answer'], rubric_json, q.get('explanation', ''), q.get('difficulty', 'medium')))
            
            saved_questions.append({
                "id": cursor.lastrowid,
                "concept_id": c_id,
                "question_type": q_type,
                "question_text": q['question_text'],
                "options": q.get('options'),
                "explanation": q.get('explanation')
            })

        conn.commit()
        conn.close()

        return {
            "quiz_id": quiz_id,
            "title": quiz_data.get('title', 'Adaptive Assessment'),
            "questions": saved_questions
        }

    def evaluate_quiz_submission(self, user_id, project_id, quiz_id, user_answers):
        """
        user_answers: dict mapping question_id -> user_response string
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, concept_id, question_type, question_text, correct_answer, rubric_json, explanation FROM questions WHERE quiz_id = ?", (quiz_id,))
        questions = cursor.fetchall()

        evaluations = []
        total_questions = len(questions)
        correct_count = 0
        concept_updates = {} # concept_id -> list of scores (0.0 to 1.0)

        for q in questions:
            q_id = q['id']
            c_id = q['concept_id']
            user_ans = user_answers.get(str(q_id), "").strip()

            if q['question_type'] == 'mcq':
                is_correct = (user_ans.lower() == q['correct_answer'].strip().lower())
                score = 1.0 if is_correct else 0.0
                if is_correct:
                    correct_count += 1
                
                evaluations.append({
                    "question_id": q_id,
                    "question_text": q['question_text'],
                    "question_type": "mcq",
                    "user_answer": user_ans,
                    "correct_answer": q['correct_answer'],
                    "is_correct": is_correct,
                    "score": score,
                    "feedback": "Correct answer!" if is_correct else f"Incorrect. Correct answer: {q['correct_answer']}. {q['explanation']}"
                })
                
                if c_id:
                    concept_updates.setdefault(c_id, []).append(score)

            elif q['question_type'] == 'open_ended':
                # Evaluate open-ended response with AI Rubric Evaluator
                system_prompt = """You are an AI Rubric Evaluator for academic assessments.
Evaluate the learner's response for understanding, accuracy, key concept coverage, and missing reasoning.

OUTPUT SCHEMA (JSON ONLY):
{
  "score": 0.85, // 0.0 to 1.0
  "is_correct": true, // true if score >= 0.7
  "concepts_covered": ["Concept A"],
  "missing_concepts": ["Concept B"],
  "feedback": "Detailed constructive feedback explaining what was understood and what was missing."
}
"""
                prompt = f"QUESTION: {q['question_text']}\nMODEL ANSWER/RUBRIC: {q['correct_answer']}\nUSER RESPONSE: {user_ans}"
                
                ai_eval = ai_engine.generate_json(prompt, system_prompt, feature="open_ended_eval", user_id=user_id, project_id=project_id)
                
                if not ai_eval or "score" not in ai_eval:
                    # Fallback evaluation
                    ai_eval = {
                        "score": 0.7,
                        "is_correct": True,
                        "feedback": "Good attempt! Make sure to review the full concept details in your materials."
                    }

                score = float(ai_eval.get('score', 0.5))
                is_correct = bool(ai_eval.get('is_correct', score >= 0.7))
                if is_correct:
                    correct_count += 1

                evaluations.append({
                    "question_id": q_id,
                    "question_text": q['question_text'],
                    "question_type": "open_ended",
                    "user_answer": user_ans,
                    "correct_answer": q['correct_answer'],
                    "is_correct": is_correct,
                    "score": score,
                    "feedback": ai_eval.get('feedback', ''),
                    "concepts_covered": ai_eval.get('concepts_covered', []),
                    "missing_concepts": ai_eval.get('missing_concepts', [])
                })

                if c_id:
                    concept_updates.setdefault(c_id, []).append(score)

        score_percent = round((correct_count / total_questions) * 100.0, 1) if total_questions > 0 else 0.0

        # Save Attempt Record
        cursor.execute("""
            INSERT INTO quiz_attempts (quiz_id, user_id, project_id, score_percent, total_questions, correct_questions, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (quiz_id, user_id, project_id, score_percent, total_questions, correct_count, json.dumps(evaluations)))

        # Update Concept Mastery in Database
        for c_id, scores in concept_updates.items():
            avg_score = sum(scores) / len(scores) # 0 to 1
            
            cursor.execute("SELECT mastery_level, total_evaluations, correct_count FROM concept_mastery WHERE project_id = ? AND concept_id = ?", (project_id, c_id))
            cm = cursor.fetchone()
            
            if cm:
                prev_mastery = cm['mastery_level']
                new_total = cm['total_evaluations'] + len(scores)
                new_correct = cm['correct_count'] + int(sum(1 for s in scores if s >= 0.7))
                
                # Exponential moving average update for mastery level
                updated_mastery = round(0.6 * prev_mastery + 0.4 * (avg_score * 100.0), 1)
                trend = "improving" if updated_mastery > prev_mastery + 2 else ("requires_attention" if updated_mastery < prev_mastery - 2 or updated_mastery < 60.0 else "stable")
                
                cursor.execute("""
                    UPDATE concept_mastery 
                    SET mastery_level = ?, trend = ?, total_evaluations = ?, correct_count = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE project_id = ? AND concept_id = ?
                """, (updated_mastery, trend, new_total, new_correct, project_id, c_id))
            else:
                updated_mastery = round(avg_score * 100.0, 1)
                trend = "requires_attention" if updated_mastery < 60.0 else "stable"
                cursor.execute("""
                    INSERT INTO concept_mastery (project_id, concept_id, mastery_level, trend, total_evaluations, correct_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (project_id, c_id, updated_mastery, trend, len(scores), int(sum(1 for s in scores if s >= 0.7))))

        # Log activity event
        cursor.execute("""
            INSERT INTO activity_events (user_id, project_id, event_type, details_json)
            VALUES (?, ?, 'quiz_completed', ?)
        """, (user_id, project_id, json.dumps({"score_percent": score_percent, "quiz_id": quiz_id})))

        conn.commit()
        conn.close()

        return {
            "score_percent": score_percent,
            "total_questions": total_questions,
            "correct_questions": correct_count,
            "evaluations": evaluations
        }

assessment_service = AssessmentService()
