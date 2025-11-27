import React, { useEffect, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';

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
                        <text x={x + bw/2} y={height - 2} fontSize={10} textAnchor="middle">{Math.round(min + i * bucketSize)}</text>
                    </g>
                );
            })}
        </svg>
    );
}

function Pie({ data, accessor, width = 200, height = 200 }) {
    let counts = {};
    if (!Array.isArray(data) && data && typeof data === 'object') {
        counts = data;
    } else {
        data.forEach(d => {
            const k = accessor(d) ?? 'Unknown';
            counts[k] = (counts[k] || 0) + 1;
        });
    }
    const total = Object.values(counts).reduce((a,b)=>a+b,0) || 1;
    let angle = 0;
    const cx = width/2, cy = height/2, r = Math.min(width, height)/2 - 10;
    const colors = ['#ef4444','#f97316','#f59e0b','#10b981','#3b82f6','#6366f1','#8b5cf6','#ec4899'];
    return (
        <svg width={width} height={height}>
            {Object.entries(counts).map(([k,v], i) => {
                const start = angle;
                const portion = v/total;
                const end = start + portion * Math.PI * 2;
                const large = end - start > Math.PI ? 1 : 0;
                const x1 = cx + r * Math.cos(start);
                const y1 = cy + r * Math.sin(start);
                const x2 = cx + r * Math.cos(end);
                const y2 = cy + r * Math.sin(end);
                const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
                angle = end;
                return <path key={k} d={d} fill={colors[i % colors.length]} stroke="#fff" />
            })}
        </svg>
    );
}

export default function AnalyticsPage() {
    const { state } = useLocation();
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(false);
    useEffect(() => {
        setLoading(true);
        fetch('/api/analytics/summary')
            .then(r => r.json())
            .then(d => { setAnalytics(d); setLoading(false); })
            .catch(e => { console.error('analytics fetch', e); setLoading(false); });
    }, []);

    const rows = analytics?.sample_rows || ((state && state.rows) || []);

    const ages = analytics ? (analytics.ages || []) : rows.map(r => Number(r.age)).filter(v => !isNaN(v));
    const genderCounts = analytics ? (analytics.gender || {}) : rows.reduce((acc, r) => {
        const g = (r.gender || 'Unknown')
        acc[g] = (acc[g] || 0) + 1; return acc;
    }, {});

    const byState = analytics ? (analytics.by_state || {}) : rows.reduce((acc, r) => {
        const s = (r.State || 'Unknown'); acc[s] = (acc[s] || 0) + 1; return acc;
    }, {});

    return (
        <div className="min-h-screen p-6 bg-gray-50">
            <div className="max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-4">
                    <h1 className="text-2xl font-bold">Analytics</h1>
                    <Link to="/admin/search" className="px-3 py-2 bg-gray-200 rounded">Back to Search</Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white p-4 rounded shadow">
                        <h3 className="font-medium mb-2">Age distribution</h3>
                        { (analytics ? (ages && ages.length) : rows.length) ? (
                            analytics ? <Histogram data={ages} valueAccessor={v=>v} buckets={10} /> : <Histogram data={rows} valueAccessor={r=>r.age} buckets={10} />
                        ) : <div>No data</div>}
                    </div>

                    <div className="bg-white p-4 rounded shadow">
                        <h3 className="font-medium mb-2">Gender breakdown</h3>
                        { (analytics ? Object.keys(genderCounts).length>0 : rows.length) ? (
                            analytics ? <Pie data={genderCounts} accessor={r=>r.gender} /> : <Pie data={rows} accessor={r=>r.gender} />
                        ) : <div>No data</div>}
                    </div>

                    <div className="bg-white p-4 rounded shadow col-span-1 md:col-span-2">
                        <h3 className="font-medium mb-2">Count by State (top 10)</h3>
                        <div className="overflow-auto">
                            <table className="min-w-full text-sm">
                                <thead className="bg-gray-100"><tr><th className="px-2 py-1 text-left">State</th><th className="px-2 py-1 text-left">Count</th></tr></thead>
                                <tbody>
                                    {Object.entries(byState).sort((a,b)=>b[1]-a[1]).slice(0,20).map(([s,c]) => (
                                        <tr key={s} className="border-t"><td className="px-2 py-1">{s}</td><td className="px-2 py-1">{c}</td></tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
