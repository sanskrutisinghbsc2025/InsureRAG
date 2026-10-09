import os
import asyncio
from typing import List, Dict, Optional
import itertools
import pickle
from urllib.parse import urlparse, unquote
import re
import tempfile
import requests
import torch
from fastapi import HTTPException

# LangChain and ML imports
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredPowerPointLoader
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from langchain_google_genai import ChatGoogleGenerativeAI
from sentence_transformers import CrossEncoder

# Device selection (RTX 4060 GPU with fallback to CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- CACHE DEFINITIONS ---
MEMORY_CACHE = {} 
CHUNK_CACHE_DIR = "doc_cache"
BM25_CACHE_DIR = "bm25_cache"
VECTOR_DB_DIR = "vector_db"
URL_MAP_PATH = "url_map.pkl"
QUERY_CACHE_PATH = "query_cache.pkl"

# Ensure cache directories exist
for d in [CHUNK_CACHE_DIR, BM25_CACHE_DIR, VECTOR_DB_DIR]:
    os.makedirs(d, exist_ok=True)

def load_query_cache():
    if os.path.exists(QUERY_CACHE_PATH):
        try:
            with open(QUERY_CACHE_PATH, "rb") as f:
                cache = pickle.load(f)
                print(f"--- RAG Tool: Successfully loaded {len(cache)} cached query answer(s) from disk. ---")
                return cache
        except Exception as e:
            print(f"Error loading query cache: {e}")
    return {}

def save_query_cache(cache):
    try:
        with open(QUERY_CACHE_PATH, "wb") as f:
            pickle.dump(cache, f)
    except Exception as e:
        print(f"Error saving query cache: {e}")

QUERY_CACHE = load_query_cache()

# --- Load the URL-to-filename map on startup ---
try:
    with open(URL_MAP_PATH, "rb") as f:
        URL_PATH_TO_FILENAME_MAP = pickle.load(f)
    print(f"--- RAG Tool: Successfully loaded URL PATH map with {len(URL_PATH_TO_FILENAME_MAP)} entries. ---")
except FileNotFoundError:
    URL_PATH_TO_FILENAME_MAP = {}

# --- HELPER FUNCTIONS ---
def reciprocal_rank_fusion(ranked_lists: List[List[Document]], k: int = 60) -> List[Document]:
    fused_scores: Dict[str, float] = {}
    doc_map = {doc.page_content: doc for doc_list in ranked_lists for doc in doc_list}
    for doc_list in ranked_lists:
        for rank, doc in enumerate(doc_list):
            doc_content = doc.page_content
            if doc_content not in fused_scores:
                fused_scores[doc_content] = 0
            fused_scores[doc_content] += 1 / (rank + k)
    reranked_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[content] for content, _ in reranked_results if content in doc_map]

