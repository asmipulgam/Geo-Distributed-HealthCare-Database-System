import React from 'react'
import { Link } from 'react-router-dom'

const navStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '10px 16px',
  background: '#0f172a',
  color: '#fff',
  boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
}

const leftStyle = { display: 'flex', gap: '12px', alignItems: 'center' }
const linkStyle = { color: '#cbd5e1', textDecoration: 'none', padding: '6px 8px', borderRadius: '6px' }
const brandStyle = { fontWeight: 700, color: '#fff', marginRight: '16px' }

export default function Navbar() {
  return (
    <nav style={navStyle}>
      <div style={leftStyle}>
        <div style={brandStyle}>HealthRecords</div>
        <Link to="/login" style={linkStyle} title="Will show customer details on logging in" aria-label="Login">Login</Link>
        <Link to="/agent/us-central" style={linkStyle} title="Show all records for us-central" aria-label="Agent us-central">Agent (us-central)</Link>
        <Link to="/agent/us-west" style={linkStyle} title="Show all records for us-west" aria-label="Agent us-west">Agent (us-west)</Link>
        <Link to="/admin" style={linkStyle} title="Open admin dashboard(similar to CockroachDB cluster dash)" aria-label="Admin dashboard">Admin</Link>
        <Link to="/admin/search" style={linkStyle} title="Search all records with custom filters" aria-label="Admin search">Admin Search</Link>
        <Link to="/adminadd" style={linkStyle} title="Add a new record manually" aria-label="Admin add">Admin Add</Link>
        <Link to="/organsearch" style={linkStyle} title="Search organs using geolocation" aria-label="Organ search">Organ Search</Link>
        <Link to="/analytics" style={linkStyle} title="View analytics data" aria-label="Analytics">Analytics</Link>
      </div>
    </nav>
  )
}
