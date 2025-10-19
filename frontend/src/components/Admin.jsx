import React, { useState } from "react";
import "tailwindcss/index.css"

export default function Admin() {
    const [formData, setFormData] = useState({
        name: "",
        role: "",
        region: "",
        email: "",
        department: "",
        remarks: "",
    });

    const [status, setStatus] = useState("");

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus("Submitting...");

        try {
            const response = await fetch("/api/admin/create", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData),
            });

            if (response.ok) {
                setStatus("✅ Record submitted successfully!");
                setFormData({
                    name: "",
                    role: "",
                    region: "",
                    email: "",
                    department: "",
                    remarks: "",
                });
            } else {
                setStatus("❌ Failed to submit record.");
            }
        } catch (error) {
            console.error("Error submitting form:", error);
            setStatus("⚠️ Network error.");
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6">
            <h2 className="text-4xl font-bold mb-8">Admin Form</h2>

            <form
                onSubmit={handleSubmit}
                className="w-full max-w-md  p-6 rounded-2xl shadow-lg border bg-green-300 space-y-4"
            >
                {Object.keys(formData).map((field) => (
                    <div key={field} className="flex flex-col">
                        <label htmlFor={field} className="capitalize mb-1 text-blue-700">
                            {field}:
                        </label>
                        <input
                            id={field}
                            name={field}
                            type="text"
                            value={formData[field]}
                            onChange={handleChange}
                            style={{marginLeft: "40px",marginRight: "40px"}}
                            className="bg-white border border-blue-400 rounded-lg p-2 text-white"
                        />
                    </div>
                ))}

                <button
                    type="submit"
                    className="w-full mt-4 py-2 border border-white rounded-full hover:bg-white hover:text-black transition-all duration-300"
                >
                    Submit
                </button>
            </form>

            {status && <p className="mt-4 text-gray-400">{status}</p>}
        </div>
    );
}
