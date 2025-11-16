import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BACKEND_URL } from './constants';
import USChoroplethMap from './USChoroplethMap';

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
                //const res = await fetch('/api/nodes'); // Example API endpoint
                //const data = await res.json();
                // Assuming API returns { summary: { total, active, dead }, nodes: [{id, region, status, logsUrl}] }
                //setStats(data.summary);
                //setNodes(data.nodes);
                setNodes({'1d782d03-e0b2-4caa-9383-384877b74427': {'primary_region': 'central', 'nodes': [{'node_region': 'us-central1', 'node_id': 'cotton-prawn-10234.jxf.gcp-us-central1.cockroachlabs.cloud'}, {'node_region': 'us-east1', 'node_id': 'cotton-prawn-10234.jxf.gcp-us-east1.cockroachlabs.cloud'}, {'node_region': 'us-west2', 'node_id': 'cotton-prawn-10234.jxf.gcp-us-west2.cockroachlabs.cloud'}]}, '588e784c-737a-46ea-a410-05ffbba8bd85': {'primary_region': 'west', 'nodes': [{'node_region': 'us-central1', 'node_id': 'sixear-gundi-10233.jxf.gcp-us-central1.cockroachlabs.cloud'}, {'node_region': 'us-east1', 'node_id': 'sixear-gundi-10233.jxf.gcp-us-east1.cockroachlabs.cloud'}, {'node_region': 'us-west2', 'node_id': 'sixear-gundi-10233.jxf.gcp-us-west2.cockroachlabs.cloud'}]}})
            } catch (err) {
                console.error('Error fetching data:', err);
            }
        }
        fetchData();
        // also fetch recent metrics for admin display
        async function fetchMetrics() {
            try {
                const res = await fetch(`${BACKEND_URL}/api/metrics`);
                if (!res.ok) throw new Error(`metrics fetch failed: ${res.status}`);
                const data = await res.json();
                setRecentMetrics(data.metrics || []);
            } catch (err) {
                console.error('Error fetching metrics:', err);
            }
        }
        fetchMetrics();
    }, []);

    // Dummy backup handler for now
    const handleBackup = () => {
        console.log('Backup triggered (dummy)')
        
        try {
            fetch(`${BACKEND_URL}/api/backup`).then(res => {
                if (!res.ok) throw new Error(`Backup failed: ${res.status}`);
                console.log('Backup successful');
            }).catch(err => {
                console.error('Backup error:', err);
            });
        } catch (err) {
            console.error('Backup error:', err);
        }
    }

    return (
        <div className="min-h-screen bg-gray-50 p-6 flex flex-col items-center">
            <div className="w-full max-w-7xl">
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-3xl font-bold text-gray-800">Cluster Dashboard</h1>
                    <div>
                        <button
                            onClick={handleBackup}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 transition"
                        >
                            Backup
                        </button>
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

                    {/* Recent Query Metrics (latest) */}
                    <div className="mt-6 px-4">
                        <div className="bg-white shadow-sm rounded-xl p-4 border border-gray-100">
                            <h3 className="text-md font-medium text-gray-700 mb-2">Recent Query Metrics</h3>
                            {(!recentMetrics || recentMetrics.length === 0) ? (
                                <div className="text-sm text-gray-500">No metrics collected yet.</div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    {recentMetrics.slice(0,3).map((m, idx) => (
                                        <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                                            <div className="text-sm text-gray-600">{new Date(m.timestamp).toLocaleString()}</div>
                                            <div className="text-sm text-gray-600">Region: {m.region}</div>
                                            <div className="text-lg font-semibold text-gray-900 mt-2">{m.metrics.rows} rows</div>
                                            <div className="text-sm text-gray-700">Query time: {m.metrics.select_time_ms} ms</div>
                                            {m.metrics.explain_time_ms != null && (
                                                <div className="text-sm text-gray-500">Explain: {m.metrics.explain_time_ms} ms</div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>


                {/* Node List (collapsible clusters) */}
                <div className="bg-white shadow-md rounded-2xl border border-gray-100 mx-4 mb-10">
                    <div className="border-b px-6 py-4">
                        <h2 className="text-xl font-semibold text-gray-800">Node Details</h2>
                    </div>
                    <div className="p-6">
                        {(!nodes || Object.keys(nodes).length === 0) ? (
                            <div className="text-center py-6 text-gray-500">Loading or no data available...</div>
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
                                                {/* Cluster-level key/value pairs (excluding nodes array) */}
                                                <div className="mb-3">
                                                    {Object.entries(cluster).filter(([k]) => k !== 'nodes').map(([k, v]) => (
                                                        <div key={k} className="flex items-start gap-4 text-sm text-gray-700">
                                                            <div className="w-36 font-semibold text-gray-600">{k}</div>
                                                            <div className="flex-1">{JSON.stringify(v)}</div>
                                                        </div>
                                                    ))}
                                                </div>

                                                {/* Nodes array: iterate and display indented */}
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
            </div>
        </div>
    );
}
