import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const Signup = () => {
    const [credentials, setCredentials] = useState({ email: "", password: "", name: "", address1: "", address2: "", city: "", state: "", zip: "" })
    const [loading, setLoading] = useState(false)
    let navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true)
        try {
            const response = await fetch(`${API_BASE_URL}/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email: credentials.email, password: credentials.password, name: credentials.name, address1: credentials.address1, address2: credentials.address2, city: credentials.city, state: credentials.state, zip: credentials.zip })
            });
            const json = await response.json()
            
            if (json.success) {
                alert('Account created successfully! You have 14 days of free trial.');
                navigate("/login");
            }
            else {
                alert(json.error);
            }
        } catch (error) {
            alert('Signup failed. Please try again.');
        } finally {
            setLoading(false)
        }
    }

    const onChange = (e) => {
        setCredentials({ ...credentials, [e.target.name]: e.target.value })
    }

    return (
        <div className="container">
            <div className="row justify-content-center align-items-center" style={{minHeight: '80vh', paddingTop: '2rem', paddingBottom: '2rem'}}>
                <div className="col-md-8 col-lg-6">
                    <div className="card shadow">
                        <div className="card-body p-4">
                            <h3 className="card-title text-center mb-4">Create Account</h3>
                            <p className="text-center text-muted mb-4">Get started with 14 days free trial</p>
                            <form onSubmit={handleSubmit}>
                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label htmlFor="name" className="form-label">Name</label>
                                        <input type="text" className="form-control" value={credentials.name} onChange={onChange} id="name" name="name" required />
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <label htmlFor="email" className="form-label">Email</label>
                                        <input type="email" className="form-control" value={credentials.email} onChange={onChange} id="email" name="email" required />
                                    </div>
                                </div>
                                <div className="mb-3">
                                    <label htmlFor="password" className="form-label">Password</label>
                                    <input type="password" className="form-control" value={credentials.password} onChange={onChange} id="password" name="password" required />
                                    <small className="form-text text-muted">Min 8 characters, 1 uppercase, 1 number, 1 special character</small>
                                </div>
                                <div className="mb-3">
                                    <label htmlFor="address1" className="form-label">Address</label>
                                    <input type="text" className="form-control" value={credentials.address1} onChange={onChange} id="address1" name="address1" placeholder="1234 Main St" />
                                </div>
                                <div className="mb-3">
                                    <label htmlFor="address2" className="form-label">Address 2</label>
                                    <input type="text" className="form-control" value={credentials.address2} onChange={onChange} id="address2" name="address2" placeholder="Apartment, studio, or floor" />
                                </div>
                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label htmlFor="city" className="form-label">City</label>
                                        <input type="text" className="form-control" value={credentials.city} onChange={onChange} id="city" name="city" placeholder="Adelaide"/>
                                    </div>
                                    <div className="col-md-4 mb-3">
                                        <label htmlFor="state" className="form-label">State</label>
                                        <select id="state" className="form-control" value={credentials.state} onChange={onChange} name="state">
                                            <option value="">Choose...</option>
                                            <option>SA</option>
                                            <option>Victoria</option>
                                            <option>NSW</option>
                                            <option>WA</option>
                                            <option>QLD</option>
                                            <option>TAS</option>
                                            <option>NT</option>
                                            <option>ACT</option>
                                        </select>
                                    </div>
                                    <div className="col-md-2 mb-3">
                                        <label htmlFor="zip" className="form-label">Zip</label>
                                        <input type="text" className="form-control" value={credentials.zip} onChange={onChange} id="zip" name="zip" />
                                    </div>
                                </div>
                                <button type="submit" className="btn btn-primary w-100" disabled={loading}>
                                    {loading ? 'Creating Account...' : 'Sign Up'}
                                </button>
                            </form>
                            <div className="text-center mt-3">
                                <small className="text-muted">
                                    Already have an account? <Link to="/login">Login</Link>
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Signup
