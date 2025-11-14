import React, { useEffect, useState } from "react";
import {useParams} from "react-router-dom";
import { BACKEND_URL } from "./constants";

export default function Agent() {

    const {region} = useParams();
    const [records, setRecords] = useState([]);
    const [nextCursor,setNextCursor] = useState(null);
    const [prevCursor, setPrevCursor] = useState(null);
    const [loading,setLoading] = useState(false);
    const [count, setCount] = useState(0);
    const [offset, setOffset] = useState(0);
    const fetchRecords = async (cursor = 0, dir = "next") => {
        setLoading(true);
        try {
            const res = await fetch(
                `${BACKEND_URL}/api/all?region=${region}&cursor=${cursor}&dir=${dir}`
            );
            if (!res.ok) throw new Error(`backend error ${res.status}`);
            const pRes = await res.json();

            // expected pRes: { records: [...], nextIndex: number|null, prevIndex: number|null }
            setRecords(pRes.records || []);
            setNextCursor(pRes.nextIndex ?? null);
            setPrevCursor(pRes.prevIndex ?? null);
            setCount(pRes.count ?? 0);
            setOffset(pRes.offset ?? 0);
        } catch (e) {
            console.error("Issue fetching paginated data:", e);
        } finally {
            setLoading(false);
        }
    };

    // Fetch once on mount and when region changes
    useEffect(() => {
        fetchRecords(0, "next");
    }, [region]);

    return (
        <div className="flex flex-col items-center justify-start min-h-screen p-6 bg-gradient-to-b from-gray-900 via-gray-950 to-black">
            <div className="w-full max-w-4xl">
                <header className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-3xl font-semibold text-white">All Patients</h2>
                        <p className="text-sm text-gray-400">Region — <span className="font-medium text-gray-200">{region}</span></p>
                    </div>
                    <div className="text-right">
                        <div className="text-sm text-gray-400">{loading ? "Loading…" : `Showing ${offset+1}-${Math.min(offset + records.length, count)} of ${count}`}</div>
                    </div>
                </header>

                <div className="bg-gray-850 rounded-lg shadow-xl border border-gray-800 overflow-hidden">
                    <table className="min-w-full table-auto">
                        <thead>
                        <tr className="bg-gray-800 text-gray-300 text-left">
                            <th className="py-3 px-4 text-sm font-medium">Agent ID</th>
                            <th className="py-3 px-4 text-sm font-medium">Name</th>
                            <th className="py-3 px-4 text-sm font-medium">Region</th>
                            <th className="py-3 px-4 text-sm font-medium">Last Active</th>
                        </tr>
                        </thead>
                        <tbody>
                        {records.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="py-8 text-center text-gray-500">No records to display</td>
                            </tr>
                        ) : (
                            records.map((agent, idx) => (
                                <tr key={agent.id} className={`${idx % 2 === 0 ? "bg-gray-900" : "bg-gray-950"} hover:bg-gray-800 transition` }>
                                    <td className="py-3 px-4 text-sm text-gray-200 font-mono">{agent.id}</td>
                                    <td className="py-3 px-4 text-sm text-gray-100">{(agent.first_name || "") + (agent.last_name ? ` ${agent.last_name}` : "")}</td>
                                    <td className="py-3 px-4 text-sm text-gray-300">{agent.Region || agent.region || region}</td>
                                    <td className="py-3 px-4 text-sm text-gray-300">{agent["Visit Date"] || agent.visit_date || "-"}</td>
                                </tr>
                            ))
                        )}
                        </tbody>
                    </table>
                </div>

                <div className="flex items-center justify-between gap-4 mt-6">
                    <button
                        disabled={(prevCursor === null || prevCursor === undefined) || loading}
                        onClick={() => fetchRecords(prevCursor, "prev")}
                        className="px-4 py-2 bg-gray-800 text-gray-200 rounded-md border border-gray-700 disabled:opacity-40"
                    >
                        Prev
                    </button>

                    <div className="text-sm text-gray-400">Page offset: {offset}</div>

                    <button
                        disabled={(nextCursor === null || nextCursor === undefined) || loading}
                        onClick={() => fetchRecords(nextCursor, "next")}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-40"
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );

}