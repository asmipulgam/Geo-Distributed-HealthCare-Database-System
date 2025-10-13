import React from "react";
import { useLocation, Link } from "react-router-dom";
//import "tailwindcss/index.css"

export default function CustomerData() {
    const location = useLocation();
    const user = location.state?.user ?? {
        id: "123456",
        name: "Jane Doe"
    };

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen">
                <h2 className="text-2xl mb-4">No data received</h2>
                <Link to="/login" className="px-6 py-2">Go Back to Login</Link>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6">
            <h2 className="text-4xl font-bold mb-8">User Details</h2>

            <div className="w-full max-w-2xl overflow-x-auto rounded-2xl shadow-lg">
                <table className="min-w-full border text-left">
                    <thead className="border-b">
                    <tr>
                        <th className="py-3 px-6 uppercase tracking-wider">Key</th>
                        <th className="py-3 px-6 uppercase tracking-wider">Value</th>
                    </tr>
                    </thead>
                    <tbody>
                    {Object.entries(user).map(([key, value], idx) => (
                        <tr
                            key={key}
                            className={`${idx % 2 === 0 ? "bg-black" : "bg-gray-900"} hover:bg-gray-800 transition`}
                        >
                            <td className="py-3 px-6 font-medium capitalize">{key}</td>
                            <td className="py-3 px-6 text-gray-300">{value.toString()}</td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>

            <Link to="/login" className="mt-8 px-6 py-2">
                Back to Login
            </Link>
        </div>
    );
}
