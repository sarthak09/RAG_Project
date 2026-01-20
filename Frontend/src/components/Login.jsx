import {useState, useContext} from 'react'
import { useNavigate, Link } from 'react-router-dom'
import loginContext  from '../context/context'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;


const Login = () => {
    const [credentials, setCredentials] = useState({email: "", password: ""}) 
    const [loading, setLoading] = useState(false)
    const value = useContext(loginContext)
    let navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true)
        try {
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({email: credentials.email, password: credentials.password})
            });
            const json = await response.json()
            
            if (json.success){
                localStorage.setItem('token', json.token);
                localStorage.setItem('trial_active', json.trial_active);
                localStorage.setItem('trial_end_date', json.trial_end_date);
                value.setlogininfo({
                    name: json.name, 
                    islog: true,
                    email: json.email,
                    trial_active: json.trial_active,
                    trial_end_date: json.trial_end_date
                })
                if (!json.trial_active) {
                    alert('Your trial period has expired. Please upgrade your plan.');
                }
                navigate("/");
            }
            else{
                alert(json.error);
            }
        } catch (error) {
            alert('Login failed. Please try again.');
        } finally {
            setLoading(false)
        }
    }

    const onChange = (e)=>{
        setCredentials({...credentials, [e.target.name]: e.target.value})
    }

    return (
        <div className="container">
            <div className="row justify-content-center align-items-center" style={{minHeight: '80vh'}}>
                <div className="col-md-5 col-lg-4">
                    <div className="card shadow">
                        <div className="card-body p-4">
                            <h3 className="card-title text-center mb-4">Login</h3>
                            <form onSubmit={handleSubmit}>
                                <div className="mb-3">
                                    <label htmlFor="email" className="form-label">Email address</label>
                                    <input 
                                        type="email" 
                                        className="form-control" 
                                        value={credentials.email} 
                                        onChange={onChange} 
                                        id="email" 
                                        name="email"
                                        required 
                                    />
                                </div>
                                <div className="mb-3">
                                    <label htmlFor="password" className="form-label">Password</label>
                                    <input 
                                        type="password" 
                                        className="form-control" 
                                        value={credentials.password} 
                                        onChange={onChange} 
                                        name="password" 
                                        id="password"
                                        required 
                                    />
                                </div>
                                <button type="submit" className="btn btn-primary w-100" disabled={loading}>
                                    {loading ? 'Logging in...' : 'Login'}
                                </button>
                            </form>
                            <div className="text-center mt-3">
                                <Link to="/reset-password" className="text-decoration-none small">
                                    Forgot Password?
                                </Link>
                            </div>
                            <div className="text-center mt-2">
                                <small className="text-muted">
                                    Don't have an account? <Link to="/signup">Sign up</Link>
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Login