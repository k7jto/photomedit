import React, { useState, useEffect } from 'react'
import { Outlet, useNavigate, useParams } from 'react-router-dom'
import { getLibraries, getFolders } from '../services/api'
import Logo from './Logo'

function LibraryBrowser() {
  const [libraries, setLibraries] = useState([])
  const [folders, setFolders] = useState([])
  const [selectedLibrary, setSelectedLibrary] = useState(null)
  const [selectedFolder, setSelectedFolder] = useState(null)
  const navigate = useNavigate()
  const params = useParams()

  useEffect(() => {
    loadLibraries()
  }, [])

  useEffect(() => {
    if (params.libraryId) {
      setSelectedLibrary(params.libraryId)
      loadFolders(params.libraryId, params.folderId || '')
    }
  }, [params.libraryId, params.folderId])

  const loadLibraries = async () => {
    try {
      const response = await getLibraries()
      setLibraries(response.data)
      if (response.data.length > 0 && !params.libraryId) {
        navigate(`/${response.data[0].id}`)
      }
    } catch (err) {
      console.error('Failed to load libraries:', err)
    }
  }

  const loadFolders = async (libraryId, parent = '') => {
    try {
      const response = await getFolders(libraryId, parent)
      setFolders(response.data)
      setSelectedLibrary(libraryId)
      setSelectedFolder(parent)
    } catch (err) {
      console.error('Failed to load folders:', err)
    }
  }

  const handleLibrarySelect = (libraryId) => {
    navigate(`/${libraryId}`)
  }

  const handleFolderSelect = (folderId) => {
    const relativePath = folderId.includes('|') ? folderId.split('|')[1] : folderId
    navigate(`/${selectedLibrary}/folder/${folderId}`)
  }

  return (
    <div className="pm-app">
      <header className="pm-header">
        <div className="pm-header-left">
          <Logo size="medium" showTagline={false} />
        </div>
        <div className="pm-header-right">
          <div style={{display: 'flex', gap: '1rem', alignItems: 'center'}}>
            <button 
              className="pm-button pm-button-ghost"
              onClick={() => navigate('/upload')}
              style={{fontSize: '0.875rem'}}
            >
              Upload
            </button>
            <button 
              className="pm-button pm-button-ghost"
              onClick={() => navigate('/mfa-setup')}
              style={{fontSize: '0.875rem'}}
            >
              MFA Setup
            </button>
            <button 
              className="pm-button pm-button-ghost"
              onClick={() => navigate('/admin')}
              style={{fontSize: '0.875rem'}}
            >
              Admin
            </button>
          </div>
        </div>
      </header>
      <div className="pm-main">
        <aside className="pm-sidebar">
          <div className="pm-panel">
            <div className="pm-panel-title">Library</div>
            <select 
              className="pm-select"
              value={selectedLibrary || ''}
              onChange={(e) => handleLibrarySelect(e.target.value)}
            >
              <option value="">Select library...</option>
              {libraries.map(lib => (
                <option key={lib.id} value={lib.id}>{lib.name}</option>
              ))}
            </select>
          </div>
          
          {selectedLibrary && (
            <div className="pm-panel">
              <div className="pm-panel-title">Folders</div>
              <ul className="pm-tree">
                <li className="pm-tree-item">
                  <button
                    className={`pm-tree-button ${!selectedFolder ? 'pm-tree-button-active' : ''}`}
                    onClick={() => navigate(`/${selectedLibrary}`)}
                  >
                    Home
                  </button>
                </li>
                {folders.map(folder => (
                  <li key={folder.id} className="pm-tree-item">
                    <button
                      className={`pm-tree-button ${selectedFolder === folder.relativePath ? 'pm-tree-button-active' : ''}`}
                      onClick={() => handleFolderSelect(folder.id)}
                    >
                      {folder.name}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
        <main className="pm-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default LibraryBrowser

