const CONFIG = {
  CRITICAL: { bg: 'bg-violet-900/60', text: 'text-violet-300', border: 'border-violet-700', dot: 'bg-violet-400' },
  HIGH:     { bg: 'bg-red-900/60',    text: 'text-red-300',    border: 'border-red-700',    dot: 'bg-red-400' },
  MEDIUM:   { bg: 'bg-amber-900/60',  text: 'text-amber-300',  border: 'border-amber-700',  dot: 'bg-amber-400' },
  LOW:      { bg: 'bg-green-900/60',  text: 'text-green-300',  border: 'border-green-700',  dot: 'bg-green-400' },
};

export default function SeverityBadge({ severity, count }) {
  const c = CONFIG[severity] ?? CONFIG.LOW;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {severity}
      {count !== undefined && <span className="ml-0.5 opacity-80">({count})</span>}
    </span>
  );
}

export function RiskLevelBadge({ level }) {
  const labels = { LOW: 'Düşük Risk', MEDIUM: 'Orta Risk', HIGH: 'Yüksek Risk', CRITICAL: 'Kritik Risk' };
  const c = CONFIG[level] ?? CONFIG.LOW;
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold border ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-2 h-2 rounded-full animate-pulse ${c.dot}`} />
      {labels[level] ?? level}
    </span>
  );
}
