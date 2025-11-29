import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import LibraryBrowser from './components/LibraryBrowser'
import MediaGrid from './components/MediaGrid'
import MediaDetail from './components/MediaDetail'
import Login from './components/Login'
import { setAuthToken, setUnauthorizedHandler } from './services/api'
import './App.css'

function ProtectedRoute({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [checkingAuth, setCheckingAuth] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // Set up unauthorized handler
    setUnauthorizedHandler(() => {
      setIsAuthenticated(false)
      navigate('/login')
    })

    // Check if we have a token
    const token = sessionStorage.getItem('authToken')
    if (token) {
      setAuthToken(token)
      setIsAuthenticated(true)
    } else {
      setIsAuthenticated(false)
    }
    setCheckingAuth(false)
  }, [navigate])

  if (checkingAuth) {
    return <div>Loading...</div>
  }

  if (!isAuthenticated) {
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
          <Route path="library/:libraryId" element={<MediaGrid />} />
          <Route path="library/:libraryId/folder/:folderId" element={<MediaGrid />} />
          <Route path="media/:mediaId" element={<MediaDetail />} />
        </Route>
      </Routes>
    </div>
  )
}

export default App

