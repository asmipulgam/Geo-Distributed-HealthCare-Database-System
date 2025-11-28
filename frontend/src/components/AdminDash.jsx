import React, { useEffect, useState } from 'react';
import { BACKEND_URL } from './constants';
import USChoroplethMap from './USChoroplethMap';
import {motion} from "framer-motion";


//A Dashboard screen similar to CockroachDB Admin Cluster Dashboard. We are using the API key to CockroachDB clusters to fetch the Cluster's and Node's informatipn and display it here.
export default function AdminDash() {
    const [stats, setStats] = useState({ total: 6, active: 6, dead: 0 });
    const [nodes, setNodes] = useState([]);
    const [recentMetrics, setRecentMetrics] = useState([]);
    const [expanded, setExpanded] = useState({});

    const toggleExpanded = (id) => {
        setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
    }

    useEffect(() => {
        async function fetchData() {
            try {
                const res = await fetch(`${BACKEND_URL}/api/nodes`); // Example API endpoint
                const data = await res.json();
                console.log("Fetched cluster/node data:", data);
                setStats({
                    total: Object.keys(data).length * 3, 
                    active: Object.values(data).filter(cluster => Array.isArray(cluster.nodes)).length * 3,
                    dead: Object.values(data).filter(cluster => Array.isArray(cluster.nodes) && cluster.nodes.every(node => node.status === 'dead')).length,
                });
                setNodes(data);
                // also fetch recent metrics for admin UI
                try {
                    const mres = await fetch(`${BACKEND_URL}/api/metrics`);
                    if (mres.ok) {
                        const md = await mres.json();
                        setRecentMetrics(md.metrics || []);
                    }
                } catch (err) {
                    console.error('Error fetching recent metrics:', err);
                }
                //setNodes({'1d782d03-e0b2-4caa-9383-384877b74427': {'primary_region': 'central', 'nodes': [{'node_region': 'us-central1', 'node_id': 'cotton-prawn-10234.jxf.gcp-us-central1.cockroachlabs.cloud'}, {'node_region': 'us-east1', 'node_id': 'cotton-prawn-10234.jxf.gcp-us-east1.cockroachlabs.cloud'}, {'node_region': 'us-west2', 'node_id': 'cotton-prawn-10234.jxf.gcp-us-west2.cockroachlabs.cloud'}]}, '588e784c-737a-46ea-a410-05ffbba8bd85': {'primary_region': 'west', 'nodes': [{'node_region': 'us-central1', 'node_id': 'sixear-gundi-10233.jxf.gcp-us-central1.cockroachlabs.cloud'}, {'node_region': 'us-east1', 'node_id': 'sixear-gundi-10233.jxf.gcp-us-east1.cockroachlabs.cloud'}, {'node_region': 'us-west2', 'node_id': 'sixear-gundi-10233.jxf.gcp-us-west2.cockroachlabs.cloud'}]}})
            } catch (err) {
                console.error('Error fetching data:', err);
            }
        }
        fetchData();
    }, []);

    //CockroachDB Free cluster automatically backups data. So what we are doing for Project purpose is displaying a List of Buckets from Google Cloud Storage directly here. 
    // const handleBackup = () => {
      
        
    //     try {
    //         fetch(`${BACKEND_URL}/api/backup`).then(res => {
    //             if (!res.ok) throw new Error(`Backup failed: ${res.status}`);
    //             console.log('Backup successful');
    //         }).catch(err => {
    //             console.error('Backup error:', err);
    //         });
    //     } catch (err) {
    //         console.error('Backup error:', err);
    //     }
    // }

    return (
        <div className="min-h-screen bg-gray-50 p-6 flex flex-col items-center">
            <div className="w-full max-w-7xl">
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-3xl font-bold text-gray-800">Cluster Dashboard</h1>
                    <div>
                        {/* <button
                            onClick={handleBackup}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 transition"
                        >
                            Backup
                        </button> */}
                    </div>
                </div>


                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10 px-4">
                    {[
                        { label: 'Total Nodes', value: stats.total },
                        { label: 'Active Nodes', value: stats.active },
                        { label: 'Dead Nodes', value: stats.dead },
                    ].map((item, index) => (
                        <motion.div
                            key={item.label}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="bg-white shadow-md rounded-2xl p-6 border border-gray-100 flex flex-col items-center justify-center text-center"
                        >
                            <h2 className="text-lg font-medium text-gray-700 mb-2">{item.label}</h2>
                            <p className="text-3xl font-semibold text-gray-900">{item.value}</p>
                        </motion.div>
                    ))}
                </div>


                <div className="bg-white shadow-md rounded-2xl border border-gray-100 mx-4 mb-10">
                    <div className="border-b px-6 py-4">
                        <h2 className="text-xl font-semibold text-gray-800">Node Details</h2>
                    </div>
                    <div className="p-6">
                        {(!nodes || Object.keys(nodes).length === 0) ? (
                            <div className="text-center py-6 text-gray-500">Loading...</div>
                        ) : (
                            <div className="space-y-4">
                                {Object.entries(nodes).map(([clusterId, cluster]) => (
                                    <div key={clusterId} className="border rounded-lg">
                                        <button
                                            type="button"
                                            onClick={() => toggleExpanded(clusterId)}
                                            className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-t-lg"
                                        >
                                            <div className="flex items-center gap-3">
                                                <svg className={`w-4 h-4 transform ${expanded[clusterId] ? 'rotate-90' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M6 4a1 1 0 011.707-.707l6 6a1 1 0 010 1.414l-6 6A1 1 0 016 16.293L11.586 10 6 4.707A1 1 0 016 4z" clipRule="evenodd" />
                                                </svg>
                                                <span className="font-medium text-gray-800">{clusterId}</span>
                                            </div>
                                            <div className="text-sm text-gray-500">{cluster.primary_region || ''}</div>
                                        </button>

                                        {expanded[clusterId] && (
                                            <div className="px-6 py-4 bg-white">
                                                <div className="mb-3">
                                                    {Object.entries(cluster).filter(([k]) => k !== 'nodes').map(([k, v]) => (
                                                        <div key={k} className="flex items-start gap-4 text-sm text-gray-700">
                                                            <div className="w-36 font-semibold text-gray-600">{k}</div>
                                                            <div className="flex-1">{JSON.stringify(v)}</div>
                                                        </div>
                                                    ))}
                                                </div>

                                                {Array.isArray(cluster.nodes) && (
                                                    <div className="space-y-2">
                                                        {cluster.nodes.map((n, idx) => (
                                                            <div key={idx} className="pl-6 border-l-2 border-gray-100">
                                                                {Object.entries(n).map(([nk, nv]) => (
                                                                    <div key={nk} className="flex items-start gap-3 text-sm text-gray-700">
                                                                        <div className="w-28 text-gray-600">{nk}</div>
                                                                        <div className="flex-1">{nv}</div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                        <div>
                            <USChoroplethMap />
                        </div>
                    </div>

                    <div className="bg-white shadow-md rounded-2xl border border-gray-100 mx-4 mb-10 p-6">
                        <div className="border-b pb-3 mb-4">
                            <h2 className="text-xl font-semibold text-gray-800">Recent Query Metrics</h2>
                        </div>
                        {(!recentMetrics || recentMetrics.length === 0) ? (
                            <div className="text-gray-500">No recent metrics available.</div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm text-left">
                                    <thead>
                                        <tr className="text-xs text-gray-500">
                                            <th className="px-2 py-1">Time</th>
                                            <th className="px-2 py-1">Endpoint</th>
                                            <th className="px-2 py-1">Region</th>
                                            <th className="px-2 py-1">Rows</th>
                                            <th className="px-2 py-1">Elapsed (ms)</th>
                                            <th className="px-2 py-1">Per-Region</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recentMetrics.slice(0, 25).map((m, idx) => (
                                            <tr key={idx} className="border-t">
                                                <td className="px-2 py-2 text-gray-700">{m.timestamp || ''}</td>
                                                <td className="px-2 py-2 text-gray-700">{m.endpoint || ''}</td>
                                                <td className="px-2 py-2 text-gray-700">{m.region || ''}</td>
                                                <td className="px-2 py-2 text-gray-700">{(m.rows ?? (m.metrics && (m.metrics.rows ?? null))) ?? '-'}</td>
                                                <td className="px-2 py-2 text-gray-700">{(m.elapsed_ms ?? (m.metrics && (m.metrics.select_time_ms ?? m.metrics.elapsed_ms ?? null))) ?? '-'}</td>
                                                <td className="px-2 py-2 text-gray-700">
                                                    {m.per_region ? (
                                                        <div className="text-xs text-gray-600">
                                                            {m.per_region.map((p, i) => (
                                                                <div key={i}>{p.region}: {p.elapsed_ms ?? '-'}ms ({p.rows ?? 0})</div>
                                                            ))}
                                                        </div>
                                                    ) : ('-')}
                                                </td>
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
