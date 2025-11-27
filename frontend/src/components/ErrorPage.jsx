import React from "react";
import { Link } from "react-router-dom";

export default function ErrorPage({ title = '404', message = 'This page is not implemented. Recheck URL.', links = [] }) {
    return (
        <div className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white font-sans overflow-hidden" style={{width: "100vw", height: "100vh", alignItems: "center"}}>
            <div className="text-center px-6">
                <h1 className="text-9xl font-extrabold text-white tracking-widest mb-4 animate-pulse">
                    {title}
                </h1>
                <p className="text-2xl md:text-3xl font-light mb-8 text-gray-400">
                    {message}
                </p>

                <div className="flex flex-col items-center gap-3">
                    <div className="flex justify-center gap-4 mb-2">
                        <Link
                            to="/"
                            className="border border-white px-6 py-2 rounded-full hover:bg-white hover:text-black transition-all duration-300"
                        >
                            Go Home
                        </Link>
                    </div>
                    {links && links.length > 0 && (
                        <div className="text-center text-gray-300">
                            <div className="mb-2">Try one of the valid agent regions:</div>
                            <div className="flex gap-3 justify-center">
                                {links.map((ln, idx) => (
                                    <Link key={idx} to={ln.to} className="underline text-blue-200 hover:text-blue-50">{ln.label}</Link>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
            <footer className="absolute bottom-6 text-gray-500 text-sm">
                &copy; {new Date().getFullYear()} — All rights reserved.
            </footer>
        </div>
    );
}
