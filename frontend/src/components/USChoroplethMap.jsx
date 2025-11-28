import React, { useEffect, useRef, useState } from 'react'
import { geoAlbersUsa, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'

// GCP zones to highlight with approximate [lon, lat]
const ZONES = [
  // us-west2 (Los Angeles area) approximate locations for a/b/c
  { name: 'us-west2-a', coords: [-118.25, 34.05] },
  { name: 'us-west2-b', coords: [-118.24, 34.06] },
  { name: 'us-west2-c', coords: [-118.23, 34.04] },

  // us-central1 (Iowa / Omaha area) approximate locations for b/c/f
  { name: 'us-central1-b', coords: [-95.9345, 41.2565] },
  { name: 'us-central1-c', coords: [-95.92, 41.26] },
  { name: 'us-central1-f', coords: [-95.95, 41.25] },

  // us-east1 (South Carolina / Charleston area) approximate locations for a/b/c
  { name: 'us-east1-a', coords: [-79.93, 32.78] },
  { name: 'us-east1-b', coords: [-79.92, 32.79] },
  { name: 'us-east1-c', coords: [-79.94, 32.77] },
]

export default function USChoroplethMap({ width = 900, height = 550 }){
  const [states, setStates] = useState(null)
  const [error, setError] = useState(null)
  const ref = useRef()

  useEffect(() => {
    let canceled = false

    async function load() {
      try {

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


        <path
          d={path({ type: 'FeatureCollection', features: states.features })}
          fill="none"
          stroke="#333"
          strokeWidth={1}
          opacity={0.6}
        />


        <g className="zones">
          {ZONES.map((z, i) => {
            const [x, y] = projection(z.coords) || [null, null]
            if (x == null || y == null) return null


            const offsets = [
              { dx: 14, dy: 6 },
              { dx: -14, dy: -14 },
              { dx: 14, dy: -14 },
              { dx: -14, dy: 6 },
              { dx: 0, dy: -18 },
              { dx: 0, dy: 18 }
            ]
            const off = offsets[i % offsets.length]

            const label = z.name
            const fontSize = 12

            const textWidth = Math.max(60, label.length * (fontSize * 0.6))
            const rectPaddingX = 8
            const rectPaddingY = 4

            const rectX = off.dx > 0 ? x + off.dx : x + off.dx - textWidth - rectPaddingX
            const rectY = y + off.dy - (fontSize / 1.5)

            return (
              <g key={z.name}>
                <g transform={`translate(${x},${y})`}>
                  <circle r={10} fill="none" stroke="#1f8ef1" strokeWidth={2.5} />
                  <circle r={5} fill="#fff" stroke="#1f8ef1" strokeWidth={1} />
                </g>

                <line x1={x} y1={y} x2={rectX + 6} y2={rectY + rectPaddingY + (fontSize / 3)} stroke="#a0aec0" strokeWidth={1} strokeLinecap="round" />


                <rect x={rectX} y={rectY} rx={6} ry={6} width={textWidth + rectPaddingX} height={fontSize + rectPaddingY * 2} fill="#ffffff" opacity={0.95} stroke="#e2e8f0" />

                <text x={rectX + rectPaddingX / 2} y={rectY + fontSize + (rectPaddingY / 2) - 2} fontSize={fontSize} fontFamily="sans-serif" fill="#0b1220">
                  {label}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
