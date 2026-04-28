const STATUS_CONFIG = {
  pending:   { icon: '○',  color: 'text-slate-500', bg: 'border-slate-700',    label: 'Bekliyor'   },
  running:   { icon: '◌',  color: 'text-blue-400',  bg: 'border-blue-700',     label: 'Çalışıyor'  },
  completed: { icon: '✓',  color: 'text-green-400', bg: 'border-green-700',    label: 'Tamamlandı' },
  failed:    { icon: '✗',  color: 'text-red-400',   bg: 'border-red-700',      label: 'Hata'       },
};

// Bulgu sayısını kısa göster (sast/sca/secret için)
function FindingSummary({ data }) {
  if (!data) return null;
  const total = data.total_count ?? data.total ?? null;
  if (total === null) return null;
  return (
    <span className="text-xs text-slate-400">
      {total === 0 ? 'Bulgu yok' : `${total} bulgu`}
    </span>
  );
}

export default function AgentProgress({ name, label, icon, status = 'pending', data = null, error = null }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;

  return (
    <div className={`flex items-center gap-4 p-4 rounded-xl border bg-slate-800/60 transition-all duration-300 ${cfg.bg}`}>
      {/* Sol: araç ikonu */}
      <div className="text-2xl w-8 text-center select-none">{icon}</div>

      {/* Orta: isim + durum */}
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm text-white truncate">{label}</div>
        <div className={`text-xs mt-0.5 flex items-center gap-1.5 ${cfg.color}`}>
          <span className={status === 'running' ? 'animate-spin inline-block' : ''}>{cfg.icon}</span>
          <span>{cfg.label}</span>
          {status === 'completed' && <FindingSummary data={data} />}
          {status === 'failed' && error && (
            <span className="text-red-400 truncate max-w-[180px]">{error}</span>
          )}
        </div>
      </div>

      {/* Sağ: durum noktası */}
      <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
        status === 'completed' ? 'bg-green-400' :
        status === 'running'   ? 'bg-blue-400 animate-pulse' :
        status === 'failed'    ? 'bg-red-400' :
        'bg-slate-600'
      }`} />
    </div>
  );
}
