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
  
  // Cloud API state
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [showKey, setShowKey] = useState(false)
  const [loading, setLoading] = useState(false)

  // Custom Endpoint state
  const [endpointUrl, setEndpointUrl] = useState('')
  const [endpointModel, setEndpointModel] = useState('')
  const [endpointKey, setEndpointKey] = useState('')
  const [showEndpointKey, setShowEndpointKey] = useState(false)
  const [endpointLoading, setEndpointLoading] = useState(false)
  const [detectedProvider, setDetectedProvider] = useState(null)

  const [message, setMessage] = useState(null) // { type, text }

  const loadConfig = async () => {
    try {
      const data = await getLLMConfig()
      setCurrentConfig(data)
      if (data.provider === 'endpoint' || data.provider === 'ollama') {
        if (data.base_url) setEndpointUrl(data.base_url)
        if (data.model) setEndpointModel(data.model)
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

  const handleEndpointSave = async (e) => {
    if (e) e.preventDefault()
    if (!endpointUrl.trim() || !endpointModel.trim()) {
      setMessage({ type: 'error', text: 'Endpoint URL and Model are required' })
      return
    }
    setEndpointLoading(true)
    setMessage(null)
    try {
      const res = await setLLMConfig({ provider: 'endpoint', model: endpointModel, base_url: endpointUrl, api_key: endpointKey })
      if (res.detected) {
        setDetectedProvider(res.detected)
      }
      setMessage({ type: 'success', text: `✅ Switched to Custom Endpoint` })
      await loadConfig()
      setEndpointKey('') // Clear key field after save
    } catch (e) {
      setMessage({ type: 'error', text: e?.response?.data?.detail || 'Failed to save endpoint config' })
    } finally {
      setEndpointLoading(false)
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
      setApiKey('') // Clear key field after save
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
        <p className="page-subtitle">Choose between a Custom LLM Endpoint or a Cloud API Provider.</p>
      </div>

      {message && (
        <div className={`alert alert-${message.type === 'success' ? 'success' : 'error'}`}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="alert-icon">{message.type === 'success' ? '✅' : '⚠️'}</span>
              <span>{message.text}</span>
            </div>
            {message.type === 'success' && detectedProvider && (
              <span className="badge badge-success" style={{ marginLeft: '12px', fontWeight: 'bold' }}>
                [ Auto-detected: {detectedProvider} ✅ ]
              </span>
            )}
          </div>
        </div>
      )}

      <div className="llm-cards">
        {/* Custom Endpoint */}
        <div className="llm-card">
          <div className="llm-card-title">🔗 Custom LLM Endpoint</div>
          <p className="llm-card-desc">
            Use any remote LLM (e.g. OpenAI-compatible server, remote Ollama).
          </p>
          
          <form onSubmit={handleEndpointSave}>
            <div className="form-group">
              <label className="form-label" htmlFor="endpoint-url">Base URL</label>
              <input
                id="endpoint-url"
                type="text"
                className="form-input"
                value={endpointUrl}
                onChange={(e) => setEndpointUrl(e.target.value)}
                placeholder="http://192.168.1.100:11434"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="endpoint-model">Model Name</label>
              <input
                id="endpoint-model"
                type="text"
                className="form-input"
                value={endpointModel}
                onChange={(e) => setEndpointModel(e.target.value)}
                placeholder="llama3.2"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label" htmlFor="endpoint-api-key">API Key (Optional)</label>
              <div className="input-wrapper">
                <input
                  id="endpoint-api-key"
                  type={showEndpointKey ? 'text' : 'password'}
                  className="form-input"
                  value={endpointKey}
                  onChange={(e) => setEndpointKey(e.target.value)}
                  placeholder="Bearer token if required..."
                />
                <button type="button" className="input-toggle" onClick={() => setShowEndpointKey(!showEndpointKey)}>
                  {showEndpointKey ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <button
              id="save-endpoint-btn"
              type="submit"
              className="btn btn-primary btn-full"
              disabled={endpointLoading}
            >
              {endpointLoading ? <><span className="spinner" /> Saving...</> : '🔗 Save Custom Endpoint'}
            </button>
          </form>
        </div>

        {/* Cloud API */}
        <div className="llm-card">
          <div className="llm-card-title">☁️ Cloud — API Providers</div>
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
              {JSON.stringify({
                 provider: currentConfig.provider,
                 model: currentConfig.model,
                 base_url: currentConfig.base_url
              }, null, 2)}
            </pre>
          ) : (
            <span style={{ color: '#6b7280' }}>// No config returned from API</span>
          )}
        </div>
      </div>
    </div>
  )
}
