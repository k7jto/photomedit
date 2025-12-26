import React, { useState, useEffect } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { getMediaDetail, updateMedia, rejectMedia, navigateMedia, getPreviewUrl, getThumbnailUrl, getPublishConfig, publishMedia } from '../services/api'
import { useMediaCache } from '../contexts/MediaCacheContext'

function MediaDetail() {
  const [media, setMedia] = useState(null)
  const [loading, setLoading] = useState(true)
  const [navigating, setNavigating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [formData, setFormData] = useState({})
  const [markReviewed, setMarkReviewed] = useState(true)
  const [showCorrectionDialog, setShowCorrectionDialog] = useState(false)
  const [correctionNotes, setCorrectionNotes] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [damConfig, setDamConfig] = useState(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { mediaId } = useParams()
  const { updateMediaItem, removeMediaItem } = useMediaCache()
  
  // Extract libraryId and folderId from the previous location state or mediaId
  const getLibraryAndFolder = () => {
    // Try to get from location state (set when navigating from MediaGrid)
    if (location.state?.libraryId && location.state?.folderId !== undefined) {
      return {
        libraryId: location.state.libraryId,
        folderId: location.state.folderId,
        reviewStatus: location.state.reviewStatus || 'unreviewed'
      }
    }
    
    // Fallback: extract from mediaId (format: "libraryId|relativePath")
    if (mediaId && mediaId.includes('|')) {
      const [libraryId, ...pathParts] = mediaId.split('|')
      const relativePath = pathParts.join('|')
      // Extract folder from path (everything except filename)
      const pathPartsArray = relativePath.split('/')
      const folderId = pathPartsArray.length > 1 
        ? pathPartsArray.slice(0, -1).join('/')
        : ''
      return { libraryId, folderId, reviewStatus: 'unreviewed' }
    }
    
    return null
  }

  useEffect(() => {
    loadMedia()
  }, [mediaId])

  useEffect(() => {
    // Load DAM config once
    getPublishConfig().then(response => {
      setDamConfig(response.data)
    }).catch(() => {
      // DAM not configured, that's fine
      setDamConfig({ enabled: false })
    })
  }, [])

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'Escape') {
        navigate(-1)
      } else if ((e.key === 'ArrowLeft' || (e.ctrlKey && e.key === 'ArrowLeft')) && !navigating && !loading) {
        handleNavigate('previous')
      } else if ((e.key === 'ArrowRight' || (e.ctrlKey && e.key === 'ArrowRight')) && !navigating && !loading) {
        handleNavigate('next')
      } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (!saving) {
          handleSave()
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [media, formData, navigating, loading, saving])

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
        reviewStatus: metadata.reviewStatus || 'unreviewed',
        correctionNeeded: metadata.correctionNeeded || false,
        correctionNotes: metadata.correctionNotes || ''
      })
      setCorrectionNotes(metadata.correctionNotes || '')
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
        
        // Update cache optimistically
        const context = getLibraryAndFolder()
        if (context) {
          updateMediaItem(
            context.libraryId,
            context.folderId,
            context.reviewStatus,
            decodeURIComponent(mediaId),
            { reviewStatus: 'reviewed' }
          )
          
          // If filtering by unreviewed, remove from cache
          if (context.reviewStatus === 'unreviewed') {
            removeMediaItem(
              context.libraryId,
              context.folderId,
              context.reviewStatus,
              decodeURIComponent(mediaId)
            )
          }
        }
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
    if (!media || navigating) return
    
    setNavigating(true)
    setError('')
    
    try {
      const context = getLibraryAndFolder()
      const reviewStatus = context?.reviewStatus || formData.reviewStatus || 'unreviewed'
      const response = await navigateMedia(decodeURIComponent(mediaId), direction, reviewStatus)
      
      if (response.data.nextId) {
        // Preserve location state when navigating
        navigate(`/media/${encodeURIComponent(response.data.nextId)}`, {
          state: context || {
            libraryId: mediaId.split('|')[0],
            folderId: '',
            reviewStatus
          }
        })
      } else {
        // No next/previous item found
        setError(`No ${direction === 'next' ? 'next' : 'previous'} item found`)
        setTimeout(() => setError(''), 2000)
      }
    } catch (err) {
      console.error('Navigation failed:', err)
      setError(err.response?.data?.message || `Failed to navigate ${direction}`)
      setTimeout(() => setError(''), 3000)
    } finally {
      setNavigating(false)
    }
  }

  const handleFlagForCorrection = async () => {
    if (!media) return
    
    setSaving(true)
    setError('')
    setSuccess('')
    
    try {
      const updateData = {
        correctionNeeded: true,
        correctionNotes: correctionNotes
      }
      await updateMedia(decodeURIComponent(mediaId), updateData)
      setFormData(prev => ({ 
        ...prev, 
        correctionNeeded: true,
        correctionNotes: correctionNotes
      }))
      setSuccess('Image flagged for correction')
      setShowCorrectionDialog(false)
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to flag for correction')
    } finally {
      setSaving(false)
    }
  }

  const handleClearCorrectionFlag = async () => {
    if (!media) return
    
    setSaving(true)
    setError('')
    setSuccess('')
    
    try {
      const updateData = {
        correctionNeeded: false,
        correctionNotes: ''
      }
      await updateMedia(decodeURIComponent(mediaId), updateData)
      setFormData(prev => ({ 
        ...prev, 
        correctionNeeded: false,
        correctionNotes: ''
      }))
      setCorrectionNotes('')
      setSuccess('Correction flag cleared')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to clear correction flag')
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!media || !damConfig?.enabled) return
    
    if (!window.confirm(`Publish this image to ${damConfig.name}? The file will be copied to the DAM folder.`)) {
      return
    }
    
    setPublishing(true)
    setError('')
    setSuccess('')
    
    try {
      const response = await publishMedia([decodeURIComponent(mediaId)])
      if (response.data.published > 0) {
        setFormData(prev => ({ 
          ...prev, 
          isPublished: true,
          publishedTo: damConfig.name
        }))
        setSuccess(`Published to ${damConfig.name}`)
        setTimeout(() => setSuccess(''), 3000)
      } else if (response.data.results?.[0]?.message) {
        setError(response.data.results[0].message)
      } else {
        setError('Failed to publish')
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to publish')
    } finally {
      setPublishing(false)
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
            <button 
              className="pm-button pm-button-ghost" 
              onClick={() => handleNavigate('previous')}
              disabled={navigating || loading}
            >
              {navigating ? 'Loading...' : '← Previous'}
            </button>
            <button 
              className="pm-button pm-button-ghost" 
              onClick={() => handleNavigate('next')}
              disabled={navigating || loading}
            >
              {navigating ? 'Loading...' : 'Next →'}
            </button>
          </div>
        </div>
        <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', padding: '2rem', background: 'var(--pm-surface)', borderRadius: 'var(--pm-radius-md)', position: 'relative'}}>
          {(loading || navigating) && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 10,
              background: 'rgba(15, 23, 42, 0.95)',
              padding: '1rem 2rem',
              borderRadius: 'var(--pm-radius-md)',
              border: '1px solid var(--pm-border-soft)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              color: 'var(--pm-text)'
            }}>
              <div style={{
                width: '20px',
                height: '20px',
                border: '2px solid var(--pm-accent-soft)',
                borderTopColor: 'var(--pm-accent)',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite'
              }}></div>
              <span>{loading ? 'Loading image...' : 'Loading next image...'}</span>
            </div>
          )}
          <img 
            src={getPreviewUrl(mediaId)} 
            alt={media.filename} 
            style={{
              maxWidth: '100%',
              maxHeight: '80vh',
              objectFit: 'contain',
              borderRadius: 'var(--pm-radius-md)',
              opacity: (loading || navigating) ? 0.3 : 1,
              transition: 'opacity 0.2s ease'
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
          
          {/* Published Indicator */}
          {formData.isPublished && (
            <div style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              borderRadius: 'var(--pm-radius-sm)',
              color: '#10b981'
            }}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '600'}}>
                <span>✓</span> Published to {formData.publishedTo || 'DAM'}
              </div>
              {formData.publishedAt && (
                <div style={{fontSize: '0.75rem', color: 'var(--pm-text-muted)', marginTop: '0.25rem'}}>
                  {new Date(formData.publishedAt).toLocaleString()}
                </div>
              )}
            </div>
          )}
          
          {/* Correction Flag Indicator */}
          {formData.correctionNeeded && (
            <div style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: 'rgba(251, 191, 36, 0.15)',
              border: '1px solid rgba(251, 191, 36, 0.4)',
              borderRadius: 'var(--pm-radius-sm)',
              color: '#fbbf24'
            }}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '600', marginBottom: '0.25rem'}}>
                <span>⚠️</span> Flagged for Correction
              </div>
              {formData.correctionNotes && (
                <div style={{fontSize: '0.875rem', color: 'var(--pm-text-muted)', marginTop: '0.25rem'}}>
                  {formData.correctionNotes}
                </div>
              )}
              <button
                className="pm-button pm-button-ghost"
                onClick={handleClearCorrectionFlag}
                disabled={saving}
                style={{marginTop: '0.5rem', fontSize: '0.75rem', padding: '0.25rem 0.5rem'}}
              >
                Clear Flag
              </button>
            </div>
          )}
          
          <div style={{marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap'}}>
            <button className="pm-button pm-button-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save (S)'}
            </button>
            <button 
              className="pm-button pm-button-ghost" 
              onClick={() => {
                setCorrectionNotes(formData.correctionNotes || '')
                setShowCorrectionDialog(true)
              }}
              disabled={saving}
              style={{
                color: formData.correctionNeeded ? '#fbbf24' : 'var(--pm-text-muted)',
                borderColor: formData.correctionNeeded ? '#fbbf24' : 'var(--pm-border)'
              }}
            >
              {formData.correctionNeeded ? '⚠️ Edit Flag' : '🚩 Flag for Correction'}
            </button>
            <button 
              className="pm-button pm-button-ghost" 
              onClick={handleReject} 
              disabled={rejecting}
              style={{color: 'var(--pm-error)', borderColor: 'var(--pm-error)'}}
            >
              {rejecting ? 'Moving...' : 'Reject'}
            </button>
            {damConfig?.enabled && !formData.isPublished && (
              <button 
                className="pm-button pm-button-ghost" 
                onClick={handlePublish}
                disabled={publishing || formData.correctionNeeded}
                style={{
                  color: formData.correctionNeeded ? 'var(--pm-text-muted)' : '#10b981',
                  borderColor: formData.correctionNeeded ? 'var(--pm-border)' : '#10b981'
                }}
                title={formData.correctionNeeded ? 'Clear correction flag before publishing' : `Publish to ${damConfig.name}`}
              >
                {publishing ? 'Publishing...' : `📤 Publish to ${damConfig.name}`}
              </button>
            )}
          </div>
          
          {/* Correction Dialog */}
          {showCorrectionDialog && (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }} onClick={() => setShowCorrectionDialog(false)}>
              <div style={{
                background: 'var(--pm-surface)',
                padding: '1.5rem',
                borderRadius: 'var(--pm-radius-md)',
                border: '1px solid var(--pm-border)',
                maxWidth: '500px',
                width: '90%',
                boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)'
              }} onClick={e => e.stopPropagation()}>
                <h3 style={{margin: '0 0 1rem 0', color: 'var(--pm-text)'}}>
                  🚩 Flag for Correction
                </h3>
                <p style={{color: 'var(--pm-text-muted)', fontSize: '0.875rem', marginBottom: '1rem'}}>
                  Describe what corrections are needed for this image:
                </p>
                {error && (
                  <div style={{color: 'var(--pm-error)', padding: '0.5rem', background: 'rgba(249, 115, 115, 0.1)', borderRadius: 'var(--pm-radius-sm)', marginBottom: '1rem', fontSize: '0.875rem'}}>
                    {error}
                  </div>
                )}
                <textarea
                  className="pm-textarea"
                  value={correctionNotes}
                  onChange={(e) => setCorrectionNotes(e.target.value)}
                  placeholder="e.g., Needs dust removal, color correction, cropping adjustment..."
                  style={{minHeight: '100px', marginBottom: '1rem'}}
                  autoFocus
                />
                <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'flex-end'}}>
                  <button 
                    className="pm-button pm-button-ghost" 
                    onClick={() => {
                      setShowCorrectionDialog(false)
                      setError('')
                    }}
                  >
                    Cancel
                  </button>
                  <button 
                    className="pm-button pm-button-primary" 
                    onClick={async () => {
                      await handleFlagForCorrection()
                    }}
                    disabled={saving}
                    style={{background: '#fbbf24', borderColor: '#fbbf24', color: '#000'}}
                  >
                    {saving ? 'Saving...' : 'Flag Image'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default MediaDetail

