import React, { useState, useEffect } from 'react'
import { Outlet, useNavigate, useParams } from 'react-router-dom'
import { getLibraries, getFolders } from '../services/api'
import Logo from './Logo'

function LibraryBrowser() {
  const [libraries, setLibraries] = useState([])
  const [rootFolders, setRootFolders] = useState([]) // Root level folders
  const [selectedLibrary, setSelectedLibrary] = useState(null)
  const [selectedFolder, setSelectedFolder] = useState(null)
  const [expandedFolders, setExpandedFolders] = useState(new Set()) // Track expanded folders by their full path
  const [folderChildren, setFolderChildren] = useState(new Map()) // Cache: path -> children array
  const navigate = useNavigate()
  const params = useParams()

  useEffect(() => {
    // Only load libraries if we have an auth token
    const token = sessionStorage.getItem('authToken')
    if (token) {
      loadLibraries()
    }
  }, [])

  useEffect(() => {
    // Only load folders if we have an auth token
    const token = sessionStorage.getItem('authToken')
    if (token && params.libraryId) {
      setSelectedLibrary(params.libraryId)
      // Extract relative path from folderId (remove library prefix if present)
      let parentPath = ''
      if (params.folderId) {
        parentPath = params.folderId.includes('|') ? params.folderId.split('|')[1] : params.folderId
      }
      setSelectedFolder(parentPath)
      // Load root folders
      loadRootFolders(params.libraryId)
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

  const loadRootFolders = async (libraryId) => {
    try {
      const response = await getFolders(libraryId, '')
      setRootFolders(response.data)
      // Cache root folders
      setFolderChildren(prev => {
        const newMap = new Map(prev)
        newMap.set('', response.data)
        return newMap
      })
    } catch (err) {
      console.error('Failed to load root folders:', err)
    }
  }

  const loadFolderChildren = async (libraryId, folderPath) => {
    console.log('Loading children for path:', folderPath)
    // Check if already cached
    if (folderChildren.has(folderPath)) {
      const cached = folderChildren.get(folderPath)
      console.log('Using cached children:', cached.length)
      return cached
    }
    
    try {
      console.log('Fetching folders from API for path:', folderPath)
      const response = await getFolders(libraryId, folderPath)
      const children = response.data || []
      console.log('API returned', children.length, 'children for', folderPath)
      
      // Cache the children
      setFolderChildren(prev => {
        const newMap = new Map(prev)
        newMap.set(folderPath, children)
        return newMap
      })
      
      return children
    } catch (err) {
      console.error('Failed to load folder children:', err)
      return []
    }
  }

  const toggleFolder = async (fullPath) => {
    console.log('Toggle folder:', fullPath, 'Currently expanded:', expandedFolders.has(fullPath))
    const isExpanded = expandedFolders.has(fullPath)
    
    if (isExpanded) {
      // Collapse
      setExpandedFolders(prev => {
        const newSet = new Set(prev)
        newSet.delete(fullPath)
        return newSet
      })
    } else {
      // Expand - load children if not cached
      setExpandedFolders(prev => {
        const newSet = new Set(prev)
        newSet.add(fullPath)
        return newSet
      })
      
      // Load children for this folder
      const children = await loadFolderChildren(selectedLibrary, fullPath)
      console.log('Loaded children for', fullPath, ':', children.length, 'folders')
    }
  }

  const handleLibrarySelect = (libraryId) => {
    navigate(`/${libraryId}`)
  }

  const handleFolderSelect = (folderId) => {
    // folderId already has library prefix from API response
    navigate(`/${selectedLibrary}/folder/${encodeURIComponent(folderId)}`)
  }

  const renderFolderTree = (foldersList, parentPath = '', depth = 0) => {
    if (!foldersList || foldersList.length === 0) {
      return null
    }
    
    return foldersList.map(folder => {
      // Extract relative path from folder.id (format: "libraryId|relativePath")
      // The relativePath from API is already the full path from library root
      const folderRelativePath = folder.relativePath || (folder.id.includes('|') ? folder.id.split('|')[1] : folder.id)
      
      // Use the relativePath directly - it's already the full path from root
      // For example: "Old Photos/2020" is already the full path, not just "2020"
      const fullPath = folderRelativePath
      
      console.log(`Rendering folder: ${folder.name}, fullPath: ${fullPath}, parentPath: ${parentPath}, depth: ${depth}`)
      
      // Check if this folder is expanded
      const isExpanded = expandedFolders.has(fullPath)
      
      // Get cached children for this path
      const children = folderChildren.get(fullPath) || []
      const hasChildren = folder.hasChildren || children.length > 0
      const isActive = selectedFolder === fullPath || selectedFolder === folderRelativePath
      
      return (
        <li key={folder.id || fullPath} className="pm-tree-item">
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {hasChildren ? (
              <button
                className="pm-tree-expand"
                onClick={async (e) => {
                  e.stopPropagation()
                  console.log('Expanding folder:', fullPath)
                  await toggleFolder(fullPath)
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--pm-text-muted)',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  fontSize: '0.7rem',
                  minWidth: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {isExpanded ? '▼' : '▶'}
              </button>
            ) : (
              <span style={{ width: '16px', display: 'inline-block' }} />
            )}
            <button
              className={`pm-tree-button ${isActive ? 'pm-tree-button-active' : ''}`}
              onClick={() => handleFolderSelect(folder.id)}
              style={{ 
                flex: 1,
                paddingLeft: '4px'
              }}
            >
              {folder.name}
            </button>
          </div>
          {isExpanded && hasChildren && (
            <ul className="pm-tree" style={{ marginLeft: '1rem', marginTop: '2px', paddingLeft: '0' }}>
              {renderFolderTree(children, fullPath, depth + 1)}
            </ul>
          )}
        </li>
      )
    })
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
          {libraries.length > 1 ? (
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
          ) : libraries.length === 1 ? (
            <div className="pm-panel">
              <div className="pm-panel-title">Library</div>
              <div style={{ 
                padding: '7px 8px', 
                fontSize: '0.85rem', 
                color: 'var(--pm-text)',
                background: '#020617',
                border: '1px solid var(--pm-border-soft)',
                borderRadius: '10px'
              }}>
                {libraries[0].name}
              </div>
            </div>
          ) : null}
          
          {selectedLibrary && (
            <div className="pm-panel">
              <div className="pm-panel-title">Folders</div>
              <ul className="pm-tree" style={{ flex: 1, overflowY: 'auto' }}>
                <li className="pm-tree-item">
                  <button
                    className={`pm-tree-button ${!selectedFolder ? 'pm-tree-button-active' : ''}`}
                    onClick={() => navigate(`/${selectedLibrary}`)}
                  >
                    Home
                  </button>
                </li>
                {/* Recursive folder tree */}
                {renderFolderTree(rootFolders)}
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
