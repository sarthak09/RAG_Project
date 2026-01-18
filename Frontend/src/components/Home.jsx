import { useState, useContext, useEffect } from 'react'
import loginContext from '../context/context'
import { Link } from 'react-router-dom'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const Home = () => {
    const value = useContext(loginContext)
    const [daysRemaining, setDaysRemaining] = useState(0)
    const [uploadedFile, setUploadedFile] = useState(null)
    const [uploading, setUploading] = useState(false)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (value.logininfo.trial_end_date) {
            const trialEnd = new Date(value.logininfo.trial_end_date)
            const now = new Date()
            const diff = Math.ceil((trialEnd - now) / (1000 * 60 * 60 * 24))
            setDaysRemaining(diff > 0 ? diff : 0)
        }
    }, [value.logininfo.trial_end_date])

    useEffect(() => {
        fetchUploadedFile()
    }, [])

    const fetchUploadedFile = async () => {
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_BASE_URL}/files`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            const data = await response.json()
            if (data.files && data.files.length > 0) {
                setUploadedFile(data.files[0])
            } else {
                setUploadedFile(null)
            }
        } catch (error) {
            console.error('Error fetching file:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleFileUpload = async (e) => {
        const file = e.target.files[0]

        if (!file) return

        if (file.type !== 'application/pdf') {
            alert('Please upload only PDF files')
            return
        }

        setUploading(true)
        const formData = new FormData()
        formData.append('files', file)

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            })

            let data;
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                data = await response.json();
            } else {
                // Handle non-JSON response (e.g., 413 from Flask/Nginx returning HTML)
                if (response.status === 413) {
                    throw new Error("File is too large. Max size is 50MB.");
                }
                throw new Error(`Upload failed with status: ${response.status}`);
            }

            if (response.ok && data.success) {
                fetchUploadedFile()
                e.target.value = ''
            } else {
                alert(data.error || "Upload failed")
            }
        } catch (error) {
            console.error(error)
            alert(error.message || 'Upload failed')
        } finally {
            setUploading(false)
        }
    }

    const handleDeleteFile = async () => {
        if (!uploadedFile || !confirm(`Delete ${uploadedFile.name}?`)) return

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_BASE_URL}/files/${uploadedFile.name}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            const data = await response.json()

            if (data.success) {
                fetchUploadedFile()
            } else {
                alert(data.error)
            }
        } catch (error) {
            alert('Delete failed')
        }
    }

    return (
        <div className="container mt-4">
            <div className="row">
                <div className="col-12">
                    <h2>Welcome, {value.logininfo.name}!</h2>
                    <p className="text-muted">Upload your PDF to start using RAG capabilities</p>
                </div>
            </div>

            {value.logininfo.trial_active ? (
                <div className="alert alert-info" role="alert">
                    <i className="bi bi-clock me-2"></i>
                    <strong>{daysRemaining} days</strong> remaining in your trial period
                </div>
            ) : (
                <div className="alert alert-warning" role="alert">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    Your trial has expired. Please upgrade to continue.
                </div>
            )}

            {value.logininfo.trial_active && (
                <div className="row mt-4">
                    <div className="col-lg-8">
                        <div className="card shadow-sm">
                            <div className="card-header bg-primary text-white">
                                <h5 className="mb-0">
                                    <i className="bi bi-file-earmark-pdf me-2"></i>
                                    PDF Document {uploadedFile ? '(1/1)' : '(0/1)'}
                                </h5>
                            </div>
                            <div className="card-body">
                                {!uploadedFile && (
                                    <div className="mb-4">
                                        <label htmlFor="fileUpload" className="form-label">
                                            Upload PDF File
                                        </label>
                                        <input
                                            type="file"
                                            className="form-control"
                                            id="fileUpload"
                                            accept=".pdf"
                                            onChange={handleFileUpload}
                                            disabled={uploading}
                                        />
                                        <small className="form-text text-muted">
                                            You can upload 1 PDF file. Previous file will be replaced if you upload a new one.
                                        </small>
                                        {uploading && (
                                            <div className="mt-2">
                                                <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                                                Uploading...
                                            </div>
                                        )}
                                    </div>
                                )}

                                {loading ? (
                                    <div className="text-center py-4">
                                        <div className="spinner-border" role="status"></div>
                                    </div>
                                ) : uploadedFile ? (
                                    <div>
                                        <div className="alert alert-success">
                                            <i className="bi bi-check-circle-fill me-2"></i>
                                            PDF uploaded successfully! You can now use the RAG functionality.
                                        </div>
                                        <div className="list-group">
                                            <div className="list-group-item d-flex justify-content-between align-items-center">
                                                <div>
                                                    <i className="bi bi-file-pdf-fill text-danger me-2"></i>
                                                    <span>{uploadedFile.name}</span>
                                                    <small className="text-muted ms-2">({uploadedFile.size})</small>
                                                </div>
                                                <button
                                                    className="btn btn-sm btn-outline-danger"
                                                    onClick={handleDeleteFile}
                                                >
                                                    <i className="bi bi-trash"></i>
                                                </button>
                                            </div>
                                        </div>
                                        <div className="mt-3">
                                            <Link to="/basic-rag" className="btn btn-success">
                                                <i className="bi bi-chat-dots me-2"></i>
                                                Start Querying with RAG
                                            </Link>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center py-5">
                                        <i className="bi bi-cloud-upload" style={{ fontSize: '3rem', color: '#ccc' }}></i>
                                        <p className="text-muted mt-3">No PDF uploaded yet</p>
                                        <p className="small text-muted">Upload your PDF to get started</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="card shadow-sm mt-4">
                            <div className="card-header">
                                <h5 className="mb-0">
                                    <i className="bi bi-list-check me-2"></i>
                                    Available RAG Features
                                </h5>
                            </div>
                            <div className="card-body">
                                <ul className="list-unstyled">
                                    <li className="mb-2">
                                        <i className="bi bi-check-circle text-success me-2"></i>
                                        <strong>Basic RAG</strong> - Ask questions about your PDF
                                    </li>
                                    <li className="mb-2">
                                        <i className="bi bi-circle me-2 text-muted"></i>
                                        Reranking RAG (Coming soon)
                                    </li>
                                    <li className="mb-2">
                                        <i className="bi bi-circle me-2 text-muted"></i>
                                        Contextual Compression (Coming soon)
                                    </li>
                                    <li className="mb-2">
                                        <i className="bi bi-circle me-2 text-muted"></i>
                                        Agentic RAG (Coming soon)
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div className="col-lg-4 mt-4 mt-lg-0">
                        <div className="card shadow-sm">
                            <div className="card-body">
                                <h6 className="card-title">Quick Tips</h6>
                                <ul className="small">
                                    <li className="mb-2">Upload 1 PDF document</li>
                                    <li className="mb-2">Choose between standard and semantic chunking</li>
                                    <li className="mb-2">Ask questions about your document</li>
                                    <li className="mb-2">Get AI-powered answers with context</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Home;