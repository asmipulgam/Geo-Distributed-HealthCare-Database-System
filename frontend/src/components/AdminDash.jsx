import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BACKEND_URL } from './constants';

export default function AdminDash() {
    const [stats, setStats] = useState({ total: 6, active: 6, dead: 0 });
    const [nodes, setNodes] = useState([]);

    useEffect(() => {
        async function fetchData() {
            try {
                const res = await fetch('/api/nodes'); // Example API endpoint
                const data = await res.json();
                // Assuming API returns { summary: { total, active, dead }, nodes: [{id, region, status, logsUrl}] }
                setStats(data.summary);
                setNodes(data.nodes);
            } catch (err) {
                console.error('Error fetching data:', err);
            }
        }
       // fetchData();
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


                {/* Node List */}
                <div className="bg-white shadow-md rounded-2xl border border-gray-100 mx-4 mb-10">
                    <div className="border-b px-6 py-4">
                        <h2 className="text-xl font-semibold text-gray-800">Node Details</h2>
                    </div>
                    <div className="overflow-x-auto p-6">
                        <table className="min-w-full text-sm text-left text-gray-600">
                            <thead className="border-b bg-gray-100 text-gray-700">
                            <tr>
                                <th className="py-3 px-4">Node ID</th>
                                <th className="py-3 px-4">Region</th>
                                <th className="py-3 px-4">Status</th>
                                <th className="py-3 px-4">Logs</th>
                            </tr>
                            </thead>
                            <tbody>
                            {nodes.length === 0 ? (
                                <tr>
                                    <td colSpan="4" className="text-center py-6 text-gray-500">
                                        Loading or no data available...
                                    </td>
                                </tr>
                            ) : (
                                nodes.map((node, i) => (
                                    <tr key={i} className="border-b hover:bg-gray-50 transition">
                                        <td className="py-3 px-4 font-medium text-gray-800">{node.id}</td>
                                        <td className="py-3 px-4">{node.region}</td>
                                        <td className={`py-3 px-4 font-semibold ${node.status === 'active' ? 'text-green-600' : 'text-red-600'}`}>
                                            {node.status}
                                        </td>
                                        <td className="py-3 px-4">
                                            <a
                                                href={node.logsUrl}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-block px-3 py-1 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-100 transition"
                                            >
                                                View Logs
                                            </a>
                                        </td>
                                    </tr>
                                ))
                            )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
