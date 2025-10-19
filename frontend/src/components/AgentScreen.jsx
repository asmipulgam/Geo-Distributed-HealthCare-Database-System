import React, {use, useEffect, useState} from "react";
import {useParams} from "react-router-dom";

export default function Agent() {

    const {region} = useParams();
    const [records, setRecords] = useState({});
    const [nextCursor,setNextCursor] = useState(null);
    const [prevCursor, setPrevCursor] = useState(null);
    const [loading,setLoading] = useState(false);

    const fetchRecords = async (cursor = null, dir = "next") => {
        setLoading(true);
        try {
            const res = await fetch(`/api/all?region=${region}&cursor=${cursor || "0"}&dir=${dir}`, {})

            const data = await res.json();

            setRecords(data.records || []);
            setNextCursor(data.records.nextIndex || null);
            setPrevCursor(data.records.prevIndex || null);
        } catch (e) {
            console.error("Issue fetching paginated data: "+e);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchRecords()
    });

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6">
            <h2 className="text-3xl font-bold mb-6">Agents — {region}</h2>

            {loading ? (
                <p className="text-gray-400">Loading...</p>
            ) : (
                <div className="w-full max-w-4xl overflow-x-auto rounded-xl shadow-lg border border-gray-800">
                    <table className="min-w-full border-collapse">
                        <thead className="bg-gray-900">
                        <tr>
                            <th className="py-3 px-6 text-left border-b border-gray-800">Agent ID</th>
                            <th className="py-3 px-6 text-left border-b border-gray-800">Name</th>
                            <th className="py-3 px-6 text-left border-b border-gray-800">Region</th>
                            <th className="py-3 px-6 text-left border-b border-gray-800">Last Active</th>
                        </tr>
                        </thead>
                        <tbody>
                        {records.map((agent, idx) => (
                            <tr
                                key={agent.id}
                                className={`${idx % 2 === 0 ? "bg-black" : "bg-gray-900"} hover:bg-gray-800 transition`}
                            >
                                <td className="py-3 px-6">{}</td>
                                <td className="py-3 px-6">{}</td>
                                <td className="py-3 px-6">{}</td>
                                <td className="py-3 px-6">{}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="flex gap-4 mt-6">
                <button
                    disabled={!prevCursor || loading}
                    onClick={() => fetchRecords(prevCursor, "prev")}
                    className="px-5 py-2 border border-white rounded-full disabled:opacity-30"
                >
                    Prev
                </button>
                <button
                    disabled={!nextCursor || loading}
                    onClick={() => fetchRecords(nextCursor, "next")}
                    className="px-5 py-2 border border-white rounded-full disabled:opacity-30"
                >
                    Next
                </button>
            </div>
        </div>

    );

}