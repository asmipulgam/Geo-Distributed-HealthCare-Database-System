import React, { useState, useEffect } from 'react';
import { BACKEND_URL } from './constants';

const COLS = [
    "Patient_ID","Patient_Name","Doctor_ID","Doctor_Name","Age","Gender","Phone","Email","Address","State","Region","Appointment_Date","Diagnosis","Date_of_Birth","is_organ_donor","lat","lon"
];

const OPERATORS = ['=', '!=', 'LIKE', '<', '>', '<=', '>=', 'IN'];

function buildWhereClause(filters) {
    if (!filters || filters.length === 0) return '';
    const parts = filters
        .filter(f => f.col && f.op && f.val !== undefined && f.val !== '')
        .map(f => {
            const col = `"${f.col}"`;
            if (f.op === 'IN') {
                const vals = f.val.split(',').map(v => v.trim()).filter(Boolean);
                const quoted = vals.map(v => `'${v.replace(/'/g, "''")}'`).join(', ');
                return `${col} IN (${quoted})`;
            }
            if (f.op === 'LIKE') {
                return `${col} LIKE '%${f.val.replace(/'/g, "''")}%'`;
            }
            const isNum = /^-?\d+(\.\d+)?$/.test(f.val);
            return isNum ? `${col} ${f.op} ${f.val}` : `${col} ${f.op} '${f.val.replace(/'/g, "''")}'`;
        });
    return parts.length ? 'WHERE ' + parts.join(' AND ') : '';
}

