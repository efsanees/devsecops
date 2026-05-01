const CATEGORY_META = {
  build_deployment:     { label: 'Build & Deployment', max: 30, icon: '🏗️' },
  testing:              { label: 'Test & Tarama',       max: 25, icon: '🧪' },
  implementation:       { label: 'Implementation',      max: 25, icon: '💻' },
  information_gathering:{ label: 'Bilgi Toplama',       max: 10, icon: '🔍' },
  culture_org:          { label: 'Kültür & Org',        max: 10, icon: '📚' },
};

const LEVEL_COLOR = {
  'Başlangıç': 'text-red-400 bg-red-900/30 border-red-700',
  'Gelişen':   'text-amber-400 bg-amber-900/30 border-amber-700',
  'Olgun':     'text-green-400 bg-green-900/30 border-green-700',
};

function barColor(pct) {
  if (pct >= 70) return 'bg-green-500';
  if (pct >= 40) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function DsommDashboard({ dsomm }) {
  if (!dsomm) return null;
  const { total_score = 0, level = 'Başlangıç', categories = {} } = dsomm;
  const levelCls = LEVEL_COLOR[level] ?? LEVEL_COLOR['Başlangıç'];

  return (
    <div className="space-y-4">
      {/* Genel skor */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <span className="text-4xl font-bold text-white">{total_score}</span>
          <span className="text-slate-500 text-lg">/100</span>
        </div>
        <span className={`px-3 py-1.5 rounded-full border text-sm font-semibold ${levelCls}`}>
          {level}
        </span>
      </div>

      {/* Kategori bar'ları */}
      <div className="space-y-3">
        {Object.entries(CATEGORY_META).map(([key, { label, max, icon }]) => {
          const score = categories[key] ?? 0;
          const pct   = Math.round((score / max) * 100);
          return (
            <div key={key}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-slate-300 flex items-center gap-1.5">
                  <span>{icon}</span>{label}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {score}<span className="text-slate-600">/{max}</span>
                </span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${barColor(pct)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
