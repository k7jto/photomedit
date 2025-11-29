import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMedia, getThumbnailUrl, downloadMedia, uploadFiles } from '../services/api'

function MediaGrid() {
  const [media, setMedia] = useState([])
  const [loading, setLoading] = useState(true)
  const [reviewStatus, setReviewStatus] = useState('unreviewed')
  const [showUpload, setShowUpload] = useState(false)
  const [uploadName, setUploadName] = useState('')
  const [selectedFiles, setSelectedFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const navigate = useNavigate()
  const { libraryId, folderId } = useParams()

  useEffect(() => {
    loadMedia()
  }, [libraryId, folderId, reviewStatus])

  const loadMedia = async () => {
    if (!libraryId) return
    
    setLoading(true)
    try {
      const folder = folderId ? folderId.replace(`${libraryId}|`, '') : ''
      const response = await getMedia(libraryId, folder, reviewStatus)
      setMedia(response.data)
    } catch (err) {
      console.error('Failed to load media:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMediaClick = (mediaId) => {
    navigate(`/media/${encodeURIComponent(mediaId)}`)
  }

  if (loading) {
    return <div>Loading...</div>
  }

  const handleDownload = async (scope) => {
    if (!libraryId) return
    
    try {
      const folder = folderId ? folderId.replace(`${libraryId}|`, '') : ''
      const response = await downloadMedia(libraryId, scope, folder)
      
      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `download-${scope}-${Date.now()}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert(err.response?.data?.message || 'Download failed')
    }
  }

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files)
    setSelectedFiles(files)
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    
    if (!uploadName.trim() || selectedFiles.length === 0) {
      alert('Please provide an upload name and select files')
      return
    }
    
    setUploading(true)
    
    try {
      await uploadFiles(uploadName, selectedFiles)
      setShowUpload(false)
      setUploadName('')
      setSelectedFiles([])
      loadMedia() // Reload media after upload
      alert('Upload successful! Files will appear after processing.')
    } catch (err) {
      alert(err.response?.data?.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="pm-content">
      <div className="pm-toolbar">
        <div className="pm-toolbar-left">
          <div className="pm-filter-group">
            <div className="pm-filter-label">Review Status</div>
            <div className="pm-pill-group">
              <span
                className={`pm-pill ${reviewStatus === 'unreviewed' ? 'pm-pill-active' : ''}`}
                onClick={() => setReviewStatus('unreviewed')}
                style={{cursor: 'pointer'}}
              >
                Unreviewed
              </span>
              <span
                className={`pm-pill ${reviewStatus === 'reviewed' ? 'pm-pill-active' : ''}`}
                onClick={() => setReviewStatus('reviewed')}
                style={{cursor: 'pointer'}}
              >
                Reviewed
              </span>
              <span
                className={`pm-pill ${reviewStatus === 'all' ? 'pm-pill-active' : ''}`}
                onClick={() => setReviewStatus('all')}
                style={{cursor: 'pointer'}}
              >
                All
              </span>
            </div>
          </div>
        </div>
        <div className="pm-toolbar-right">
          <button
            className="pm-button pm-button-primary"
            onClick={() => setShowUpload(!showUpload)}
            style={{marginRight: '0.5rem'}}
          >
            {showUpload ? 'Cancel Upload' : '+ Upload'}
          </button>
          <button
            className="pm-button pm-button-ghost"
            onClick={() => handleDownload('all')}
            style={{marginRight: '0.5rem'}}
          >
            Download All
          </button>
          <button
            className="pm-button pm-button-ghost"
            onClick={() => handleDownload('reviewed')}
          >
            Download Reviewed
          </button>
        </div>
      </div>

      {showUpload && (
        <div className="pm-form-card" style={{marginBottom: '1.5rem', padding: '1.5rem'}}>
          <h3 style={{marginTop: 0}}>Upload to Current Location</h3>
          <form onSubmit={handleUpload}>
            <div className="pm-field" style={{marginBottom: '1rem'}}>
              <div className="pm-field-label">Upload Name</div>
              <input
                className="pm-input"
                type="text"
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                placeholder="e.g., New Photos"
                required
                maxLength={100}
              />
            </div>
            <div className="pm-field" style={{marginBottom: '1rem'}}>
              <div className="pm-field-label">Select Files</div>
              <input
                type="file"
                multiple
                accept="image/*,video/*"
                onChange={handleFileSelect}
                style={{display: 'none'}}
                id="upload-file-input"
              />
              <label
                htmlFor="upload-file-input"
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
                  {selectedFiles.slice(0, 5).map((f, i) => (
                    <div key={i}>{f.name} ({(f.size / 1024 / 1024).toFixed(2)} MB)</div>
                  ))}
                  {selectedFiles.length > 5 && <div>... and {selectedFiles.length - 5} more</div>}
                </div>
              )}
            </div>
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button
                type="submit"
                className="pm-button pm-button-primary"
                disabled={uploading || !uploadName.trim() || selectedFiles.length === 0}
              >
                {uploading ? 'Uploading...' : 'Upload Files'}
              </button>
              <button
                type="button"
                className="pm-button pm-button-ghost"
                onClick={() => {
                  setShowUpload(false)
                  setUploadName('')
                  setSelectedFiles([])
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
      
      <div className="pm-media-grid-wrap">
        <div className="pm-media-grid">
          {media.map(item => (
            <div
              key={item.id}
              className="pm-media-card"
              onClick={() => handleMediaClick(item.id)}
            >
              <img 
                src={getThumbnailUrl(item.id)} 
                alt={item.filename} 
                className="pm-media-thumb"
                onError={(e) => {
                  e.target.style.display = 'none'
                  e.target.nextSibling.style.display = 'flex'
                }}
              />
              <div className="media-placeholder" style={{display: 'none', width: '100%', aspectRatio: '4/3', alignItems: 'center', justifyContent: 'center', background: 'var(--pm-surface)', color: 'var(--pm-text-muted)'}}>
                No thumbnail
              </div>
              {item.mediaType === 'video' && (
                <div className="pm-media-type-badge">VIDEO</div>
              )}
              {item.reviewStatus === 'reviewed' && (
                <div className="pm-media-status-badge reviewed">✓</div>
              )}
              <div className="pm-media-meta">
                <div className="pm-media-title">{item.filename}</div>
                <div className="pm-media-subline">
                  {item.hasSubject && 'Subject '}
                  {item.hasPeople && 'People '}
                  {item.hasNotes && 'Notes'}
                </div>
              </div>
            </div>
          ))}
        </div>
        {media.length === 0 && (
          <div style={{textAlign: 'center', padding: '3rem', color: 'var(--pm-text-muted)'}}>No media files found</div>
        )}
      </div>
    </div>
  )
}

export default MediaGrid

