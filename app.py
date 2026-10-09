import os
import sys
import asyncio
import tempfile
import torch
import streamlit as st
from dotenv import load_dotenv, set_key

# Page Configuration
st.set_page_config(
    page_title="InsureRAG Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# SaaS-style Custom CSS
st.markdown("""
<style>
    /* Hide Streamlit Default Chrome */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main Background & Padding */
    .stApp {
        background-color: #f4f7f6;
    }
    
    /* Top Header Styling */
    .saas-header {
        background-color: #ffffff;
        padding: 1rem 2rem;
        border-bottom: 1px solid #e2e8f0;
        margin-top: -4rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .saas-header h1 {
        margin: 0;
        font-size: 1.5rem;
        color: #0f172a;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    .saas-header .badge {
        background-color: #e0e7ff;
        color: #4338ca;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.875rem;
        font-weight: 600;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        border-bottom: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3.5rem;
        background-color: transparent;
        color: #64748b;
        font-weight: 500;
        padding: 0 0.5rem;
    }
    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        border-bottom: 2px solid #2563eb !important;
        font-weight: 600;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Chat Messages */
    [data-testid="stChatMessage"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* Subheaders */
    h3 {
        color: #334155;
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }
    
    /* Document text */
    .doc-preview-text {
        font-family: 'Georgia', serif;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# Load existing environment
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from text_pipeline import (
    process_text_document, 
    load_text_document,
    reciprocal_rank_fusion,
    get_reranker,
    DEVICE,
    CHUNK_CACHE_DIR,
    BM25_CACHE_DIR,
    VECTOR_DB_DIR
)
from structured_pipeline import handle_excel
from file_utils import download_and_get_path
from brain import ApiKeyManager, INSURANCE_MEGA_PROMPT, BATCHED_HYDE_PROMPT, embedding_model

# --- System & GPU Check ---
cuda_available = torch.cuda.is_available()
gpu_name = torch.cuda.get_device_name(0) if cuda_available else "CPU Mode"
gpu_badge_text = f"⚡ {gpu_name}" if cuda_available else "⚙️ CPU Mode"

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_doc_path" not in st.session_state:
    st.session_state.current_doc_path = "sample_insurance_policy.pdf"
if "current_doc_name" not in st.session_state:
    st.session_state.current_doc_name = "Star Health Shield Comprehensive Policy"

# --- TOP NAVIGATION (SaaS Header) ---
st.markdown(f"""
<div class="saas-header">
    <h1>InsureRAG Platform</h1>
    <div class="badge">{gpu_badge_text}</div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR (Settings & Context) ---
with st.sidebar:
    st.markdown("### Workspace Context")
    st.info(f"📄 **{st.session_state.current_doc_name}**")
    
    st.markdown("### API Configuration")
    current_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    user_api_key = st.text_input(
        "Google Gemini Key",
        value=current_key,
        type="password",
        placeholder="AIzaSy..."
    )
    
    if st.button("Save Configuration", use_container_width=True, type="primary"):
        if user_api_key.strip():
            os.environ["GEMINI_API_KEY"] = user_api_key.strip()
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={user_api_key.strip()}\n")
            st.success("Configuration Saved")
            st.rerun()
            
    if not os.getenv("GEMINI_API_KEY"):
        st.warning("Running in Verbatim Extraction Mode (No LLM)")

    st.markdown("---")
    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# --- MAIN WORKSPACE ---
tab_analysis, tab_documents, tab_architecture = st.tabs([
    "🔍 Analysis & Q&A", 
    "📁 Document Library", 
    "⚙️ System Architecture"
])

# --- TAB 1: ANALYSIS (SaaS Split Pane) ---
with tab_analysis:
    col_viewer, col_chat = st.columns([1.2, 1])
    
    # Document Viewer
    with col_viewer:
        st.markdown("### Document Viewer")
        doc_container = st.container(height=650)
        with doc_container:
            if os.path.exists(st.session_state.current_doc_path):
                try:
                    _, ext = os.path.splitext(st.session_state.current_doc_path)
                    preview_docs = load_text_document(st.session_state.current_doc_path, ext.lower())
                    if preview_docs:
                        full_text = "\n\n".join([f"**Page {i+1}**\n\n" + d.page_content for i, d in enumerate(preview_docs)])
                        # Render as clean markdown rather than a text area
                        st.markdown(f'<div class="doc-preview-text">{full_text[:12000]}</div>', unsafe_allow_html=True)
                        if len(full_text) > 12000:
                            st.caption("... [Document truncated for preview]")
                    else:
                        st.write("Preview not available for this file type.")
                except Exception as e:
                    st.error(f"Error loading preview: {e}")
            else:
                st.info("Remote URL or file not found locally. Preview disabled.")

    # Chat Interface
    with col_chat:
        st.markdown("### Intelligence Chat")
        
        # Action Buttons (Pills)
        st.caption("Suggested Actions:")
        action_col1, action_col2 = st.columns(2)
        prompt_to_run = None
        with action_col1:
            if st.button("Check Waiting Periods", use_container_width=True): prompt_to_run = "What is the waiting period for pre-existing diseases?"
            if st.button("Check Sub-Limits", use_container_width=True): prompt_to_run = "What are the room rent sub-limits?"
        with action_col2:
            if st.button("Permanent Exclusions", use_container_width=True): prompt_to_run = "List all permanent exclusions."
            if st.button("Claim Process", use_container_width=True): prompt_to_run = "What is the claim submission process?"

        # Chat History
        chat_container = st.container(height=450)
        
        async def execute_query(doc_path: str, query: str):
            answers = await process_text_document(
                doc_path=doc_path,
                doc_url=doc_path,
                questions=[query],
                api_key_manager=ApiKeyManager(),
                embedding_model=embedding_model,
                batch_hyde_prompt=BATCHED_HYDE_PROMPT,
                mega_prompt=INSURANCE_MEGA_PROMPT
            )
            return answers[0] if answers else "No response generated."

        # Input Box
        user_query = st.chat_input("Ask a question about this policy...")
        if prompt_to_run:
            user_query = prompt_to_run

        with chat_container:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
            if user_query:
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(user_query)
                    
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing document structure & clauses..."):
                        try:
                            _, ext = os.path.splitext(st.session_state.current_doc_path)
                            if ext.lower() in [".xlsx", ".xls"]:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                answers = loop.run_until_complete(
                                    handle_excel(st.session_state.current_doc_path, [user_query], ApiKeyManager(), INSURANCE_MEGA_PROMPT)
                                )
                                answer = answers[0]
                            else:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                answer = loop.run_until_complete(
                                    execute_query(st.session_state.current_doc_path, user_query)
                                )
                        except Exception as e:
                            answer = f"**Error processing query:** {e}"
                        
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})

