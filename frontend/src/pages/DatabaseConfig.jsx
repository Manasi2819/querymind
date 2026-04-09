import { useEffect, useState } from 'react'
import { getDBConfig, setDBConfig } from '../api/client'

const DEFAULT_PORTS = { mysql: 3306, postgresql: 5432, sqlite: 0 }

export default function DatabaseConfig() {
  const [dbType, setDbType] = useState('mysql')
  const [method, setMethod] = useState('fields') // 'fields' | 'url'
  const [host, setHost] = useState('localhost')
  const [port, setPort] = useState(3306)
  const [database, setDatabase] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [connUrl, setConnUrl] = useState('')
  const [fetchSchema, setFetchSchema] = useState(true)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [currentConn, setCurrentConn] = useState(null)

  const loadCurrent = async () => {
    try {
      const data = await getDBConfig()
      setCurrentConn(data)
    } catch {
      setCurrentConn(null)
    }
  }
  useEffect(() => { loadCurrent() }, [])

  const handleDbTypeChange = (t) => {
    setDbType(t)
    setPort(DEFAULT_PORTS[t] || 3306)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMessage(null)
    setLoading(true)
    try {
      const payload = {
        db_type: dbType,
        url: method === 'url' ? connUrl : null,
        host: method === 'fields' ? host : null,
        port: method === 'fields' ? port : null,
        database: method === 'fields' ? database : null,
        username: method === 'fields' ? username : null,
        password: method === 'fields' ? password : null,
      }
      const data = await setDBConfig(payload, fetchSchema)
      const tables = data.tables?.join(', ') || '—'
      setMessage({ type: 'success', text: `${data.message}  |  Indexed tables: ${tables}` })
      await loadCurrent()
    } catch (e) {
      setMessage({ type: 'error', text: e?.response?.data?.detail || 'Connection failed. Check your credentials.' })
    } finally {
      setLoading(false)
    }
  }

  const urlPlaceholder = {
    mysql: 'mysql+pymysql://user:pass@host:3306/dbname',
    postgresql: 'postgresql://user:pass@host:5432/dbname',
    sqlite: 'sqlite:///path/to/db.sqlite3',
  }[dbType]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">SQL Database Configuration</h1>
        <p className="page-subtitle">
          Connect your database. The chatbot will query it directly using{' '}
          <span style={{ color: 'var(--purple-light)' }}>Metadata RAG</span> for high accuracy.
        </p>
      </div>

      {message && (
        <div className={`alert alert-${message.type === 'success' ? 'success' : 'error'}`}>
          <span className="alert-icon">{message.type === 'success' ? '✅' : '⚠️'}</span>
          <span>{message.text}</span>
        </div>
      )}

      <div className="card">
        {/* DB Type + Method */}
        <div className="form-grid-2" style={{ marginBottom: 20 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="db-type">Database Type</label>
            <select
              id="db-type"
              className="form-select"
              value={dbType}
              onChange={(e) => handleDbTypeChange(e.target.value)}
            >
              <option value="mysql">mysql</option>
              <option value="postgresql">postgresql</option>
              <option value="sqlite">sqlite</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Connection Method</label>
            <div className="toggle-radio">
              <button
                id="method-fields"
                type="button"
                className={`toggle-radio-btn ${method === 'fields' ? 'active' : ''}`}
                onClick={() => setMethod('fields')}
              >
                Detailed Fields
              </button>
              <button
                id="method-url"
                type="button"
                className={`toggle-radio-btn ${method === 'url' ? 'active' : ''}`}
                onClick={() => setMethod('url')}
              >
                Direct URL
              </button>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {method === 'url' ? (
            <div className="form-group">
              <label className="form-label" htmlFor="conn-url">Connection URL</label>
              <input
                id="conn-url"
                type="text"
                className="form-input"
                value={connUrl}
                onChange={(e) => setConnUrl(e.target.value)}
                placeholder={urlPlaceholder}
                required
              />
              <p className="form-caption">💡 Supported: mysql+pymysql://, postgresql://, sqlite:///</p>
            </div>
          ) : (
            <>
              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label" htmlFor="db-host">Host</label>
                  <input
                    id="db-host"
                    type="text"
                    className="form-input"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    placeholder="localhost"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="db-port">Port</label>
                  <input
                    id="db-port"
                    type="number"
                    className="form-input"
                    value={port}
                    onChange={(e) => setPort(Number(e.target.value))}
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label" htmlFor="db-name">Database Name</label>
                  <input
                    id="db-name"
                    type="text"
                    className="form-input"
                    value={database}
                    onChange={(e) => setDatabase(e.target.value)}
                    placeholder="my_database"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="db-password">Password</label>
                  <div className="input-wrapper">
                    <input
                      id="db-password"
                      type={showPass ? 'text' : 'password'}
                      className="form-input"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                    />
                    <button type="button" className="input-toggle" onClick={() => setShowPass(!showPass)}>
                      {showPass ? '🙈' : '👁️'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="db-username">Username</label>
                <input
                  id="db-username"
                  type="text"
                  className="form-input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="root"
                />
              </div>
            </>
          )}

          <div style={{ marginBottom: 16 }}>
            <label className="checkbox-label">
              <input
                id="fetch-schema-checkbox"
                type="checkbox"
                checked={fetchSchema}
                onChange={(e) => setFetchSchema(e.target.checked)}
              />
              Auto-fetch &amp; Index Schema (Recommended)
            </label>
          </div>

          <div className="info-box" style={{ marginBottom: 20 }}>
            <span>💡</span>
            <span>Indexing the schema allows the AI to &apos;know&apos; your tables and columns before generating SQL.</span>
          </div>

          <button
            id="connect-db-btn"
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> Connecting &amp; Indexing...</> : '🔌 Connect & Sync Metadata'}
          </button>
        </form>
      </div>

      <hr className="section-divider" />

      {/* Current connection */}
      <div className="section-title">🔗 Current Connection</div>
      <div className="card">
        {currentConn?.configured ? (
          <div className="alert alert-success" style={{ marginBottom: 0 }}>
            <span className="alert-icon">✅</span>
            <span>
              Connected to <code style={{ background: 'rgba(16,185,129,0.15)', padding: '1px 6px', borderRadius: 4 }}>{currentConn.database}</code>
              {' '}on <code style={{ background: 'rgba(16,185,129,0.15)', padding: '1px 6px', borderRadius: 4 }}>{currentConn.host}</code>
            </span>
          </div>
        ) : (
          <div className="alert alert-warning" style={{ marginBottom: 0 }}>
            <span className="alert-icon">⚠️</span>
            <span>No database configured yet.</span>
          </div>
        )}
      </div>
    </div>
  )
}
