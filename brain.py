import os
import asyncio
from typing import List, Optional, Union
import itertools
import shutil
import tempfile
import torch
from dotenv import load_dotenv

import requests
from fastapi import FastAPI, Security, HTTPException, UploadFile, File, Form
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables (.env file)
load_dotenv()

# --- Device & Hardware Check ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
VRAM_GB = torch.cuda.get_device_properties(0).total_memory / (1024**3) if torch.cuda.is_available() else 0.0

print(f"==================================================")
print(f"[+] Initializing Antigravity Insurance RAG Server")
print(f"[+] Hardware Acceleration: {DEVICE.upper()} ({GPU_NAME})")
if torch.cuda.is_available():
    print(f"[+] VRAM Available: {VRAM_GB:.2f} GB")
print(f"==================================================")

# --- Import modular pipelines ---
from file_utils import download_and_get_path, handle_zip_file, convert_to_pdf
from text_pipeline import process_text_document, process_ocr_document
from structured_pipeline import handle_excel
from vision_pipeline import handle_image
from web_pipeline import handle_web_endpoint

# --- 1. CONFIGURATION and SECURITY ---
API_KEY_NAME = "Authorization"
# auto_error=False allows easy testing in Swagger UI and local development
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

app = FastAPI(
    title="Insurance Policy RAG System",
    description="High-Precision Hybrid RAG (BM25 + Dense Embeddings + CrossEncoder Reranking) for Insurance Policies on GPU.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Key Manager ---
class ApiKeyManager:
    def __init__(self, keys_str: Optional[str] = None):
        env_keys = keys_str or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.set_keys(env_keys)

    def set_keys(self, keys_str: str):
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip() and not k.strip().startswith("<") and "YOUR_" not in k.strip()]
        self.current_index = 0
        if not self.keys:
            print("--- [!] NOTICE: No valid GEMINI_API_KEY set. ---")
        else:
            print(f"--- API Key Manager initialized with {len(self.keys)} Google GenAI key(s). ---")

    def get_key(self) -> str:
        if not self.keys:
            return ""
        return self.keys[self.current_index]

    def rotate_key(self) -> str:
        if not self.keys:
            return ""
        self.current_index = (self.current_index + 1) % len(self.keys)
        new_key = self.keys[self.current_index]
        masked = new_key[:6] + "..." + new_key[-4:] if len(new_key) > 10 else "***"
        print(f"--- [!] Rate limit / Key rotation: Switched to key #{self.current_index + 1}/{len(self.keys)} ({masked}) ---")
        return new_key

    def has_keys(self) -> bool:
        return len(self.keys) > 0

    def key_count(self) -> int:
        return len(self.keys)

api_key_manager = ApiKeyManager()

# --- Pydantic Data Models ---
class InsureRAGRequest(BaseModel):
    documents: str = Field(..., description="URL or local path to insurance document (e.g. sample_insurance_policy.pdf)")
    questions: List[str]

class InsureRAGResponse(BaseModel):
    answers: List[str]

class InsuranceQueryRequest(BaseModel):
    document: Optional[str] = Field("sample_insurance_policy.pdf", description="Document file path or URL")
    questions: List[str]

class InsuranceQueryResponse(BaseModel):
    document: str
    results: List[dict]

# --- Global Embedding Model on GPU ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
print(f"--- Loading Dense Embedding Model ('{EMBEDDING_MODEL_NAME}') on {DEVICE}... ---")

embedding_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_NAME,
    model_kwargs={'device': DEVICE},
    encode_kwargs={'normalize_embeddings': True}
)

# --- Domain-Specific Insurance Prompts ---
INSURANCE_MEGA_PROMPT = ChatPromptTemplate.from_template("""
You are a senior insurance claims analyst and policy expert. Your task is to accurately answer questions regarding insurance policy documents based STRICTLY on the provided Context.

CRITICAL INSURANCE POLICY RULES:
1. FACTUAL GROUNDING: Rely ONLY on the provided Context. Do NOT extrapolate or assume coverage not stated.
2. NUMERICAL ACCURACY: State exact figures, percentages, waiting periods (e.g. 30 days, 24 months, 36 months), room rent sub-limits (e.g. 1% of SI), deductibles, and co-payment percentages when mentioned in the context.
3. EXCLUSIONS & CONDITIONS: When answering whether something is covered or excluded, explicitly cite the relevant clause or section (e.g. "Under Section 4.2 Specific Illness Waiting Period...").
4. MISSING INFORMATION: If the answer cannot be determined from the provided Context, you MUST state: "The information is not available in the provided document."
5. FORMATTING: Start each answer with "Answer <Question Number>:".

BATCH OF QUESTIONS AND CONTEXTS:
{formatted_questions_and_contexts}

YOUR BATCH OF ANSWERS:""")

