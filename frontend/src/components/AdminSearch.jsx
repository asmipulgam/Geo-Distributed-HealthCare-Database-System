import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BACKEND_URL } from './constants';

const COLS = [
    "id","first_name","last_name","email","Phone number","weight","age","gender","Prefix","Martial Status","Address","City","State","Hospital Name","Hospital Address","Region","Visit Date","Treatment","Doctor Appointed","Number of Doctors Appointed","Doctor's Contact","Allergies","Height",
];

const OPERATORS = ['=', '!=', 'LIKE', '<', '>', '<=', '>=', 'IN'];

function buildWhereClause(filters) {
    if (!filters || filters.length === 0) return '';
    const parts = filters
        .filter(f => f.col && f.op && f.val !== undefined && f.val !== '')
        .map(f => {
            const col = `\"${f.col}\"`;
            if (f.op === 'IN') {
                // assume comma-separated values
                const vals = f.val.split(',').map(v => v.trim()).filter(Boolean);
                const quoted = vals.map(v => `'${v.replace(/'/g, "''")}'`).join(', ');
                return `${col} IN (${quoted})`;
            }
            if (f.op === 'LIKE') {
                return `${col} LIKE '%${f.val.replace(/'/g, "''")}%'`;
            }
            // numeric-looking values should not be quoted — naive heuristic
            const isNum = /^-?\d+(\.\d+)?$/.test(f.val);
            return isNum ? `${col} ${f.op} ${f.val}` : `${col} ${f.op} '${f.val.replace(/'/g, "''")}'`;
        });
    return parts.length ? 'WHERE ' + parts.join(' AND ') : '';
}

export default function AdminSearch() {
    const [filters, setFilters] = useState([{ col: 'id', op: '=', val: '' }]);
    const [region, setRegion] = useState('us-west');
    const [results, setResults] = useState([]);
    const [sqlPreview, setSqlPreview] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    function updateFilter(i, key, value) {
        const next = [...filters];
        next[i] = { ...next[i], [key]: value };
        setFilters(next);
    }

    function addFilter() {
        setFilters(prev => [...prev, { col: 'id', op: '=', val: '' }]);
    }

    function removeFilter(i) {
        setFilters(prev => prev.filter((_, idx) => idx !== i));
    }

    async function runSearch(e) {
        e && e.preventDefault();
        setLoading(true);
        try {
            // Build SQL preview
            const where = buildWhereClause(filters);
            const sql = `SELECT * FROM patients ${where} LIMIT 1000;`;
            setSqlPreview(sql);

            // Try backend search endpoint first (if implemented)
            let data = null;
            try {
                const res = await fetch(`${BACKEND_URL}/api/search`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ region, filters }),
                });
                if (res.ok) {
                    data = await res.json();
                    // expected: { records: [...] }
                    if (data && data.records) {
                        setResults(data.records);
                        setLoading(false);
                        return;
                    }
                }
            } catch (err) {
                // ignore and fallback to client-side filtering
            }

            // Fallback: fetch a larger page from /api/all, then filter client-side
            const pageRes = await fetch(`${BACKEND_URL}/api/all?region=${region}&page_size=1000`);
            const page = await pageRes.json();
            const rows = page.records || [];

            // apply filters client-side
            const filtered = rows.filter(r => {
                return filters.every(f => {
                    if (!f.col || f.val === undefined || f.val === '') return true;
                    const raw = r[f.col];
                    if (raw === null || raw === undefined) return false;
                    const sval = String(raw).toLowerCase();
                    const q = String(f.val).toLowerCase();
                    switch (f.op) {
                        case '=': return sval === q;
                        case '!=': return sval !== q;
                        case 'LIKE': return sval.includes(q);
                        case 'IN': return f.val.split(',').map(s=>s.trim().toLowerCase()).includes(sval);
                        case '>': return Number(sval) > Number(q);
                        case '<': return Number(sval) < Number(q);
                        case '>=': return Number(sval) >= Number(q);
                        case '<=': return Number(sval) <= Number(q);
                        default: return true;
                    }
                });
            });

            setResults(filtered);
        } catch (err) {
            console.error('Search failed', err);
        } finally {
            setLoading(false);
        }
    }

    function openAnalytics() {
        // Navigate to analytics page and pass results in state
        navigate('/analytics', { state: { rows: results } });
    }

    return (
        <div className="min-h-screen p-6 bg-gray-50">
            <div className="max-w-6xl mx-auto">
                <h1 className="text-2xl font-bold mb-4">Admin Search</h1>

                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700">Region</label>
                    <select className="mt-1 p-2 border rounded" value={region} onChange={e => setRegion(e.target.value)}>
                        <option value="us-west">us-west</option>
                        <option value="us-central">us-central</option>
                        <option value="us-east">us-east</option>
                    </select>
                </div>

                <form onSubmit={runSearch} className="space-y-3 mb-6">
                    {filters.map((f, i) => (
                        <div key={i} className="flex gap-2 items-center">
                            <select value={f.col} onChange={e => updateFilter(i, 'col', e.target.value)} className="p-2 border rounded">
                                {COLS.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                            <select value={f.op} onChange={e => updateFilter(i, 'op', e.target.value)} className="p-2 border rounded">
                                {OPERATORS.map(op => <option key={op} value={op}>{op}</option>)}
                            </select>
                            <input value={f.val} onChange={e => updateFilter(i, 'val', e.target.value)} className="p-2 border rounded flex-1" placeholder="value" />
                            <button type="button" onClick={() => removeFilter(i)} className="px-3 py-1 bg-red-500 text-white rounded">Remove</button>
                        </div>
                    ))}

                    <div className="flex gap-2">
                        <button type="button" onClick={addFilter} className="px-3 py-2 bg-blue-600 text-white rounded">Add Filter</button>
                        <button type="submit" className="px-3 py-2 bg-green-600 text-white rounded">Run Search</button>
                        <button type="button" onClick={runSearch} className="px-3 py-2 bg-gray-200 rounded">Refresh</button>
                        <button type="button" onClick={openAnalytics} className="ml-auto px-3 py-2 bg-indigo-600 text-white rounded" disabled={!results || results.length===0}>Open Analytics</button>
                    </div>
                </form>

                <div className="mb-6">
                    <h3 className="font-medium">SQL Preview</h3>
                    <pre className="bg-white p-3 rounded border text-sm">{sqlPreview || '—'}</pre>
                </div>

                <div>
                    <h3 className="font-medium mb-2">Results ({results.length})</h3>
                    {loading ? <div>Loading...</div> : (
                        <div className="overflow-auto border rounded bg-white">
                            <table className="min-w-full text-sm">
                                <thead className="bg-gray-100">
                                    <tr>
                                        {COLS.map(c => <th key={c} className="px-2 py-1 text-left">{c}</th>)}
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.map((r, idx) => (
                                        <tr key={idx} className="border-t">
                                            {COLS.map(c => <td key={c} className="px-2 py-1">{String(r[c] ?? '')}</td>)}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
