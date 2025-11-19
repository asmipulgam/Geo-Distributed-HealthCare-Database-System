import React, { useState } from "react";
import "tailwindcss/index.css"
import { BACKEND_URL } from "./constants";

const US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
    'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana',
    'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
}

export default function AdminAdd() {
    const [formData, setFormData] = useState({
        Patient_ID: '',
        Patient_Name: '',
        Doctor_ID: '',
        Doctor_Name: '',
        Age: '',
        Gender: '',
        Phone: '',
        Email: '',
        Address: '',
        State: '',
        Region: '',
        Appointment_Date: '',
        Diagnosis: '',
        Date_of_Birth: '',
        is_organ_donor: false,
        lat: '',
        lon: '',
    });

    const [status, setStatus] = useState("");

    const handleChange = (e) => {
        const { name, type, value, checked } = e.target;
        setFormData({
            ...formData,
            [name]: type === 'checkbox' ? checked : value,
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus("Submitting...");

        try {
            const response = await fetch(`${BACKEND_URL}/api/admin/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData),
            });

            if (response.ok) {
                setStatus(" Record submitted successfully!");
                setFormData({
                    Patient_ID: '', Patient_Name: '', Doctor_ID: '', Doctor_Name: '', Age: '', Gender: '', Phone: '', Email: '', Address: '', State: '', Region: '', Appointment_Date: '', Diagnosis: '', Date_of_Birth: '', is_organ_donor: false, lat: '', lon: ''
                });
            } else {
                setStatus(" Failed to submit record.");
            }
        } catch (error) {
            console.error("Error submitting form:", error);
            setStatus(" Network error.");
        }
    };

    // Dummy region update function; user will replace with real logic
    const updateRegionForState = (stateAbbrev) => {
        const west = new Set(['AK','AZ','CA','CO','HI','ID','MT','NV','NM','OR','UT','WA','WY'])
        const central = new Set(['AR','IA','IL','IN','KS','KY','LA','MI','MN','MO','MS','NE','ND','OH','OK','SD','TN','TX','WI'])
        const east = new Set(['AL','CT','DE','FL','GA','MA','MD','ME','NH','NJ','NY','NC','PA','RI','SC','VT','VA','WV'])

        let regionVal = ''
        if (west.has(stateAbbrev)) regionVal = 'us-west'
        else if (central.has(stateAbbrev)) regionVal = 'us-central'
        else if (east.has(stateAbbrev)) regionVal = 'us-east'
        else regionVal = ''

        setFormData(prev => ({ ...prev, 'Region': regionVal }))
    }

    const handleStateChange = (e) => {
        const val = e.target.value
        setFormData(prev => ({ ...prev, 'State': val }))
        updateRegionForState(val)
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6 bg-gray-50">
            <h2 className="text-3xl font-semibold mb-6 text-gray-800">Admin Form</h2>

            <form
                onSubmit={handleSubmit}
                className="w-full max-w-3xl p-6 rounded-2xl shadow bg-white border border-gray-100 space-y-4"
            >
                {Object.keys(formData).map((field) => (
                    <div key={field} className="flex flex-col">
                        <label htmlFor={field} className="text-sm font-medium text-gray-700 mb-1">{field}</label>

                        {field === 'State' ? (
                            <select
                                id={field}
                                name={field}
                                value={formData[field]}
                                onChange={(e) => { handleChange(e); handleStateChange(e); }}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="">Select a state</option>
                                {Object.entries(US_STATES).map(([abbrev, full]) => (
                                    <option key={abbrev} value={abbrev}>{full}</option>
                                ))}
                            </select>
                        ) : field === 'Region' ? (
                            <input
                                id={field}
                                name={field}
                                type="text"
                                value={formData[field]}
                                readOnly
                                className="mt-1 block w-full rounded-md border-gray-200 bg-gray-50 py-2 px-3"
                            />
                        ) : field === 'is_organ_donor' ? (
                            <div className="flex items-center gap-2">
                                <input id={field} name={field} type="checkbox" checked={!!formData[field]} onChange={handleChange} className="h-4 w-4" />
                                <label htmlFor={field} className="text-sm">Is organ donor</label>
                            </div>
                        ) : (
                            <input
                                id={field}
                                name={field}
                                type={field.includes('Date') || field === 'Date_of_Birth' ? 'date' : (field === 'Age' ? 'number' : 'text')}
                                value={formData[field]}
                                onChange={handleChange}
                                className="mt-1 block w-full rounded-md border-gray-300 p-2"
                            />
                        )}
                    </div>
                ))}

                <div className="flex items-center justify-end">
                    <button
                        type="submit"
                        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                        Submit
                    </button>
                </div>
            </form>

            {status && <p className="mt-4 text-gray-600">{status}</p>}
        </div>
    );
}
