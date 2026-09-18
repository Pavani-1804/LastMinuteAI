import json
import time
import uuid
import logging
import threading
from database import get_db_connection
from services.rag_service import rag_service
from services.growth_service import growth_service

class BackgroundWorker:
    def __init__(self):
        self._thread = None
        self._running = False

    def enqueue_job(self, job_type, payload):
        job_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO background_jobs (id, job_type, payload_json, status, retries)
            VALUES (?, ?, ?, 'queued', 0)
        """, (job_id, job_type, json.dumps(payload)))
        conn.commit()
        conn.close()
        
        # Ensure worker thread is running
        self.start()
        return job_id

    def process_pending_jobs(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, job_type, payload_json, retries FROM background_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 5")
        jobs = cursor.fetchall()
        
        for job in jobs:
            job_id = job['id']
            job_type = job['job_type']
            payload = json.loads(job['payload_json'])
            retries = job['retries']

            # Mark as processing
            cursor.execute("UPDATE background_jobs SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))
            conn.commit()

            try:
                if job_type == 'process_material':
                    material_id = payload.get('material_id')
                    success, msg = rag_service.process_and_index_material(material_id)
                    if not success:
                        raise Exception(msg)
                
                elif job_type == 'generate_recommendations':
                    user_id = payload.get('user_id')
                    project_id = payload.get('project_id')
                    growth_service.generate_recommendations(user_id, project_id)

                # Mark as completed
                cursor.execute("UPDATE background_jobs SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))
                conn.commit()

            except Exception as e:
                logging.error(f"Job {job_id} failed: {e}")
                if retries < 3:
                    cursor.execute("""
                        UPDATE background_jobs 
                        SET status = 'queued', retries = retries + 1, error_msg = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (str(e), job_id))
                else:
                    cursor.execute("""
                        UPDATE background_jobs 
                        SET status = 'failed', error_msg = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (str(e), job_id))
                conn.commit()

        conn.close()

    def _worker_loop(self):
        while self._running:
            try:
                self.process_pending_jobs()
            except Exception as e:
                logging.error(f"Background worker loop error: {e}")
            time.sleep(3)

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False

background_worker = BackgroundWorker()
