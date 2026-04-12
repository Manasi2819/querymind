import { useEffect, useState } from 'react'
import { fetchStats, disconnectDB } from '../api/client'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [disconnecting, setDisconnecting] = useState(false)
  const [disconnectMsg, setDisconnectMsg] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchStats()
      setStats(data)
    } catch {
      setError('Could not connect to backend service. Make sure the API is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDisconnect = async () => {
    setDisconnecting(true)
    try {
      await disconnectDB()
      setDisconnectMsg('Database disconnected successfully.')
      await load()
    } catch {
      setDisconnectMsg('Failed to disconnect database.')
    } finally {
      setDisconnecting(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">System Overview</h1>
        <p className="page-subtitle">Real-time status of your QueryMind configuration</p>
      </div>

      {error && (
        <div className="alert alert-error">
          <span className="alert-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {loading && !error && (
        <div className="flex-center" style={{ padding: '60px 0' }}>
          <span className="spinner spinner-lg" />
        </div>
      )}

      {stats && !loading && (
        <>
          {/* Stats Grid */}
          <div className="stats-grid">
            <div className="stat-card purple">
              <div className="stat-icon">🗄️</div>
              <div className="stat-value">{stats.tables ?? 0}</div>
              <div className="stat-label">Indexed Tables</div>
            </div>
            <div className="stat-card blue">
              <div className="stat-icon">📚</div>
              <div className="stat-value">{stats.files ?? 0}</div>
              <div className="stat-label">Knowledge Particles</div>
            </div>
            <div className="stat-card green">
              <div className="stat-icon">🤖</div>
              <div className="stat-value" style={{ fontSize: 18, paddingTop: 6 }}>{stats.llm ?? 'N/A'}</div>
              <div className="stat-label">LLM Provider</div>
            </div>
          </div>

          <hr className="section-divider" />

          {/* Active Connections */}
          <div className="section-title">⚡ Active Connections</div>
          <div className="card">
            {disconnectMsg && (
              <div className="alert alert-info" style={{ marginBottom: 14 }}>
                <span className="alert-icon">ℹ️</span>
                <span>{disconnectMsg}</span>
              </div>
            )}
            {stats.db_connected ? (
              <div className="flex-between">
                <div className="alert alert-success" style={{ marginBottom: 0, flex: 1 }}>
                  <span className="alert-icon">✅</span>
                  <span>
                    Database {stats.db_name ? <strong>{stats.db_name}</strong> : ''} is connected and schema is synced.
                  </span>
                </div>

                <button
                  id="disconnect-db-btn"
                  className="btn btn-danger btn-sm"
                  style={{ marginLeft: 16, flexShrink: 0 }}
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                >
                  {disconnecting ? <><span className="spinner" /> Disconnecting...</> : '✕ Disconnect Database'}
                </button>
              </div>
            ) : (
              <div className="alert alert-warning" style={{ marginBottom: 0 }}>
                <span className="alert-icon">⚠️</span>
                <span>No database connected. Go to <strong>Databases</strong> in the sidebar to get started.</span>
              </div>
            )}
          </div>

          <hr className="section-divider" />

          {/* Quick Tips */}
          <div className="section-title">💡 Quick Start Guide</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
            {[
              { step: '1', icon: '⚙️', title: 'Configure LLM', desc: 'Pick Ollama (local) or OpenAI/Anthropic cloud provider.' },
              { step: '2', icon: '🗄️', title: 'Connect Database', desc: 'Link your MySQL, PostgreSQL, or SQLite database.' },
              { step: '3', icon: '📚', title: 'Upload Knowledge', desc: 'Ingest PDFs, Word docs, SQL schemas, and CSVs.' },
            ].map((item) => (
              <div key={item.step} className="card" style={{ padding: '18px 20px' }}>
                <div style={{ fontSize: 22, marginBottom: 8 }}>{item.icon}</div>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 5, color: 'var(--text-primary)' }}>
                  <span style={{ color: 'var(--purple-light)', marginRight: 6 }}>Step {item.step}.</span>
                  {item.title}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{item.desc}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
