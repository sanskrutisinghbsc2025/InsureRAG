import os
import shutil
import asyncio
import time
from urllib.parse import unquote
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch

from text_pipeline import process_text_document, load_text_document, get_document_journey_telemetry, QUERY_CACHE, save_query_cache
from structured_pipeline import handle_excel
from brain import ApiKeyManager, INSURANCE_MEGA_PROMPT, BATCHED_HYDE_PROMPT, embedding_model, api_key_manager

app = FastAPI(title="InsureRAG API")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    doc_path: str
    api_key: Optional[str] = None

class JourneyRequest(BaseModel):
    doc_path: str
    query: Optional[str] = None

class KeysRequest(BaseModel):
    api_keys: str

@app.get("/api/files/{filename:path}")
async def serve_file(filename: str):
    clean_name = unquote(filename).strip()
    
    # 1. Direct local file path
    if os.path.exists(clean_name):
        return FileResponse(
            os.path.abspath(clean_name), 
            media_type="application/pdf" if clean_name.lower().endswith(".pdf") else None
        )
        
    # 2. File inside uploaded_policies
    base_name = os.path.basename(clean_name)
    uploaded_path = os.path.abspath(os.path.join("uploaded_policies", base_name))
    if os.path.exists(uploaded_path):
        return FileResponse(
            uploaded_path, 
            media_type="application/pdf" if uploaded_path.lower().endswith(".pdf") else None
        )
        
    # 3. File in root project directory
    root_path = os.path.abspath(base_name)
    if os.path.exists(root_path):
        return FileResponse(
            root_path, 
            media_type="application/pdf" if root_path.lower().endswith(".pdf") else None
        )
        
    # 4. HDFC policy fallback matcher
    hdfc_path = os.path.abspath("uploaded_policies/HDFC-Life-Sampoorn-Nivesh-Plus-V01-Policy-Document.pdf")
    if ("hdfc" in clean_name.lower() or "sampoorn" in clean_name.lower()) and os.path.exists(hdfc_path):
        return FileResponse(hdfc_path, media_type="application/pdf")

    # 5. Star Health fallback matcher
    sample_path = os.path.abspath("sample_insurance_policy.pdf")
    if ("star" in clean_name.lower() or "sample" in clean_name.lower()) and os.path.exists(sample_path):
        return FileResponse(sample_path, media_type="application/pdf")

    raise HTTPException(status_code=404, detail=f"File not found: {filename}")

@app.get("/api/system")
def get_system_status():
    cuda_available = torch.cuda.is_available()
    return {
        "gpu_mode": cuda_available,
        "gpu_name": torch.cuda.get_device_name(0) if cuda_available else "CPU",
        "vram_total_gb": torch.cuda.get_device_properties(0).total_memory / (1024**3) if cuda_available else 0,
        "vram_allocated_gb": torch.cuda.memory_allocated(0) / (1024**3) if cuda_available else 0,
        "key_count": api_key_manager.key_count(),
        "cache_count": len(QUERY_CACHE)
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    os.makedirs("uploaded_policies", exist_ok=True)
    file_path = os.path.join("uploaded_policies", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": os.path.abspath(file_path)}

@app.post("/api/keys")
async def update_keys(req: KeysRequest):
    api_key_manager.set_keys(req.api_keys)
    os.environ["GEMINI_API_KEY"] = req.api_keys
    return {"status": "success", "active_keys": api_key_manager.key_count()}

@app.post("/api/query")
async def process_query(req: QueryRequest):
    start_time = time.time()
    
    if req.api_key:
        api_key_manager.set_keys(req.api_key)
        os.environ["GEMINI_API_KEY"] = req.api_key
        
    target_path = req.doc_path
    if not os.path.exists(target_path) and not target_path.startswith("http"):
        alt_path = os.path.join("uploaded_policies", os.path.basename(req.doc_path))
        if os.path.exists(alt_path):
            target_path = alt_path
        else:
            raise HTTPException(status_code=400, detail=f"Document not found: {req.doc_path}")
        
    cache_key = (target_path, (req.query,))
    is_cached = cache_key in QUERY_CACHE

    _, ext = os.path.splitext(target_path)
    try:
        context_used = ""
        if ext.lower() in [".xlsx", ".xls"]:
            answers = await handle_excel(target_path, [req.query], api_key_manager, INSURANCE_MEGA_PROMPT)
            answer = answers[0] if answers else "No response generated."
        else:
            res = await process_text_document(
                doc_path=target_path,
                doc_url=target_path,
                questions=[req.query],
                api_key_manager=api_key_manager,
                embedding_model=embedding_model,
                batch_hyde_prompt=BATCHED_HYDE_PROMPT,
                mega_prompt=INSURANCE_MEGA_PROMPT
            )
            if isinstance(res, tuple) and len(res) == 2:
                answers, contexts = res
            elif isinstance(res, list):
                answers, contexts = res, [""] * len(res)
            else:
                answers, contexts = [str(res)], [""]

            answer = answers[0] if answers else "No response generated."
            context_used = contexts[0] if contexts else ""

        save_query_cache(QUERY_CACHE)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
            
        return {
            "answer": answer, 
            "context": context_used, 
            "cached": is_cached, 
            "latency_ms": elapsed_ms
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/journey")
async def get_pipeline_journey(req: JourneyRequest):
    target_path = req.doc_path
    if not os.path.exists(target_path) and not target_path.startswith("http"):
        alt_path = os.path.join("uploaded_policies", os.path.basename(req.doc_path))
        if os.path.exists(alt_path):
            target_path = alt_path
        else:
            raise HTTPException(status_code=400, detail=f"Document not found: {req.doc_path}")

    try:
        telemetry = await get_document_journey_telemetry(
            doc_path=target_path,
            embedding_model=embedding_model,
            query=req.query
        )
        return telemetry
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telemetry generation error: {str(e)}")

@app.get("/api/cache/stats")
def get_cache_stats():
    return {
        "cached_queries_count": len(QUERY_CACHE),
        "cache_file": "query_cache.pkl"
    }

@app.post("/api/cache/clear")
def clear_cache():
    QUERY_CACHE.clear()
    save_query_cache(QUERY_CACHE)
    return {"status": "cleared", "count": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