def load_text_document(temp_path: str, file_type: str) -> List[Document]:
    """Robust loader for insurance documents (PDF, DOCX, PPTX, TXT, MD)."""
    print(f"--- RAG Tool: Loading document of type: {file_type} from {temp_path} ---")
    if file_type == ".pdf":
        try:
            docs = PyPDFLoader(temp_path).load()
            if docs and any(d.page_content.strip() for d in docs):
                return docs
        except Exception as e:
            print(f"PyPDFLoader encountered an issue: {e}. Trying pdfplumber fallback...")
        
        # Robust pdfplumber fallback (great for insurance tables & schedules)
        try:
            import pdfplumber
            docs = []
            with pdfplumber.open(temp_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            table_str = "\n".join([" | ".join([str(c) if c else "" for c in row]) for row in table])
                            text += f"\n\n[Table Page {idx+1}]:\n{table_str}"
                    if text.strip():
                        docs.append(Document(page_content=text, metadata={"page": idx+1, "source": temp_path}))
            return docs
        except Exception as e:
            print(f"pdfplumber fallback error: {e}")
            return []

    if file_type == ".docx":
        return Docx2txtLoader(temp_path).load()
    if file_type == ".pptx":
        try:
            return UnstructuredPowerPointLoader(temp_path).load()
        except Exception:
            return []
    if file_type in [".txt", ".md"]:
        with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            return [Document(page_content=content, metadata={"source": temp_path})]
    return []

class FastGPUReranker:
    def __init__(self, model_name="BAAI/bge-reranker-base", device=DEVICE, top_n=4):
        print(f"--- Loading CrossEncoder ('{model_name}') on {device}... ---")
        self.model = CrossEncoder(model_name, device=device)
        self.top_n = top_n

    def compress_documents(self, documents: List[Document], query: str) -> List[Document]:
        if not documents:
            return []
        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(pairs)
        doc_scores = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        top_docs = []
        for doc, score in doc_scores[:self.top_n]:
            doc.metadata["rerank_score"] = float(score)
            top_docs.append(doc)
        return top_docs

# Singleton reranker to conserve GPU memory
_RERANKER_CACHE = None
def get_reranker():
    global _RERANKER_CACHE
    if _RERANKER_CACHE is None:
        _RERANKER_CACHE = FastGPUReranker()
    return _RERANKER_CACHE

# --- THE MAIN PIPELINE FUNCTION ---
async def process_text_document(
    doc_path: str,
    doc_url: str,
    questions: List[str], 
    api_key_manager, 
    embedding_model,
    batch_hyde_prompt,
    mega_prompt
) -> List[str]:
    """The hybrid RAG pipeline for insurance documents running on GPU."""
    try:
        url_path = urlparse(doc_url).path if (doc_url.startswith("http://") or doc_url.startswith("https://")) else doc_url
        clean_filename = URL_PATH_TO_FILENAME_MAP.get(url_path)

        reranker = get_reranker()

        # --- CACHE-FIRST LOGIC ---
        if clean_filename and clean_filename in MEMORY_CACHE:
            print(f"--- RAG Tool: MEMORY CACHE HIT for document: {clean_filename}... ---")
            cached_data = MEMORY_CACHE[clean_filename]
            base_retriever = cached_data['base_retriever']
            bm25 = cached_data['bm25']
            all_chunks = cached_data['all_chunks']
        elif clean_filename and os.path.exists(os.path.join(CHUNK_CACHE_DIR, f"{clean_filename}.pkl")):
            print(f"--- RAG Tool: DISK CACHE HIT for document: {clean_filename}... ---")
            db_path = os.path.join(VECTOR_DB_DIR, clean_filename)
            chunk_path = os.path.join(CHUNK_CACHE_DIR, f"{clean_filename}.pkl")
            bm25_path = os.path.join(BM25_CACHE_DIR, f"{clean_filename}.pkl")

            with open(chunk_path, "rb") as f: all_chunks = pickle.load(f)
            with open(bm25_path, "rb") as f: bm25 = pickle.load(f)

            vectorstore = Chroma(persist_directory=db_path, embedding_function=embedding_model)
            base_retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
            
            MEMORY_CACHE.clear()
            MEMORY_CACHE[clean_filename] = {
                'base_retriever': base_retriever, 'bm25': bm25,
                'all_chunks': all_chunks, 'reranker': reranker
            }
            print("--- RAG Tool: All components loaded and stored in memory cache. ---")
        else:
            # Live document ingestion & clause-aware chunking
            print(f"--- RAG Tool: LIVE Document Processing for {doc_path}... ---")
            _, file_type = os.path.splitext(doc_path)
            raw_docs = load_text_document(doc_path, file_type.lower())
            if not raw_docs:
                raise ValueError(f"Document loading failed or returned no text: {doc_path}")

            # Clause-aware text splitting tailored for insurance policies
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=750,
                chunk_overlap=150,
                separators=["\n\nSECTION ", "\n\nSection ", "\n\nClause ", "\n\n### ", "\n\n## ", "\n\n", "\n", ". ", " "]
            )
            all_chunks = text_splitter.split_documents(raw_docs)
            print(f"--- Chunked into {len(all_chunks)} coherent policy segments. Embedding on {DEVICE}... ---")

            vectorstore = Chroma.from_documents(documents=all_chunks, embedding=embedding_model)
            base_retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
            tokenized_corpus = [doc.page_content.split(" ") for doc in all_chunks]
            bm25 = BM25Okapi(tokenized_corpus)

        # --- PHASE 1: BATCHED HYDE (Hypothetical Document Embeddings) ---
        hypothetical_answers = questions[:] # Default fallback to original questions
        try:
            hyde_key = api_key_manager.get_key()
            if hyde_key and not hyde_key.startswith("<") and "YOUR_" not in hyde_key:
                hyde_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=hyde_key)
                hyde_chain = batch_hyde_prompt | hyde_llm
                formatted_questions = "\n".join([f"Question {i+1}: {q}" for i, q in enumerate(questions)])
                hyde_result = await hyde_chain.ainvoke({"formatted_questions": formatted_questions})
                hyde_text_block = hyde_result.content if hasattr(hyde_result, "content") else str(hyde_result)
                if isinstance(hyde_text_block, list): hyde_text_block = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in hyde_text_block)
                for line in hyde_text_block.splitlines():
                    if line.startswith("HyDE Answer"):
                        try:
                            q_num = int(line.split(" ")[2].replace(":", "")) - 1
                            if 0 <= q_num < len(hypothetical_answers):
                                hypothetical_answers[q_num] = line.split(":", 1)[-1].strip()
                        except (ValueError, IndexError): continue
        except Exception as hyde_err:
            print(f"--- HyDE step skipped/fallback: {hyde_err} ---")

        # --- PHASE 2: THROTTLED HYBRID RETRIEVAL (Dense + BM25 + CrossEncoder) ---
        CONCURRENCY_LIMIT = 5 
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def get_throttled_reranked_context(question: str, hypo_answer: str) -> str:
            async with semaphore:
                semantic_docs = await base_retriever.ainvoke(hypo_answer)
                tokenized_query = question.split(" ")
                bm25_indices = bm25.get_top_n(tokenized_query, range(len(all_chunks)), n=15)
                bm25_docs = [all_chunks[i] for i in bm25_indices]
                fused_docs = reciprocal_rank_fusion([semantic_docs, bm25_docs])
                if not fused_docs:
                    return ""
                reranked_docs = reranker.compress_documents(documents=fused_docs, query=question)
                return "\n\n---\n\n".join([doc.page_content for doc in reranked_docs])

        print(f"--- RAG Tool: Retrieving hybrid contexts for {len(questions)} question(s) with GPU Cross-Encoder... ---")
        context_tasks = [get_throttled_reranked_context(q, ha) for q, ha in zip(questions, hypothetical_answers)]
        all_contexts = await asyncio.gather(*context_tasks)

        # --- PHASE 3: BATCHED FINAL ANSWER GENERATION ---
        BATCH_SIZE = 6
        final_answers = ["The information is not available in the provided document."] * len(questions)
        qa_pairs = list(zip(questions, all_contexts))

        # Check Query Cache
        global QUERY_CACHE
        cache_key = (doc_path, tuple(questions))
        if cache_key in QUERY_CACHE:
            print("--- RAG Tool: Returning answers from QUERY_CACHE! ---")
            cached_val = QUERY_CACHE[cache_key]
            if isinstance(cached_val, tuple) and len(cached_val) == 2:
                return cached_val
            elif isinstance(cached_val, list):
                return cached_val, [""] * len(cached_val)
            else:
                return [str(cached_val)], [""]

        # Check if an API key is available
        has_api_key = False
        try:
            test_key = api_key_manager.get_key()
            if test_key and not test_key.startswith("<") and "YOUR_" not in test_key:
                has_api_key = True
        except Exception:
            has_api_key = False

        if has_api_key:
            for i in range(0, len(qa_pairs), BATCH_SIZE):
                batch = qa_pairs[i:i + BATCH_SIZE]
                
                formatted_input = ""
                for j, (question, context) in enumerate(batch):
                    original_q_num = i + j + 1
                    formatted_input += f"Question {original_q_num}:\n{question}\n\nContext {original_q_num}:\n{context}\n\n---\n\n"

                llm_success = False
                max_retries = max(1, api_key_manager.key_count())
                
                for attempt in range(max_retries):
                    key = api_key_manager.get_key()
                    if not key or key.startswith("<") or "YOUR_" in key:
                        break
                    try:
                        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
                        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0, google_api_key=key)
                        final_answer_chain = mega_prompt | llm
                        
                        result = await final_answer_chain.ainvoke({"formatted_questions_and_contexts": formatted_input})
                        final_text_block = result.content if hasattr(result, "content") else str(result)
                        if isinstance(final_text_block, list): 
                            final_text_block = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in final_text_block)
                        
                        import re
                        matches = re.finditer(r'(?:^|\n)\s*(?:\#+|\*+)?\s*Answer\s+(\d+)\s*(?:\#+|\*+)?[\s:]*(.*?)(?=\n\s*(?:\#+|\*+)?\s*Answer\s+\d+|$)', final_text_block, re.DOTALL | re.IGNORECASE)
                        for match in matches:
                            try:
                                q_num = int(match.group(1)) - 1
                                if 0 <= q_num < len(final_answers):
                                    final_answers[q_num] = match.group(2).strip()
                            except (ValueError, IndexError):
                                continue
                        
                        llm_success = True
                        break
                    except Exception as llm_err:
                        print(f"--- [!] LLM key attempt #{attempt + 1} failed: {llm_err}. Rotating key... ---")
                        api_key_manager.rotate_key()

                if not llm_success:
                    print("--- [!] All LLM keys failed or unavailable. Falling back to Verbatim Context Passage Extraction. ---")
                    for j, (question, context) in enumerate(batch):
                        idx = i + j
                        if context.strip():
                            clean_ctx = context.split("\n\n---\n\n")[0].strip()
                            final_answers[idx] = f"Based on the insurance document context:\n{clean_ctx}"
                        else:
                            final_answers[idx] = "The information is not available in the provided document."
        else:
            # Direct context extraction fallback when Gemini API key is not yet set
            for idx, (question, context) in enumerate(qa_pairs):
                if context.strip():
                    clean_ctx = context.split("\n\n---\n\n")[0].strip()
                    final_answers[idx] = f"Based on the insurance document:\n{clean_ctx}\n\n(Tip: Set your GEMINI_API_KEY for fully synthesized generative answers)."
                else:
                    final_answers[idx] = "The information is not available in the provided document."
        
        QUERY_CACHE[cache_key] = (final_answers, all_contexts)
        return final_answers, all_contexts

    except Exception as e:
        print(f"Error in RAG pipeline: {e}")
        err_msgs = [f"An error occurred while processing the document: {e}"] * len(questions)
        empty_ctxs = [""] * len(questions)
        return err_msgs, empty_ctxs
    
