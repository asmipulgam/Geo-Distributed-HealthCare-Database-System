import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { login, isAuthenticated } from '../auth'
import ALImage from '../assets/Adminlogin.png'  

export default function LoginScreen(){
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || location.state?.from || location.pathname || '/admin'

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
      const res = await Promise.resolve(login(username.trim(), password))
      setLoading(false)
      if (res && res.ok){
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
    <div
      className="min-h-screen flex items-center justify-center bg-no-repeat bg-center bg-cover relative"
      style={{ backgroundImage: `url(${ALImage})` }} >
      <div className="absolute inset-0 bg-black/40"></div>
      <div className="relative z-10 w-full max-w-md p-8 bg-white/90 backdrop-blur-xl rounded-xl shadow-2xl border">
        <h1 className="text-2xl font-semibold mb-4 text-center">Sign in</h1>
        <p className="text-sm text-gray-500 mb-6 text-center">
          Enter admin credentials to continue.
        </p>

        <form onSubmit={handleSubmit}>
          <label className="block mb-3">
            <span className="text-sm text-gray-600">User ID</span>
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500"
            />
          </label>

          <label className="block mb-4">
            <span className="text-sm text-gray-600">Password</span>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500"
            />
          </label>

          {error && (
            <div className="text-sm text-red-600 mb-3 text-center">
              {error}
            </div>
          )}

          <div className="flex items-center justify-center">
            <button
              disabled={loading}
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md 
                         hover:bg-blue-700 active:bg-blue-800 
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