BATCHED_HYDE_PROMPT = ChatPromptTemplate.from_template("""
You are an expert insurance underwriter. For each numbered question below, write a short, hypothetical insurance policy clause that provides a plausible answer.
Instructions:
1. Start each answer with "HyDE Answer <Question Number>:".
2. Each answer must be on a new line.
3. Output strictly in English.

BATCH OF QUESTIONS:
{formatted_questions}

YOUR BATCH OF HYPOTHETICAL CLAUSES:""")

# --- HELPER SECURITY ---
async def get_api_key(api_key: Optional[str] = Security(api_key_header)):
    return api_key

# --- ENDPOINTS ---
@app.get("/", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "Antigravity Insurance RAG System",
        "device": DEVICE,
        "gpu_name": GPU_NAME,
        "vram_gb": round(VRAM_GB, 2),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "reranker_model": "BAAI/bge-reranker-base (on CUDA)",
        "gemini_api_key_configured": api_key_manager.has_keys(),
        "default_sample_document": "sample_insurance_policy.pdf"
    }

@app.post("/api/v1/insurance/query", tags=["Insurance Q&A"])
async def query_insurance(request: InsuranceQueryRequest):
    """Query an insurance policy document with questions."""
    doc_identifier = request.document or "sample_insurance_policy.pdf"
    InsureRAG_req = InsureRAGRequest(documents=doc_identifier, questions=request.questions)
    res = await run_InsureRAG_query(InsureRAG_req)
    results = [{"question": q, "answer": a} for q, a in zip(request.questions, res.answers)]
    return InsuranceQueryResponse(document=doc_identifier, results=results)

@app.post("/api/v1/insurance/upload", tags=["Insurance Documents"])
async def upload_insurance_document(file: UploadFile = File(...)):
    """Upload a new insurance policy document (PDF, DOCX, TXT, XLSX)."""
    upload_dir = "uploaded_policies"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    return {
        "message": f"Successfully uploaded {file.filename}",
        "saved_path": file_path,
        "filename": file.filename,
        "size_bytes": os.path.getsize(file_path)
    }

@app.post("/api/v1/InsureRAG/run", response_model=InsureRAGResponse, tags=["Insurance Q&A"])
async def run_InsureRAG_query(request: InsureRAGRequest, api_key: Optional[str] = Security(get_api_key)):
    doc_url = str(request.documents)
    questions = request.questions
    tmp_path = None
    converted_pdf_path = None
    temp_dir_obj = None
    
    try:
        # Step 1: Special endpoint handling
        if "get-secret-token" in doc_url:
            answers = await handle_web_endpoint(doc_url, questions, api_key_manager)
            return InsureRAGResponse(answers=answers)
            
        # Step 2: Resolve or download file
        tmp_path, downloaded_file_type = download_and_get_path(doc_url)
        doc_path_to_process = tmp_path
        final_file_type = downloaded_file_type
        
        # Step 3: Handle ZIP archives
        if downloaded_file_type == ".zip":
            doc_path_to_process, final_file_type, temp_dir_obj = handle_zip_file(tmp_path)

        # Step 4: Convert Office docs to PDF if needed
        if final_file_type in [".docx", ".pptx"]:
            converted_pdf_path = convert_to_pdf(doc_path_to_process, final_file_type)
            if converted_pdf_path != doc_path_to_process:
                doc_path_to_process = converted_pdf_path
                final_file_type = ".pdf"
            
        # Step 5: Route to appropriate pipeline
        if final_file_type in [".xlsx", ".xls"]:
            answers = await handle_excel(doc_path_to_process, questions, api_key_manager, INSURANCE_MEGA_PROMPT)
        elif final_file_type in [".png", ".jpg", ".jpeg"]:
            answers = await handle_image(doc_path_to_process, questions, api_key_manager)
        elif final_file_type in [".pdf", ".docx", ".pptx", ".txt", ".md"]:
            print(f"--- Routing to GPU Hybrid RAG Tool for {final_file_type} ---")
            answers, _ = await process_text_document(
                doc_path=doc_path_to_process,
                doc_url=doc_url, 
                questions=questions,
                api_key_manager=api_key_manager,
                embedding_model=embedding_model,
                batch_hyde_prompt=BATCHED_HYDE_PROMPT,
                mega_prompt=INSURANCE_MEGA_PROMPT
            )
        else:
            answers = [f"Unsupported file type: {final_file_type}"] * len(questions)
            
        return InsureRAGResponse(answers=answers)

    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Internal error in RAG server: {str(e)}")
    finally:
        # Cleanup temporary files (preserve local user files)
        if temp_dir_obj:
            temp_dir_obj.cleanup()
        if converted_pdf_path and converted_pdf_path != doc_path_to_process and os.path.exists(converted_pdf_path):
            try: os.remove(converted_pdf_path)
            except Exception: pass
        if tmp_path and tmp_path.startswith(tempfile.gettempdir()) and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