async def process_ocr_document(
    doc_path: str,
    questions: List[str], 
    api_key_manager,
    mega_prompt
) -> List[str]:
    """Robust OCR / Fallback document processing."""
    print(f"--- RAG Tool: Processing document: {doc_path} ---")
    try:
        _, ext = os.path.splitext(doc_path)
        docs = load_text_document(doc_path, ext.lower())
        context = "\n".join([doc.page_content for doc in docs])

        if not context or context.isspace():
            return ["Could not extract any readable text from the document."] * len(questions)
        
        print(f"--- Document extracted text length: {len(context)} chars ---")

        key = api_key_manager.get_key()
        if not key or key.startswith("<") or "YOUR_" in key:
            return [f"Extracted Policy Text Preview:\n{context[:500]}..."] * len(questions)

        BATCH_SIZE = 6
        final_answers = ["The information is not available in the provided document."] * len(questions)
        qa_pairs = [(q, context) for q in questions]

        for i in range(0, len(qa_pairs), BATCH_SIZE):
            batch = qa_pairs[i:i + BATCH_SIZE]
            llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=key)
            final_answer_chain = mega_prompt | llm
            
            formatted_input = ""
            for j, (question, ctx) in enumerate(batch):
                original_q_num = i + j + 1
                formatted_input += f"Question {original_q_num}:\n{question}\n\nContext {original_q_num}:\n{ctx}\n\n---\n\n"

            result = await final_answer_chain.ainvoke({"formatted_questions_and_contexts": formatted_input})
            final_text_block = result.content if hasattr(result, "content") else str(result)
            if isinstance(final_text_block, list): final_text_block = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in final_text_block)
            
            print(f"--- RAW LLM OUTPUT (OCR) ---\n{final_text_block}\n----------------------")

            import re
            matches = re.finditer(r'(?:^|\n)\s*(?:\#+|\*+)?\s*Answer\s+(\d+)\s*(?:\#+|\*+)?[\s:]*(.*?)(?=\n\s*(?:\#+|\*+)?\s*Answer\s+\d+|$)', final_text_block, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    q_num = int(match.group(1)) - 1
                    if 0 <= q_num < len(final_answers):
                        final_answers[q_num] = match.group(2).strip()
                except (ValueError, IndexError):
                    continue
        
        return final_answers
    
    except Exception as e:
        print(f"Error in OCR pipeline: {e}")
        return [f"An error occurred during document processing: {e}"] * len(questions)


async def get_document_journey_telemetry(doc_path: str, embedding_model, query: Optional[str] = None) -> Dict:
    """Generate comprehensive pipeline telemetry showing document journey, chunks, vector embeddings, and retrieval."""
    if not os.path.exists(doc_path) and not doc_path.startswith("http"):
        # Check uploaded_policies
        alt_path = os.path.join("uploaded_policies", os.path.basename(doc_path))
        if os.path.exists(alt_path):
            doc_path = alt_path

    _, ext = os.path.splitext(doc_path)
    file_type = ext.lower() or ".pdf"
    file_name = os.path.basename(doc_path)
    file_size_bytes = os.path.getsize(doc_path) if os.path.exists(doc_path) else 0

    # 1. Load Document
    raw_docs = load_text_document(doc_path, file_type)
    page_count = len(raw_docs)
    total_chars = sum(len(d.page_content) for d in raw_docs)
    total_words = sum(len(d.page_content.split()) for d in raw_docs)

    pages_summary = []
    for idx, doc in enumerate(raw_docs[:10]):
        pages_summary.append({
            "page": doc.metadata.get("page", idx + 1),
            "char_count": len(doc.page_content),
            "word_count": len(doc.page_content.split()),
            "sample_text": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else "")
        })

    # 2. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=150,
        separators=["\n\nSECTION ", "\n\nSection ", "\n\nClause ", "\n\n### ", "\n\n## ", "\n\n", "\n", ". ", " "]
    )
    all_chunks = text_splitter.split_documents(raw_docs) if raw_docs else []

    chunks_data = []
    # Embed a sample chunk to show vector representation
    sample_vectors = []
    for idx, chunk in enumerate(all_chunks):
        # Generate sample vector embedding representation for first 15 chunks
        vec_sample = []
        if idx < 15 and embedding_model:
            try:
                emb = embedding_model.embed_query(chunk.page_content[:200])
                vec_sample = [round(float(v), 4) for v in emb[:384]]
            except Exception:
                vec_sample = []
        
        chunks_data.append({
            "id": idx + 1,
            "page": chunk.metadata.get("page", 1),
            "char_count": len(chunk.page_content),
            "word_count": len(chunk.page_content.split()),
            "content": chunk.page_content,
            "vector_dimensions": 384,
            "vector_sample": vec_sample[:16], # Top 16 float values for visual grid
            "vector_full_count": len(vec_sample)
        })

    # 3. BM25 Tokenization Stats
    tokenized_corpus = [doc.page_content.split(" ") for doc in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
    vocab = set(token for doc_tokens in tokenized_corpus for token in doc_tokens)

    # 4. Retrieval Telemetry (if query provided)
    query_telemetry = None
    if query and all_chunks and embedding_model:
        start_time = asyncio.get_event_loop().time()
        
        # Check cache
        cache_key = (doc_path, (query,))
        is_cached = cache_key in QUERY_CACHE

        # BM25 Top Matches
        tokenized_q = query.split(" ")
        bm25_top_indices = bm25.get_top_n(tokenized_q, range(len(all_chunks)), n=5) if bm25 else []
        bm25_results = [{
            "rank": i + 1,
            "chunk_id": idx + 1,
            "page": all_chunks[idx].metadata.get("page", 1),
            "snippet": all_chunks[idx].page_content[:250] + "..."
        } for i, idx in enumerate(bm25_top_indices)]

        # Dense Vector Matches
        vectorstore = Chroma.from_documents(documents=all_chunks, embedding=embedding_model)
        dense_docs = vectorstore.similarity_search_with_score(query, k=5)
        dense_results = [{
            "rank": i + 1,
            "score": round(float(score), 4),
            "page": doc.metadata.get("page", 1),
            "snippet": doc.page_content[:250] + "..."
        } for i, (doc, score) in enumerate(dense_docs)]

        # CrossEncoder Rerank
        reranker = get_reranker()
        fused_docs = [doc for doc, _ in dense_docs]
        reranked_docs = reranker.compress_documents(fused_docs, query) if fused_docs else []
        rerank_results = [{
            "rank": i + 1,
            "score": round(float(doc.metadata.get("rerank_score", 0.0)), 4),
            "page": doc.metadata.get("page", 1),
            "snippet": doc.page_content[:250] + "..."
        } for i, doc in enumerate(reranked_docs)]

        elapsed_ms = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)

        query_telemetry = {
            "query": query,
            "is_cached": is_cached,
            "latency_ms": elapsed_ms,
            "bm25_matches": bm25_results,
            "dense_matches": dense_results,
            "reranked_matches": rerank_results
        }

    return {
        "doc_info": {
            "filename": file_name,
            "file_type": file_type,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
            "page_count": page_count,
            "total_chars": total_chars,
            "total_words": total_words,
            "chunk_count": len(all_chunks)
        },
        "pages": pages_summary,
        "chunking": {
            "strategy": "Clause-Aware Recursive Character Splitting",
            "chunk_size": 750,
            "chunk_overlap": 150,
            "separators": ["\n\nSECTION ", "\n\nSection ", "\n\nClause ", "\n\n### ", "\n\n## ", "\n\n", "\n", ". ", " "],
            "total_chunks": len(all_chunks),
            "chunks": chunks_data
        },
        "embedding": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "dimensions": 384,
            "device": DEVICE,
            "distance_metric": "Cosine Similarity",
            "vector_store": "ChromaDB"
        },
        "bm25": {
            "vocab_size": len(vocab),
            "k1": 1.5,
            "b": 0.75
        },
        "query_telemetry": query_telemetry
    }

