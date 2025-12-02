import React, { createContext, useContext, useState, useCallback } from 'react'

const MediaCacheContext = createContext()

export const useMediaCache = () => {
  const context = useContext(MediaCacheContext)
  if (!context) {
    throw new Error('useMediaCache must be used within MediaCacheProvider')
  }
  return context
}

export const MediaCacheProvider = ({ children }) => {
  // Cache structure: { 'libraryId|folderId|reviewStatus': { data: [...], timestamp: number } }
  const [cache, setCache] = useState({})

  const getCacheKey = (libraryId, folderId, reviewStatus) => {
    return `${libraryId}|${folderId || ''}|${reviewStatus}`
  }

  const getCachedMedia = useCallback((libraryId, folderId, reviewStatus, maxAge = 5 * 60 * 1000) => {
    const key = getCacheKey(libraryId, folderId, reviewStatus)
    const cached = cache[key]
    
    if (cached && (Date.now() - cached.timestamp) < maxAge) {
      return cached.data
    }
    
    return null
  }, [cache])

  const setCachedMedia = useCallback((libraryId, folderId, reviewStatus, data) => {
    const key = getCacheKey(libraryId, folderId, reviewStatus)
    setCache(prev => ({
      ...prev,
      [key]: {
        data: data,
        timestamp: Date.now()
      }
    }))
  }, [])

  const updateMediaItem = useCallback((libraryId, folderId, reviewStatus, mediaId, updates) => {
    const key = getCacheKey(libraryId, folderId, reviewStatus)
    setCache(prev => {
      const cached = prev[key]
      if (!cached) return prev

      const updatedData = cached.data.map(item => {
        if (item.id === mediaId) {
          return { ...item, ...updates }
        }
        return item
      })

      return {
        ...prev,
        [key]: {
          ...cached,
          data: updatedData
        }
      }
    })
  }, [])

  const removeMediaItem = useCallback((libraryId, folderId, reviewStatus, mediaId) => {
    const key = getCacheKey(libraryId, folderId, reviewStatus)
    setCache(prev => {
      const cached = prev[key]
      if (!cached) return prev

      const updatedData = cached.data.filter(item => item.id !== mediaId)

      return {
        ...prev,
        [key]: {
          ...cached,
          data: updatedData
        }
      }
    })
  }, [])

  const invalidateCache = useCallback((libraryId, folderId, reviewStatus) => {
    const key = getCacheKey(libraryId, folderId, reviewStatus)
    setCache(prev => {
      const newCache = { ...prev }
      delete newCache[key]
      return newCache
    })
  }, [])

  const clearCache = useCallback(() => {
    setCache({})
  }, [])

  return (
    <MediaCacheContext.Provider value={{
      getCachedMedia,
      setCachedMedia,
      updateMediaItem,
      removeMediaItem,
      invalidateCache,
      clearCache
    }}>
      {children}
    </MediaCacheContext.Provider>
  )
}


