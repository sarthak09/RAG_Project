import React, { useState, useContext, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import loginContext from '../context/context'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const BasicRag = () => {
    const value = useContext(loginContext)
    const navigate = useNavigate()
    const [uploadedFile, setUploadedFile] = useState(null)
    const [chunkingMethod, setChunkingMethod] = useState('standard')
    const [useHybridSearch, setUseHybridSearch] = useState(false)
    const [useReranker, setUseReranker] = useState(false)
    const [queryEnhancementMode, setQueryEnhancementMode] = useState('normal')
    const [processingStatus, setProcessingStatus] = useState('not_started') // not_started, processing, ready
    const [question, setQuestion] = useState('')
    const [conversation, setConversation] = useState([])
    const [loading, setLoading] = useState(true)
    const [querying, setQuerying] = useState(false)

    useEffect(() => {
        checkFileAndStatus()
    }, [])

    const checkFileAndStatus = async () => {
        try {
            const token = localStorage.getItem('token')
            
            // Check if file exists
            const fileResponse = await fetch(`${API_BASE_URL}/files`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            const fileData = await fileResponse.json()
            
            if (!fileData.files || fileData.files.length === 0) {
                setLoading(false)
                return
            }
            
            setUploadedFile(fileData.files[0])
            
            // Check processing status
            const statusResponse = await fetch(`${API_BASE_URL}/rag-status`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            const statusData = await statusResponse.json()
            
            if (statusData.status) {
                setProcessingStatus(statusData.status)
                if (statusData.chunking_method) {
                    setChunkingMethod(statusData.chunking_method)
                }
                if (statusData.hybrid_search !== undefined) {
                    setUseHybridSearch(statusData.hybrid_search)
                }
                if (statusData.use_reranker !== undefined) {
                    setUseReranker(statusData.use_reranker)
                }
                if (statusData.query_enhancement_mode) {
                    setQueryEnhancementMode(statusData.query_enhancement_mode)
                }
            }
        } catch (error) {
            console.error('Error checking file and status:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleStartProcessing = async () => {
        setProcessingStatus('processing')
        
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_BASE_URL}/process-document`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    chunking_method: chunkingMethod,
                    hybrid_search: useHybridSearch,
                    use_reranker: useReranker,
                    query_enhancement_mode: queryEnhancementMode
                })
            })
            
            const data = await response.json()
            
            if (data.success) {
                // Poll for status updates
                pollProcessingStatus()
            } else {
                alert(data.error || 'Processing failed')
                setProcessingStatus('not_started')
            }
        } catch (error) {
            alert('Error starting processing')
            setProcessingStatus('not_started')
        }
    }

    const pollProcessingStatus = async () => {
        const token = localStorage.getItem('token')
        
        const poll = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/rag-status`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })
                const data = await response.json()
                
                if (data.status === 'ready') {
                    setProcessingStatus('ready')
                } else if (data.status === 'processing') {
                    setTimeout(poll, 2000) // Poll every 2 seconds
                } else {
                    setProcessingStatus('not_started')
                }
            } catch (error) {
                console.error('Error polling status:', error)
                setTimeout(poll, 2000)
            }
        }
        
        poll()
    }

    const handleQuerySubmit = async (e) => {
        e.preventDefault()
        if (!question.trim()) return
        
        const currentQuestion = question
        setQuestion('')
        setQuerying(true)
        
        // Add question to conversation
        setConversation(prev => [...prev, {
            type: 'question',
            content: currentQuestion,
            timestamp: new Date().toLocaleTimeString()
        }])
        
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_BASE_URL}/query`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: currentQuestion,
                    query_enhancement_mode: queryEnhancementMode
                })
            })
            
            const data = await response.json()
            
            if (data.success) {
                // Add enhanced query if different from original
                if (data.enhanced_query && data.enhanced_query !== currentQuestion) {
                    setConversation(prev => [...prev, {
                        type: 'enhanced_query',
                        content: data.enhanced_query,
                        mode: data.query_enhancement_mode,
                        timestamp: new Date().toLocaleTimeString()
                    }])
                }
                
                setConversation(prev => [...prev, {
                    type: 'answer',
                    content: data.answer,
                    context: data.context,
                    timestamp: new Date().toLocaleTimeString()
                }])
            } else {
                setConversation(prev => [...prev, {
                    type: 'error',
                    content: data.error || 'Failed to get answer',
                    timestamp: new Date().toLocaleTimeString()
                }])
            }
        } catch (error) {
            setConversation(prev => [...prev, {
                type: 'error',
                content: 'Error processing your question',
                timestamp: new Date().toLocaleTimeString()
            }])
        } finally {
            setQuerying(false)
        }
    }

    const clearConversation = () => {
        setConversation([])
    }

    if (loading) {
        return (
            <div className="container mt-4">
                <div className="text-center">
                    <div className="spinner-border" role="status"></div>
                    <p>Loading...</p>
                </div>
            </div>
        )
    }

    if (!uploadedFile) {
        return (
            <div className="container mt-4">
                <div className="alert alert-warning">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    No PDF uploaded. Please <Link to="/">upload a file</Link> first.
                </div>
            </div>
        )
    }

    return (
        <div className="container mt-4">
            <div className="row">
                <div className="col-12">
                    <h2>Basic RAG System</h2>
                    <p className="text-muted">Ask questions about your uploaded PDF document</p>
                </div>
            </div>

            {uploadedFile && (
                <div className="row mt-4">
                    <div className="col-lg-8">
                        {/* Processing Section */}
                        <div className="card shadow-sm mb-4">
                            <div className="card-header bg-info text-white">
                                <h5 className="mb-0">
                                    <i className="bi bi-gear me-2"></i>
                                    Document Processing
                                </h5>
                            </div>
                            <div className="card-body">
                                <div className="mb-3">
                                    <p><strong>Document:</strong> {uploadedFile.name}</p>
                                    <p><strong>Size:</strong> {uploadedFile.size}</p>
                                </div>

                                {processingStatus === 'not_started' && (
                                    <div>
                                        <div className="mb-3">
                                            <label className="form-label">Choose Chunking Method:</label>
                                            <div className="form-check">
                                                <input 
                                                    className="form-check-input" 
                                                    type="radio" 
                                                    name="chunkingMethod" 
                                                    id="standard"
                                                    value="standard"
                                                    checked={chunkingMethod === 'standard'}
                                                    onChange={(e) => setChunkingMethod(e.target.value)}
                                                />
                                                <label className="form-check-label" htmlFor="standard">
                                                    <strong>Standard Chunking</strong>
                                                    <small className="d-block text-muted">
                                                        Fixed-size text chunks with overlap. Fast and reliable.
                                                    </small>
                                                </label>
                                            </div>
                                            <div className="form-check">
                                                <input 
                                                    className="form-check-input" 
                                                    type="radio" 
                                                    name="chunkingMethod" 
                                                    id="semantic"
                                                    value="semantic"
                                                    checked={chunkingMethod === 'semantic'}
                                                    onChange={(e) => setChunkingMethod(e.target.value)}
                                                />
                                                <label className="form-check-label" htmlFor="semantic">
                                                    <strong>Semantic Chunking</strong>
                                                    <small className="d-block text-muted">
                                                        Context-aware chunks based on meaning. Better quality but slower.
                                                    </small>
                                                </label>
                                            </div>
                                        </div>
                                        
                                        <div className="mb-3">
                                            <label className="form-label">Advanced Options:</label>
                                            <div className="form-check form-switch mb-2">
                                                <input 
                                                    className="form-check-input" 
                                                    type="checkbox" 
                                                    role="switch"
                                                    id="hybridSearch"
                                                    checked={useHybridSearch}
                                                    onChange={(e) => setUseHybridSearch(e.target.checked)}
                                                />
                                                <label className="form-check-label" htmlFor="hybridSearch">
                                                    <strong>Enable Hybrid Search (Dense + BM25)</strong>
                                                    <small className="d-block text-muted">
                                                        {useHybridSearch ? 
                                                            "Uses both semantic embeddings (70%) and BM25 keyword matching (30%) for better retrieval quality." :
                                                            "Uses only semantic embeddings for retrieval. Enable for hybrid dense + sparse search."
                                                        }
                                                    </small>
                                                </label>
                                            </div>
                                            <div className="form-check form-switch">
                                                <input 
                                                    className="form-check-input" 
                                                    type="checkbox" 
                                                    role="switch"
                                                    id="useReranker"
                                                    checked={useReranker}
                                                    onChange={(e) => setUseReranker(e.target.checked)}
                                                />
                                                <label className="form-check-label" htmlFor="useReranker">
                                                    <strong>Enable Reranking (Cross-Encoder)</strong>
                                                    <small className="d-block text-muted">
                                                        {useReranker ? 
                                                            "Reranks retrieved documents using cross-encoder model for improved relevance scoring." :
                                                            "Uses standard retrieval ranking. Enable for enhanced document relevance through reranking."
                                                        }
                                                    </small>
                                                </label>
                                            </div>
                                        </div>
                                        
                                        <div className="mb-3">
                                            <label className="form-label">Query Enhancement:</label>
                                            <div className="form-check">
                                                <input 
                                                    className="form-check-input" 
                                                    type="radio" 
                                                    name="queryEnhancement" 
                                                    id="queryNormal"
                                                    value="normal"
                                                    checked={queryEnhancementMode === 'normal'}
                                                    onChange={(e) => setQueryEnhancementMode(e.target.value)}
                                                />
                                                <label className="form-check-label" htmlFor="queryNormal">
                                                    <strong>Normal Mode</strong>
                                                    <small className="d-block text-muted">
                                                        Use original query as-is without modification
                                                    </small>
                                                </label>
                                            </div>
                                            <div className="form-check">
                                                <input 
                                                    className="form-check-input" 
                                                    type="radio" 
                                                    name="queryEnhancement" 
                                                    id="queryExpansion"
                                                    value="expansion"
                                                    checked={queryEnhancementMode === 'expansion'}
                                                    onChange={(e) => setQueryEnhancementMode(e.target.value)}
                                                />
                                                <label className="form-check-label" htmlFor="queryExpansion">
                                                    <strong>Query Expansion</strong>
                                                    <small className="d-block text-muted">
                                                        Expands query with synonyms, technical terms, and context for better retrieval
                                                    </small>
                                                </label>
                                            </div>
                                            <div className="form-check">
                                                <input 
                                                    className="form-check-input" 
                                                    type="radio" 
                                                    name="queryEnhancement" 
                                                    id="queryDecomposition"
                                                    value="decomposition"
                                                    checked={queryEnhancementMode === 'decomposition'}
                                                    onChange={(e) => setQueryEnhancementMode(e.target.value)}
                                                />
                                                <label className="form-check-label" htmlFor="queryDecomposition">
                                                    <strong>Query Decomposition</strong>
                                                    <small className="d-block text-muted">
                                                        Breaks down complex questions into sub-questions for comprehensive retrieval
                                                    </small>
                                                </label>
                                            </div>
                                        </div>
                                        <button 
                                            className="btn btn-primary"
                                            onClick={handleStartProcessing}
                                        >
                                            <i className="bi bi-play-circle me-2"></i>
                                            Start Processing
                                        </button>
                                    </div>
                                )}

                                {processingStatus === 'processing' && (
                                    <div className="text-center">
                                        <div className="spinner-border text-primary me-3" role="status"></div>
                                        <p className="mb-0">
                                            Processing your document with <strong>{chunkingMethod}</strong> chunking
                                            {useHybridSearch && <span>, <strong>hybrid search</strong> (Dense + BM25)</span>}
                                            {useReranker && <span>, <strong>reranking</strong></span>}
                                            {queryEnhancementMode !== 'normal' && <span>, <strong>{queryEnhancementMode === 'expansion' ? 'query expansion' : 'query decomposition'}</strong></span>}...
                                        </p>
                                        <small className="text-muted">This may take a few moments</small>
                                    </div>
                                )}

                                {processingStatus === 'ready' && (
                                    <div className="alert alert-success">
                                        <i className="bi bi-check-circle-fill me-2"></i>
                                        Document processed successfully with <strong>{chunkingMethod}</strong> chunking
                                        {useHybridSearch && <span>, <strong>hybrid search</strong> enabled</span>}
                                        {useReranker && <span>, <strong>reranking</strong> enabled</span>}
                                        {queryEnhancementMode !== 'normal' && <span>, <strong>{queryEnhancementMode === 'expansion' ? 'query expansion' : 'query decomposition'}</strong> enabled</span>}! 
                                        You can now start asking questions.
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Query Section */}
                        {processingStatus === 'ready' && (
                            <div className="card shadow-sm">
                                <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
                                    <h5 className="mb-0">
                                        <i className="bi bi-chat-dots me-2"></i>
                                        Ask Questions
                                    </h5>
                                    {conversation.length > 0 && (
                                        <button 
                                            className="btn btn-sm btn-outline-light"
                                            onClick={clearConversation}
                                        >
                                            Clear History
                                        </button>
                                    )}
                                </div>
                                <div className="card-body">
                                    {/* Conversation History */}
                                    {conversation.length > 0 && (
                                        <div className="mb-4" style={{maxHeight: '400px', overflowY: 'auto'}}>
                                            {conversation.map((item, index) => (
                                                <div key={index} className={`mb-3 p-3 rounded ${
                                                    item.type === 'question' ? 'bg-light' : 
                                                    item.type === 'enhanced_query' ? 'bg-info bg-opacity-10 border border-info' :
                                                    item.type === 'error' ? 'bg-danger bg-opacity-10' : 
                                                    'bg-success bg-opacity-10'
                                                }`}>
                                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                                        <strong>
                                                            {item.type === 'question' ? 'You' : 
                                                             item.type === 'enhanced_query' ? (
                                                                <span>
                                                                    <i className="bi bi-magic me-1"></i>
                                                                    Enhanced Query 
                                                                    <span className="badge bg-info ms-2">
                                                                        {item.mode === 'expansion' ? 'Expanded' : 'Decomposed'}
                                                                    </span>
                                                                </span>
                                                             ) :
                                                             item.type === 'error' ? 'Error' : 'AI Assistant'}
                                                        </strong>
                                                        <small className="text-muted">{item.timestamp}</small>
                                                    </div>
                                                    <div style={{
                                                        whiteSpace: 'pre-wrap',
                                                        fontStyle: item.type === 'enhanced_query' ? 'italic' : 'normal'
                                                    }}>
                                                        {item.content}
                                                    </div>
                                                    {item.context && (
                                                        <div className="mt-2">
                                                            <small className="text-muted">
                                                                <strong>Sources:</strong> Relevant content from your document
                                                            </small>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Query Input */}
                                    <form onSubmit={handleQuerySubmit}>
                                        <div className="input-group">
                                            <input 
                                                type="text"
                                                className="form-control"
                                                placeholder="Ask a question about your document..."
                                                value={question}
                                                onChange={(e) => setQuestion(e.target.value)}
                                                disabled={querying}
                                            />
                                            <button 
                                                className="btn btn-primary" 
                                                type="submit"
                                                disabled={querying || !question.trim()}
                                            >
                                                {querying ? (
                                                    <>
                                                        <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                                                        Asking...
                                                    </>
                                                ) : (
                                                    <>
                                                        <i className="bi bi-send me-2"></i>
                                                        Ask
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Sidebar */}
                    <div className="col-lg-4">
                        <div className="card shadow-sm">
                            <div className="card-body">
                                <h6 className="card-title">How to Use</h6>
                                <ol className="small">
                                    <li className="mb-2">Choose your preferred chunking method</li>
                                    <li className="mb-2">Toggle hybrid search for BM25 + Dense retrieval</li>
                                    <li className="mb-2">Click "Start Processing" to prepare your document</li>
                                    <li className="mb-2">Wait for processing to complete</li>
                                    <li className="mb-2">Ask questions about your document</li>
                                </ol>
                                
                                <hr />
                                
                                <h6 className="card-title">Sample Questions</h6>
                                <ul className="small">
                                    <li className="mb-1">What is the main topic of this document?</li>
                                    <li className="mb-1">Can you summarize the key points?</li>
                                    <li className="mb-1">What does it say about [specific topic]?</li>
                                    <li className="mb-1">Are there any recommendations mentioned?</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default BasicRag