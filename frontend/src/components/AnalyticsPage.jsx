import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BACKEND_URL } from "./constants";

const AsImage = "/src/assets/Analytics.png";

/* ================================
   Histogram
================================ */
function Histogram({ data, valueAccessor, buckets = 10, width = 600, height = 200 }) {
  const vals = data.map(valueAccessor).map(v => Number(v)).filter(v => !isNaN(v));
  if (!vals.length) return <div>No numeric data for histogram</div>;

  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const bucketSize = range / buckets;
  const counts = new Array(buckets).fill(0);

  vals.forEach(v => {
    let idx = Math.floor((v - min) / bucketSize);
    if (idx < 0) idx = 0;
    if (idx >= buckets) idx = buckets - 1;
    counts[idx]++;
  });

  const maxCount = Math.max(...counts);

  return (
    <svg width={width} height={height}>
      {counts.map((c, i) => {
        const bw = width / buckets;
        const h = (c / maxCount) * (height - 20);
        const x = i * bw;
        const y = height - h - 10;

        return (
          <g key={i}>
            <rect x={x + 1} y={y} width={bw - 2} height={h} fill="#4f46e5" />
            <text x={x + bw / 2} y={height - 2} fontSize={10} textAnchor="middle">
              {Math.round(min + i * bucketSize)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ================================
   Pie
================================ */
function Pie({ data, width = 200, height = 200 }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  let angle = 0;

  const cx = width / 2;
  const cy = height / 2;
  const r = Math.min(width, height) / 2 - 10;
  const colors = ['#ef4444','#f97316','#f59e0b','#10b981','#3b82f6','#6366f1'];

  return (
    <svg width={width} height={height}>
      {Object.entries(data).map(([k, v], i) => {
        const start = angle;
        const portion = v / total;
        const end = start + portion * Math.PI * 2;
        const large = end - start > Math.PI ? 1 : 0;

        const x1 = cx + r * Math.cos(start);
        const y1 = cy + r * Math.sin(start);
        const x2 = cx + r * Math.cos(end);
        const y2 = cy + r * Math.sin(end);

        const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
        angle = end;

        return <path key={k} d={d} fill={colors[i % colors.length]} stroke="#fff" />;
      })}
    </svg>
  );
}

/* ================================
   Analytics Page (REAL DB DATA)
================================ */
export default function AnalyticsPage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);

    fetch(`${BACKEND_URL}/api/all?region=central&cursor=0&dir=next`)
      .then(res => res.json())
      .then(data => {
        setRecords(data.records || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Analytics fetch failed:", err);
        setLoading(false);
      });
  }, []);

  /* ✅ ANALYTICS COMPUTED FROM REAL RECORDS */

  const ages = records.map(r => Number(r.Age)).filter(v => !isNaN(v));

  const genderCounts = records.reduce((acc, r) => {
    const g = r.Gender || "Unknown";
    acc[g] = (acc[g] || 0) + 1;
    return acc;
  }, {});

  const byState = records.reduce((acc, r) => {
    const s = r.State || "Unknown";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  return (
  <div
    className="min-h-screen flex justify-center items-start p-6 pt-10"
    style={{
      backgroundImage: `url(${AsImage})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat",
      position: "relative"
    }}
  >
    {/* ✅ TRANSLUCENT OVERLAY */}
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(255,255,255,0.65)",
        zIndex: 0
      }}
    />

    {/* ✅ DASHBOARD — CENTERED HORIZONTALLY, TOP ALIGNED */}
    <div
      className="w-full max-w-5xl mx-auto"
      style={{ position: "relative", zIndex: 1 }}
    >
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Analytics</h1>
        <Link to="/admin/search" className="px-4 py-2 bg-gray-200 rounded">
          Back to Search
        </Link>
      </div>

      {/* ✅ LOADING STATE */}
      {loading && (
        <div className="bg-white p-6 rounded shadow text-center mb-6">
          Loading analytics...
        </div>
      )}

      {/* ✅ GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 place-items-center">

        {/* ✅ AGE DISTRIBUTION */}
        <div className="bg-white p-4 rounded shadow w-full flex flex-col items-center">
          <h3 className="font-medium mb-3">Age distribution</h3>
          {ages.length > 0 ? (
            <Histogram
              data={records}
              valueAccessor={r => r.Age}
              buckets={10}
            />
          ) : (
            <div className="text-gray-500">No age data available</div>
          )}
        </div>

        {/* ✅ GENDER BREAKDOWN */}
        <div className="bg-white p-4 rounded shadow w-full flex flex-col items-center">
          <h3 className="font-medium mb-3">Gender breakdown</h3>
          {Object.keys(genderCounts).length > 0 ? (
            <Pie data={genderCounts} />
          ) : (
            <div className="text-gray-500">No gender data available</div>
          )}
        </div>

        {/* ✅ STATE TABLE */}
        <div className="bg-white p-4 rounded shadow w-full md:col-span-2">
          <h3 className="font-medium mb-3 text-center">
            Count by State (top 20)
          </h3>

          {Object.keys(byState).length > 0 ? (
            <div className="overflow-auto">
              <table className="min-w-full text-sm text-center">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-2 py-1">State</th>
                    <th className="px-2 py-1">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(byState)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 20)
                    .map(([s, c]) => (
                      <tr key={s} className="border-t">
                        <td className="px-2 py-1">{s}</td>
                        <td className="px-2 py-1 font-semibold">{c}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-500 text-center">
              No state data available
            </div>
          )}
        </div>

      </div>
    </div>
  </div>
);

}
