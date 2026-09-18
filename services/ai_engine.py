import os
import time
import json
import logging
from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class AIEngine:
    def __init__(self):
        self.groq_client = None
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                logging.warning(f"Failed to initialize Groq client: {e}")

    def log_ai_usage(self, user_id, project_id, feature, model, prompt_tokens, completion_tokens, latency_ms, status='success', error_msg=None):
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = round((total_tokens / 1_000_000.0) * 0.59, 6)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_usage_logs (user_id, project_id, feature, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd, status, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, project_id, feature, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd, status, error_msg))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error logging AI usage: {e}")

    def generate_text(self, prompt, system_prompt="You are an expert AI Study Partner.", feature="general", user_id=None, project_id=None, temperature=0.7):
        start_time = time.time()
        
        # 1. Primary: Groq Compound Mini
        if self.groq_client:
            models_to_try = ["groq/compound-mini", "groq/compound", "openai/gpt-oss-120b"]
            for model_name in models_to_try:
                try:
                    response = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature,
                        max_tokens=2048
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    content = response.choices[0].message.content or ""
                    prompt_tokens = response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else len(prompt)//4
                    completion_tokens = response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else len(content)//4

                    self.log_ai_usage(user_id, project_id, feature, model_name, prompt_tokens, completion_tokens, latency_ms, 'success')
                    return content
                except Exception as e:
                    logging.warning(f"Groq model {model_name} failed: {e}. Trying next model...")

        # 2. Secondary Fallback: Gemini Flash
        if GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                full_prompt = f"System Instruction: {system_prompt}\n\n{prompt}"
                res = model.generate_content(full_prompt)
                content = res.text
                latency_ms = int((time.time() - start_time) * 1000)
                self.log_ai_usage(user_id, project_id, feature, "gemini-1.5-flash", len(prompt)//4, len(content)//4, latency_ms, 'success')
                return content
            except Exception as ge:
                logging.warning(f"Gemini fallback failed: {ge}")

        # 3. Rule-based fallback if APIs fail
        latency_ms = int((time.time() - start_time) * 1000)
        self.log_ai_usage(user_id, project_id, feature, "rule_based_fallback", 10, 50, latency_ms, 'fallback')
        return "I am currently analyzing your query based on project notes. Please ask your question again or check your API keys."

    def generate_json(self, prompt, system_prompt, feature="json_gen", user_id=None, project_id=None):
        raw_response = self.generate_text(prompt, system_prompt + " Output strictly valid JSON without markdown codeblock formatting.", feature, user_id, project_id, temperature=0.2)
        clean = raw_response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        
        try:
            return json.loads(clean)
        except Exception as e:
            logging.error(f"Failed to parse JSON output: {e}\nRaw output: {raw_response}")
            return None

ai_engine = AIEngine()
