import { useState, useEffect } from 'react'
import { getToken, setToken } from './api/client'
import {
  getSessions, createSession as apiCreateSession,
  getSession, deleteSession as apiDeleteSession,
  updateSessionTitle as apiUpdateSessionTitle
} from './api/client'
import LoginPage from './pages/LoginPage'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import LLMSettings from './pages/LLMSettings'
import DatabaseConfig from './pages/DatabaseConfig'
import KnowledgeBase from './pages/KnowledgeBase'
import ChatInterface from './pages/ChatInterface'

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  llm: 'LLM Settings',
  databases: 'Database Configuration',
  knowledge: 'Knowledge Base',
  chat: 'QueryMind Chat',
}

let _sidCounter = 0
const newSessionId = () => `session-${++_sidCounter}-${Date.now()}`

export default function App() {
  const [authenticated, setAuthenticated] = useState(!!getToken())
  const [theme, setTheme] = useState(() => localStorage.getItem('qm_theme') || 'light')
  const [activePage, setActivePage] = useState('dashboard')

  // ── Persistent chat sessions (loaded from backend) ──
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('qm_theme', theme)
  }, [theme])

  // Fetch sessions from backend
  const loadDBSessions = async () => {
    try {
      if (authenticated) {
        const data = await getSessions()
        if (Array.isArray(data)) {
          setSessions(data)
        } else {
          console.error('getSessions did not return an array:', data)
          setSessions([])
        }
      }
    } catch (e) {
      console.error('Failed to load sessions', e)
    }
  }

  useEffect(() => {
    loadDBSessions()
  }, [authenticated])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  // ── Auth ──────────────────────────────────────────────────────────
  const handleLogin = () => {
    setAuthenticated(true)
  }

  const handleLogout = () => {
    setToken(null)
    setAuthenticated(false)
    setSessions([])
    setCurrentSessionId(null)
  }

  // ── Session management ────────────────────────────────────────────
  const handleNewChat = async () => {
    try {
      const newSession = await apiCreateSession('New chat')
      setSessions((prev) => [newSession, ...prev])
      setCurrentSessionId(newSession.id)
      setActivePage('chat')
    } catch (e) {
      console.error('Create session failed', e)
    }
  }

  const handleSelectHistory = async (sessionId) => {
    setCurrentSessionId(sessionId)
    setActivePage('chat')
    // Optionally fetch full session messages if missing
    try {
      const fullSession = await getSession(sessionId)
      setSessions((prev) => prev.map(s => s.id === sessionId ? fullSession : s))
    } catch(e) {
      console.error('Fetch session failed', e)
    }
  }

  const handleDeleteSession = async (sessionId) => {
    try {
      await apiDeleteSession(sessionId)
      setSessions((prev) => {
        const updated = prev.filter(s => s.id !== sessionId)
        if (sessionId === currentSessionId) {
          if (updated.length > 0) {
            setCurrentSessionId(updated[0].id)
          } else {
            setCurrentSessionId(null)
            setActivePage('dashboard')
          }
        }
        return updated
      })
    } catch (e) {
      console.error('Delete session failed', e)
    }
  }

  const handleNavigate = (page) => {
    setActivePage(page)
    if (page === 'chat') {
      if (!currentSessionId) {
        // Auto-create a new session if none selected
        handleNewChat()
        return
      }
    }
  }

  // ── Message updates (called from ChatInterface) ───────────────────
  const handleAddMessage = (sessionId, message) => {
    setSessions((prev) => prev.map((s) => {
      if (s.id !== sessionId) return s
      const updatedData = {
        ...s,
        messages: [...(s.messages || []), message]
      }
      return updatedData
    }))
  }

  const handleFirstMessage = async (sessionId, text) => {
    const title = text.length > 38 ? text.slice(0, 38) + '\u2026' : text
    try {
      await apiUpdateSessionTitle(sessionId, title)
      setSessions((prev) => prev.map((s) => s.id === sessionId ? { ...s, title } : s))
    } catch (e) {
      console.error('Update title failed', e)
    }
  }

  // ── Render ────────────────────────────────────────────────────────
  if (!authenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  const currentSession = sessions.find((s) => s.id === currentSessionId) || null
  const isChatPage = activePage === 'chat'

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <Dashboard />
      case 'llm': return <LLMSettings />
      case 'databases': return <DatabaseConfig />
      case 'knowledge': return <KnowledgeBase />
      case 'chat':
        if (!currentSession) {
          handleNewChat()
          return null
        }
        return (
          <ChatInterface
            session={currentSession}
            onAddMessage={handleAddMessage}
            onFirstMessage={handleFirstMessage}
          />
        )
      default: return <Dashboard />
    }
  }

  return (
    <div className="app-layout">
      <Sidebar
        activePage={activePage}
        currentSessionId={currentSessionId}
        onNavigate={handleNavigate}
        sessions={sessions}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectHistory}
        onDeleteSession={handleDeleteSession}
        onLogout={handleLogout}
      />
      <div className="main-content">
        <div className="topbar">
          <span className="topbar-title">
            {isChatPage && currentSession
              ? (currentSession.title === 'New chat' ? '🧠 QueryMind Chat' : currentSession.title)
              : PAGE_TITLES[activePage] || 'QueryMind'}
          </span>
          <div className="topbar-actions">
            <button
              id="theme-toggle-btn"
              className="theme-toggle"
              onClick={toggleTheme}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>
          </div>
        </div>

        {isChatPage ? renderPage() : (
          <div className="page-content">{renderPage()}</div>
        )}
      </div>
    </div>
  )
}
