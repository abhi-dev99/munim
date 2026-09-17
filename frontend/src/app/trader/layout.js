export default function TraderLayout({ children }) {
  return (
    <div className="max-w-md mx-auto min-h-screen bg-[var(--bg-primary)] shadow-2xl overflow-hidden relative">
      {/* Mobile Status Bar Simulation */}
      <div className="h-6 w-full bg-black/5 flex items-center justify-between px-4">
        <span className="text-[10px] font-medium">9:41</span>
        <div className="flex gap-1">
          <div className="w-3 h-3 rounded-full bg-black/20"></div>
          <div className="w-3 h-3 rounded-full bg-black/20"></div>
          <div className="w-3 h-3 rounded-full bg-black/20"></div>
        </div>
      </div>
      {children}
    </div>
  );
}
