"use client";

import { CheckCircle2, Clock, CalendarDays } from "lucide-react";

export default function GSTTimeline({ isComposition }) {
  const today = new Date().getDate();

  const regularSteps = [
    { day: 11, label: "GSTR-1 Due", desc: "Outward supplies", completed: today > 11 },
    { day: 14, label: "GSTR-2B Generated", desc: "Auto-drafted ITC", completed: today > 14 },
    { day: 20, label: "GSTR-3B Due", desc: "Tax payment & filing", completed: today > 20 },
  ];

  const compositionSteps = [
    { day: 18, label: "CMP-08 Due", desc: "Quarterly self-assessed tax", completed: today > 18 },
    { day: 30, label: "GSTR-4 Due", desc: "Annual return (April 30th)", completed: false },
  ];

  const steps = isComposition ? compositionSteps : regularSteps;

  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-white border border-[var(--border-subtle)] overflow-hidden flex flex-col h-full max-h-[600px]">
      <div className="p-4 border-b border-[var(--border-subtle)] bg-white space-y-1 flex justify-between items-start">
        <div>
          <h3 className="font-bold text-sm uppercase tracking-wider text-black flex items-center gap-2">
            <CalendarDays size={16} className="text-[var(--text-muted)]" />
            Compliance Timeline
          </h3>
          <p className="text-[10px] text-[var(--text-secondary)] uppercase tracking-widest mt-1">
            {isComposition ? "Quarterly Cycle" : "Monthly Cycle"}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs font-mono font-bold text-black bg-gray-100 px-2 py-1 rounded">
            {currentTime.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
          <div className="text-[9px] text-[var(--text-secondary)] uppercase tracking-widest mt-0.5">
            {currentTime.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
          </div>
        </div>
      </div>

      <div className="p-5 flex-1 flex flex-col justify-center">
        <div className="relative border-l border-[var(--border-subtle)] ml-3 space-y-6">
          {steps.map((step, idx) => {
            // Calculate actual date based on current month/year
            const currentYear = new Date().getFullYear();
            const currentMonth = new Date().toLocaleString('default', { month: 'long' });
            
            // Format suffix (st, nd, rd, th)
            const d = step.day;
            const suffix = ["th", "st", "nd", "rd"][(d % 10 > 3) || (Math.floor(d % 100 / 10) === 1) ? 0 : d % 10];
            
            const exactDateStr = isComposition && step.day === 30 && step.label === "GSTR-4 Due" 
              ? "30th April, " + (currentYear + 1) + " - 11:59 PM" 
              : `${d}${suffix} ${currentMonth}, ${currentYear} - 11:59 PM`;

            // Identify the imminent deadline (the first one that is NOT completed)
            const isImminent = !step.completed && steps.findIndex(s => !s.completed) === idx;
            const isGstr1 = step.label.includes("GSTR-1");
            
            const ItemWrapper = isGstr1 ? "div" : "a";
            const wrapperProps = isGstr1 ? {} : { href: "file:///D:/hackathob/kleos-4.0/demo/index.html", target: "_blank", rel: "noopener noreferrer" };

            return (
              <ItemWrapper 
                key={idx} 
                {...wrapperProps}
                className={`relative pl-6 block group p-2 -ml-2 rounded-lg transition-colors ${isGstr1 ? '' : 'cursor-pointer hover:bg-[var(--bg-secondary)]'} ${isImminent ? 'bg-yellow-50/50 border border-yellow-200 shadow-sm' : ''}`}
              >
                {/* Dot */}
                <div className={`absolute -left-[3px] top-2.5 w-4 h-4 rounded-full border-2 flex items-center justify-center bg-white ${step.completed ? 'border-[var(--green-primary)]' : isImminent ? 'border-red-500 animate-pulse' : 'border-[var(--border-subtle)]'}`}>
                  {step.completed ? (
                    <CheckCircle2 size={10} className="text-[var(--green-primary)]" />
                  ) : isImminent ? (
                    <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                  ) : (
                    <Clock size={10} className="text-[var(--text-muted)]" />
                  )}
                </div>
                
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold uppercase tracking-widest ${step.completed ? 'text-[var(--green-primary)]' : isImminent ? 'text-red-600' : 'text-[var(--text-secondary)]'} ${!isGstr1 && 'group-hover:text-black'} transition-colors`}>
                      {exactDateStr}
                    </span>
                    {isImminent && (
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-red-100 text-red-600 uppercase tracking-wider animate-pulse">
                        Due Soon
                      </span>
                    )}
                  </div>
                  <span className={`text-sm font-bold mt-1 ${!isGstr1 && 'group-hover:underline'} ${step.completed ? 'text-black' : isImminent ? 'text-red-700' : 'text-[var(--text-secondary)]'}`}>
                    {step.label}
                  </span>
                  <span className={`text-xs mt-0.5 ${isImminent ? 'text-red-600/80' : 'text-[var(--text-muted)]'}`}>
                    {step.desc}
                  </span>
                </div>
              </ItemWrapper>
            );
          })}
        </div>
      </div>
    </div>
  );
}
