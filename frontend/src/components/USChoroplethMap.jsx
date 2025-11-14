import React, { useEffect, useRef, useState } from 'react'
import { geoAlbersUsa, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'

// Cities to highlight with [lon, lat]
const CITIES = [
  { name: 'Omaha', coords: [-95.9345, 41.2565] },
  { name: 'New York', coords: [-74.0060, 40.7128] },
  { name: 'Seattle', coords: [-122.3321, 47.6062] },
]

export default function USChoroplethMap({ width = 900, height = 550 }){
  const [states, setStates] = useState(null)
  const [error, setError] = useState(null)
  const ref = useRef()

  useEffect(() => {
    let canceled = false

    async function load() {
      try {
        // Fetch TopoJSON of US states (public cdn)
        const res = await fetch('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json')
        if (!res.ok) throw new Error('Failed to fetch map data')
        const topo = await res.json()
        const geo = feature(topo, topo.objects.states)
        if (!canceled) setStates(geo)
      } catch (err) {
        if (!canceled) setError(err.message || String(err))
      }
    }

    load()
    return () => { canceled = true }
  }, [])

  if (error) {
    return <div className="p-4 text-red-600">Map load error: {error}</div>
  }

  if (!states) {
    return <div className="p-4 text-gray-600">Loading map…</div>
  }

  const projection = geoAlbersUsa().translate([width / 2, height / 2]).scale(1100)
  const path = geoPath().projection(projection)

  // Simple color function for a choropleth-like feel (light gradient by state id)
  const colorFor = (i) => `rgba(${50 + (i % 10) * 20}, ${120 + (i % 7) * 15}, 200, 0.7)`

  return (
    <div className="shadow rounded bg-white" style={{ width }} ref={ref}>
      <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
        <g className="states">
          {states.features.map((f, i) => (
            <path
              key={f.id || i}
              d={path(f)}
              fill={colorFor(i)}
              stroke="#ffffff"
              strokeWidth={0.6}
              opacity={0.95}
            />
          ))}
        </g>

        {/* Outline for the whole US */}
        <path
          d={path({ type: 'FeatureCollection', features: states.features })}
          fill="none"
          stroke="#333"
          strokeWidth={1}
          opacity={0.6}
        />

        {/* Highlight cities with outlined circles and labels */}
        <g className="cities">
          {CITIES.map((c) => {
            const [x, y] = projection(c.coords) || [null, null]
            if (x == null || y == null) return null
            return (
              <g key={c.name} transform={`translate(${x},${y})`}>
                <circle r={10} fill="none" stroke="#ff4500" strokeWidth={2.5} />
                <circle r={5} fill="#fff" stroke="#ff4500" strokeWidth={1} />
                <text x={14} y={6} fontSize={12} fontFamily="sans-serif" fill="#111">
                  {c.name}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
