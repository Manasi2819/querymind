import { useRef, useEffect, useState } from 'react'
import { sendChat } from '../api/client'
import { checkQueryCache, storeQueryCache } from '../api/sessionStore'

// Read user_id from the JWT payload (simple base64 decode, no verification needed)
function getUserIdFromToken() {
  try {
    const token = localStorage.getItem('qm_token')
    if (!token) return 1
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.user_id || 1
  } catch {
    return 1
  }
}

export default function ChatInterface({ session, onAddMessage, onFirstMessage }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expandedSql, setExpandedSql] = useState({})
  const messagesEndRef = useRef(null)

  const messages = session?.messages || []
  const sessionId = session?.id

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const toggleSql = (idx) => {
    setExpandedSql((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading || !sessionId) return

    const userId = getUserIdFromToken()
    const isFirstMessage = messages.length === 0

    // Add user message immediately (optimistic update)
    const userMsg = { role: 'user', content: text }
    onAddMessage(sessionId, userMsg)
    if (isFirstMessage) onFirstMessage(sessionId, text)
    setInput('')
    setLoading(true)

    try {
      // ── Same-day frontend cache check ─────────────────────────
      const cached = checkQueryCache(userId, text)
      if (cached) {
        const cachedMsg = {
          role: 'assistant',
          content: cached.answer,
          sql: cached.sql || null,
          data: cached.data || null,
          source: cached.source || 'cache',
          _cached: true,
        }
        onAddMessage(sessionId, cachedMsg)
        setLoading(false)
        return
      }

      // ── Build history to pass to backend
      // Pass all messages BEFORE the current user message (the optimistic add
      // puts it in session.messages, so slice everything except the last)
      const historyToSend = messages.map((m) => ({
        role: m.role,
        content: m.content,
        sql: m.sql || null,
        data: m.data || null,
        source: m.source || null,
      }))

      // ── Call backend ──────────────────────────────────────────
      const data = await sendChat(text, sessionId, historyToSend, isFirstMessage ? text : null, userId)

      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        sql: data.sql || null,
        data: data.data || null,
        source: data.source || null,
        _cached: data.cached || false,
      }
      onAddMessage(sessionId, assistantMsg)

      // ── Store in same-day frontend cache ──────────────────────
      // Do not cache errors so the user can easily retry
      const isError = data.answer && (data.answer.startsWith('Error') || data.answer.startsWith('⚠️ Error'));
      if (!data.cached && !isError) {
        storeQueryCache(userId, text, {
          answer: data.answer,
          sql: data.sql || null,
          data: data.data || null,
          source: data.source || null,
        })
      }
    } catch {
      onAddMessage(sessionId, {
        role: 'assistant',
        content: '⚠️ Error: Could not reach the backend. Make sure the API is running on port 8000.',
        source: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-layout">
      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && !loading ? (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">🧠</div>
            <h2 className="chat-welcome-title">What do you want to know?</h2>
            <p className="chat-welcome-sub">
              I can help you analyze your{' '}
              <span>databases</span> and{' '}
              <span>documents</span> in real-time.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? 'AD' : '🧠'}
                </div>
                <div>
                  <div className="message-bubble">
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

                    {/* SQL Expander */}
                    {msg.sql && (
                      <div className="sql-expander">
                        <button
                          className="sql-expander-btn"
                          onClick={() => toggleSql(i)}
                        >
                          <span>{expandedSql[i] ? '▾' : '▸'}</span>
                          <span>{expandedSql[i] ? 'Hide' : 'View'} Generated SQL</span>
                        </button>
                        {expandedSql[i] && (
                          <div className="sql-code">{msg.sql}</div>
                        )}
                      </div>
                    )}

                    {/* Data Table */}
                    {msg.data && msg.data.length > 0 && (
                      <div className="chat-table-wrapper">
                        <table className="data-table">
                          <thead>
                            <tr>
                              {Object.keys(msg.data[0]).map((col) => (
                                <th key={col}>{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {msg.data.map((row, ri) => (
                              <tr key={ri}>
                                {Object.values(row).map((val, vi) => (
                                  <td key={vi}>{String(val)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Source + cache indicator */}
                  <div className="message-source">
                    {msg.source && `Source: ${msg.source}`}
                    {msg._cached && (
                      <span style={{
                        marginLeft: 8,
                        fontSize: 10,
                        background: 'rgba(124,58,237,0.12)',
                        color: '#a78bfa',
                        padding: '2px 6px',
                        borderRadius: 4,
                      }}>
                        ⚡ Cached
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="message assistant">
                <div className="message-avatar">🧠</div>
                <div className="message-bubble">
                  <div className="loading-dots">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <button className="chat-attach-btn" title="Attach file (coming soon)" disabled>
            📎
          </button>
          <textarea
            id="chat-input"
            className="chat-input"
            placeholder="Ask anything about your data..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button
            id="chat-send-btn"
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            title="Send message"
          >
            ➤
          </button>
        </div>
        <p className="chat-disclaimer">QueryMind can make mistakes. Check important info.</p>
      </div>
    </div>
  )
}
