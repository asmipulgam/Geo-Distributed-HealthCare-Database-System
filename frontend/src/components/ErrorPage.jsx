import React from "react";
import { Link } from "react-router-dom";

export default function ErrorPage() {
    return (
        <div className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white font-sans overflow-hidden" style={{width: "100vw", height: "100vh", alignItems: "center"}}>
            {/* Main content */}
            <div className="text-center px-6">
                <h1 className="text-9xl font-extrabold text-white tracking-widest mb-4 animate-pulse">
                    404
                </h1>
                <p className="text-2xl md:text-3xl font-light mb-8 text-gray-400">
                    Oops — The page you’re looking for doesn’t exist.
                </p>

                <div className="flex justify-center gap-4">
                    <Link
                        to="/"
                        className="border border-white px-6 py-2 rounded-full hover:bg-white hover:text-black transition-all duration-300"
                    >
                        Go Home
                    </Link>
                </div>
            </div>

            {/* Footer (absolute, not affecting centering) */}
            <footer className="absolute bottom-6 text-gray-500 text-sm">
                &copy; {new Date().getFullYear()} — All rights reserved.
            </footer>
        </div>
    );
}
