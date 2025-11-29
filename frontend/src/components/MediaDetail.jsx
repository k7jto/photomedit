import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMediaDetail, updateMedia, rejectMedia, navigateMedia, getPreviewUrl, getThumbnailUrl } from '../services/api'

function MediaDetail() {
  const [media, setMedia] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [formData, setFormData] = useState({})
  const [markReviewed, setMarkReviewed] = useState(true)
  const navigate = useNavigate()
  const { mediaId } = useParams()

  useEffect(() => {
    loadMedia()
  }, [mediaId])

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'Escape') {
        navigate(-1)
      } else if (e.key === 'ArrowLeft' || (e.ctrlKey && e.key === 'ArrowLeft')) {
        handleNavigate('previous')
      } else if (e.key === 'ArrowRight' || (e.ctrlKey && e.key === 'ArrowRight')) {
        handleNavigate('next')
      } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [media, formData])

  const loadMedia = async () => {
    if (!mediaId) return
    
    setLoading(true)
    setError('')
    try {
      const response = await getMediaDetail(decodeURIComponent(mediaId))
      setMedia(response.data)
      const metadata = response.data.logicalMetadata || {}
      setFormData({
        eventDate: metadata.eventDate || '',
        eventDateDisplay: metadata.eventDateDisplay || '',
        eventDatePrecision: metadata.eventDatePrecision || 'UNKNOWN',
        eventDateApproximate: metadata.eventDateApproximate || false,
        subject: metadata.subject || '',
        notes: metadata.notes || '',
        people: (metadata.people || []).join(', '),
        locationName: metadata.locationName || '',
        reviewStatus: metadata.reviewStatus || 'unreviewed'
      })
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load media')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setSuccess('')
    setError('')
  }

  const handleSave = async () => {
    if (!media) return
    
    setSaving(true)
    setError('')
    setSuccess('')
    
    try {
      const updateData = {
        ...formData,
        people: formData.people ? formData.people.split(',').map(p => p.trim()).filter(p => p) : [],
        markReviewed: markReviewed
      }
      await updateMedia(decodeURIComponent(mediaId), updateData)
      setSuccess('Metadata saved successfully' + (markReviewed ? ' and marked as reviewed' : ''))
      if (markReviewed) {
        setFormData(prev => ({ ...prev, reviewStatus: 'reviewed' }))
      }
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save metadata')
    } finally {
      setSaving(false)
    }
  }

  const handleReject = async () => {
    if (!media || !window.confirm('Move this image to the rejected folder? It will be excluded from exports.')) {
      return
    }
    
    setRejecting(true)
    setError('')
    setSuccess('')
    
    try {
      await rejectMedia(decodeURIComponent(mediaId))
      setSuccess('Image moved to rejected folder')
      // Navigate back after a short delay
      setTimeout(() => {
        navigate(-1)
      }, 1500)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reject image')
      setRejecting(false)
    }
  }

  const handleNavigate = async (direction) => {
    if (!media) return
    
    try {
      const reviewStatus = formData.reviewStatus || 'unreviewed'
      const response = await navigateMedia(decodeURIComponent(mediaId), direction, reviewStatus)
      if (response.data.nextId) {
        navigate(`/media/${encodeURIComponent(response.data.nextId)}`)
      }
    } catch (err) {
      console.error('Navigation failed:', err)
    }
  }

  if (loading) {
    return <div>Loading...</div>
  }

  if (!media) {
    return <div>Media not found</div>
  }

  return (
    <div className="pm-grid-and-detail">
      <div className="pm-media-grid-wrap">
        <div className="pm-toolbar">
          <div className="pm-toolbar-left">
            <button className="pm-button pm-button-ghost" onClick={() => navigate(-1)}>← Back</button>
            <span className="pm-media-title" style={{marginLeft: '1rem'}}>{media.filename}</span>
          </div>
          <div className="pm-toolbar-right">
            <button className="pm-button pm-button-ghost" onClick={() => handleNavigate('previous')}>← Previous</button>
            <button className="pm-button pm-button-ghost" onClick={() => handleNavigate('next')}>Next →</button>
          </div>
        </div>
        <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', padding: '2rem', background: 'var(--pm-surface)', borderRadius: 'var(--pm-radius-md)'}}>
          <img 
            src={getPreviewUrl(mediaId)} 
            alt={media.filename} 
            style={{
              maxWidth: '100%',
              maxHeight: '80vh',
              objectFit: 'contain',
              borderRadius: 'var(--pm-radius-md)'
            }}
            onError={(e) => {
              // Fallback to thumbnail if preview fails
              e.target.src = getThumbnailUrl(mediaId)
            }}
          />
        </div>
      </div>
      
      <div className="pm-detail">
        <div className="pm-detail-meta">
          {error && <div style={{color: 'var(--pm-error)', padding: '0.5rem', background: 'rgba(249, 115, 115, 0.1)', borderRadius: 'var(--pm-radius-sm)', marginBottom: '1rem'}}>{error}</div>}
          {success && <div style={{color: 'var(--pm-success)', padding: '0.5rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: 'var(--pm-radius-sm)', marginBottom: '1rem'}}>{success}</div>}
          
          <div className="pm-field">
            <div className="pm-field-label">Event Date</div>
            <input
              className="pm-input"
              type="text"
              value={formData.eventDate || ''}
              onChange={(e) => handleChange('eventDate', e.target.value)}
              placeholder="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
            />
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">Event Date Display</div>
            <input
              className="pm-input"
              type="text"
              value={formData.eventDateDisplay || ''}
              onChange={(e) => handleChange('eventDateDisplay', e.target.value)}
              placeholder="e.g., Summer 1923"
            />
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">Date Precision</div>
            <select
              className="pm-select-small"
              value={formData.eventDatePrecision || 'UNKNOWN'}
              onChange={(e) => handleChange('eventDatePrecision', e.target.value)}
            >
              <option value="YEAR">Year</option>
              <option value="MONTH">Month</option>
              <option value="DAY">Day</option>
              <option value="UNKNOWN">Unknown</option>
            </select>
          </div>
          
          <div className="pm-field">
            <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer'}}>
              <input
                type="checkbox"
                checked={formData.eventDateApproximate || false}
                onChange={(e) => handleChange('eventDateApproximate', e.target.checked)}
                style={{cursor: 'pointer'}}
              />
              <span className="pm-field-label" style={{margin: 0}}>Approximate Date</span>
            </label>
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">Subject</div>
            <input
              className="pm-input"
              type="text"
              value={formData.subject || ''}
              onChange={(e) => handleChange('subject', e.target.value)}
            />
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">Notes</div>
            <textarea
              className="pm-textarea"
              value={formData.notes || ''}
              onChange={(e) => handleChange('notes', e.target.value)}
            />
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">People (comma-separated)</div>
            <input
              className="pm-input"
              type="text"
              value={formData.people || ''}
              onChange={(e) => handleChange('people', e.target.value)}
              placeholder="John Doe, Jane Smith"
            />
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">Location</div>
            <input
              className="pm-input"
              type="text"
              value={formData.locationName || ''}
              onChange={(e) => handleChange('locationName', e.target.value)}
            />
          </div>
          
          <div className="pm-field">
            <div className="pm-field-label">Review Status</div>
            <div style={{display: 'flex', gap: '1rem', alignItems: 'center'}}>
              <select
                className="pm-select-small"
                value={formData.reviewStatus || 'unreviewed'}
                onChange={(e) => handleChange('reviewStatus', e.target.value)}
                style={{flex: 1}}
              >
                <option value="unreviewed">Unreviewed</option>
                <option value="reviewed">Reviewed</option>
              </select>
              <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', whiteSpace: 'nowrap'}}>
                <input
                  type="checkbox"
                  checked={markReviewed}
                  onChange={(e) => setMarkReviewed(e.target.checked)}
                  style={{cursor: 'pointer'}}
                />
                <span className="pm-field-label" style={{margin: 0, fontSize: '0.875rem'}}>Mark reviewed when saving</span>
              </label>
            </div>
          </div>
          
          <div style={{marginTop: '1rem', display: 'flex', gap: '0.5rem'}}>
            <button className="pm-button pm-button-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save (S)'}
            </button>
            <button 
              className="pm-button pm-button-ghost" 
              onClick={handleReject} 
              disabled={rejecting}
              style={{color: 'var(--pm-error)', borderColor: 'var(--pm-error)'}}
            >
              {rejecting ? 'Moving...' : 'Reject'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MediaDetail

