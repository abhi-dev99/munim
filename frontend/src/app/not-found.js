import Link from 'next/link';
import { FileQuestion } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4 font-sans text-center">
      <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <div className="mx-auto w-12 h-12 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mb-4">
          <FileQuestion size={24} />
        </div>
        <h2 className="text-2xl font-black text-gray-900 mb-2">Page Not Found</h2>
        <p className="text-gray-500 mb-6 text-sm">We couldn't find the page you're looking for.</p>
        <Link 
          href="/"
          className="w-full py-3 px-4 bg-black text-white font-semibold rounded-xl hover:bg-gray-800 transition-colors inline-block"
        >
          Return Home
        </Link>
      </div>
    </div>
  );
}
