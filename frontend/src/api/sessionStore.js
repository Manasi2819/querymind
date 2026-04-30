/**
 * sessionStore.js
 * ────────────────────────────────────────────────────────────────
 * Same-day UI query cache for repeated questions (saves LLM tokens).
 *
 * Storage key: "qm_cache_<userId>"
 * ────────────────────────────────────────────────────────────────
 */

// ── Same-day query cache ────────────────────────────────────────────────
// Stored in localStorage as:  "qm_cache_<userId>" → { date → { hash → response } }

const md5Simple = (str) => {
  // Simple but sufficient hash for cache keys (not cryptographic)
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const chr = str.charCodeAt(i)
    hash = (hash << 5) - hash + chr
    hash |= 0
  }
  return String(Math.abs(hash))
}

const todayStr = () => new Date().toISOString().slice(0, 10) // "YYYY-MM-DD"

function cacheStorageKey(userId, sessionId) {
  return `qm_cache_${userId}_${sessionId}`
}

export function checkQueryCache(userId, sessionId, question) {
  try {
    const raw = localStorage.getItem(cacheStorageKey(userId, sessionId))
    if (!raw) return null
    const store = JSON.parse(raw)
    const today = todayStr()
    const hash = md5Simple(question.trim().toLowerCase())
    return store[today]?.[hash] ?? null
  } catch {
    return null
  }
}

export function storeQueryCache(userId, sessionId, question, response) {
  try {
    const key = cacheStorageKey(userId, sessionId)
    const today = todayStr()
    const hash = md5Simple(question.trim().toLowerCase())

    let store = {}
    try { store = JSON.parse(localStorage.getItem(key) || '{}') } catch {}

    // Purge previous days
    const freshStore = { [today]: { ...(store[today] || {}), [hash]: response } }
    localStorage.setItem(key, JSON.stringify(freshStore))
  } catch (e) {
    console.warn('sessionStore: failed to write query cache', e)
  }
}

export function clearQueryCache() {
  try {
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith('qm_cache_')) {
        localStorage.removeItem(key)
      }
    }
  } catch (e) {
    console.warn('sessionStore: failed to clear query caches', e)
  }
}
