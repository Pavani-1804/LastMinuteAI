import os
import json
import logging

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from database import get_db_connection
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class RAGService:
    def extract_text_from_pdf(self, file_path):
        """Extract text page by page from PDF file."""
        pages = []
        if pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        pages.append({"page_number": i + 1, "text": text.strip()})
                if pages and any(p["text"] for p in pages):
                    return pages
            except Exception as e:
                logging.warning(f"pdfplumber extraction failed: {e}. Trying pypdf...")

        if PdfReader:
            try:
                reader = PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append({"page_number": i + 1, "text": text.strip()})
                return pages
            except Exception as e:
                logging.error(f"pypdf extraction failed: {e}")
        
        # Fallback reading raw file text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return [{"page_number": 1, "text": content}]
        except Exception as e:
            logging.error(f"Fallback plain text reading failed: {e}")
            return []

    def chunk_document(self, pages, chunk_size=800, overlap=150):
        """Create overlapping text chunks associated with source page numbers."""
        chunks = []
        for page in pages:
            page_num = page["page_number"]
            text = page["text"]
            if not text:
                continue

            words = text.split()
            if not words:
                continue

            # Sliding window by character/word count
            i = 0
            step = max(1, (chunk_size - overlap) // 6)
            words_per_chunk = chunk_size // 6

            while i < len(words):
                chunk_words = words[i : i + words_per_chunk]
                chunk_text = " ".join(chunk_words)
                if len(chunk_text.strip()) > 30:
                    chunks.append({
                        "page_number": page_num,
                        "content": chunk_text
                    })
                i += step
        return chunks

    def process_and_index_material(self, material_id):
        """Ingests material PDF, extracts chunks, saves to SQLite DB."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, project_id, filename, file_path FROM materials WHERE id = ?", (material_id,))
        mat = cursor.fetchone()
        if not mat:
            conn.close()
            return False, "Material not found"

        project_id = mat['project_id']
        file_path = mat['file_path']

        # Update status to processing
        cursor.execute("UPDATE materials SET status = 'processing' WHERE id = ?", (material_id,))
        conn.commit()

        try:
            pages = self.extract_text_from_pdf(file_path)
            if not pages:
                cursor.execute("UPDATE materials SET status = 'failed', error_msg = 'No readable text extracted' WHERE id = ?", (material_id,))
                conn.commit()
                conn.close()
                return False, "No readable text extracted"

            chunks = self.chunk_document(pages)
            
            # Save chunks to database
            for chunk in chunks:
                cursor.execute(
                    "INSERT INTO chunks (material_id, project_id, page_number, content) VALUES (?, ?, ?, ?)",
                    (material_id, project_id, chunk["page_number"], chunk["content"])
                )

            # Update material status & count
            cursor.execute(
                "UPDATE materials SET status = 'ready', chunk_count = ? WHERE id = ?",
                (len(chunks), material_id)
            )

            # Log event
            cursor.execute(
                "SELECT user_id FROM materials WHERE id = ?", (material_id,)
            )
            u_id = cursor.fetchone()['user_id']
            cursor.execute(
                "INSERT INTO activity_events (user_id, project_id, event_type, details_json) VALUES (?, ?, ?, ?)",
                (u_id, project_id, "material_processed", json.dumps({"filename": mat['filename'], "chunks": len(chunks)}))
            )

            conn.commit()
            conn.close()
            return True, f"Successfully processed {len(chunks)} chunks."

        except Exception as e:
            cursor.execute("UPDATE materials SET status = 'failed', error_msg = ? WHERE id = ?", (str(e), material_id))
            conn.commit()
            conn.close()
            return False, str(e)

    def retrieve_context(self, project_id, query, top_k=4, min_similarity=0.08):
        """Retrieves relevant chunks with TF-IDF cosine similarity for project data isolation."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.material_id, m.filename, c.page_number, c.content 
            FROM chunks c
            JOIN materials m ON c.material_id = m.id
            WHERE c.project_id = ?
        """, (project_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return [], False

        documents = [r['content'] for r in rows]
        
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(documents)
            query_vector = vectorizer.transform([query])
            similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

            results = []
            for idx in similarities.argsort()[::-1][:top_k]:
                score = float(similarities[idx])
                if score >= min_similarity:
                    r = rows[idx]
                    results.append({
                        "chunk_id": r['id'],
                        "source": r['filename'],
                        "page": r['page_number'],
                        "content": r['content'],
                        "score": round(score, 4)
                    })

            has_enough_evidence = len(results) > 0 and results[0]['score'] >= min_similarity
            return results, has_enough_evidence

        except Exception as e:
            logging.error(f"Retrieval failed: {e}")
            return [], False

rag_service = RAGService()
