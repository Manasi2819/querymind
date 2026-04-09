import { useEffect, useState } from 'react'
import { getLLMConfig, setLLMConfig } from '../api/client'

const MODEL_MAP = {
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022'],
  gemini: ['gemini-1.5-flash', 'gemini-1.5-pro'],
  groq: ['llama-3.1-8b-instant', 'llama-3.1-70b-versatile', 'llama3-70b-8192', 'mixtral-8x7b-32768', 'gemma2-9b-it']
}

export default function LLMSettings() {
  const [currentConfig, setCurrentConfig] = useState(null)
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [showKey, setShowKey] = useState(false)
  const [loading, setLoading] = useState(false)
  const [ollamaLoading, setOllamaLoading] = useState(false)
  const [message, setMessage] = useState(null) // { type, text }

  const loadConfig = async () => {
    try {
      const data = await getLLMConfig()
      setCurrentConfig(data)
    } catch {
      setCurrentConfig(null)
    }
  }

  useEffect(() => { loadConfig() }, [])

  const handleProviderChange = (p) => {
    setProvider(p)
    setModel(MODEL_MAP[p][0])
  }

  const handleOllama = async () => {
    setOllamaLoading(true)
    setMessage(null)
    try {
      await setLLMConfig({ provider: 'ollama' })
      setMessage({ type: 'success', text: '✅ Switched to Ollama phi3-mini (local)' })
      await loadConfig()
    } catch (e) {
      setMessage({ type: 'error', text: e?.response?.data?.detail || 'Failed to switch to Ollama' })
    } finally {
      setOllamaLoading(false)
    }
  }

  const handleCloudSave = async (e) => {
    e.preventDefault()
    if (!apiKey.trim()) {
      setMessage({ type: 'error', text: 'API key is required' })
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      await setLLMConfig({ provider, api_key: apiKey, model })
      setMessage({ type: 'success', text: `✅ Switched to ${provider} / ${model}` })
      await loadConfig()
    } catch (e) {
      setMessage({ type: 'error', text: e?.response?.data?.detail || 'Failed to save config' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">LLM Provider Configuration</h1>
        <p className="page-subtitle">Choose between a local Ollama model (free, private) or a cloud API key.</p>
      </div>

      {message && (
        <div className={`alert alert-${message.type === 'success' ? 'success' : 'error'}`}>
          <span className="alert-icon">{message.type === 'success' ? '✅' : '⚠️'}</span>
          <span>{message.text}</span>
        </div>
      )}

      <div className="llm-cards">
        {/* Local Ollama */}
        <div className="llm-card">
          <div className="llm-card-title">🏠 Local — Ollama phi3-mini</div>
          <p className="llm-card-desc">
            Runs entirely on your machine. <span style={{ color: 'var(--success)' }}>No data sent externally.</span> Requires Ollama to be running locally.
          </p>
          <button
            id="use-ollama-btn"
            className="btn btn-primary btn-full"
            onClick={handleOllama}
            disabled={ollamaLoading}
          >
            {ollamaLoading ? <><span className="spinner" /> Switching...</> : '🏠 Use Ollama (phi3-mini)'}
          </button>
        </div>

        {/* Cloud API */}
        <div className="llm-card">
          <div className="llm-card-title">☁️ Cloud — API Key</div>
          <form onSubmit={handleCloudSave}>
            <div className="form-group">
              <label className="form-label" htmlFor="llm-provider">Provider</label>
              <select
                id="llm-provider"
                className="form-select"
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
              >
                <option value="openai">openai</option>
                <option value="anthropic">anthropic</option>
                <option value="gemini">gemini</option>
                <option value="groq">groq</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="llm-api-key">API Key</label>
              <div className="input-wrapper">
                <input
                  id="llm-api-key"
                  type={showKey ? 'text' : 'password'}
                  className="form-input"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                />
                <button type="button" className="input-toggle" onClick={() => setShowKey(!showKey)}>
                  {showKey ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="llm-model">Model</label>
              <select
                id="llm-model"
                className="form-select"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                {MODEL_MAP[provider].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <button
              id="save-cloud-config-btn"
              type="submit"
              className="btn btn-primary btn-full"
              disabled={loading}
            >
              {loading ? <><span className="spinner" /> Saving...</> : '☁️ Save Cloud Config'}
            </button>
          </form>
        </div>
      </div>

      <hr className="section-divider" />

      {/* Current Config */}
      <div className="section-title">📋 Current Configuration</div>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="json-viewer">
          {currentConfig ? (
            <pre>
              {`{\n`}
              {Object.entries(currentConfig).map(([k, v]) => (
                `  `
              )).join('')}
              {JSON.stringify(currentConfig, null, 2)}
            </pre>
          ) : (
            <span style={{ color: '#6b7280' }}>// No config returned from API</span>
          )}
        </div>
      </div>
    </div>
  )
}
