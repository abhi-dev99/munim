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

  return (
    <div className="bg-white border border-[var(--border-subtle)] overflow-hidden flex flex-col h-full max-h-[600px]">
      <div className="p-4 border-b border-[var(--border-subtle)] bg-white space-y-1">
        <h3 className="font-bold text-sm uppercase tracking-wider text-black flex items-center gap-2">
          <CalendarDays size={16} className="text-[var(--text-muted)]" />
          Compliance Timeline
        </h3>
        <p className="text-[10px] text-[var(--text-secondary)] uppercase tracking-widest">
          {isComposition ? "Quarterly Cycle" : "Monthly Cycle"}
        </p>
      </div>

      <div className="p-6 flex-1 flex flex-col justify-center">
        <div className="relative border-l border-[var(--border-subtle)] ml-3 space-y-8">
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

            return (
              <a 
                key={idx} 
                href="/demo/gst-portal" 
                target="_blank" 
                rel="noopener noreferrer"
                className="relative pl-6 block group hover:bg-[var(--bg-secondary)] p-2 -ml-2 rounded-lg transition-colors cursor-pointer"
              >
                {/* Dot */}
                <div className={`absolute -left-0.5 top-2.5 w-4 h-4 rounded-full border-2 flex items-center justify-center bg-white ${step.completed ? 'border-[var(--green-primary)]' : 'border-[var(--border-subtle)]'}`}>
                  {step.completed ? (
                    <CheckCircle2 size={10} className="text-[var(--green-primary)]" />
                  ) : (
                    <Clock size={10} className="text-[var(--text-muted)]" />
                  )}
                </div>
                
                <div className="flex flex-col">
                  <span className={`text-[10px] font-bold uppercase tracking-widest ${step.completed ? 'text-[var(--green-primary)]' : 'text-[var(--text-secondary)]'} group-hover:text-black transition-colors`}>
                    {exactDateStr}
                  </span>
                  <span className={`text-sm font-bold mt-1 group-hover:underline ${step.completed ? 'text-black' : 'text-[var(--text-secondary)]'}`}>
                    {step.label}
                  </span>
                  <span className="text-xs text-[var(--text-muted)] mt-0.5">
                    {step.desc}
                  </span>
                </div>
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}
