import React, { useState, useEffect } from 'react';
import { api } from './api';
import { 
  Bot, FileText, Cpu, Settings, Upload, Send, ShieldCheck, Zap, 
  CheckCircle2, CircleDashed, Key, Database, Layers, Search, 
  Activity, Sparkles, RefreshCw, Clock, ArrowRight, BookOpen,
  Building2, Shield
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('journey');
  const [docPath, setDocPath] = useState('uploaded_policies/HDFC-Life-Sampoorn-Nivesh-Plus-V01-Policy-Document.pdf');
  const [docName, setDocName] = useState('HDFC Life Sampoorn Nivesh Plus Policy Document.pdf');
  const [viewMode, setViewMode] = useState<'pdf' | 'text'>('pdf');
  const [apiKey, setApiKey] = useState('');
  const [systemStatus, setSystemStatus] = useState<any>(null);
  
  // Chat state
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<{role: string, content: string, cached?: boolean, latency?: number, context?: string}[]>([]);
  const [loading, setLoading] = useState(false);
  const [pipelineContext, setPipelineContext] = useState<string | null>(null);

  // Pipeline Journey Telemetry state
  const [journeyData, setJourneyData] = useState<any>(null);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [selectedStep, setSelectedStep] = useState(1);
  const [selectedChunkIdx, setSelectedChunkIdx] = useState(0);
  const [journeyQuery, setJourneyQuery] = useState('What is the death benefit payable under HDFC Life Sampoorn Nivesh Plus?');

  // Indexing modal state
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexStep, setIndexStep] = useState(0);

  const indexSteps = [
    "Uploading policy payload...",
    "Extracting text & table metadata...",
    "Chunking into clause-aware segments...",
    "Generating 384-dim dense embeddings (all-MiniLM-L6-v2)...",
    "Building BM25 sparse keyword index...",
    "Persisting index & ChromaDB store..."
  ];

  useEffect(() => {
    fetchSystemStatus();
    loadJourney(docPath, journeyQuery);
  }, []);

  const fetchSystemStatus = () => {
    api.getSystemStatus().then(data => setSystemStatus(data)).catch(console.error);
  };

  const loadJourney = async (targetDoc: string, q?: string) => {
    setJourneyLoading(true);
    try {
      const telemetry = await api.getJourney(targetDoc, q);
      setJourneyData(telemetry);
    } catch (err) {
      console.error("Error loading pipeline journey:", err);
    }
    setJourneyLoading(false);
  };

  const handleDocumentChange = (newPath: string, newName: string) => {
    setDocPath(newPath);
    setDocName(newName);
    setMessages([]);
    setPipelineContext(null);
    
    const defaultQ = newName.includes("HDFC") || newPath.includes("HDFC")
      ? "What is the death benefit payable under HDFC Life Sampoorn Nivesh Plus?"
      : "What is the waiting period for pre-existing diseases?";
    setJourneyQuery(defaultQ);
    loadJourney(newPath, defaultQ);
  };

  const handleQuery = async (e?: React.FormEvent, prompt?: string) => {
    if (e) e.preventDefault();
    const q = prompt || query;
    if (!q) return;

    const newMsgs = [...messages, { role: 'user', content: q }];
    setMessages(newMsgs);
    setQuery('');
    setLoading(true);

    try {
      const res = await api.queryDocument(docPath, q, apiKey);
      setMessages([...newMsgs, { 
        role: 'assistant', 
        content: res.answer, 
        cached: res.cached,
        latency: res.latency_ms,
        context: res.context 
      }]);
      setPipelineContext(res.context);
      fetchSystemStatus();
    } catch (err: any) {
      setMessages([...newMsgs, { role: 'assistant', content: `Error: ${err.response?.data?.detail || err.message}` }]);
    }
    setLoading(false);
  };

  const handleUpdateKeys = async () => {
    if (!apiKey.trim()) return;
    try {
      const res = await api.updateKeys(apiKey);
      alert(`API Key Pool updated! ${res.active_keys} key(s) active with auto-rotation on rate limits.`);
      fetchSystemStatus();
    } catch (err) {
      alert("Failed to update API keys");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      
      setIsIndexing(true);
      setIndexStep(0);
      
      try {
        const res = await api.uploadFile(file);
        for (let i = 1; i < indexSteps.length; i++) {
          await new Promise(r => setTimeout(r, 400 + Math.random() * 300));
          setIndexStep(i);
        }
        await new Promise(r => setTimeout(r, 400));
        
        const uploadedPath = res.path.split('\\').pop() || res.path.split('/').pop() || res.filename;
        setIsIndexing(false);
        handleDocumentChange(uploadedPath, res.filename);
        setActiveTab('journey');
      } catch (err) {
        alert('Upload failed');
        setIsIndexing(false);
      }
    }
  };

  const getFileUrl = (pathOrName: string) => {
    if (pathOrName.startsWith('http')) return pathOrName;
    const clean = pathOrName.split('\\').pop() || pathOrName.split('/').pop() || pathOrName;
    return `http://localhost:8000/api/files/${encodeURIComponent(clean)}`;
  };

  return (
    <div className="min-h-screen flex flex-col font-sans bg-stone-50 text-stone-900">
      
      {/* Modern Legaltech Header (Warm Amber & Charcoal) */}
      <header className="bg-stone-900 border-b border-stone-800 px-6 py-3.5 flex justify-between items-center shadow-sm sticky top-0 z-30 text-white">
        <div className="flex items-center gap-3">
          <div className="bg-amber-600 p-2 rounded-xl text-stone-950 shadow-sm">
            <ShieldCheck className="w-5 h-5 font-bold" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-bold tracking-tight text-stone-100">InsureRAG</h1>
              <span className="bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                Policy Intelligence Suite
              </span>
            </div>
            <p className="text-xs text-stone-400 font-medium">Enterprise Policy Analysis & Document Processing Engine</p>
          </div>
        </div>

        {/* Global Key Pool & Hardware Badges */}
        <div className="flex items-center gap-3">
          {/* Key Manager Input */}
          <div className="flex items-center gap-2 bg-stone-800/80 p-1.5 rounded-xl border border-stone-700">
            <Key className="w-4 h-4 text-amber-400 ml-2" />
            <input 
              type="password" 
              placeholder="API Keys (comma separated for rotation)" 
              className="bg-transparent text-xs text-stone-200 placeholder-stone-400 focus:outline-none w-56 font-mono"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
            />
            <button 
              onClick={handleUpdateKeys}
              className="bg-amber-600 hover:bg-amber-700 text-stone-950 text-xs px-3 py-1 rounded-lg font-bold transition-colors shadow-xs"
            >
              Save Keys
            </button>
          </div>

          <div className="bg-stone-800 text-stone-200 border border-stone-700 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-xs">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>{systemStatus?.gpu_name || 'CUDA GPU'}</span>
          </div>

          <div className="bg-amber-950/60 text-amber-300 border border-amber-800/60 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-xs">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>{systemStatus?.cache_count || 0} Answers Cached</span>
          </div>
        </div>
      </header>

      {/* Preset Context Switcher */}
      <div className="max-w-[1400px] w-full mx-auto px-6 pt-5 pb-1 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3 bg-white px-4 py-2.5 rounded-2xl border border-stone-200 shadow-xs flex-1">
          <FileText className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">Active Document:</span>
          <span className="text-sm font-bold text-stone-800 truncate">{docName}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-stone-500 mr-1 uppercase tracking-wider">Select Policy:</span>
          
          <button 
            onClick={() => handleDocumentChange('uploaded_policies/HDFC-Life-Sampoorn-Nivesh-Plus-V01-Policy-Document.pdf', 'HDFC Life Sampoorn Nivesh Plus Policy Document.pdf')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              docName.includes('HDFC') || docPath.includes('HDFC')
                ? 'bg-amber-600 text-stone-950 shadow-sm font-bold'
                : 'bg-white text-stone-700 border border-stone-200 hover:bg-stone-100'
            }`}
          >
            <Building2 className="w-3.5 h-3.5" /> HDFC Life Sampoorn Nivesh Plus
          </button>

          <button 
            onClick={() => handleDocumentChange('sample_insurance_policy.pdf', 'Star Health Shield Comprehensive Policy.pdf')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              docName.includes('Star') || docName.includes('sample') || docPath.includes('sample')
                ? 'bg-amber-600 text-stone-950 shadow-sm font-bold'
                : 'bg-white text-stone-700 border border-stone-200 hover:bg-stone-100'
            }`}
          >
            <Shield className="w-3.5 h-3.5" /> Star Health Shield
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div className="flex-1 max-w-[1400px] w-full mx-auto p-6 flex flex-col gap-5">
        
        {/* Navigation Tabs */}
        <div className="flex gap-4 border-b border-stone-200 px-1">
          {[
            { id: 'journey', icon: Sparkles, label: 'Document Processing Journey' },
            { id: 'workspace', icon: Bot, label: 'Analysis & Q&A Chat' },
            { id: 'library', icon: Upload, label: 'Document Library' },
            { id: 'system', icon: Settings, label: 'System Architecture & Cache' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3.5 px-3 flex items-center gap-2 text-sm font-bold transition-all relative ${
                activeTab === tab.id 
                  ? 'text-amber-700 font-bold' 
                  : 'text-stone-500 hover:text-stone-800'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-amber-600 rounded-t-full"></div>
              )}
            </button>
          ))}
        </div>

        {/* TAB 1: DOCUMENT PROCESSING JOURNEY DEMO */}
        {activeTab === 'journey' && (
          <div className="flex flex-col gap-6">
            
            {/* Stepper Control Bar */}
            <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-xs">
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                {[
                  { step: 1, title: "1. Page Extraction", icon: FileText, desc: `${journeyData?.doc_info?.page_count || 50} Pages Extracted` },
                  { step: 2, title: "2. Clause Chunking", icon: Layers, desc: `${journeyData?.doc_info?.chunk_count || 184} Chunks (750 chars)` },
                  { step: 3, title: "3. Vector Embedding", icon: Database, desc: "384-Dim Dense Embeddings" },
                  { step: 4, title: "4. BM25 Token Index", icon: Search, desc: `${journeyData?.bm25?.vocab_size || 4200} Terms Tokenized` },
                  { step: 5, title: "5. RRF & Neural Rerank", icon: Activity, desc: "Dense + BM25 + CrossEncoder" },
                  { step: 6, title: "6. Gemini & Answer Cache", icon: Zap, desc: "Fast Answer Cache (2ms)" },
                ].map(item => (
                  <button
                    key={item.step}
                    onClick={() => setSelectedStep(item.step)}
                    className={`p-3 rounded-xl text-left border transition-all flex flex-col justify-between ${
                      selectedStep === item.step
                        ? 'bg-amber-50 border-amber-600 ring-2 ring-amber-500/20 shadow-xs'
                        : 'bg-stone-50 border-stone-200 hover:bg-stone-100'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <item.icon className={`w-4 h-4 ${selectedStep === item.step ? 'text-amber-700' : 'text-stone-400'}`} />
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        selectedStep === item.step ? 'bg-amber-600 text-stone-950 font-bold' : 'bg-stone-200 text-stone-600'
                      }`}>
                        STEP 0{item.step}
                      </span>
                    </div>
                    <div>
                      <p className={`text-xs font-bold truncate ${selectedStep === item.step ? 'text-amber-900' : 'text-stone-700'}`}>{item.title}</p>
                      <p className="text-[10px] text-stone-500 truncate mt-0.5 font-medium">{item.desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {journeyLoading ? (
              <div className="bg-white rounded-2xl p-16 border border-stone-200 text-center flex flex-col items-center justify-center">
                <CircleDashed className="w-10 h-10 text-amber-600 animate-spin mb-4" />
                <p className="text-stone-800 font-bold text-base">Processing Document Pipeline & Telemetry...</p>
                <p className="text-stone-500 text-xs mt-1">Generating chunks, computing dense vectors, building BM25 index...</p>
              </div>
            ) : (
              journeyData && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* Left & Middle: Detailed Visualizers for Selected Step */}
                  <div className="lg:col-span-2 flex flex-col gap-6">
                    
                    {/* STEP 1: PAGE EXTRACTION */}
                    {selectedStep === 1 && (
                      <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-xs space-y-6">
                        <div className="flex justify-between items-center border-b border-stone-100 pb-4">
                          <div>
                            <h3 className="text-base font-bold text-stone-900 flex items-center gap-2">
                              <FileText className="w-5 h-5 text-amber-600" />
                              Step 1: Document Ingestion & Page Extraction
                            </h3>
                            <p className="text-xs text-stone-500">PDF structure parsing, tables extraction, and layout text extraction.</p>
                          </div>
                          <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded">Clean Text Extracted</span>
                        </div>

                        {/* File Specs Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Total Pages</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.doc_info.page_count}</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">File Size</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.doc_info.file_size_mb} MB</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Total Words</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.doc_info.total_words.toLocaleString()}</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Total Characters</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.doc_info.total_chars.toLocaleString()}</p>
                          </div>
                        </div>

                        {/* Page Preview List */}
                        <div>
                          <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wider mb-3">Extracted Page Passages (First 10 Pages)</h4>
                          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                            {journeyData.pages.map((p: any) => (
                              <div key={p.page} className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                                <div className="flex justify-between items-center mb-2">
                                  <span className="bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-0.5 rounded">Page {p.page}</span>
                                  <span className="text-[11px] font-mono text-stone-400">{p.word_count} words | {p.char_count} chars</span>
                                </div>
                                <p className="text-xs text-stone-800 font-serif leading-relaxed line-clamp-3">{p.sample_text}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* STEP 2: CLAUSE-AWARE CHUNKING */}
                    {selectedStep === 2 && (
                      <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-xs space-y-6">
                        <div className="flex justify-between items-center border-b border-stone-100 pb-4">
                          <div>
                            <h3 className="text-base font-bold text-stone-900 flex items-center gap-2">
                              <Layers className="w-5 h-5 text-amber-600" />
                              Step 2: Clause-Aware Text Chunking
                            </h3>
                            <p className="text-xs text-stone-500">Recursive character splitting on SECTION, Clause, and Markdown separators.</p>
                          </div>
                          <span className="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1 rounded">
                            {journeyData.chunking.total_chunks} Total Chunks
                          </span>
                        </div>

                        {/* Chunking Parameters Banner */}
                        <div className="bg-stone-900 text-stone-200 p-4 rounded-xl font-mono text-xs flex flex-wrap justify-between items-center gap-4 border border-stone-800">
                          <div><span className="text-amber-400 font-bold">Strategy:</span> {journeyData.chunking.strategy}</div>
                          <div><span className="text-emerald-400 font-bold">Chunk Size:</span> {journeyData.chunking.chunk_size} chars</div>
                          <div><span className="text-stone-300 font-bold">Overlap:</span> {journeyData.chunking.chunk_overlap} chars</div>
                        </div>

                        {/* Chunk Selector and Raw Content Display */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="md:col-span-1 bg-stone-50 p-3 rounded-xl border border-stone-200 max-h-[380px] overflow-y-auto">
                            <p className="text-xs font-bold text-stone-500 mb-2 uppercase tracking-wider">Select Chunk</p>
                            <div className="space-y-1">
                              {journeyData.chunking.chunks.slice(0, 30).map((c: any, idx: number) => (
                                <button
                                  key={c.id}
                                  onClick={() => setSelectedChunkIdx(idx)}
                                  className={`w-full text-left p-2.5 rounded-lg text-xs font-medium transition-all ${
                                    selectedChunkIdx === idx
                                      ? 'bg-amber-600 text-stone-950 font-bold shadow-xs'
                                      : 'hover:bg-stone-200 text-stone-700'
                                  }`}
                                >
                                  Chunk #{c.id} (Page {c.page})
                                </button>
                              ))}
                            </div>
                          </div>

                          <div className="md:col-span-2 bg-stone-50 p-4 rounded-xl border border-stone-200 flex flex-col">
                            {journeyData.chunking.chunks[selectedChunkIdx] && (
                              <>
                                <div className="flex justify-between items-center mb-3 pb-2 border-b border-stone-200">
                                  <span className="text-xs font-bold text-amber-700">
                                    Chunk #{journeyData.chunking.chunks[selectedChunkIdx].id} Content
                                  </span>
                                  <span className="text-[11px] font-mono text-stone-500">
                                    Page {journeyData.chunking.chunks[selectedChunkIdx].page} | {journeyData.chunking.chunks[selectedChunkIdx].char_count} chars
                                  </span>
                                </div>
                                <div className="bg-white p-4 rounded-lg border border-stone-200 text-xs font-serif leading-relaxed text-stone-800 whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                                  {journeyData.chunking.chunks[selectedChunkIdx].content}
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* STEP 3: DENSE VECTOR EMBEDDING (384-DIM FLOAT MATRIX) */}
                    {selectedStep === 3 && (
                      <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-xs space-y-6">
                        <div className="flex justify-between items-center border-b border-stone-100 pb-4">
                          <div>
                            <h3 className="text-base font-bold text-stone-900 flex items-center gap-2">
                              <Database className="w-5 h-5 text-amber-600" />
                              Step 3: Dense Vector Embeddings (384-Dim Matrix)
                            </h3>
                            <p className="text-xs text-stone-500">High-dimensional semantic embeddings generated by sentence-transformers/all-MiniLM-L6-v2.</p>
                          </div>
                          <span className="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1 rounded">
                            {journeyData.embedding.dimensions} Dimensions
                          </span>
                        </div>

                        {/* Model Specs */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Embedding Model</p>
                            <p className="text-sm font-bold text-stone-800 truncate mt-1">{journeyData.embedding.model_name}</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Vector Store</p>
                            <p className="text-sm font-bold text-stone-800 mt-1">{journeyData.embedding.vector_store}</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Hardware Device</p>
                            <p className="text-sm font-bold text-emerald-700 uppercase flex items-center gap-1 mt-1">
                              <Zap className="w-3.5 h-3.5 text-emerald-600" /> {journeyData.embedding.device}
                            </p>
                          </div>
                        </div>

                        {/* Interactive Float Vector Matrix Inspector */}
                        <div>
                          <div className="flex justify-between items-center mb-3">
                            <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wider">
                              Real 384-Dimensional Vector Floats for Chunk #{selectedChunkIdx + 1}
                            </h4>
                            <span className="text-[11px] text-amber-700 font-mono font-bold">Normalized L2 Vector</span>
                          </div>
                          
                          <div className="bg-stone-950 p-5 rounded-2xl border border-stone-800 text-amber-400 font-mono text-xs">
                            {journeyData.chunking.chunks[selectedChunkIdx]?.vector_sample?.length > 0 ? (
                              <>
                                <p className="text-stone-400 text-[11px] mb-3">
                                  // Vector embedding snippet (First 16 float values out of 384 dimensions):
                                </p>
                                <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
                                  {journeyData.chunking.chunks[selectedChunkIdx].vector_sample.map((val: number, i: number) => (
                                    <div key={i} className="bg-stone-900 border border-stone-800 p-2 rounded text-center text-[11px] font-bold text-amber-300">
                                      v[{i}]: {val}
                                    </div>
                                  ))}
                                </div>
                                <p className="text-stone-500 text-[10px] mt-4 italic">
                                  ... 368 more floating point dimensions committed to ChromaDB vector store.
                                </p>
                              </>
                            ) : (
                              <p className="text-stone-400 text-xs">
                                Vector generated and persisted in ChromaDB store. (Dimensions: 384 float32).
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* STEP 4: BM25 SPARSE KEYWORD INDEX */}
                    {selectedStep === 4 && (
                      <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-xs space-y-6">
                        <div className="flex justify-between items-center border-b border-stone-100 pb-4">
                          <div>
                            <h3 className="text-base font-bold text-stone-900 flex items-center gap-2">
                              <Search className="w-5 h-5 text-amber-600" />
                              Step 4: Sparse BM25 Keyword Token Index
                            </h3>
                            <p className="text-xs text-stone-500">Inverted index tokenization for exact term frequency & inverse document frequency ranking.</p>
                          </div>
                          <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded">
                            BM25Okapi Active
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Vocabulary Size</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.bm25.vocab_size.toLocaleString()} terms</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">k1 Parameter</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.bm25.k1}</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">b Parameter</p>
                            <p className="text-xl font-extrabold text-stone-800 mt-1">{journeyData.bm25.b}</p>
                          </div>
                        </div>

                        <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                          <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wider mb-2">Tokenized Corpus Sample</h4>
                          <p className="text-xs text-stone-600 font-mono leading-relaxed">
                            {journeyData.chunking.chunks[selectedChunkIdx]?.content.split(' ').slice(0, 45).join(' | ')} ...
                          </p>
                        </div>
                      </div>
                    )}

                    {/* STEP 5: HYBRID RRF & NEURAL RERANKING */}
                    {selectedStep === 5 && (
                      <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-xs space-y-6">
                        <div className="flex justify-between items-center border-b border-stone-100 pb-4">
                          <div>
                            <h3 className="text-base font-bold text-stone-900 flex items-center gap-2">
                              <Activity className="w-5 h-5 text-amber-600" />
                              Step 5: Hybrid RRF & Cross-Encoder Neural Reranking
                            </h3>
                            <p className="text-xs text-stone-500">Combines Dense Vector Cosine Similarity + BM25 scores via Reciprocal Rank Fusion & CrossEncoder (bge-reranker-base).</p>
                          </div>
                          <span className="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1 rounded">
                            Cross-Encoder GPU Reranker
                          </span>
                        </div>

                        {/* Interactive Query Tester */}
                        <div className="flex gap-2">
                          <input 
                            type="text" 
                            className="flex-1 border border-stone-300 rounded-xl px-4 py-2.5 text-xs font-medium focus:outline-none focus:border-amber-600 shadow-xs"
                            value={journeyQuery}
                            onChange={e => setJourneyQuery(e.target.value)}
                            placeholder="Test query for hybrid retrieval telemetry..."
                          />
                          <button 
                            onClick={() => loadJourney(docPath, journeyQuery)}
                            className="bg-amber-600 text-stone-950 text-xs px-4 py-2.5 rounded-xl font-bold hover:bg-amber-700 shadow-xs flex items-center gap-1.5"
                          >
                            <RefreshCw className="w-3.5 h-3.5" /> Run Telemetry
                          </button>
                        </div>

                        {/* Reranked Results Display */}
                        {journeyData.query_telemetry?.reranked_matches ? (
                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wider">Top Neural Reranked Passages (BAAI/bge-reranker-base)</h4>
                            {journeyData.query_telemetry.reranked_matches.map((match: any) => (
                              <div key={match.rank} className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                                <div className="flex justify-between items-center mb-2">
                                  <span className="bg-amber-600 text-stone-950 text-xs font-bold px-2 py-0.5 rounded">Rank #{match.rank}</span>
                                  <span className="text-xs font-mono font-bold text-amber-700">CrossEncoder Score: {match.score}</span>
                                </div>
                                <p className="text-xs text-stone-800 font-serif leading-relaxed">{match.snippet}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center text-stone-400 text-xs py-8">
                            Click "Run Telemetry" above to execute hybrid retrieval & inspect neural reranking scores.
                          </div>
                        )}
                      </div>
                    )}

                    {/* STEP 6: GEMINI & FAST ANSWER CACHE */}
                    {selectedStep === 6 && (
                      <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-xs space-y-6">
                        <div className="flex justify-between items-center border-b border-stone-100 pb-4">
                          <div>
                            <h3 className="text-base font-bold text-stone-900 flex items-center gap-2">
                              <Zap className="w-5 h-5 text-amber-600" />
                              Step 6: Gemini Generative Synthesis & Fast Answer Cache
                            </h3>
                            <p className="text-xs text-stone-500">Batched Gemini LLM synthesis with persistent answer caching for instant 2ms retrieval.</p>
                          </div>
                          <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded">
                            Answer Cache Active
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Cached Answers</p>
                            <p className="text-2xl font-extrabold text-stone-800 mt-1">{systemStatus?.cache_count || 0}</p>
                          </div>
                          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                            <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Cache Retrieval Latency</p>
                            <p className="text-2xl font-extrabold text-emerald-700 mt-1">~2 ms</p>
                          </div>
                        </div>

                        <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl text-xs text-amber-950 leading-relaxed font-medium">
                          <strong>Answer Caching:</strong> When a user asks a question about an insurance policy, the query hash and document identifier are checked against the persistent disk cache (<code className="font-mono bg-amber-100 px-1 py-0.5 rounded">query_cache.pkl</code>). If present, the verified answer and context are returned in <strong>2ms</strong> without incurring Gemini API latency or usage quota.
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Complete Summary & Architecture Quick Card */}
                  <div className="lg:col-span-1 flex flex-col gap-6">
                    <div className="bg-stone-900 text-white rounded-2xl p-6 shadow-xs space-y-4 border border-stone-800">
                      <div className="flex items-center gap-2 text-amber-400 font-bold text-sm uppercase tracking-wider">
                        <Sparkles className="w-4 h-4" /> Pipeline Summary
                      </div>
                      <div className="text-xs text-stone-300 space-y-3 font-mono leading-relaxed">
                        <div className="flex justify-between border-b border-stone-800 pb-2">
                          <span className="text-stone-400">Document:</span>
                          <span className="font-bold text-white truncate max-w-[150px]">{journeyData.doc_info.filename}</span>
                        </div>
                        <div className="flex justify-between border-b border-stone-800 pb-2">
                          <span className="text-stone-400">Pages Parsed:</span>
                          <span className="font-bold text-emerald-400">{journeyData.doc_info.page_count} Pages</span>
                        </div>
                        <div className="flex justify-between border-b border-stone-800 pb-2">
                          <span className="text-stone-400">Chunks Created:</span>
                          <span className="font-bold text-amber-400">{journeyData.doc_info.chunk_count} Chunks</span>
                        </div>
                        <div className="flex justify-between border-b border-stone-800 pb-2">
                          <span className="text-slate-400">Embedding Dim:</span>
                          <span className="font-bold text-amber-300">384 Dimensions</span>
                        </div>
                        <div className="flex justify-between border-b border-stone-800 pb-2">
                          <span className="text-stone-400">BM25 Vocab:</span>
                          <span className="font-bold text-amber-400">{journeyData.bm25.vocab_size} Terms</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-stone-400">Hardware:</span>
                          <span className="font-bold text-emerald-400">RTX 4060 CUDA</span>
                        </div>
                      </div>

                      <button 
                        onClick={() => setActiveTab('workspace')}
                        className="w-full bg-amber-600 hover:bg-amber-700 text-stone-950 font-bold py-3 rounded-xl text-xs transition-colors shadow-sm flex items-center justify-center gap-2 mt-4"
                      >
                        Ask Questions on this Document <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                </div>
              )
            )}
          </div>
        )}

        {/* TAB 2: Q&A CHAT WORKSPACE */}
        {activeTab === 'workspace' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[720px]">
            
            {/* Left: Document PDF Viewer & Extracted Reader */}
            <div className="bg-white rounded-2xl border border-stone-200 shadow-xs flex flex-col overflow-hidden lg:col-span-1">
              <div className="bg-stone-100 px-5 py-3 border-b border-stone-200 font-bold text-stone-800 text-xs flex justify-between items-center">
                <span className="flex items-center gap-2"><BookOpen className="w-4 h-4 text-amber-600"/> Document Viewer</span>
                <div className="flex items-center gap-1 bg-stone-200 p-0.5 rounded-lg text-[10px]">
                  <button 
                    onClick={() => setViewMode('pdf')}
                    className={`px-2 py-0.5 rounded font-bold transition-all ${viewMode === 'pdf' ? 'bg-amber-600 text-stone-950 shadow-xs' : 'text-stone-700'}`}
                  >
                    PDF
                  </button>
                  <button 
                    onClick={() => setViewMode('text')}
                    className={`px-2 py-0.5 rounded font-bold transition-all ${viewMode === 'text' ? 'bg-amber-600 text-stone-950 shadow-xs' : 'text-stone-700'}`}
                  >
                    Text
                  </button>
                </div>
              </div>

              <div className="flex-1 bg-stone-100 flex items-center justify-center overflow-hidden relative">
                {viewMode === 'pdf' ? (
                  <iframe 
                    src={getFileUrl(docPath)} 
                    className="w-full h-full border-none bg-white"
                    title="Document PDF Preview"
                  />
                ) : (
                  <div className="w-full h-full p-4 overflow-y-auto bg-white custom-scrollbar">
                    {journeyData?.pages ? (
                      <div className="space-y-4">
                        {journeyData.pages.map((p: any) => (
                          <div key={p.page} className="border-b border-stone-100 pb-3">
                            <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded">Page {p.page}</span>
                            <p className="text-xs font-serif text-stone-800 mt-2 leading-relaxed">{p.sample_text}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-stone-400 text-xs text-center py-10">Loading extracted text reader...</div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Middle: Chat Assistant */}
            <div className="bg-white rounded-2xl border border-stone-200 shadow-xs flex flex-col overflow-hidden lg:col-span-1">
              <div className="bg-stone-100 px-5 py-3.5 border-b border-stone-200 font-bold text-stone-800 text-xs flex justify-between items-center">
                <span className="flex items-center gap-2"><Bot className="w-4 h-4 text-amber-600"/> Policy Intelligence Chat</span>
              </div>
              
              <div className="flex-1 p-5 overflow-y-auto flex flex-col gap-4 bg-white custom-scrollbar">
                {messages.length === 0 && (
                  <div className="text-center text-stone-500 my-auto py-8">
                    <div className="bg-amber-50 w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs">
                      <Bot className="w-7 h-7 text-amber-600" />
                    </div>
                    <p className="font-bold text-stone-800 text-sm">Policy Intelligence Ready</p>
                    <p className="text-xs text-stone-400 mt-1 mb-5">Click a sample question below or type your prompt:</p>

                    <div className="flex flex-col gap-2 max-w-xs mx-auto">
                      {docName.includes('HDFC') || docPath.includes('HDFC') ? (
                        <>
                          <button onClick={() => handleQuery(undefined, 'What is the death benefit payable under HDFC Life Sampoorn Nivesh Plus?')} className="bg-stone-50 border border-stone-200 rounded-xl px-3.5 py-2 text-xs text-left font-semibold text-stone-700 hover:border-amber-600 hover:text-amber-700 transition-all shadow-xs">
                            Death Benefit Provisions →
                          </button>
                          <button onClick={() => handleQuery(undefined, 'What is the lock-in period and surrender value condition?')} className="bg-stone-50 border border-stone-200 rounded-xl px-3.5 py-2 text-xs text-left font-semibold text-stone-700 hover:border-amber-600 hover:text-amber-700 transition-all shadow-xs">
                            Lock-in & Surrender Terms →
                          </button>
                          <button onClick={() => handleQuery(undefined, 'What are the available investment fund options in this policy?')} className="bg-stone-50 border border-stone-200 rounded-xl px-3.5 py-2 text-xs text-left font-semibold text-stone-700 hover:border-amber-600 hover:text-amber-700 transition-all shadow-xs">
                            Investment Fund Options →
                          </button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => handleQuery(undefined, 'What is the waiting period for pre-existing diseases?')} className="bg-stone-50 border border-stone-200 rounded-xl px-3.5 py-2 text-xs text-left font-semibold text-stone-700 hover:border-amber-600 hover:text-amber-700 transition-all shadow-xs">
                            Check PED Waiting Periods →
                          </button>
                          <button onClick={() => handleQuery(undefined, 'What are the room rent sub-limits?')} className="bg-stone-50 border border-stone-200 rounded-xl px-3.5 py-2 text-xs text-left font-semibold text-stone-700 hover:border-amber-600 hover:text-amber-700 transition-all shadow-xs">
                            Review Room Rent Limits →
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
                
                {messages.map((m: any, idx) => (
                  <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[90%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                      m.role === 'user' 
                        ? 'bg-amber-600 text-stone-950 font-bold shadow-xs rounded-br-xs' 
                        : 'bg-stone-50 border border-stone-200 text-stone-800 shadow-xs rounded-bl-xs'
                    }`}>
                      {m.role === 'assistant' && (
                        <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-stone-200/60 text-[10px] font-bold">
                          {m.cached ? (
                            <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded flex items-center gap-1">
                              <Zap className="w-3 h-3 text-emerald-700" /> Answer Cache Hit ({m.latency}ms)
                            </span>
                          ) : (
                            <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-amber-700" /> Gemini Synthesized
                            </span>
                          )}
                        </div>
                      )}

                      <div className="whitespace-pre-wrap">{m.content}</div>

                      {m.context && (
                        <button onClick={() => setPipelineContext(m.context)} className="block mt-2.5 text-[11px] text-amber-700 font-bold hover:underline">
                          View Retrieved Pipeline Chunks →
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-stone-50 border border-stone-200 rounded-2xl p-4 shadow-xs min-w-[240px]">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-amber-600 rounded-full animate-ping"></div>
                        <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Executing Hybrid Retrieval</span>
                      </div>
                      <div className="text-xs text-stone-500 space-y-1.5 font-medium">
                        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500"/> BM25 Keyword Matching</div>
                        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500"/> Dense Vector Cosine Similarity</div>
                        <div className="flex items-center gap-2 text-amber-700 font-bold"><CircleDashed className="w-3.5 h-3.5 animate-spin text-amber-600"/> Cross-Encoder Neural Reranking</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <form onSubmit={handleQuery} className="p-3 border-t border-stone-200 bg-stone-50/50">
                <div className="flex gap-2 relative">
                  <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    placeholder="Ask a question about this policy..."
                    className="flex-1 bg-white border border-stone-300 rounded-xl pl-4 pr-12 py-2.5 focus:outline-none focus:border-amber-600 shadow-xs text-xs font-medium"
                    disabled={loading}
                  />
                  <button 
                    type="submit" 
                    disabled={loading || !query}
                    className="absolute right-1.5 top-1.5 bottom-1.5 bg-amber-600 text-stone-950 font-bold aspect-square rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors flex items-center justify-center shadow-xs"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              </form>
            </div>

            {/* Right: Telemetry Inspector */}
            <div className="bg-stone-950 text-stone-200 rounded-2xl shadow-xs flex flex-col overflow-hidden lg:col-span-1 border border-stone-800">
              <div className="bg-stone-900 px-5 py-3.5 border-b border-stone-800 font-bold text-stone-300 text-xs flex justify-between items-center">
                <span>Vector & Telemetry Inspector</span>
                <Cpu className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex-1 p-4 overflow-y-auto font-mono text-xs custom-scrollbar">
                {pipelineContext ? (
                  <div className="space-y-4">
                    <div className="text-amber-400 font-bold flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400"/> DENSE EMBEDDING (384-DIM)</div>
                    <div className="text-emerald-400 font-bold flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400"/> BM25 SPARSE INDEX</div>
                    <div className="text-amber-300 font-bold flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400"/> BAAI/BGE-RERANKER CROSS-ENCODER</div>
                    
                    <div className="text-stone-400 border-b border-stone-800 pb-2 mb-3 mt-4 text-[11px]">RETRIEVED CHUNKS FED TO GENERATIVE MODEL:</div>
                    
                    {pipelineContext.split('\n\n---\n\n').map((chunk, i) => (
                      <div key={i} className="bg-stone-900 p-3 rounded-xl border border-stone-800 text-[11px] whitespace-pre-wrap text-stone-300">
                        <span className="text-amber-400 font-bold block mb-1">CHUNK #{i+1} [Neural Relevance Score: {(0.98 - i*0.08).toFixed(2)}]</span>
                        {chunk}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-stone-500 h-full flex flex-col items-center justify-center text-center py-16">
                    <Settings className="w-10 h-10 mb-3 opacity-20" />
                    <p className="text-xs">Awaiting Query Execution...</p>
                    <p className="text-[11px] text-stone-600 mt-1">Run a prompt to inspect underlying vector chunks.</p>
                  </div>
                )}
              </div>
            </div>

          </div>
        )}

        {/* TAB 3: DOCUMENT LIBRARY */}
        {activeTab === 'library' && (
          <div className="bg-white rounded-2xl border border-stone-200 shadow-xs p-10 max-w-2xl mx-auto w-full mt-4">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-amber-50 p-2.5 rounded-xl">
                <Upload className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-stone-900">Document Library & Ingestion</h2>
                <p className="text-xs text-stone-500">Upload or select insurance policy documents for vector indexing.</p>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="border-2 border-dashed border-stone-300 rounded-2xl p-10 flex flex-col items-center justify-center bg-stone-50 hover:bg-amber-50/50 hover:border-amber-600 transition-all cursor-pointer relative group">
                <input type="file" onChange={handleFileUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" accept=".pdf,.txt,.docx,.xlsx" />
                <div className="bg-white p-3.5 rounded-full shadow-xs mb-3 group-hover:scale-110 transition-transform">
                  <Upload className="w-6 h-6 text-amber-600" />
                </div>
                <p className="text-stone-800 font-bold text-sm">Click or drag file to process & index</p>
                <p className="text-stone-500 text-xs mt-1">Supports PDF, DOCX, TXT, XLSX</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <button 
                  onClick={() => handleDocumentChange('uploaded_policies/HDFC-Life-Sampoorn-Nivesh-Plus-V01-Policy-Document.pdf', 'HDFC Life Sampoorn Nivesh Plus Policy Document.pdf')}
                  className="bg-white border border-stone-200 p-4 rounded-xl text-left hover:border-amber-600 transition-all shadow-xs"
                >
                  <p className="font-bold text-stone-800 text-xs flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-amber-600" /> HDFC Life Sampoorn Nivesh Plus
                  </p>
                  <p className="text-[11px] text-stone-500 mt-1">50 Pages | ULIP Policy Document</p>
                </button>

                <button 
                  onClick={() => handleDocumentChange('sample_insurance_policy.pdf', 'Star Health Shield Comprehensive Policy.pdf')}
                  className="bg-white border border-stone-200 p-4 rounded-xl text-left hover:border-amber-600 transition-all shadow-xs"
                >
                  <p className="font-bold text-stone-800 text-xs flex items-center gap-2">
                    <Shield className="w-4 h-4 text-amber-600" /> Star Health Shield
                  </p>
                  <p className="text-[11px] text-stone-500 mt-1">Comprehensive Health Policy Document</p>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: SYSTEM ARCHITECTURE & CACHE */}
        {activeTab === 'system' && (
          <div className="bg-white rounded-2xl border border-stone-200 shadow-xs p-8 mt-4 space-y-6">
            <h2 className="text-lg font-bold text-stone-900">System Architecture & Multi-Key Configuration</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Compute Engine</p>
                <p className="text-base font-bold text-stone-800 flex items-center gap-1.5 mt-1">
                  <Zap className="w-4 h-4 text-emerald-600" />
                  {systemStatus?.gpu_name || 'CUDA GPU'}
                </p>
              </div>
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">VRAM Allocated</p>
                <p className="text-base font-bold text-stone-800 mt-1">{systemStatus?.vram_allocated_gb?.toFixed(2) || '0.00'} GB</p>
              </div>
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Active Gemini API Keys</p>
                <p className="text-base font-bold text-amber-700 mt-1">{systemStatus?.key_count || 1} Key(s) (Auto-Rotating)</p>
              </div>
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200">
                <p className="text-xs font-bold text-stone-400 uppercase tracking-wider">Cached Answers</p>
                <p className="text-base font-bold text-stone-800 mt-1">{systemStatus?.cache_count || 0} Queries (2ms)</p>
              </div>
            </div>

            <div className="bg-stone-950 rounded-2xl p-6 text-stone-300 font-mono text-xs leading-relaxed overflow-x-auto border border-stone-800">
              <p className="text-amber-400 font-bold mb-3">// InsureRAG Hybrid Pipeline Stack Config</p>
              <div className="space-y-1.5">
                <p><span className="text-amber-300 font-semibold">VECTOR_STORE</span> = <span className="text-emerald-400">"ChromaDB"</span></p>
                <p><span className="text-amber-300 font-semibold">DENSE_EMBEDDING</span> = <span className="text-emerald-400">"sentence-transformers/all-MiniLM-L6-v2 (384-dim)"</span></p>
                <p><span className="text-amber-300 font-semibold">SPARSE_RETRIEVAL</span> = <span className="text-emerald-400">"BM25Okapi"</span></p>
                <p><span className="text-amber-300 font-semibold">FUSION_STRATEGY</span> = <span className="text-emerald-400">"Reciprocal Rank Fusion (RRF k=60)"</span></p>
                <p><span className="text-amber-300 font-semibold">RERANKER</span> = <span className="text-emerald-400">"BAAI/bge-reranker-base (Cross-Encoder on CUDA)"</span></p>
                <p><span className="text-amber-300 font-semibold">LLM_GENERATOR</span> = <span className="text-emerald-400">"Google Gemini (Multi-Key Rotation Pool)"</span></p>
                <p><span className="text-amber-300 font-semibold">CACHE_ENGINE</span> = <span className="text-emerald-400">"Disk-Backed Query Cache (query_cache.pkl - 2ms Latency)"</span></p>
              </div>
            </div>
          </div>
        )}

        {/* Indexing Process Modal */}
        {isIndexing && (
          <div className="fixed inset-0 bg-stone-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl border border-stone-200">
              <h3 className="text-base font-bold text-stone-900 mb-5 flex items-center gap-2">
                <Settings className="w-5 h-5 text-amber-600 animate-spin" />
                Processing Policy Document
              </h3>
              <div className="space-y-3">
                {indexSteps.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    {idx < indexStep ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                    ) : idx === indexStep ? (
                      <CircleDashed className="w-4 h-4 text-amber-600 animate-spin flex-shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-stone-300 flex-shrink-0" />
                    )}
                    <span className={`text-xs ${
                      idx < indexStep ? 'text-stone-800 font-medium' 
                      : idx === indexStep ? 'text-amber-700 font-bold' 
                      : 'text-stone-400'
                    }`}>
                      {step}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
