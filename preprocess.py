import os
import requests
import pickle
from urllib.parse import urlparse
import shutil
import tempfile
import torch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

# Define directories for pre-processed assets
CHUNK_CACHE_DIR = "./doc_cache"
BM25_CACHE_DIR = "./bm25_cache"
VECTOR_DB_DIR = "./vector_db"
URL_MAP_PATH = "url_map.pkl"

def preprocess_documents(doc_targets=None):
    """
    Pre-processes insurance documents, creating Chroma Vector Stores, BM25 models,
    and pickled chunk caches for ultra-fast GPU retrieval.
    """
    if doc_targets is None:
        doc_targets = ["sample_insurance_policy.pdf"]

    for d in [CHUNK_CACHE_DIR, BM25_CACHE_DIR, VECTOR_DB_DIR]:
        os.makedirs(d, exist_ok=True)

    # Load existing url map or initialize
    url_map = {}
    if os.path.exists(URL_MAP_PATH):
        try:
            with open(URL_MAP_PATH, "rb") as f:
                url_map = pickle.load(f)
        except Exception:
            url_map = {}

    print(f"--- Initializing embedding model ('{EMBEDDING_MODEL_NAME}') on {DEVICE}... ---")
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': DEVICE},
        encode_kwargs={'normalize_embeddings': True}
    )

    for target in doc_targets:
        try:
            is_url = target.startswith("http://") or target.startswith("https://")
            if is_url:
                parsed_url = urlparse(target)
                filename = os.path.basename(parsed_url.path) or "downloaded_policy.pdf"
                print(f"[+] Downloading and processing URL {target} -> {filename}...")
                resp = requests.get(target); resp.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(resp.content)
                    doc_path = tmp.name
                url_map[parsed_url.path] = filename
            else:
                doc_path = os.path.abspath(target)
                filename = os.path.basename(doc_path)
                print(f"[+] Processing local insurance document: {filename}...")
                url_map[target] = filename
                url_map[filename] = filename

            # 1. Load and Clause-Aware Chunking
            print(f"    - Loading and chunking {filename}...")
            docs = PyPDFLoader(doc_path).load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=750, 
                chunk_overlap=150,
                separators=["\n\nSECTION ", "\n\nSection ", "\n\nClause ", "\n\n### ", "\n\n## ", "\n\n", "\n", ". ", " "]
            )
            all_chunks = text_splitter.split_documents(docs)
            
            clean_name = os.path.splitext(filename)[0]
            with open(os.path.join(CHUNK_CACHE_DIR, f"{clean_name}.pkl"), "wb") as f:
                pickle.dump(all_chunks, f)
            print(f"    - Saved {len(all_chunks)} chunks to {CHUNK_CACHE_DIR}.")

            # 2. Embed on GPU & Persist Vector Store
            print(f"    - Embedding {len(all_chunks)} chunks into ChromaDB on {DEVICE}...")
            db_path = os.path.join(VECTOR_DB_DIR, clean_name)
            Chroma.from_documents(all_chunks, embedding_model, persist_directory=db_path)
            print(f"    - Persisted vector store to {db_path}")

            # 3. Create and Save BM25 Model
            print(f"    - Creating BM25 sparse index...")
            tokenized_corpus = [doc.page_content.split(" ") for doc in all_chunks]
            bm25 = BM25Okapi(tokenized_corpus)
            with open(os.path.join(BM25_CACHE_DIR, f"{clean_name}.pkl"), "wb") as f:
                pickle.dump(bm25, f)
            print(f"    - Saved BM25 model to {BM25_CACHE_DIR}.")

            if is_url:
                os.remove(doc_path)

        except Exception as e:
            print(f"[!] ERROR processing {target}: {e}")

    # Persist updated URL map
    with open(URL_MAP_PATH, "wb") as f:
        pickle.dump(url_map, f)
    print(f"--- Pre-processing complete. URL / File map updated at {URL_MAP_PATH} ---")

if __name__ == "__main__":
    preprocess_documents()
