import React from 'react'
import './Logo.css'

function Logo({ size = 'medium', showTagline = true }) {
  return (
    <div className={`logo logo-${size}`}>
      <div className="logo-icon">
        <svg viewBox="0 0 64 64" className="logo-svg">
          <defs>
            <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#3498db', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#1abc9c', stopOpacity: 1}} />
            </linearGradient>
          </defs>
          <circle cx="32" cy="32" r="30" fill="url(#logoGradient)" />
          <rect x="12" y="18" width="40" height="28" rx="2" fill="none" stroke="white" strokeWidth="2" />
          <path d="M 20 28 L 28 28 M 20 32 L 44 32 M 20 36 L 40 36" stroke="white" strokeWidth="2" strokeLinecap="round" />
          <circle cx="48" cy="20" r="4" fill="white" />
        </svg>
      </div>
      <div className="logo-text">
        <div className="logo-title">PhotoMedit</div>
        {showTagline && <div className="logo-tagline">Because every photo has a story</div>}
      </div>
    </div>
  )
}

export default Logo

