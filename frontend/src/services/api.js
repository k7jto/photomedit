import axios from 'axios'

const API_BASE = '/api'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add token to requests if available
let authToken = null
let onUnauthorized = null

export const setUnauthorizedHandler = (handler) => {
  onUnauthorized = handler
}

export const setAuthToken = (token) => {
  authToken = token
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && onUnauthorized) {
      // Clear token and redirect to login
      sessionStorage.removeItem('authToken')
      setAuthToken(null)
      onUnauthorized()
    }
    return Promise.reject(error)
  }
)

// Auth API
export const login = async (username, password, mfaToken = null) => {
  const response = await api.post('/auth/login', { username, password, mfaToken })
  if (response.data.token) {
    setAuthToken(response.data.token)
  }
  return response.data
}

export const forgotPassword = (email) => api.post('/auth/forgot-password', { email })
export const resetPassword = (token, password) => api.post('/auth/reset-password', { token, password })
export const setupMFA = () => api.get('/auth/mfa/setup')
export const verifyMFASetup = (token) => api.post('/auth/mfa/verify', { token })
export const disableMFA = (password) => api.post('/auth/mfa/disable', { password })

// Libraries API
export const getLibraries = () => api.get('/libraries')
export const getFolders = (libraryId, parent = '') => 
  api.get(`/libraries/${libraryId}/folders`, { params: { parent } })
export const getMedia = (libraryId, folderId, reviewStatus = 'unreviewed') => {
  // Handle empty folderId (root folder) - use special route without folder segment
  if (!folderId || folderId === '') {
    return api.get(`/libraries/${libraryId}/folders/media`, { params: { reviewStatus } })
  }
  return api.get(`/libraries/${libraryId}/folders/${folderId}/media`, { params: { reviewStatus } })
}

// Media API
export const getMediaDetail = (mediaId) => api.get(`/media/${mediaId}`)
export const updateMedia = (mediaId, data) => api.patch(`/media/${mediaId}`, data)
export const rejectMedia = (mediaId) => api.post(`/media/${mediaId}/reject`)
export const navigateMedia = (mediaId, direction, reviewStatus = 'unreviewed') =>
  api.get(`/media/${mediaId}/navigate`, { params: { direction, reviewStatus } })

// Get image URLs with auth token
const getImageUrl = (mediaId, type) => {
  const token = sessionStorage.getItem('authToken')
  const encodedId = encodeURIComponent(mediaId)
  return `${API_BASE}/media/${encodedId}/${type}${token ? `?token=${encodeURIComponent(token)}` : ''}`
}

export const getPreviewUrl = (mediaId) => getImageUrl(mediaId, 'preview')
export const getThumbnailUrl = (mediaId) => getImageUrl(mediaId, 'thumbnail')

// Search API
export const search = (params) => api.get('/search', { params })

// Admin API
export const getUsers = () => api.get('/admin/users')
export const getLogs = (limit = 100, level = null, user = null) => {
  const params = { limit }
  if (level) params.level = level
  if (user) params.user = user
  return api.get('/admin/logs', { params })
}
export const createUser = (userData) => api.post('/admin/users', {
  username: userData.username,
  email: userData.email,
  password: userData.password,
  role: userData.role || (userData.isAdmin ? 'admin' : 'user')
})
export const updateUser = (username, userData) => api.put(`/admin/users/${username}`, {
  password: userData.password || undefined,
  role: userData.role || (userData.isAdmin ? 'admin' : 'user')
})
export const deleteUser = (username) => api.delete(`/admin/users/${username}`)

// Upload API
export const uploadFiles = (uploadName, files, libraryId = null, folder = null) => {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  if (uploadName) {
    formData.append('uploadName', uploadName)
  }
  if (libraryId) {
    formData.append('libraryId', libraryId)
  }
  if (folder) {
    formData.append('folder', folder)
  }
  // Don't set Content-Type header - let axios set it automatically with boundary
  return api.post('/upload', formData, {
    headers: { 'Content-Type': undefined }
  })
}

// Download API
export const downloadMedia = (libraryId, scope, folder = '') => {
  return api.post('/download', { libraryId, scope, folder }, {
    responseType: 'blob'
  })
}

export default api

