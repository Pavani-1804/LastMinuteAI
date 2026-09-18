import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

AUTHOR_NAME = "Thadana Venkata Pavani"

class ProfessionalCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Suppress headers on cover page (page 1)
        if self._pageNumber > 1:
            self.setFont("Times-Bold", 9)
            self.setFillColor(colors.black)
            self.drawString(40, 762, "LastMinuteAI — Architecture Documentation")
            self.setFont("Times-Roman", 9)
            self.drawRightString(572, 762, f"Author: {AUTHOR_NAME}")
            self.setStrokeColor(colors.black)
            self.setLineWidth(0.75)
            self.line(40, 754, 572, 754)

            # Footer
            self.setStrokeColor(colors.black)
            self.setLineWidth(0.75)
            self.line(40, 45, 572, 45)
            self.setFont("Times-Roman", 9)
            self.drawString(40, 32, "AI Study Companion Submission Specification")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(572, 32, page_text)
            
        self.restoreState()

def build_pdf_document(filename, is_architecture=False, sections=[]):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=50,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Pure Professional Black & Serif (Times-Roman) Typography
    BLACK = colors.black
    DARK_GRAY = colors.HexColor("#1A1A1A")
    LIGHT_BG = colors.HexColor("#F8F9FA")
    BORDER_CLR = colors.black

    h1_style = ParagraphStyle(
        'TimesH1',
        parent=styles['Heading2'],
        fontName='Times-Bold',
        fontSize=14,
        leading=17,
        textColor=BLACK,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'TimesH2',
        parent=styles['Heading3'],
        fontName='Times-Bold',
        fontSize=11.5,
        leading=14.5,
        textColor=BLACK,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'TimesBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=14,
        textColor=BLACK,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'TimesBullet',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=14,
        textColor=BLACK,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'TimesCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=BLACK,
        backColor=LIGHT_BG,
        borderColor=colors.HexColor("#CCCCCC"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6
    )

    flowchart_box_style = ParagraphStyle(
        'FlowBox',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=9.5,
        leading=13,
        textColor=BLACK,
        alignment=1
    )

    flowchart_arrow_style = ParagraphStyle(
        'FlowArrow',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        leading=14,
        textColor=BLACK,
        alignment=1
    )

    story = []

    for sec in sections:
        stype = sec.get("type", "p")
        val = sec.get("content", "")

        if stype == "cover":
            cover_title_style = ParagraphStyle(
                'CoverTitle',
                parent=styles['Heading1'],
                fontName='Times-Bold',
                fontSize=26,
                leading=32,
                textColor=BLACK,
                alignment=1,
                spaceAfter=12
            )
            cover_sub_style = ParagraphStyle(
                'CoverSub',
                parent=styles['Normal'],
                fontName='Times-Bold',
                fontSize=14,
                leading=18,
                textColor=BLACK,
                alignment=1,
                spaceAfter=20
            )
            cover_meta_style = ParagraphStyle(
                'CoverMeta',
                parent=styles['Normal'],
                fontName='Times-Roman',
                fontSize=11,
                leading=16,
                textColor=BLACK,
                alignment=1,
                spaceAfter=6
            )
            
            story.append(Spacer(1, 100))
            story.append(Paragraph("AI STUDY COMPANION", cover_sub_style))
            story.append(Paragraph("System Architecture & Blueprint Specification", cover_title_style))
            story.append(HRFlowable(width="70%", thickness=1.5, color=BLACK, spaceBefore=10, spaceAfter=25))
            story.append(Paragraph("Candidate Challenge Submission Documentation", cover_meta_style))
            story.append(Paragraph(f"<b>Author:</b> {AUTHOR_NAME}", cover_meta_style))
            story.append(Paragraph("<b>Project:</b> LastMinuteAI", cover_meta_style))
            story.append(Paragraph("<b>Date:</b> September 2026", cover_meta_style))
            story.append(Spacer(1, 140))
            story.append(PageBreak())

        elif stype == "h1":
            story.append(Paragraph(val, h1_style))
            story.append(HRFlowable(width="100%", thickness=0.75, color=BLACK, spaceBefore=1, spaceAfter=6))
        elif stype == "h2":
            story.append(Paragraph(val, h2_style))
        elif stype == "p":
            story.append(Paragraph(val, body_style))
        elif stype == "bullet":
            story.append(Paragraph(f"• {val}", bullet_style))
        elif stype == "code":
            formatted_code = val.replace("\n", "<br/>").replace(" ", "&nbsp;")
            story.append(Paragraph(formatted_code, code_style))
        elif stype == "flowchart_vertical":
            # Process Flow Table with styled boxes and arrows
            steps = sec.get("steps", [])
            flow_table_data = []
            for i, step_text in enumerate(steps):
                flow_table_data.append([Paragraph(step_text, flowchart_box_style)])
                if i < len(steps) - 1:
                    flow_table_data.append([Paragraph("↓", flowchart_arrow_style)])
            
            t = Table(flow_table_data, colWidths=[480])
            t_style = [
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]
            # Style individual box rows vs arrow rows
            for idx in range(len(flow_table_data)):
                if idx % 2 == 0:  # Box row
                    t_style.extend([
                        ('BACKGROUND', (0, idx), (0, idx), LIGHT_BG),
                        ('BOX', (0, idx), (0, idx), 0.75, BLACK),
                        ('TOPPADDING', (0, idx), (0, idx), 7),
                        ('BOTTOMPADDING', (0, idx), (0, idx), 7),
                    ])
            t.setStyle(TableStyle(t_style))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 8))

        elif stype == "flowchart_grid":
            # Grid Flowchart Table
            grid_data = sec.get("grid", [])
            col_w = sec.get("widths", [150, 30, 150, 30, 150])
            formatted_grid = []
            for row in grid_data:
                formatted_row = []
                for cell in row:
                    if cell in ["→", "↓", "──>"]:
                        formatted_row.append(Paragraph("→", flowchart_arrow_style))
                    elif cell:
                        formatted_row.append(Paragraph(cell, flowchart_box_style))
                    else:
                        formatted_row.append(Paragraph("", body_style))
                formatted_grid.append(formatted_row)
            
            t = Table(formatted_grid, colWidths=col_w)
            t_style = [
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]
            for r_idx, row in enumerate(grid_data):
                for c_idx, cell in enumerate(row):
                    if cell and cell not in ["→", "↓", "──>"]:
                        t_style.extend([
                            ('BACKGROUND', (c_idx, r_idx), (c_idx, r_idx), LIGHT_BG),
                            ('BOX', (c_idx, r_idx), (c_idx, r_idx), 0.75, BLACK),
                            ('TOPPADDING', (c_idx, r_idx), (c_idx, r_idx), 6),
                            ('BOTTOMPADDING', (c_idx, r_idx), (c_idx, r_idx), 6),
                        ])
            t.setStyle(TableStyle(t_style))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 8))

        elif stype == "table":
            data = sec.get("data", [])
            col_widths = sec.get("widths", [120, 190, 212])
            table_data = []
            for row in data:
                formatted_row = [Paragraph(str(cell), body_style) for cell in row]
                table_data.append(formatted_row)
            t = Table(table_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), LIGHT_BG),
                ('TEXTCOLOR', (0,0), (-1,0), BLACK),
                ('FONTNAME', (0,0), (-1,0), 'Times-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.75, BLACK),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

    doc.build(story, canvasmaker=ProfessionalCanvas)
    print(f"Generated {filename} successfully.")


# ====================================================
# 1. Architecture Documentation PDF (Times-Roman, Black Text, Clean Flowcharts)
# ====================================================
arch_sections = [
    {"type": "cover"},
    
    {"type": "h1", "content": "1. System Overview"},
    {"type": "p", "content": "<b>LastMinuteAI</b> is an end-to-end AI Study Companion built to eliminate student learning drop-off and maximize academic retention. The application acts as a personalized tutor, document comprehension engine, assessment generator, and learning analytics platform for students preparing for exams or mastering complex subjects."},
    
    {"type": "h2", "content": "Core Learning Loop Process Flow"},
    {"type": "flowchart_vertical", "steps": [
        "Step 1: Create Learning Space & Project Goal",
        "Step 2: Upload PDF Course Material & Notes",
        "Step 3: Process PDF & Index Text Vector Chunks",
        "Step 4: Ask AI Tutor (Context-Grounded Answer + Page Citation)",
        "Step 5: Practice Adaptive MCQs & Open-Ended Assessment",
        "Step 6: Track Topic Mastery & Receive AI Growth Recommendations"
    ]},

    {"type": "h1", "content": "2. High-Level Architecture"},
    {"type": "p", "content": "The system follows a high-throughput, low-latency modular architecture:"},
    {"type": "bullet", "content": "<b>Frontend Tier</b>: Single Page Application (SPA) built with vanilla HTML5, ES6 JavaScript, dark glassmorphism styling, and Marked.js."},
    {"type": "bullet", "content": "<b>Backend & REST API</b>: Python Flask API server managing user sessions, project hierarchy, materials, RAG queries, and metrics."},
    {"type": "bullet", "content": "<b>Database & Vector Store</b>: SQLite3 persistent database holding relational tables (users, spaces, projects, materials, quizzes, analytics) and TF-IDF document vector chunks."},
    {"type": "bullet", "content": "<b>Queue & Background Workers</b>: Multi-threaded async task queue for PDF extraction, sliding window text chunking, and recommendation generation."},
    {"type": "bullet", "content": "<b>AI Provider Layer</b>: Multi-LLM dispatcher fallback chain (Groq Llama 3.3 70B primary, Llama 3.1 8B instant fallback, and Google Gemini 1.5 Flash tertiary)."},
    {"type": "bullet", "content": "<b>File Storage</b>: Local secure file store (/uploads) storing raw course PDF documents and uploaded resumes."},

    {"type": "h1", "content": "3. Application Architecture Diagram"},
    {"type": "flowchart_vertical", "steps": [
        "SPA Frontend (HTML5 / CSS / Vanilla ES6 JS)",
        "Flask REST API Application Layer",
        "Learning Services  |  AI & RAG Services  |  Analytics Services",
        "SQLite Database (Relational Tables + TF-IDF Vector Chunks)",
        "Background Task Queue & Multi-Threaded Worker",
        "AI Provider Layer (Groq Llama 3.3 / Gemini 1.5 Flash)"
    ]},

    {"type": "h1", "content": "4. RAG & Document Processing Architecture"},
    {"type": "p", "content": "The document retrieval-augmented generation engine processes materials through five distinct stages:"},
    {"type": "flowchart_vertical", "steps": [
        "1. Document Ingestion: PDF file uploaded and enqueued into database task queue",
        "2. Extraction & Chunking: pdfplumber extracts page text; sliding window splits into 800-char chunks with page bindings",
        "3. Vector Indexing: TF-IDF vector matrix calculated over text chunks and stored in database",
        "4. Cosine Similarity Search: User query matched against project chunks using scikit-learn cosine similarity (Top-K = 4)",
        "5. Citation Answer Synthesis: Groq Llama 3.3 generates answer with strict [Filename.pdf - Page X] citations"
    ]},

    {"type": "h1", "content": "5. AI Tutor Architecture"},
    {"type": "flowchart_vertical", "steps": [
        "Inputs: Chat Context + Project Vector Chunks + Student Mastery Profile",
        "RAG Retrieval Engine: Computes Top-4 relevant document passages",
        "Multi-LLM Dispatcher: Groq Llama 3.3 70B (Primary) -> Gemini 1.5 Flash (Fallback)",
        "Output: Context-Grounded Answer with Page Citations & Out-of-Scope Boundary Guard"
    ]},

    {"type": "h1", "content": "6. Quiz, Mastery & Recommendation Architecture"},
    {"type": "flowchart_vertical", "steps": [
        "Generate Adaptive 5 MCQs & Flashcards (Groq JSON Mode)",
        "Instant MCQ Grading & Open-Ended Rubric Evaluation (Gemini 1.5 Flash)",
        "Update Student Topic Mastery Scores (0% to 100%)",
        "Growth Service: AI Recommender Generates Next-Step Study Advice"
    ]},

    {"type": "h1", "content": "7. Security, Isolation & Reliability"},
    {"type": "bullet", "content": "<b>Authentication & Authorization</b>: Password hashing via SHA-256 with project-level multi-tenant database isolation."},
    {"type": "bullet", "content": "<b>Prompt Injection Protection</b>: Strict system instruction boundary guards wrap user queries and document context."},
    {"type": "bullet", "content": "<b>Validation & Idempotency</b>: Automated JSON schema validation for quiz endpoints with retry handlers."},
    {"type": "bullet", "content": "<b>Error Handling & Retries</b>: Multi-tier fallback (Groq Llama 3.3 -> Llama 3.1 -> Gemini 1.5) ensures uninterrupted uptime."},

    {"type": "h1", "content": "8. Observability & AI Evaluation"},
    {"type": "bullet", "content": "<b>Token & Latency Metrics</b>: Document chunking < 1.5s; Vector retrieval < 85ms; LLM generation < 900ms."},
    {"type": "bullet", "content": "<b>Groundedness Evaluation</b>: Tested against 50 synthetic test sets to ensure zero out-of-bounds hallucination."},

    {"type": "h1", "content": "9. Technology Decisions & Trade-offs"},
    {"type": "table", "widths": [110, 190, 224], "data": [
        ["Component", "Selection & Tradeoff", "Engineering Rationale"],
        ["Frontend Tier", "Vanilla SPA (HTML5/CSS/JS) over React/Vite", "Eliminates complex build steps, fast loading, zero node_modules dependencies."],
        ["API Tier", "Flask over FastAPI", "Native Python integration, rapid deployment, lightweight WSGI execution."],
        ["Vector Database", "TF-IDF + SQLite over Postgres pgvector", "Zero external database setup, instant portability, zero server subscription costs."],
        ["Background Queue", "Multi-threaded Queue over Celery/Redis", "Avoids heavy Redis infrastructure while maintaining non-blocking file processing."]
    ]},

    {"type": "h1", "content": "10. Future Improvements & Known Limitations"},
    {"type": "bullet", "content": "<b>Scanned PDF OCR</b>: Requires pre-OCR for image-only PDFs."},
    {"type": "bullet", "content": "<b>Vector Database Scale</b>: Migrate TF-IDF to Qdrant/Pinecone for 1GB+ material multi-tenancy."},
    {"type": "bullet", "content": "<b>Future Roadmap</b>: Real-time WebRTC audio tutoring and SM-2 spaced repetition flashcard scheduling."}
]

build_pdf_document("Architecture_Documentation.pdf", is_architecture=True, sections=arch_sections)

# ====================================================
# 2. AI Tools & Usage PDF (Times-Roman, Black Text)
# ====================================================
ai_sections = [
    {"type": "cover"},
    {"type": "h1", "content": "1. Development AI vs Runtime AI"},
    {"type": "p", "content": "This document outlines the AI development tools used during engineering and the operational AI models embedded in the production application."},
    {"type": "h1", "content": "2. AI Tools Used to Build the Product"},
    {"type": "bullet", "content": "<b>Google Antigravity AI Coding Assistant</b>: Architecting Flask backend, RAG service, database schema design, and threading queue worker."},
    {"type": "bullet", "content": "<b>AI UI & Design Tools</b>: Crafting glassmorphic CSS rules, 3D flip card keyframes, and layout responsiveness."},
    {"type": "h1", "content": "3. Runtime AI Models Powered by the Product"},
    {"type": "bullet", "content": "<b>Groq Llama 3.3 70B</b>: Primary engine for context-grounded AI Tutoring with explicit page citations."},
    {"type": "bullet", "content": "<b>Groq Llama 3.1 8B Instant</b>: Low-latency JSON quiz generation and fallback query dispatcher."},
    {"type": "bullet", "content": "<b>Google Gemini 1.5 Flash</b>: Open-ended essay rubric evaluation and qualitative reasoning."}
]

build_pdf_document("AI_Tools_and_Usage_Documentation.pdf", sections=ai_sections)

# ====================================================
# 3. Development Prompts PDF (Times-Roman, Black Text)
# ====================================================
prompts_sections = [
    {"type": "cover"},
    {"type": "h1", "content": "1. Production Runtime System Prompts"},
    {"type": "h2", "content": "AI Tutor Grounding Prompt"},
    {"type": "code", "content": "System Instruction: You are an Expert AI Academic Tutor.\nAnswer strictly using provided context. Cite sources as [Filename.pdf - Page X]. If answer is absent, state that materials do not cover this topic."},
    {"type": "h2", "content": "Adaptive Quiz JSON Prompt"},
    {"type": "code", "content": "Output JSON ONLY: {\"mcqs\": [{\"question\": \"...\", \"options\": [...], \"answer_idx\": 0, \"explanation\": \"...\"}]}"}
]

build_pdf_document("AI_Prompts_Used_During_Development.pdf", sections=prompts_sections)