export default function AdminSearch() {
    const [filters, setFilters] = useState([{ col: 'Patient_ID', op: '=', val: '' }]);

    const [regions, setRegions] = useState(['us-west']);
    const [limit, setLimit] = useState(10);
    const [results, setResults] = useState([]);
    const [sqlPreview, setSqlPreview] = useState('');
    const [loading, setLoading] = useState(false);
    const [columnMap, setColumnMap] = useState({});
    const [searchMs, setSearchMs] = useState(null);

    useEffect(() => {
        if (results && results.length) console.log('AdminSearch results:', results.slice(0,3));
        if (results && results.length > 0) {
            const first = results[0];
            const m = {};
            for (const c of COLS) {
                const k = getMatchedKey(first, c);
                if (k) m[c] = k;
            }
            setColumnMap(m);
        } else {
            setColumnMap({});
        }
    }, [results]);
    function getValueFromRow(row, col) {
        if (!row) return '';

        function unwrap(r) {
            if (!r) return r;
            if (Array.isArray(r) && r.length > 0 && typeof r[0] === 'object') return r[0];
            const keys = Object.keys(r || {});
            if (keys.length === 1 && typeof r[keys[0]] === 'object') return r[keys[0]];
            return r;
        }

        const src = unwrap(row);
        if (!src) return '';

        if (Object.prototype.hasOwnProperty.call(src, col)) return src[col];

        const normalizedCol = String(col).replace(/[^a-z0-9]/gi, '').toLowerCase();

        const variants = [
            col,
            col.toLowerCase(),
            col.toUpperCase(),
            col.replace(/_/g, ' ').toLowerCase(),
            col.replace(/ /g, '_').toLowerCase(),

            col.replace(/([A-Z])/g, '_$1').toLowerCase(),

            col.toLowerCase().replace(/_([a-z])/g, (_, g) => g.toUpperCase()),
        ];

        for (const v of variants) {
            if (v && Object.prototype.hasOwnProperty.call(src, v)) return src[v];
        }
        for (const k of Object.keys(src)) {
            const nk = String(k).replace(/[^a-z0-9]/gi, '').toLowerCase();
            if (nk === normalizedCol) return src[k];
        }

        return '';
    }

   

    function formatCellValue(v) {
        if (v === true) return 'Yes';
        if (v === false) return 'No';
        if (v === null || v === undefined) return '';
        if (typeof v === 'object') {
            try { return JSON.stringify(v); } catch { return String(v); }
        }
        return String(v);
    }


    function getMatchedKey(row, col) {
        if (!row) return null;
        function unwrap(r) {
            if (!r) return r;
            if (Array.isArray(r) && r.length > 0 && typeof r[0] === 'object') return r[0];
            const keys = Object.keys(r || {});
            if (keys.length === 1 && typeof r[keys[0]] === 'object') return r[keys[0]];
            return r;
        }
        const src = unwrap(row);
        if (!src) return null;
        if (Object.prototype.hasOwnProperty.call(src, col)) return col;
        const normalizedCol = String(col).replace(/[^a-z0-9]/gi, '').toLowerCase();
        const variants = [
            col,
            col.toLowerCase(),
            col.toUpperCase(),
            col.replace(/_/g, ' ').toLowerCase(),
            col.replace(/ /g, '_').toLowerCase(),
            col.replace(/([A-Z])/g, '_$1').toLowerCase(),
            col.toLowerCase().replace(/_([a-z])/g, (_, g) => g.toUpperCase()),
        ];
        for (const v of variants) if (v && Object.prototype.hasOwnProperty.call(src, v)) return v;
        for (const k of Object.keys(src)) {
            const nk = String(k).replace(/[^a-z0-9]/gi, '').toLowerCase();
            if (nk === normalizedCol) return k;
        }
        return null;
    }
    function updateFilter(i, key, value) {
        const next = [...filters];
        next[i] = { ...next[i], [key]: value };
        setFilters(next);
    }

    function addFilter() {
        setFilters(prev => [...prev, { col: 'Patient_ID', op: '=', val: '' }]);
    }

    function removeFilter(i) {
        setFilters(prev => prev.filter((_, idx) => idx !== i));
    }

    async function runSearch(e) {
        e && e.preventDefault();
        setLoading(true);
        try {

            const where = buildWhereClause(filters);
            const sql = `SELECT * FROM patients ${where} LIMIT 10;`;
            setSqlPreview(sql);


            let data = null;
            try {
                const res = await fetch(`${BACKEND_URL}/api/search`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ regions, filters, limit }),
                });
                if (res.ok) {
                    data = await res.json();

                    console.log('Backend search data', data.records );
                    if (data && data.records) {
                        setResults(data.records);
                        setSearchMs(data.elapsed_ms ?? null);
                        setLoading(false);
                        return;
                    }
                }
            } catch (err) {

                console.error('Backend search error', err);
            }


            const fallbackRegion = (regions && regions.length) ? regions[0] : 'us-west';
            const pageRes = await fetch(`${BACKEND_URL}/api/all?region=${fallbackRegion}&page_size=10`);
            const page = await pageRes.json();
            const rows = page.records || [];


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
            setSearchMs(null);
        } catch (err) {
            console.error('Search failed', err);
        } finally {
            setLoading(false);
        }
    }


    return (
        <div className="min-h-screen p-6 bg-gray-50">
            <div className="max-w-6xl mx-auto">
                <h1 className="text-2xl font-bold mb-4">Admin Search</h1>

                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700">Regions (hold Ctrl/Cmd to select multiple)</label>
                    <select multiple className="mt-1 p-2 border rounded h-32" value={regions} onChange={e => setRegions(Array.from(e.target.selectedOptions).map(o => o.value))}>
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
                        <div className="flex items-center gap-2">
                            <label className="text-sm">Limit</label>
                            <input type="number" min={1} max={90000} value={limit} onChange={e => setLimit(Number(e.target.value || 0))} className="p-2 border rounded w-28" />
                        </div>
                        <button type="button" onClick={addFilter} className="px-3 py-2 bg-blue-600 text-white rounded">Add Filter</button>
                        <button type="submit" className="px-3 py-2 bg-green-600 text-white rounded">Run Search</button>
                        <button type="button" onClick={runSearch} className="px-3 py-2 bg-gray-200 rounded">Refresh</button>
                    </div>
                </form>

                <div className="mb-6">
                    <h3 className="font-medium">SQL Preview</h3>
                    <pre className="bg-white p-3 rounded border text-sm">{sqlPreview || '—'}</pre>
                    <div className="text-sm text-gray-600 mt-2">{searchMs !== null ? `Query time: ${searchMs} ms` : ''}</div>
                </div>

                <div>
                    <h3 className="font-medium mb-2">Results ({results.length})</h3>
                    {loading ? <div>Loading...</div> : (
                        <div className="overflow-auto border rounded bg-white shadow-sm">
                            <table className="min-w-full text-sm table-fixed border border-gray-300 bg-white rounded-sm">
                                <thead className="bg-gray-100">
                                    <tr>
                                        {COLS.map(c => <th key={c} className="px-2 py-1 text-center text-black border border-gray-300">{c}</th>)}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                        {results.map((r, idx) => (
                                            <tr key={idx} className="bg-white">
                                                {COLS.map(c => {

                                                    const mapped = columnMap[c];
                                                    const rawVal = mapped && Object.prototype.hasOwnProperty.call(r, mapped) ? r[mapped] : getValueFromRow(r, c);
                                                    const val = formatCellValue(rawVal);
                                                    return <td key={c} className="px-2 py-1 text-black border-l border-gray-200 text-center">{val}</td>;
                                                })}
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
