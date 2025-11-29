import React, { useState, useEffect } from 'react'
import { getUsers, createUser, updateUser, deleteUser } from '../services/api'
import './Admin.css'

function Admin() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [formData, setFormData] = useState({ username: '', email: '', password: '', role: 'user' })

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getUsers()
      setUsers(response.data || [])
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load users')
      setUsers([]) // Set empty array on error to prevent blank page
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    
    try {
      const response = await createUser(formData)
      setSuccess('User created successfully')
      setShowCreateForm(false)
      setFormData({ username: '', email: '', password: '', role: 'user' })
      await loadUsers() // Wait for users to reload
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create user')
      setShowCreateForm(true) // Keep form open on error
    }
  }

  const handleUpdate = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    
    try {
      await updateUser(editingUser.username, formData)
      setSuccess('User updated successfully')
      setEditingUser(null)
      setFormData({ username: '', email: '', password: '', role: 'user' })
      loadUsers()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update user')
    }
  }

  const handleDelete = async (username) => {
    if (!window.confirm(`Delete user "${username}"?`)) {
      return
    }
    
    setError('')
    setSuccess('')
    
    try {
      await deleteUser(username)
      setSuccess('User deleted successfully')
      loadUsers()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to delete user')
    }
  }

  const startEdit = (user) => {
    setEditingUser(user)
    setFormData({
      username: user.username || user.get('username'),
      email: user.email || user.get('email') || '',
      password: '',
      role: user.role || (user.isAdmin || user.get('isAdmin', false) ? 'admin' : 'user')
    })
    setShowCreateForm(false)
  }

  return (
    <div className="pm-admin">
      {loading && (
        <div style={{padding: '2rem', textAlign: 'center', color: 'var(--pm-text-muted)'}}>
          Loading users...
        </div>
      )}
      <div className="pm-panel">
        <div className="pm-panel-header">
          <h2>User Management</h2>
          <button 
            className="pm-button pm-button-primary"
            onClick={() => {
              setShowCreateForm(true)
              setEditingUser(null)
              setFormData({ username: '', email: '', password: '', role: 'user' })
            }}
          >
            + Add User
          </button>
        </div>

        {error && <div style={{color: 'var(--pm-error)', padding: '0.5rem', marginBottom: '1rem'}}>{error}</div>}
        {success && <div style={{color: 'var(--pm-success)', padding: '0.5rem', marginBottom: '1rem'}}>{success}</div>}

        {showCreateForm && (
          <div className="pm-form-card" style={{marginBottom: '1rem'}}>
            <h3>Create User</h3>
            <form onSubmit={handleCreate}>
              <div className="pm-field">
                <div className="pm-field-label">Username</div>
                <input
                  className="pm-input"
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  required
                />
              </div>
              <div className="pm-field">
                <div className="pm-field-label">Email</div>
                <input
                  className="pm-input"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              <div className="pm-field">
                <div className="pm-field-label">Password</div>
                <input
                  className="pm-input"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  required
                />
              </div>
              <div className="pm-field">
                <div className="pm-field-label">Role</div>
                <select
                  className="pm-select"
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
                <button type="submit" className="pm-button pm-button-primary">Create</button>
                <button 
                  type="button" 
                  className="pm-button pm-button-ghost"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {editingUser && (
          <div className="pm-form-card" style={{marginBottom: '1rem'}}>
            <h3>Edit User: {editingUser.username}</h3>
            <form onSubmit={handleUpdate}>
              <div className="pm-field">
                <div className="pm-field-label">Email</div>
                <input
                  className="pm-input"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              <div className="pm-field">
                <div className="pm-field-label">New Password (leave empty to keep current)</div>
                <input
                  className="pm-input"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  placeholder="Enter new password or leave empty"
                />
              </div>
              <div className="pm-field">
                <div className="pm-field-label">Role</div>
                <select
                  className="pm-select"
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
                <button type="submit" className="pm-button pm-button-primary">Update</button>
                <button 
                  type="button" 
                  className="pm-button pm-button-ghost"
                  onClick={() => {
                    setEditingUser(null)
                    setFormData({ username: '', email: '', password: '', role: 'user' })
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="pm-table">
          <table style={{width: '100%'}}>
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>MFA</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.username || user.get('username')}>
                  <td>{user.username || user.get('username')}</td>
                  <td>{user.email || user.get('email') || ''}</td>
                  <td>{user.role || (user.isAdmin || user.get('isAdmin', false) ? 'admin' : 'user')}</td>
                  <td>{user.mfaEnabled ? '✓' : ''}</td>
                  <td>{user.lastLogin ? new Date(user.lastLogin).toLocaleString() : 'Never'}</td>
                  <td>
                    {user.source !== 'config' && (
                      <>
                        <button 
                          className="pm-button pm-button-ghost"
                          onClick={() => startEdit(user)}
                          style={{marginRight: '0.5rem'}}
                        >
                          Edit
                        </button>
                        {user.mfaEnabled && (
                          <button 
                            className="pm-button pm-button-ghost"
                            onClick={async () => {
                              if (window.confirm(`Disable MFA for "${user.username || user.get('username')}"?`)) {
                                try {
                                  await fetch(`/api/admin/users/${user.username || user.get('username')}/disable-mfa`, {
                                    method: 'POST',
                                    headers: {
                                      'Authorization': `Bearer ${sessionStorage.getItem('authToken')}`,
                                      'Content-Type': 'application/json'
                                    }
                                  })
                                  loadUsers()
                                } catch (err) {
                                  alert('Failed to disable MFA')
                                }
                              }
                            }}
                            style={{marginRight: '0.5rem', fontSize: '0.875rem'}}
                            title="Disable MFA (recovery)"
                          >
                            Disable MFA
                          </button>
                        )}
                        <button 
                          className="pm-button pm-button-ghost"
                          onClick={() => handleDelete(user.username || user.get('username'))}
                          style={{color: 'var(--pm-error)'}}
                        >
                          Delete
                        </button>
                      </>
                    )}
                    {user.source === 'config' && (
                      <span style={{color: 'var(--pm-text-muted)', fontSize: '0.875rem'}}>Config user</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Admin

