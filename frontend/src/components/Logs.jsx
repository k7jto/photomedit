import React, { useState, useEffect } from 'react'
import { getLogs } from '../services/api'
import './Logs.css'

function Logs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [limit, setLimit] = useState(100)
  const [levelFilter, setLevelFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    loadLogs()
  }, [limit, levelFilter, userFilter])

  const loadLogs = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getLogs(limit, levelFilter || null, userFilter || null)
      setLogs(response.data)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load logs')
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  const getLevelColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
        return 'var(--pm-error)'
      case 'WARNING':
        return 'var(--pm-warning)'
      case 'INFO':
        return 'var(--pm-info, #3b82f6)'
      case 'DEBUG':
        return 'var(--pm-text-muted)'
      default:
        return 'var(--pm-text)'
    }
  }

  if (loading) {
    return <div style={{padding: '2rem', textAlign: 'center', color: 'var(--pm-text-muted)'}}>Loading logs...</div>
  }

  return (
    <div className="pm-logs">
      <div className="pm-panel">
        <div className="pm-panel-header">
          <h2>Application Logs</h2>
        </div>

        {error && (
          <div style={{color: 'var(--pm-error)', padding: '0.5rem', marginBottom: '1rem'}}>{error}</div>
        )}

        <div style={{marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap'}}>
          <div className="pm-field" style={{flex: '0 0 auto'}}>
            <div className="pm-field-label">Limit</div>
            <input
              className="pm-input"
              type="number"
              min="1"
              max="1000"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
              style={{width: '100px'}}
            />
          </div>
          <div className="pm-field" style={{flex: '0 0 auto'}}>
            <div className="pm-field-label">Level</div>
            <select
              className="pm-select"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              style={{width: '120px'}}
            >
              <option value="">All</option>
              <option value="ERROR">Error</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
              <option value="DEBUG">Debug</option>
            </select>
          </div>
          <div className="pm-field" style={{flex: '1 1 200px'}}>
            <div className="pm-field-label">User</div>
            <input
              className="pm-input"
              type="text"
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              placeholder="Filter by username"
            />
          </div>
          <button
            className="pm-button pm-button-ghost"
            onClick={loadLogs}
            style={{alignSelf: 'flex-end'}}
          >
            Refresh
          </button>
        </div>

        <div className="pm-table">
          <table style={{width: '100%'}}>
            <thead>
              <tr>
                <th style={{width: '160px'}}>Timestamp</th>
                <th style={{width: '80px'}}>Level</th>
                <th style={{width: '120px'}}>Logger</th>
                <th>Message</th>
                <th style={{width: '100px'}}>User</th>
                <th style={{width: '120px'}}>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id}>
                  <td style={{fontSize: '0.875rem', color: 'var(--pm-text-muted)'}}>
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: 'var(--pm-radius-sm)',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        color: getLevelColor(log.level),
                        background: `${getLevelColor(log.level)}20`
                      }}
                    >
                      {log.level}
                    </span>
                  </td>
                  <td style={{fontSize: '0.875rem', color: 'var(--pm-text-muted)'}}>
                    {log.logger || '-'}
                  </td>
                  <td>
                    <div style={{maxWidth: '500px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                      {log.message}
                    </div>
                    {log.details && (
                      <details style={{marginTop: '0.25rem'}}>
                        <summary style={{fontSize: '0.75rem', color: 'var(--pm-text-muted)', cursor: 'pointer'}}>
                          Details
                        </summary>
                        <pre style={{
                          fontSize: '0.75rem',
                          padding: '0.5rem',
                          background: 'var(--pm-surface)',
                          borderRadius: 'var(--pm-radius-sm)',
                          marginTop: '0.25rem',
                          overflow: 'auto',
                          maxHeight: '200px'
                        }}>
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </td>
                  <td style={{fontSize: '0.875rem'}}>{log.user || '-'}</td>
                  <td style={{fontSize: '0.875rem', color: 'var(--pm-text-muted)'}}>
                    {log.ip_address || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && (
            <div style={{textAlign: 'center', padding: '2rem', color: 'var(--pm-text-muted)'}}>
              No logs found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Logs

