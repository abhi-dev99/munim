"use client";

import { useState, useRef } from "react";
import { Camera, Zap, RefreshCcw, X, CheckCircle2, FileText, ChevronLeft, Upload } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function InvoiceScanner() {
  const [stream, setStream] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const videoRef = useRef(null);

  // In a real app, this would request camera permissions using navigator.mediaDevices.getUserMedia
  // For the hackathon/demo, we simulate the camera view or allow file upload fallback
  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.log("Camera access denied or unavailable, using fallback.", err);
    }
  };

  const captureImage = () => {
    setScanning(true);
    // Simulate capturing and scanning delay
    setTimeout(() => {
      setCapturedImage("demo_invoice");
      // Stop scanning animation after 2.5s
      setTimeout(() => {
        setScanning(false);
        simulateExtraction();
      }, 2500);
    }, 500);
  };

  const simulateExtraction = () => {
    // In a real flow, we'd POST the image to /api/v1/webhook/invoice
    setResult({
      supplier: "Balaji Hardware",
      amount: "14,500",
      date: "12-Jun-2026",
      gstin: "27XXBBR4321R1Z9",
      status: "Verified & Synced"
    });
  };

  const resetScanner = () => {
    setCapturedImage(null);
    setResult(null);
    setScanning(false);
  };

  return (
    <div className="fixed inset-0 bg-black text-white flex flex-col h-dvh overflow-hidden font-sans">
      
      {/* Top Navigation */}
      <div className="flex items-center justify-between p-4 z-20 absolute top-0 left-0 right-0 bg-gradient-to-b from-black/80 to-transparent">
        <Link href="/" className="p-2 rounded-full bg-black/40 backdrop-blur border border-white/10 text-white">
          <ChevronLeft size={24} />
        </Link>
        <div className="flex items-center gap-4">
          <button className="p-2 rounded-full bg-black/40 backdrop-blur border border-white/10 text-white">
            <Zap size={20} />
          </button>
        </div>
      </div>

      {/* Main Viewfinder Area */}
      <div className="flex-1 relative bg-[#111] overflow-hidden flex items-center justify-center">
        
        {/* Mock Camera Feed Background */}
        {!capturedImage && (
          <div className="absolute inset-0 opacity-40 bg-[url('https://images.unsplash.com/photo-1626263468007-88229bbf7df5?q=80&w=1000&auto=format&fit=crop')] bg-cover bg-center filter blur-sm grayscale" />
        )}

        {/* Captured Image */}
        {capturedImage && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute inset-4 rounded-2xl bg-[url('https://images.unsplash.com/photo-1626263468007-88229bbf7df5?q=80&w=1000&auto=format&fit=crop')] bg-cover bg-center shadow-2xl border border-white/20"
          />
        )}

        {/* Viewfinder Frame (Only when not captured) */}
        {!capturedImage && (
          <div className="relative w-3/4 max-w-sm aspect-[3/4] border-2 border-white/30 rounded-3xl z-10">
            {/* Corner Markers */}
            <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-white rounded-tl-3xl -ml-1 -mt-1" />
            <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-white rounded-tr-3xl -mr-1 -mt-1" />
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-white rounded-bl-3xl -ml-1 -mb-1" />
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-white rounded-br-3xl -mr-1 -mb-1" />
            
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="text-white/60 text-sm font-medium tracking-wide">Align invoice within frame</p>
            </div>
          </div>
        )}

        {/* Laser Scanning Animation */}
        <AnimatePresence>
          {scanning && (
            <motion.div 
              initial={{ top: '10%' }}
              animate={{ top: '90%' }}
              transition={{ duration: 1.2, repeat: Infinity, repeatType: 'reverse', ease: 'linear' }}
              className="absolute left-4 right-4 h-1 bg-[var(--blue-primary)] shadow-[0_0_20px_rgba(59,130,246,1)] z-20"
            />
          )}
        </AnimatePresence>

        {/* Success Overlay */}
        <AnimatePresence>
          {result && (
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute inset-4 bg-black/80 backdrop-blur-md rounded-3xl p-6 z-30 flex flex-col justify-center items-center text-center border border-[var(--border-subtle)]"
            >
              <motion.div 
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", delay: 0.2 }}
                className="w-20 h-20 rounded-full bg-[var(--green-glow)] border border-[rgba(16,185,129,0.2)] flex items-center justify-center mb-6"
              >
                <CheckCircle2 size={40} className="text-[var(--green-primary)]" />
              </motion.div>
              <h2 className="text-2xl font-bold mb-2">Invoice Captured</h2>
              <p className="text-white/70 mb-8 text-sm">Munim.ai has extracted the data and synced it with your CA's dashboard.</p>
              
              <div className="w-full bg-white/10 rounded-2xl p-4 text-left space-y-3 mb-8 border border-white/10">
                <div className="flex justify-between items-center border-b border-white/10 pb-2">
                  <span className="text-white/60 text-sm">Supplier</span>
                  <span className="font-bold">{result.supplier}</span>
                </div>
                <div className="flex justify-between items-center border-b border-white/10 pb-2">
                  <span className="text-white/60 text-sm">Amount</span>
                  <span className="font-bold text-[var(--green-primary)]">₹{result.amount}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-white/60 text-sm">GSTIN</span>
                  <span className="font-mono text-sm">{result.gstin}</span>
                </div>
              </div>

              <button 
                onClick={resetScanner}
                className="w-full py-4 rounded-xl bg-white text-black font-bold tracking-wide hover:bg-gray-200 transition-colors"
              >
                Scan Another Invoice
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom Controls */}
      <div className="h-40 bg-black flex items-center justify-around px-8 pb-8 z-20">
        <button className="p-4 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors">
          <FileText size={24} />
        </button>

        {/* Shutter Button */}
        <button 
          onClick={captureImage}
          disabled={scanning || result}
          className="relative w-20 h-20 rounded-full border-4 border-white flex items-center justify-center disabled:opacity-50"
        >
          <div className="w-16 h-16 bg-white rounded-full transition-transform active:scale-90" />
        </button>

        <button className="p-4 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors relative overflow-hidden">
          <Upload size={24} />
          <input type="file" accept="image/*" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => {
            if(e.target.files && e.target.files[0]) {
              captureImage();
            }
          }} />
        </button>
      </div>
    </div>
  );
}
