/**
 * sessionStore.js
 * ────────────────────────────────────────────────────────────────
 * Session-isolated UI query cache with a 5-hour expiration limit.
 *
 * Storage key: "qm_cache_<userId>"
 * ────────────────────────────────────────────────────────────────
 */

// ── Session query cache ────────────────────────────────────────────────
// Stored in localStorage as: "qm_cache_<userId>" → { sessionId → { hash → { response, timestamp } } }

const CACHE_EXPIRY_MS = 5 * 60 * 60 * 1000; // 5 hours

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

function cacheStorageKey(userId) {
  return `qm_cache_${userId}`
}

export function checkQueryCache(userId, sessionId, question) {
  if (!sessionId) return null;
  try {
    const raw = localStorage.getItem(cacheStorageKey(userId))
    if (!raw) return null
    const store = JSON.parse(raw)
    
    const hash = md5Simple(question.trim().toLowerCase())
    const entry = store[sessionId]?.[hash]
    
    if (entry) {
      const age = Date.now() - entry.timestamp
      if (age <= CACHE_EXPIRY_MS) {
        return entry.response
      } else {
        // Expired, cleanup the specific entry
        delete store[sessionId][hash]
        if (Object.keys(store[sessionId]).length === 0) {
          delete store[sessionId]
        }
        localStorage.setItem(cacheStorageKey(userId), JSON.stringify(store))
        return null
      }
    }
    return null
  } catch {
    return null
  }
}

export function storeQueryCache(userId, sessionId, question, response) {
  if (!sessionId) return;
  try {
    const key = cacheStorageKey(userId)
    const hash = md5Simple(question.trim().toLowerCase())

    let store = {}
    try { store = JSON.parse(localStorage.getItem(key) || '{}') } catch {}

    // Initialize session object if needed
    if (!store[sessionId]) {
      store[sessionId] = {}
    }
    
    // Store response with current timestamp
    store[sessionId][hash] = {
      response,
      timestamp: Date.now()
    }
    
    // Clean up extremely old sessions periodically to prevent quota issues
    const now = Date.now()
    for (const sId in store) {
      let activeSessionKeys = 0;
      for (const h in store[sId]) {
         if (now - store[sId][h].timestamp > CACHE_EXPIRY_MS) {
             delete store[sId][h]
         } else {
             activeSessionKeys++;
         }
      }
      if (activeSessionKeys === 0) {
          delete store[sId]
      }
    }

    localStorage.setItem(key, JSON.stringify(store))
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
