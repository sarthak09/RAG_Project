import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const ResetPassword = () => {
    const [step, setStep] = useState(1) // 1 = email, 2 = password
    const [email, setEmail] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()

    const handleEmailSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const response = await fetch(`${API_BASE_URL}/check-email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            })

            const data = await response.json()

            if (data.success) {
                setStep(2)
            } else {
                setError(data.error || 'Email not found')
            }
        } catch (error) {
            setError('Failed to verify email. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handlePasswordSubmit = async (e) => {
        e.preventDefault()
        setError('')

        // Validate passwords match
        if (newPassword !== confirmPassword) {
            setError('Passwords do not match')
            return
        }

        // Validate password length
        if (newPassword.length < 8) {
            setError('Password must be at least 8 characters')
            return
        }

        setLoading(true)

        try {
            const response = await fetch(`${API_BASE_URL}/reset-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    email, 
                    new_password: newPassword 
                })
            })

            const data = await response.json()

            if (data.success) {
                alert('Password reset successfully! Please login with your new password.')
                navigate('/login')
            } else {
                setError(data.error || 'Failed to reset password')
            }
        } catch (error) {
            setError('Failed to reset password. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleBackToStep1 = () => {
        setStep(1)
        setNewPassword('')
        setConfirmPassword('')
        setError('')
    }

    return (
        <div className="container">
            <div className="row justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
                <div className="col-md-5 col-lg-4">
                    <div className="card shadow">
                        <div className="card-body p-4">
                            <h3 className="card-title text-center mb-4">Reset Password</h3>
                            
                            {/* Step Indicator */}
                            <div className="mb-4">
                                <div className="d-flex justify-content-between align-items-center">
                                    <div className="text-center" style={{ flex: 1 }}>
                                        <div className={`rounded-circle d-inline-flex align-items-center justify-content-center ${step === 1 ? 'bg-primary text-white' : 'bg-success text-white'}`} 
                                             style={{ width: '30px', height: '30px', fontSize: '14px' }}>
                                            {step === 1 ? '1' : '✓'}
                                        </div>
                                        <div className="small mt-1">Email</div>
                                    </div>
                                    <div style={{ flex: 1, height: '2px', backgroundColor: step === 2 ? '#198754' : '#dee2e6', margin: '0 10px' }}></div>
                                    <div className="text-center" style={{ flex: 1 }}>
                                        <div className={`rounded-circle d-inline-flex align-items-center justify-content-center ${step === 2 ? 'bg-primary text-white' : 'bg-secondary text-white'}`}
                                             style={{ width: '30px', height: '30px', fontSize: '14px' }}>
                                            2
                                        </div>
                                        <div className="small mt-1">New Password</div>
                                    </div>
                                </div>
                            </div>

                            {error && (
                                <div className="alert alert-danger" role="alert">
                                    {error}
                                </div>
                            )}

                            {/* Step 1: Email Input */}
                            {step === 1 && (
                                <form onSubmit={handleEmailSubmit}>
                                    <div className="mb-3">
                                        <label htmlFor="email" className="form-label">Email address</label>
                                        <input
                                            type="email"
                                            className="form-control"
                                            id="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            autoFocus
                                            placeholder="Enter your email"
                                        />
                                        <small className="text-muted">
                                            Enter the email associated with your account
                                        </small>
                                    </div>
                                    <button 
                                        type="submit" 
                                        className="btn btn-primary w-100" 
                                        disabled={loading}
                                    >
                                        {loading ? 'Verifying...' : 'Continue'}
                                    </button>
                                </form>
                            )}

                            {/* Step 2: Password Input */}
                            {step === 2 && (
                                <form onSubmit={handlePasswordSubmit}>
                                    <div className="alert alert-info mb-3">
                                        <small>
                                            <i className="bi bi-info-circle me-2"></i>
                                            Resetting password for: <strong>{email}</strong>
                                        </small>
                                    </div>
                                    
                                    <div className="mb-3">
                                        <label htmlFor="newPassword" className="form-label">New Password</label>
                                        <input
                                            type="password"
                                            className="form-control"
                                            id="newPassword"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            required
                                            autoFocus
                                            placeholder="Enter new password"
                                        />
                                    </div>

                                    <div className="mb-3">
                                        <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
                                        <input
                                            type="password"
                                            className="form-control"
                                            id="confirmPassword"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            placeholder="Confirm new password"
                                        />
                                        <small className="text-muted">
                                            Min 8 characters, 1 uppercase, 1 number, 1 special character
                                        </small>
                                    </div>

                                    <button 
                                        type="submit" 
                                        className="btn btn-primary w-100 mb-2" 
                                        disabled={loading}
                                    >
                                        {loading ? 'Resetting...' : 'Reset Password'}
                                    </button>

                                    <button 
                                        type="button" 
                                        className="btn btn-outline-secondary w-100" 
                                        onClick={handleBackToStep1}
                                        disabled={loading}
                                    >
                                        Back to Email
                                    </button>
                                </form>
                            )}

                            <div className="text-center mt-3">
                                <small className="text-muted">
                                    Remember your password? <Link to="/login">Login</Link>
                                </small>
                            </div>

                            {step === 1 && (
                                <div className="alert alert-warning mt-3 mb-0" role="alert">
                                    <small>
                                        <i className="bi bi-exclamation-triangle me-2"></i>
                                        <strong>Demo Mode:</strong> This is a simplified reset for demonstration purposes only.
                                    </small>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ResetPassword