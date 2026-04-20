import { useEffect, useState } from 'react'
import { getLLMConfig, setLLMConfig } from '../api/client'

const MODEL_MAP = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'o1-preview', 'o1-mini', 'gpt-4-turbo'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
  gemini: ['gemini-1.5-flash', 'gemini-1.5-pro'],
  groq: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'llama3-70b-8192', 'llama3-8b-8192', 'gemma2-9b-it']
}

export default function LLMSettings() {
  const [currentConfig, setCurrentConfig] = useState(null)
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')
  const [ollamaModel, setOllamaModel] = useState('llama3.2')
  const [showKey, setShowKey] = useState(false)
  const [loading, setLoading] = useState(false)
  const [ollamaLoading, setOllamaLoading] = useState(false)
  const [message, setMessage] = useState(null) // { type, text }

  const loadConfig = async () => {
    try {
      const data = await getLLMConfig()
      setCurrentConfig(data)
      if (data.provider === 'ollama') {
        if (data.base_url) setOllamaUrl(data.base_url)
        if (data.model) setOllamaModel(data.model)
      } else if (data.provider) {
        setProvider(data.provider)
        const validModels = MODEL_MAP[data.provider] || []
        if (data.model && validModels.includes(data.model)) {
          setModel(data.model)
        } else if (validModels.length > 0) {
          setModel(validModels[0])
        }
      }
    } catch {
      setCurrentConfig(null)
    }
  }

  useEffect(() => { loadConfig() }, [])

  const handleProviderChange = (p) => {
    setProvider(p)
    setModel(MODEL_MAP[p][0])
  }

  const handleOllama = async (e) => {
    if (e) e.preventDefault()
    setOllamaLoading(true)
    setMessage(null)
    try {
      await setLLMConfig({ provider: 'ollama', model: ollamaModel, base_url: ollamaUrl })
      setMessage({ type: 'success', text: `✅ Switched to Ollama ${ollamaModel} (${ollamaUrl})` })
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
          <div className="llm-card-title">🏠 Local — Ollama</div>
          <p className="llm-card-desc">
            Runs entirely on your machine. <span style={{ color: 'var(--success)' }}>No data leaves your environment.</span>
          </p>
          
          <form onSubmit={handleOllama}>
            <div className="form-group">
              <label className="form-label" htmlFor="ollama-url">Ollama Endpoint</label>
              <input
                id="ollama-url"
                type="text"
                className="form-input"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://localhost:11434"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="ollama-model">Model Name</label>
              <input
                id="ollama-model"
                type="text"
                className="form-input"
                value={ollamaModel}
                onChange={(e) => setOllamaModel(e.target.value)}
                placeholder="llama3.2"
              />
              <p className="form-help">Ensure you have run <code>ollama pull {ollamaModel}</code> first.</p>
            </div>

            <button
              id="use-ollama-btn"
              type="submit"
              className="btn btn-primary btn-full"
              disabled={ollamaLoading}
            >
              {ollamaLoading ? <><span className="spinner" /> Switching...</> : '🏠 Save & Use Ollama'}
            </button>
          </form>
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
