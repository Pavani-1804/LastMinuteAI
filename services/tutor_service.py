import json
import logging
from database import get_db_connection
from services.ai_engine import ai_engine
from services.rag_service import rag_service

class TutorService:
    def answer_question(self, user_id, project_id, conversation_id, user_query):
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Project Details & Learning Goal
        cursor.execute("SELECT name, description, learning_goal FROM projects WHERE id = ?", (project_id,))
        proj = cursor.fetchone()
        project_name = proj['name'] if proj else "General Study"
        learning_goal = proj['learning_goal'] if proj else "Master course content"

        # 2. Fetch Weak Concepts (Persistent Learning Context)
        cursor.execute("""
            SELECT c.name, cm.mastery_level, cm.trend 
            FROM concept_mastery cm
            JOIN concepts c ON cm.concept_id = c.id
            WHERE cm.project_id = ? AND cm.mastery_level < 60.0
            ORDER BY cm.mastery_level ASC
            LIMIT 3
        """, (project_id,))
        weak_concepts = [f"{r['name']} ({r['mastery_level']}%)" for r in cursor.fetchall()]

        # 3. Retrieve Relevant Material Chunks (RAG)
        retrieved_chunks, has_enough_evidence = rag_service.retrieve_context(project_id, user_query, top_k=4)

        # 4. Check if material exists for project
        cursor.execute("SELECT COUNT(*) as cnt FROM materials WHERE project_id = ? AND status = 'ready'", (project_id,))
        has_materials = cursor.fetchone()['cnt'] > 0

        citations = []
        context_str = ""

        if retrieved_chunks:
            context_blocks = []
            for chunk in retrieved_chunks:
                context_blocks.append(f"[Source: {chunk['source']} — Page {chunk['page']}]\n{chunk['content']}")
                citations.append({
                    "source": chunk['source'],
                    "page": chunk['page'],
                    "snippet": chunk['content'][:150] + "..."
                })
            context_str = "\n\n".join(context_blocks)

        # 5. Handle Unsupported Questions if materials exist but query has zero evidence
        if has_materials and not has_enough_evidence:
            system_prompt = (
                f"You are an AI Tutor for the project '{project_name}'. "
                "The user asked a question, but the uploaded learning materials do not contain sufficient evidence to answer it reliably.\n"
                "IMPORTANT RULE: Politely inform the user that the uploaded project materials do not contain sufficient evidence for this question. "
                "Explain what is missing and suggest how they might upload relevant materials or ask about related topics covered in their materials."
            )
            prompt = f"User Question: {user_query}\n\nUploaded materials evidence: NONE FOUND."
            
            response_text = ai_engine.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                feature="tutor_insufficient_evidence",
                user_id=user_id,
                project_id=project_id
            )
            
            # Save assistant message
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, citations_json, insufficient_evidence)
                VALUES (?, 'assistant', ?, ?, 1)
            """, (conversation_id, response_text, json.dumps([])))
            conn.commit()
            conn.close()

            return {
                "answer": response_text,
                "citations": [],
                "insufficient_evidence": True
            }

        # 6. Standard Grounded Response
        weak_str = ", ".join(weak_concepts) if weak_concepts else "None identified yet"
        system_prompt = f"""You are the AI Academic Tutor for the project '{project_name}'.
Learning Goal: {learning_goal}
Learner's Known Weak Concepts: {weak_str}

CRITICAL GROUNDEDNESS RULES:
1. Prioritize the provided Project Material Context to answer the query.
2. Provide precise inline citations referencing the source and page number whenever referencing material details, e.g. [Source: Filename.pdf — Page X].
3. Maintain an encouraging, clear, and structured educational tone. Break down complex ideas with key takeaways or bullet points where appropriate.
"""
        prompt = f"PROJECT MATERIAL CONTEXT:\n{context_str}\n\nUSER QUESTION: {user_query}"
        
        response_text = ai_engine.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            feature="tutor_chat",
            user_id=user_id,
            project_id=project_id
        )

        # Save assistant message
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, citations_json, insufficient_evidence)
            VALUES (?, 'assistant', ?, ?, 0)
        """, (conversation_id, response_text, json.dumps(citations)))
        
        # Log activity event
        cursor.execute("""
            INSERT INTO activity_events (user_id, project_id, event_type, details_json)
            VALUES (?, ?, 'tutor_interaction', ?)
        """, (user_id, project_id, json.dumps({"query": user_query[:50]})))

        conn.commit()
        conn.close()

        return {
            "answer": response_text,
            "citations": citations,
            "insufficient_evidence": False
        }

tutor_service = TutorService()
