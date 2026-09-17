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
    <div className="flex-none bg-white border border-[var(--border-subtle)]">
      <div className="px-4 py-2.5 border-b border-[var(--border-subtle)] flex items-center gap-2">
        <CalendarDays size={14} className="text-[var(--text-muted)]" />
        <span className="font-bold text-xs uppercase tracking-wider text-black">Compliance Timeline</span>
        <span className="text-[10px] text-[var(--text-muted)] ml-auto uppercase tracking-widest">
          {isComposition ? "Quarterly" : "Monthly Cycle"}
        </span>
      </div>
      <div className="flex divide-x divide-[var(--border-subtle)]">
        {steps.map((step, idx) => (
          <div key={idx} className="flex-1 px-3 py-3">
            <div className={`flex items-center gap-1.5 mb-0.5 ${step.completed ? "text-[var(--green-primary)]" : "text-[var(--text-secondary)]"}`}>
              {step.completed ? <CheckCircle2 size={11} /> : <Clock size={11} />}
              <span className="text-[10px] font-bold uppercase tracking-widest">
                {isComposition ? step.day + "th" : "+" + step.day + "th"}
              </span>
            </div>
            <div className={`text-xs font-bold leading-tight ${step.completed ? "text-black" : "text-[var(--text-secondary)]"}`}>
              {step.label}
            </div>
            <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{step.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
