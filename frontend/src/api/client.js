import axios from 'axios'
import { clearQueryCache } from './sessionStore'

const API_BASE = '' // proxied via vite.config.js → localhost:8000

let token = localStorage.getItem('qm_token') || null

export const setToken = (t) => {
  token = t
  if (t) localStorage.setItem('qm_token', t)
  else localStorage.removeItem('qm_token')
}

export const getToken = () => token

const authHeaders = () => ({
  Authorization: `Bearer ${token}`,
})

// ── AUTH ────────────────────────────────────────────────────────────────
export const login = async (username, password) => {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  const res = await axios.post(`${API_BASE}/admin/token`, form)
  return res.data // { access_token, token_type }
}

// ── DASHBOARD ───────────────────────────────────────────────────────────
export const fetchStats = async () => {
  const res = await axios.get(`${API_BASE}/admin/stats`, { headers: authHeaders() })
  return res.data
}

export const disconnectDB = async () => {
  const res = await axios.delete(`${API_BASE}/admin/db-config`, { headers: authHeaders() })
  clearQueryCache()
  return res.data
}

// ── LLM CONFIG ──────────────────────────────────────────────────────────
export const getLLMConfig = async () => {
  const res = await axios.get(`${API_BASE}/admin/llm-config`, { headers: authHeaders() })
  return res.data
}

export const setLLMConfig = async (payload) => {
  const res = await axios.post(`${API_BASE}/admin/llm-config`, payload, { headers: authHeaders() })
  clearQueryCache()
  return res.data
}

// ── DB CONFIG ───────────────────────────────────────────────────────────
export const getDBConfig = async () => {
  const res = await axios.get(`${API_BASE}/admin/db-config`, { headers: authHeaders() })
  return res.data
}

export const setDBConfig = async (payload, fetchSchema = true) => {
  const res = await axios.post(
    `${API_BASE}/admin/db-config?fetch_schema=${fetchSchema}`,
    payload,
    { headers: authHeaders() }
  )
  clearQueryCache()
  return res.data
}

// ── KNOWLEDGE BASE ───────────────────────────────────────────────────────
export const getFiles = async () => {
  const res = await axios.get(`${API_BASE}/admin/files`, { headers: authHeaders() })
  return res.data
}

export const uploadFile = async (file, fileType) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('file_type', fileType)
  const res = await axios.post(`${API_BASE}/admin/upload`, formData, {
    headers: { ...authHeaders(), 'Content-Type': 'multipart/form-data' },
  })
  clearQueryCache()
  return res.data
}

export const deleteFile = async (filename) => {
  const res = await axios.delete(`${API_BASE}/admin/files/${encodeURIComponent(filename)}`, {
    headers: authHeaders(),
  })
  clearQueryCache()
  return res.data
}

// ── CHAT ────────────────────────────────────────────────────────────────
/**
 * Send a chat message with full history for LLM context.
 * @param {string} message - The new user message
 * @param {string} session_id - Unique session identifier
 * @param {Array}  history - Full message array [{role, content, sql?, data?, source?}]
 * @param {string} session_title - First user message (used for sidebar labelling)
 * @param {number} user_id - The authenticated user's ID (stored in localStorage)
 */
export const sendChat = async (message, session_id, history = [], session_title = null, user_id = 1) => {
  const res = await axios.post(`${API_BASE}/chat`, {
    message,
    session_id,
    history,
    session_title,
    user_id,
  }, { headers: authHeaders() })
  return res.data
}

// ── SESSIONS (Server-Side History) ───────────────────────────────────────
export const getSessions = async (user_id = 1) => {
  const res = await axios.get(`${API_BASE}/sessions?user_id=${user_id}`, { headers: authHeaders() })
  return res.data
}

export const createSession = async (title, session_id = null, user_id = 1) => {
  const res = await axios.post(`${API_BASE}/sessions?user_id=${user_id}`, {
    title,
    id: session_id
  }, { headers: authHeaders() })
  return res.data
}

export const getSession = async (session_id, user_id = 1) => {
  const res = await axios.get(`${API_BASE}/sessions/${session_id}?user_id=${user_id}`, { headers: authHeaders() })
  return res.data
}

export const deleteSession = async (session_id, user_id = 1) => {
  const res = await axios.delete(`${API_BASE}/sessions/${session_id}?user_id=${user_id}`, { headers: authHeaders() })
  return res.data
}

export const updateSessionTitle = async (session_id, title, user_id = 1) => {
  const res = await axios.patch(`${API_BASE}/sessions/${session_id}?title=${encodeURIComponent(title)}&user_id=${user_id}`, {}, { headers: authHeaders() })
  return res.data
}
