import React, { useContext } from 'react'
import { Link } from 'react-router-dom'
import loginContext from '../context/context'

const About = () => {
  const value = useContext(loginContext)

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card shadow">
            <div className="card-body p-5">
              <h2 className="card-title mb-4">About This Project</h2>
              <p className="lead">
                This is a RAG (Retrieval Augmented Generation) application that allows you to interact with your documents using AI.
              </p>
              <p>
                Created by Sarthak as a demonstration project showcasing modern web development technologies including:
              </p>
              <ul>
                <li>React with Vite for the frontend</li>
                <li>Flask for the backend API</li>
                <li>JWT-based authentication</li>
                <li>RAG capabilities for document interaction</li>
              </ul>
              
              {!value.logininfo.islog ? (
                <div className="alert alert-info mt-4" role="alert">
                  <h5 className="alert-heading">
                    <i className="bi bi-info-circle-fill me-2"></i>
                    Get Started
                  </h5>
                  <p className="mb-3">
                    To access the RAG application and interact with your documents, please create an account or login.
                  </p>
                  <div className="d-flex gap-2">
                    <Link to="/signup" className="btn btn-primary">
                      Sign Up - 14 Days Free Trial
                    </Link>
                    <Link to="/login" className="btn btn-outline-primary">
                      Login
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="alert alert-success mt-4" role="alert">
                  <i className="bi bi-check-circle-fill me-2"></i>
                  You're logged in as <strong>{value.logininfo.name}</strong>
                </div>
              )}

              <div className="mt-4">
                <h5>Features</h5>
                <div className="row mt-3">
                  <div className="col-md-6 mb-3">
                    <div className="card h-100">
                      <div className="card-body">
                        <h6 className="card-title">
                          <i className="bi bi-file-earmark-pdf me-2"></i>
                          Document Upload
                        </h6>
                        <p className="card-text small">Upload your PDF documents for AI-powered analysis</p>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-6 mb-3">
                    <div className="card h-100">
                      <div className="card-body">
                        <h6 className="card-title">
                          <i className="bi bi-chat-dots me-2"></i>
                          Interactive Chat
                        </h6>
                        <p className="card-text small">Ask questions and get answers from your documents</p>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-6 mb-3">
                    <div className="card h-100">
                      <div className="card-body">
                        <h6 className="card-title">
                          <i className="bi bi-shield-check me-2"></i>
                          Secure Access
                        </h6>
                        <p className="card-text small">Your data is protected with industry-standard security</p>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-6 mb-3">
                    <div className="card h-100">
                      <div className="card-body">
                        <h6 className="card-title">
                          <i className="bi bi-clock-history me-2"></i>
                          14-Day Trial
                        </h6>
                        <p className="card-text small">Full access to all features during your trial period</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default About
