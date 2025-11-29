import React, { useState, useEffect } from 'react'
import { setupMFA, verifyMFASetup, disableMFA } from '../services/api'
import './MFASetup.css'

function MFASetup() {
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [qrCode, setQrCode] = useState('')
  const [secret, setSecret] = useState('')
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [showDisable, setShowDisable] = useState(false)
  const [disablePassword, setDisablePassword] = useState('')

  useEffect(() => {
    loadMFASetup()
  }, [])

  const loadMFASetup = async () => {
    try {
      const response = await setupMFA()
      setQrCode(response.data.qrCode)
      setSecret(response.data.secret)
      setMfaEnabled(response.data.qrCode !== null) // If we get a QR code, MFA is being set up
    } catch (err) {
      // If MFA is already enabled, we might get an error
      if (err.response?.status === 400) {
        setMfaEnabled(true)
      }
    }
  }

  const handleVerify = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      await verifyMFASetup(token)
      setSuccess('MFA verified and enabled successfully')
      setMfaEnabled(true)
      setToken('')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to verify MFA token')
    } finally {
      setLoading(false)
    }
  }

  const handleDisable = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      await disableMFA(disablePassword)
      setSuccess('MFA disabled successfully')
      setMfaEnabled(false)
      setShowDisable(false)
      setDisablePassword('')
      loadMFASetup() // Reload to get new secret
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to disable MFA')
    } finally {
      setLoading(false)
    }
  }

  if (mfaEnabled && !showDisable) {
    return (
      <div className="pm-mfa-setup">
        <div className="pm-panel">
          <h3>Multi-Factor Authentication</h3>
          <p style={{color: 'var(--pm-text-muted)', marginBottom: '1rem'}}>
            MFA is currently enabled for your account.
          </p>
          {error && <div style={{color: 'var(--pm-error)', marginBottom: '1rem'}}>{error}</div>}
          {success && <div style={{color: 'var(--pm-success)', marginBottom: '1rem'}}>{success}</div>}
          <button 
            className="pm-button pm-button-ghost"
            onClick={() => setShowDisable(true)}
            style={{color: 'var(--pm-error)'}}
          >
            Disable MFA
          </button>
        </div>

        {showDisable && (
          <div className="pm-panel" style={{marginTop: '1rem'}}>
            <h4>Disable MFA</h4>
            <p style={{color: 'var(--pm-text-muted)', marginBottom: '1rem'}}>
              Enter your password to disable MFA.
            </p>
            <form onSubmit={handleDisable}>
              <div className="pm-field">
                <div className="pm-field-label">Password</div>
                <input
                  className="pm-input"
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  required
                />
              </div>
              <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
                <button type="submit" className="pm-button pm-button-primary" disabled={loading}>
                  {loading ? 'Disabling...' : 'Disable MFA'}
                </button>
                <button 
                  type="button" 
                  className="pm-button pm-button-ghost"
                  onClick={() => setShowDisable(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="pm-mfa-setup">
      <div className="pm-panel">
        <h3>Setup Multi-Factor Authentication</h3>
        <p style={{color: 'var(--pm-text-muted)', marginBottom: '1.5rem'}}>
          Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)
        </p>

        {qrCode && (
          <div style={{textAlign: 'center', marginBottom: '1.5rem'}}>
            <img src={qrCode} alt="MFA QR Code" style={{maxWidth: '300px', border: '1px solid var(--pm-border-soft)', borderRadius: 'var(--pm-radius-md)'}} />
          </div>
        )}

        {secret && (
          <div style={{marginBottom: '1.5rem', padding: '0.75rem', background: 'rgba(15,23,42,0.5)', borderRadius: 'var(--pm-radius-sm)'}}>
            <div style={{fontSize: '0.875rem', color: 'var(--pm-text-muted)', marginBottom: '0.25rem'}}>Secret Key (manual entry):</div>
            <code style={{fontSize: '0.875rem', wordBreak: 'break-all'}}>{secret}</code>
          </div>
        )}

        {error && <div style={{color: 'var(--pm-error)', marginBottom: '1rem'}}>{error}</div>}
        {success && <div style={{color: 'var(--pm-success)', marginBottom: '1rem'}}>{success}</div>}

        <form onSubmit={handleVerify}>
          <div className="pm-field">
            <div className="pm-field-label">Enter 6-digit code from your app</div>
            <input
              className="pm-input"
              type="text"
              value={token}
              onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength="6"
              required
              style={{textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem'}}
            />
          </div>
          <button type="submit" className="pm-button pm-button-primary" disabled={loading || token.length !== 6}>
            {loading ? 'Verifying...' : 'Verify and Enable MFA'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default MFASetup

