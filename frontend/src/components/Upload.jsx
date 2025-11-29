import React, { useState } from 'react'
import { uploadFiles } from '../services/api'
import './Upload.css'

function Upload() {
  const [uploadName, setUploadName] = useState('')
  const [selectedFiles, setSelectedFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files)
    setSelectedFiles(files)
    setError('')
    setResult(null)
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    
    if (!uploadName.trim()) {
      setError('Upload name is required')
      return
    }
    
    if (selectedFiles.length === 0) {
      setError('Please select at least one file')
      return
    }
    
    setUploading(true)
    setError('')
    setResult(null)
    
    try {
      const response = await uploadFiles(uploadName, selectedFiles)
      setResult(response.data)
      setUploadName('')
      setSelectedFiles([])
      // Reset file input
      const fileInput = document.getElementById('file-input')
      if (fileInput) fileInput.value = ''
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const successCount = result?.files?.filter(f => f.status === 'ok').length || 0
  const errorCount = result?.files?.filter(f => f.status === 'error').length || 0

  return (
    <div className="pm-upload">
      <div className="pm-panel">
        <h2>Upload Media</h2>
        <p style={{color: 'var(--pm-text-muted)', marginBottom: '1.5rem'}}>
          Upload photos and videos. Files will be placed in a new folder named after your upload.
          Only image and video files are accepted.
        </p>

        {error && (
          <div style={{
            padding: '0.75rem',
            marginBottom: '1rem',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--pm-error)',
            borderRadius: 'var(--pm-radius-sm)',
            color: 'var(--pm-error)'
          }}>
            {error}
          </div>
        )}

        {result && (
          <div style={{
            padding: '1rem',
            marginBottom: '1.5rem',
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid var(--pm-success)',
            borderRadius: 'var(--pm-radius-sm)'
          }}>
            <h3 style={{marginTop: 0}}>Upload Complete</h3>
            <p>Upload ID: <code>{result.uploadId}</code></p>
            <p>Target Directory: <code>{result.targetDirectory}</code></p>
            <p style={{marginBottom: 0}}>
              {successCount} file(s) uploaded successfully
              {errorCount > 0 && `, ${errorCount} file(s) failed`}
            </p>
            {errorCount > 0 && (
              <details style={{marginTop: '1rem'}}>
                <summary style={{cursor: 'pointer'}}>View Errors</summary>
                <ul style={{marginTop: '0.5rem', paddingLeft: '1.5rem'}}>
                  {result.files
                    .filter(f => f.status === 'error')
                    .map((f, i) => (
                      <li key={i}>
                        <strong>{f.originalName}</strong>: {f.errorMessage || f.errorCode}
                      </li>
                    ))}
                </ul>
              </details>
            )}
          </div>
        )}

        <form onSubmit={handleUpload}>
          <div className="pm-field">
            <div className="pm-field-label">Name this upload</div>
            <input
              className="pm-input"
              type="text"
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              placeholder="e.g., Grandma Box 1"
              required
              maxLength={100}
            />
            <div style={{fontSize: '0.875rem', color: 'var(--pm-text-muted)', marginTop: '0.25rem'}}>
              This will be used to create a folder for your files
            </div>
          </div>

          <div className="pm-field">
            <div className="pm-field-label">Choose photos and videos</div>
            <input
              id="file-input"
              type="file"
              multiple
              accept="image/*,video/*"
              onChange={handleFileSelect}
              style={{display: 'none'}}
            />
            <label
              htmlFor="file-input"
              className="pm-button pm-button-ghost"
              style={{
                display: 'inline-block',
                cursor: 'pointer',
                padding: '0.75rem 1.5rem',
                border: '2px dashed var(--pm-border-soft)',
                borderRadius: 'var(--pm-radius-md)',
                textAlign: 'center',
                width: '100%'
              }}
            >
              {selectedFiles.length > 0
                ? `${selectedFiles.length} file(s) selected`
                : 'Click to select files'}
            </label>
            {selectedFiles.length > 0 && (
              <div style={{marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--pm-text-muted)'}}>
                {selectedFiles.map((f, i) => (
                  <div key={i}>{f.name} ({(f.size / 1024 / 1024).toFixed(2)} MB)</div>
                ))}
              </div>
            )}
          </div>

          <div style={{marginTop: '1.5rem'}}>
            <button
              type="submit"
              className="pm-button pm-button-primary"
              disabled={uploading || !uploadName.trim() || selectedFiles.length === 0}
            >
              {uploading ? 'Uploading...' : 'Upload Files'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Upload

