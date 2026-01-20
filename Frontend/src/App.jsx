import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './components/Home'
import About from './components/About'
import Login from './components/Login'
import Signup from './components/Signup'
import BasicRag from './components/BasicRag'
import ResetPassword from './components/ResetPassword'
import loginContext from './context/context'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

function App() {
  const [logininfo, setlogininfo] = useState({
    name: "", 
    islog: false, 
    email: "", 
    trial_active: false, 
    trial_end_date: ""
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token')
      if (token) {
        try {
          const response = await fetch(`${API_BASE_URL}/verify`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          const data = await response.json()
          
          if (data.valid) {
            setlogininfo({
              name: data.name,
              islog: true,
              email: data.email,
              trial_active: data.trial_active,
              trial_end_date: data.trial_end_date
            })
            localStorage.setItem('trial_active', data.trial_active)
            localStorage.setItem('trial_end_date', data.trial_end_date)
          } else {
            localStorage.removeItem('token')
            localStorage.removeItem('trial_active')
            localStorage.removeItem('trial_end_date')
          }
        } catch (error) {
          console.log('Token verification failed:', error)
          localStorage.removeItem('token')
          localStorage.removeItem('trial_active')
          localStorage.removeItem('trial_end_date')
        }
      }
      setLoading(false)
    }

    verifyToken()
  }, [])

  if (loading) {
    return <div className="d-flex justify-content-center align-items-center" style={{minHeight: '100vh'}}>
      <div className="spinner-border" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  }

  return (
    <loginContext.Provider value={{ logininfo, setlogininfo }}>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/" element={logininfo.islog ? <Home /> : <Navigate to="/login" />} />
          <Route path="/about" element={<About />} />
          <Route path="/basic-rag" element={logininfo.islog ? <BasicRag /> : <Navigate to="/login" />} />
          <Route path="/login" element={!logininfo.islog ? <Login /> : <Navigate to="/" />} />
          <Route path="/signup" element={!logininfo.islog ? <Signup /> : <Navigate to="/" />} />
          <Route path="/reset-password" element={!logininfo.islog ? <ResetPassword /> : <Navigate to="/" />} />
        </Routes>
      </Router>
    </loginContext.Provider>
  )
}

export default App