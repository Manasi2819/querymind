import { useState } from 'react'

export default function Sidebar({
  activePage,
  currentSessionId,
  onNavigate,
  sessions,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onLogout,
}) {
  const [hoveredSession, setHoveredSession] = useState(null)

  const configItems = [
    { id: 'databases', icon: '🗄️', label: 'Databases' },
    { id: 'knowledge', icon: '📚', label: 'Knowledge' },
    { id: 'llm', icon: '⚙️', label: 'LLM Settings' },
  ]

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🧠</div>
        <span className="sidebar-logo-text">QueryMind</span>
      </div>

      <nav className="sidebar-nav">
        {/* Dashboard */}
        <button
          id="nav-dashboard"
          className={`sidebar-item ${activePage === 'dashboard' ? 'active' : ''}`}
          onClick={() => onNavigate('dashboard')}
        >
          <span className="sidebar-item-icon">⊞</span>
          <span className="sidebar-item-text">Dashboard</span>
        </button>

        {/* New Chat */}
        <button
          id="nav-new-chat"
          className="new-chat-btn"
          onClick={onNewChat}
        >
          <span>＋</span>
          <span>New Chat</span>
        </button>

        {/* Recent History */}
        <span className="sidebar-section-label">Recent History</span>
        {sessions.length === 0 ? (
          <div style={{ padding: '6px 12px', fontSize: 12, color: '#4b5563', fontStyle: 'italic' }}>
            No chats yet
          </div>
        ) : (
          sessions.slice(0, 12).map((session) => (
            <div
              key={session.id}
              className={`history-item ${currentSessionId === session.id && activePage === 'chat' ? 'active' : ''}`}
              onClick={() => onSelectSession(session.id)}
              onMouseEnter={() => setHoveredSession(session.id)}
              onMouseLeave={() => setHoveredSession(null)}
              title={session.title}
              style={{ position: 'relative', paddingRight: 26 }}
            >
              <span style={{ fontSize: 12, flexShrink: 0 }}>💬</span>
              <span style={{
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {session.title}
              </span>
              {hoveredSession === session.id && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteSession(session.id)
                  }}
                  style={{
                    position: 'absolute',
                    right: 6,
                    background: 'none',
                    border: 'none',
                    color: '#9ca3af',
                    cursor: 'pointer',
                    fontSize: 13,
                    padding: '0 2px',
                    lineHeight: 1,
                    transition: 'color 0.15s',
                  }}
                  title="Delete this chat"
                  onMouseEnter={(e) => (e.target.style.color = '#ef4444')}
                  onMouseLeave={(e) => (e.target.style.color = '#9ca3af')}
                >
                  ×
                </button>
              )}
            </div>
          ))
        )}

        {/* Configuration */}
        <span className="sidebar-section-label" style={{ marginTop: 8 }}>
          Configuration
        </span>
        {configItems.map((item) => (
          <button
            key={item.id}
            id={`nav-${item.id}`}
            className={`sidebar-item ${activePage === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            <span className="sidebar-item-icon">{item.icon}</span>
            <span className="sidebar-item-text">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Bottom user bar */}
      <div className="sidebar-bottom">
        <div className="sidebar-avatar">AD</div>
        <div className="sidebar-user-info">
          <div className="sidebar-username">admin</div>
          <div className="sidebar-user-role">Pro Member</div>
        </div>
        <button
          className="sidebar-logout-btn"
          onClick={onLogout}
          title="Logout"
        >
          →
        </button>
      </div>
    </aside>
  )
}
