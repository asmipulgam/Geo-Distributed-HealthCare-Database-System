// Minimal auth utility using localStorage
const AUTH_KEY = 'gdhs_auth'

export function login(username, password) {
  // Hardcoded single user: admin/admin
  const USER = 'admin'
  const PASS = 'admin'
  if (username === USER && password === PASS) {
    const token = btoa(`${username}:${Date.now()}`)
    const payload = { user: username, token }
    localStorage.setItem(AUTH_KEY, JSON.stringify(payload))
    return { ok: true, user: username }
  }
  return { ok: false, error: 'Invalid credentials' }
}

export function logout() {
  localStorage.removeItem(AUTH_KEY)
}

export function isAuthenticated() {
  try {
    const v = localStorage.getItem(AUTH_KEY)
    return !!v
  } catch (e) {
    return false
  }
}

export function getUser() {
  try {
    const v = JSON.parse(localStorage.getItem(AUTH_KEY) || 'null')
    return v && v.user
  } catch (e) { 
    return null
  }
}

export default { login, logout, isAuthenticated, getUser }
