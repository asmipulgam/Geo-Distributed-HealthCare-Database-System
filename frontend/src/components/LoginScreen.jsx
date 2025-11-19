import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { login, isAuthenticated } from '../auth'

export default function LoginScreen(){
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // `from` may be a location object or a pathname string. Prefer the pathname when available.
  // If no state was set (LoginScreen rendered directly as the route element), fall back to the
  // current pathname so we redirect back to the same protected route after login.
  const from = location.state?.from?.pathname || location.state?.from || location.pathname || '/admin'

  // If already authenticated on mount, redirect to the original destination.
  useEffect(() => {
    if (isAuthenticated()) {
      navigate(from, { replace: true })
    }
  }, [from, navigate])

  const handleSubmit = async (e) =>{
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      // Support both sync and async `login` implementations.
      const res = await Promise.resolve(login(username.trim(), password))
      setLoading(false)
      if (res && res.ok){
        // Perform a hard navigation so the top-level routing logic re-evaluates
        // authentication (some routes conditionally render the LoginScreen
        // inline and won't update correctly without a full reload). Using
        // window.location ensures the app initializes in the authenticated state.
        window.location.href = from
        return
      } else {
        setError((res && res.error) || 'Login failed')
      }
    } catch (err) {
      setLoading(false)
      setError(err?.message || 'Login failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-100 to-white">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-semibold mb-4">Sign in</h1>
        <p className="text-sm text-gray-500 mb-6">Enter admin credentials to continue.</p>
        <form onSubmit={handleSubmit}>
          <label className="block mb-3">
            <span className="text-sm text-gray-600">User ID</span>
            <input value={username} onChange={e=>setUsername(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500" />
          </label>
          <label className="block mb-4">
            <span className="text-sm text-gray-600">Password</span>
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500" />
          </label>
          {error && <div className="text-sm text-red-600 mb-3">{error}</div>}
          <div className="flex items-center justify-between">
            <button disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-md">{loading? 'Signing...' : 'Sign in'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
