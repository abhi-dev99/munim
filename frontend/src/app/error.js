'use client';
import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle } from 'lucide-react';

export default function Error({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4 font-sans text-center">
      <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <div className="mx-auto w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
          <AlertTriangle size={24} />
        </div>
        <h2 className="text-2xl font-black text-gray-900 mb-2">Something went wrong!</h2>
        <p className="text-gray-500 mb-6 text-sm">{error.message || "An unexpected error occurred."}</p>
        <div className="flex flex-col gap-3">
          <button
            onClick={() => reset()}
            className="w-full py-3 px-4 bg-black text-white font-semibold rounded-xl hover:bg-gray-800 transition-colors"
          >
            Try again
          </button>
          <Link 
            href="/"
            className="w-full py-3 px-4 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition-colors inline-block"
          >
            Return Home
          </Link>
        </div>
      </div>
    </div>
  );
}
