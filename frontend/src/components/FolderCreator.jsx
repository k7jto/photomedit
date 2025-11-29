import React, { useState } from 'react'
import { createFolder } from '../services/api'
import './FolderCreator.css'

function FolderCreator({ libraryId, currentFolder, onFolderCreated }) {
  const [folderName, setFolderName] = useState('')
  const [showDialog, setShowDialog] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!folderName.trim()) {
      setError('Folder name is required')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const parent = currentFolder || ''
      await createFolder(libraryId, parent, folderName.trim())
      setSuccess('Folder created successfully')
      setFolderName('')
      setShowDialog(false)
      if (onFolderCreated) {
        onFolderCreated()
      }
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create folder')
    } finally {
      setLoading(false)
    }
  }

  if (!showDialog) {
    return (
      <button 
        className="pm-button pm-button-ghost"
        onClick={() => setShowDialog(true)}
        style={{marginBottom: '1rem'}}
      >
        + New Folder
      </button>
    )
  }

  return (
    <div className="pm-folder-creator-dialog">
      <div className="pm-folder-creator-overlay" onClick={() => setShowDialog(false)}></div>
      <div className="pm-folder-creator-content">
        <h3>Create New Folder</h3>
        {error && <div style={{color: 'var(--pm-error)', marginBottom: '1rem'}}>{error}</div>}
        {success && <div style={{color: 'var(--pm-success)', marginBottom: '1rem'}}>{success}</div>}
        <form onSubmit={handleCreate}>
          <div className="pm-field">
            <div className="pm-field-label">Folder Name</div>
            <input
              className="pm-input"
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              placeholder="Enter folder name"
              autoFocus
              required
            />
          </div>
          <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
            <button type="submit" className="pm-button pm-button-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create'}
            </button>
            <button 
              type="button" 
              className="pm-button pm-button-ghost"
              onClick={() => {
                setShowDialog(false)
                setFolderName('')
                setError('')
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default FolderCreator

