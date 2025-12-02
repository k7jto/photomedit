import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import LibraryBrowser from './components/LibraryBrowser'
import MediaGrid from './components/MediaGrid'
import MediaDetail from './components/MediaDetail'
import Login from './components/Login'
import ForgotPassword from './components/ForgotPassword'
import Admin from './components/Admin'
import Logs from './components/Logs'
import MFASetup from './components/MFASetup'
import Upload from './components/Upload'
import { MediaCacheProvider } from './contexts/MediaCacheContext'
import { setAuthToken, setUnauthorizedHandler } from './services/api'
import './App.css'

function ProtectedRoute({ children }) {
  const navigate = useNavigate()
  
  // Check auth synchronously on first render to prevent children from mounting
  const token = sessionStorage.getItem('authToken')
  const [isAuthenticated, setIsAuthenticated] = useState(!!token)
  
  useEffect(() => {
    // Set up unauthorized handler
    setUnauthorizedHandler(() => {
      setIsAuthenticated(false)
      navigate('/login')
    })

    // Set token if we have one
    if (token) {
      setAuthToken(token)
      setIsAuthenticated(true)
    } else {
      setIsAuthenticated(false)
    }
  }, [navigate, token])

  // Redirect immediately if no token (synchronous check)
  if (!token || !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

function App() {
  const navigate = useNavigate()

  useEffect(() => {
    // Set up unauthorized handler globally
    setUnauthorizedHandler(() => {
      navigate('/login')
    })

    // Check initial auth state and set token if present
    const token = sessionStorage.getItem('authToken')
    if (token) {
      setAuthToken(token)
    }
  }, [navigate])

  return (
    <MediaCacheProvider>
      <div className="App">
        <Routes>
        <Route path="/login" element={<Login onLogin={() => navigate('/')} />} />
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <LibraryBrowser />
            </ProtectedRoute>
          }
        >
          <Route path=":libraryId" element={<MediaGrid />} />
          <Route path=":libraryId/folder/:folderId" element={<MediaGrid />} />
          <Route path="media/:mediaId" element={<MediaDetail />} />
        </Route>
              <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
              <Route path="/logs" element={<ProtectedRoute><Logs /></ProtectedRoute>} />
              <Route path="/mfa-setup" element={<ProtectedRoute><MFASetup /></ProtectedRoute>} />
              <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
        </Routes>
      </div>
    </MediaCacheProvider>
  )
}

export default App

