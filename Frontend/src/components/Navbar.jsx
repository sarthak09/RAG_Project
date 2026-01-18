import { Link, useLocation, useNavigate } from "react-router-dom";
import {useContext} from 'react'
import loginContext  from '../context/context'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const Navbar = () => {
    let location = useLocation();
    let navigate = useNavigate();
    const value = useContext(loginContext)

    const handlelogout = async () => {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                await fetch(`${API_BASE_URL}/signout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            } catch (error) {
                console.log('Signout error:', error);
            }
        }
        localStorage.removeItem('token');
        localStorage.removeItem('trial_active');
        localStorage.removeItem('trial_end_date');
        value.setlogininfo({name: "", islog: false, email: "", trial_active: false, trial_end_date: ""})
        navigate("/login");
    }

    return (
        <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
            <div className="container-fluid">
                <Link className="navbar-brand" to="/">Sarthak</Link>
                <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                    <span className="navbar-toggler-icon"></span>
                </button>
                <div className="collapse navbar-collapse" id="navbarSupportedContent">
                    <ul className="navbar-nav me-auto mb-2 mb-lg-0">
                        <li className="nav-item">
                            {value.logininfo.islog ? <Link className={`nav-link ${location.pathname === "/" ? "active" : ""}`} aria-current="page" to="/">Home</Link>: <></>}
                        </li>
                        <li className="nav-item">
                            {value.logininfo.islog ? <Link className={`nav-link ${location.pathname === "/basic-rag" ? "active" : ""}`} to="/basic-rag">Basic RAG</Link>: <></>}
                        </li>
                        <li className="nav-item">
                            <Link className={`nav-link ${location.pathname === "/about" ? "active" : ""}`} to="/about">About</Link>
                        </li>

                    </ul>
                    {!localStorage.getItem('token') ? <form className="d-flex">
                        <Link className="btn btn-primary mx-1" to="/login" role="button">Login</Link>
                        <Link className="btn btn-primary mx-1" to="/signup" role="button">Signup</Link>
                    </form> : <button onClick={handlelogout} className="btn btn-primary">Logout</button>}
                </div>
            </div>
        </nav>
    )
}

export default Navbar