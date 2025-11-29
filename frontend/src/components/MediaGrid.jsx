import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMedia, getThumbnailUrl, downloadMedia } from '../services/api'

function MediaGrid() {
  const [media, setMedia] = useState([])
  const [loading, setLoading] = useState(true)
  const [reviewStatus, setReviewStatus] = useState('unreviewed')
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

