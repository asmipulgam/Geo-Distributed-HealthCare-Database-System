import React, { useState } from 'react';
import { BACKEND_URL } from './constants';

// Hardcoded hospitals list (name, address, coords, region, state)
const HOSPITALS = [
    { id: 'h1', name: 'Saint Mary Medical Center', address: '123 Main St, Los Angeles, CA', lat: 34.0522, lng: -118.2437, region: 'us-west', state: 'CA' },
    { id: 'h2', name: 'Pioneer Regional Hospital', address: '456 Oak Ave, San Francisco, CA', lat: 37.7749, lng: -122.4194, region: 'us-west', state: 'CA' },
    { id: 'h3', name: 'Central Valley Clinic', address: '789 Pine Rd, Fresno, CA', lat: 36.7378, lng: -119.7871, region: 'us-west', state: 'CA' },
    { id: 'h4', name: 'Rocky Ridge Hospital', address: '10 Summit Dr, Denver, CO', lat: 39.7392, lng: -104.9903, region: 'us-west', state: 'CO' },
    { id: 'h5', name: 'Lakeside Medical', address: '22 Lake St, Seattle, WA', lat: 47.6062, lng: -122.3321, region: 'us-west', state: 'WA' },
    { id: 'h6', name: 'Midtown Central Hospital', address: '1 Center Plaza, Chicago, IL', lat: 41.8781, lng: -87.6298, region: 'us-central', state: 'IL' },
    { id: 'h7', name: 'Great Plains Hospital', address: '77 Prairie Rd, Omaha, NE', lat: 41.2565, lng: -95.9345, region: 'us-central', state: 'NE' },
    { id: 'h8', name: 'Bayview Hospital', address: '300 Bay St, Miami, FL', lat: 25.7617, lng: -80.1918, region: 'us-east', state: 'FL' },
    { id: 'h9', name: 'Riverside General', address: '9 River Rd, New York, NY', lat: 40.7128, lng: -74.0060, region: 'us-east', state: 'NY' },
    { id: 'h10', name: 'Northern Health Center', address: '400 North Ave, Minneapolis, MN', lat: 44.9778, lng: -93.2650, region: 'us-central', state: 'MN' },
];

export default function OrganSearch() {
    const [hospitalId, setHospitalId] = useState(HOSPITALS[0].id);
    const [donorOnly, setDonorOnly] = useState(true);
    const [ageMin, setAgeMin] = useState('');
    const [ageMax, setAgeMax] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const selectedHospital = HOSPITALS.find(h => h.id === hospitalId);

    async function handleSearch(e) {
        e && e.preventDefault();
        setLoading(true); setError(null); setResults([]);
        try {
            const body = {
                hospital: selectedHospital,
                donor_only: donorOnly,
                age_min: ageMin ? Number(ageMin) : undefined,
                age_max: ageMax ? Number(ageMax) : undefined,
            };

            const res = await fetch(`${BACKEND_URL}/api/organ_search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                const err = await res.json().catch(()=>({error:res.statusText}));
                throw new Error(err.error || err.message || 'search failed');
            }

            const data = await res.json();
            setResults(data.records || []);
        } catch (err) {
            console.error('Organ search error', err);
            setError(String(err));
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen p-6 bg-gray-50">
            <div className="max-w-4xl mx-auto bg-white p-6 rounded shadow">
                <h1 className="text-xl font-bold mb-4">Organ Donation — Find Potential Donors</h1>
                <form onSubmit={handleSearch} className="space-y-3">
                    <div>
                        <label className="block text-sm font-medium">Hospital</label>
                        <select value={hospitalId} onChange={e => setHospitalId(e.target.value)} className="mt-1 p-2 border rounded w-full">
                            {HOSPITALS.map(h => (
                                <option key={h.id} value={h.id}>{h.name} — {h.address}</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div className="flex items-center gap-2">
                            <input id="donorOnly" type="checkbox" checked={donorOnly} onChange={e=>setDonorOnly(e.target.checked)} className="h-4 w-4" />
                            <label htmlFor="donorOnly" className="text-sm">Require organ donor</label>
                        </div>

                        <div>
                            <label className="block text-sm font-medium">Min age</label>
                            <input className="mt-1 p-2 border rounded w-full" value={ageMin} onChange={e=>setAgeMin(e.target.value)} type="number" />
                        </div>

                        <div>
                            <label className="block text-sm font-medium">Max age</label>
                            <input className="mt-1 p-2 border rounded w-full" value={ageMax} onChange={e=>setAgeMax(e.target.value)} type="number" />
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">Search</button>
                        <button type="button" className="px-4 py-2 bg-gray-200 rounded" onClick={()=>{ setResults([]); setError(null); }}>Clear</button>
                    </div>
                </form>

                <div className="mt-6">
                    <h2 className="font-medium">Results ({results.length})</h2>
                    {loading && <div className="text-sm text-gray-500">Searching...</div>}
                    {error && <div className="text-sm text-red-600">{error}</div>}

                    <div className="overflow-auto mt-3 border rounded bg-white">
                        <table className="min-w-full text-sm">
                            <thead className="bg-gray-100"><tr>
                                <th className="px-2 py-1 text-left">Donor Patient_ID</th>
                                <th className="px-2 py-1 text-left">Distance</th>
                                <th className="px-2 py-1 text-left">Patient_Name</th>
                                <th className="px-2 py-1 text-left">Age</th>
                                <th className="px-2 py-1 text-left">Gender</th>
                                <th className="px-2 py-1 text-left">Address</th>
                                <th className="px-2 py-1 text-left">State</th>
                                <th className="px-2 py-1 text-left">Doctor / Hospital</th>
                            </tr></thead>
                            <tbody>
                                {results.map((r, idx) => (
                                    <tr key={r.Patient_ID || idx} className="border-t">
                                        <td className="px-2 py-1">{r.Patient_ID || r.id}</td>
                                        <td className="px-2 py-1">{(r.distance_km !== undefined && r.distance_km !== null) ? `${Number(r.distance_km).toFixed(2)} km` : ''}</td>
                                        <td className="px-2 py-1">{r.Patient_Name || `${r.first_name || ''} ${r.last_name || ''}`}</td>
                                        <td className="px-2 py-1">{r.Age || r.age}</td>
                                        <td className="px-2 py-1">{r.Gender || r.gender}</td>
                                        <td className="px-2 py-1">{r.Address || r.City || ''}</td>
                                        <td className="px-2 py-1">{r.State}</td>
                                        <td className="px-2 py-1">{r.Doctor_Name || r['Doctor Appointed'] || r['Hospital Name'] || r.doctor_hospital || ''}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