# --- TAB 2: DOCUMENT LIBRARY ---
with tab_documents:
    st.markdown("### Document Library")
    st.write("Manage and ingest new insurance policies into the intelligence platform.")
    
    doc_source = st.selectbox("Select Source Type", ["Local Upload", "Sample Policy", "Remote URL"])

    if doc_source == "Sample Policy":
        sample_path = os.path.abspath("sample_insurance_policy.pdf")
        if st.button("Load Star Health Shield (Sample)", type="primary"):
            st.session_state.current_doc_path = sample_path
            st.session_state.current_doc_name = "Star Health Shield Comprehensive Policy"
            st.success("Document active in workspace.")
            
    elif doc_source == "Local Upload":
        uploaded_file = st.file_uploader("Upload Policy Document", type=["pdf", "docx", "txt", "xlsx"])
        if uploaded_file:
            upload_dir = "uploaded_policies"
            os.makedirs(upload_dir, exist_ok=True)
            saved_file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(saved_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.current_doc_path = saved_file_path
            st.session_state.current_doc_name = uploaded_file.name
            st.success("Document uploaded and set as active context.")
            
    elif doc_source == "Remote URL":
        url_input = st.text_input("Document URL", placeholder="https://...")
        if st.button("Fetch Document", type="primary") and url_input.strip():
            st.session_state.current_doc_path = url_input.strip()
            st.session_state.current_doc_name = "Web Document"
            st.success("URL set as active context.")

# --- TAB 3: SYSTEM ARCHITECTURE ---
with tab_architecture:
    st.markdown("### System Metrics")
    col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
    
    if cuda_available:
        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        allocated_vram_gb = torch.cuda.memory_allocated(0) / (1024**3)
        
        col_metrics1.metric("Compute Engine", gpu_name)
        col_metrics2.metric("VRAM Utilized", f"{allocated_vram_gb:.2f} GB")
        col_metrics3.metric("VRAM Total", f"{total_vram_gb:.2f} GB")
    else:
        col_metrics1.metric("Compute Engine", "CPU")
        col_metrics2.metric("Status", "Standard")
        
    st.markdown("---")
    st.markdown("### Pipeline Configuration")
    st.code("""
    VECTOR_STORE = "ChromaDB"
    DISTANCE_METRIC = "Cosine Similarity"
    DENSE_EMBEDDING = "sentence-transformers/all-MiniLM-L6-v2"
    SPARSE_RETRIEVAL = "BM25Okapi"
    FUSION_STRATEGY = "Reciprocal Rank Fusion (RRF)"
    RERANKER = "BAAI/bge-reranker-base (Cross-Encoder)"
    GENERATOR = "Google Gemini 1.5"
    """, language="python")
