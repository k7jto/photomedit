import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { forgotPassword, resetPassword } from '../services/api'
import Logo from './Logo'
import './Login.css'

function ForgotPassword() {
  const [step, setStep] = useState('request') // 'request' or 'reset'
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleRequestReset = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const response = await forgotPassword(email)
      setSuccess('If the email exists, a reset link has been sent. Check your email or use the token below (development only).')
      if (response.data.resetToken) {
        setToken(response.data.resetToken) // In production, this would come via email only
        setStep('reset')
      } else {
        setSuccess('If the email exists, a reset link has been sent to your email.')
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to request password reset')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)

    try {
      await resetPassword(token, password)
      setSuccess('Password reset successfully. Redirecting to login...')
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-header">
        <Logo size="large" showTagline={true} />
      </div>
      
      {step === 'request' ? (
        <form className="login-form" onSubmit={handleRequestReset}>
          <h2>Forgot Password</h2>
          <p style={{color: 'var(--pm-text-muted)', marginBottom: '1.5rem'}}>
            Enter your email address to receive a password reset link.
          </p>
          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <button type="submit" className="button" disabled={loading}>
            {loading ? 'Sending...' : 'Request Reset'}
          </button>
          <button 
            type="button" 
            className="button secondary" 
            onClick={() => navigate('/login')}
            style={{marginTop: '0.5rem'}}
          >
            Back to Login
          </button>
        </form>
      ) : (
        <form className="login-form" onSubmit={handleReset}>
          <h2>Reset Password</h2>
          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}
          <div className="form-group">
            <label htmlFor="token">Reset Token</label>
            <input
              type="text"
              id="token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">New Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="button" disabled={loading}>
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
          <button 
            type="button" 
            className="button secondary" 
            onClick={() => setStep('request')}
            style={{marginTop: '0.5rem'}}
          >
            Back
          </button>
        </form>
      )}
    </div>
  )
}

export default ForgotPassword

