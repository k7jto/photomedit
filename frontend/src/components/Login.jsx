import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, setAuthToken } from '../services/api'
import Logo from './Logo'
import './Login.css'

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [mfaToken, setMfaToken] = useState('')
  const [mfaRequired, setMfaRequired] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await login(username, password, mfaToken || null)
      
      // Check if MFA is required
      if (data.mfaRequired) {
        setMfaRequired(true)
        setLoading(false)
        return
      }
      
      sessionStorage.setItem('authToken', data.token)
      setAuthToken(data.token)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed')
      setMfaRequired(false)
      setMfaToken('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-header">
        <Logo size="large" showTagline={true} />
      </div>
      <form className="login-form" onSubmit={handleSubmit}>
        <h2>Login</h2>
        <div className="form-group">
          <label htmlFor="username">Username</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={mfaRequired}
          />
        </div>
        {mfaRequired && (
          <div className="form-group">
            <label htmlFor="mfaToken">MFA Code (6 digits)</label>
            <input
              type="text"
              id="mfaToken"
              value={mfaToken}
              onChange={(e) => setMfaToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength="6"
              required
              autoFocus
              style={{textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem'}}
            />
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <button type="submit" className="button" disabled={loading || (mfaRequired && mfaToken.length !== 6)}>
          {loading ? 'Logging in...' : mfaRequired ? 'Verify MFA' : 'Login'}
        </button>
        <div style={{marginTop: '1rem', textAlign: 'center'}}>
          <button 
            type="button" 
            className="button secondary" 
            onClick={() => navigate('/forgot-password')}
            style={{fontSize: '0.875rem'}}
          >
            Forgot Password?
          </button>
        </div>
      </form>
    </div>
  )
}

export default Login

