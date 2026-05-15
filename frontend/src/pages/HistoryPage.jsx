import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getJobsHistory } from '../api/client.js';

const STATUS_COLORS = {
  completed: 'text-green-400',
  failed:    'text-red-400',
  running:   'text-amber-400',
  pending:   'text-slate-400',
};

function timeAgo(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'Az önce';
  if (m < 60) return `${m} dk önce`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} sa önce`;
  return `${Math.floor(h / 24)} gün önce`;
}

function DsommChip({ score }) {
  if (score == null) return <span className="text-slate-600">—</span>;
  const color = score >= 70 ? 'text-green-400' : score >= 40 ? 'text-amber-400' : 'text-red-400';
  return <span className={`font-semibold ${color}`}>{score.toFixed(1)}</span>;
}

export default function HistoryPage() {
  const [records, setRecords]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [selected, setSelected] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    getJobsHistory(50).then((res) => {
      setLoading(false);
      if (res.ok) setRecords(res.data);
      else setError(res.error);
    });
  }, []);

  const toggleSelect = (jobId) => {
    setSelected((prev) => {
      if (prev.includes(jobId)) return prev.filter((id) => id !== jobId);
      if (prev.length >= 2) return prev;
      return [...prev, jobId];
    });
  };

  const handleCompare = () => {
    if (selected.length === 2) {
      navigate(`/compare?job_a=${selected[0]}&job_b=${selected[1]}`);
    }
  };

  const handleTrends = (repoUrl) => {
    navigate(`/trends?repo_url=${encodeURIComponent(repoUrl)}`);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Analiz Geçmişi</h1>
          <p className="text-slate-400 text-sm mt-1">
            Son {records.length} analiz · Karşılaştırmak için 2 satır seçin
          </p>
        </div>
        <div className="flex gap-3">
          {selected.length === 2 && (
            <button className="btn-primary text-sm" onClick={handleCompare}>
              🔄 Karşılaştır ({selected.length}/2)
            </button>
          )}
          {selected.length === 1 && (
            <span className="text-xs text-slate-400 self-center">1 seçildi — 1 tane daha seçin</span>
          )}
          <button className="btn-ghost text-sm" onClick={() => navigate('/')}>
            + Yeni Analiz
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center py-20">
          <span className="text-slate-500 animate-pulse">Yükleniyor...</span>
        </div>
      )}

      {error && (
        <div className="card border-red-700 text-red-300 text-sm">⚠ {error}</div>
      )}

      {!loading && !error && records.length === 0 && (
        <div className="text-center py-20">
          <p className="text-4xl mb-3">📭</p>
          <p className="text-slate-400">Henüz analiz yapılmamış.</p>
          <button className="btn-primary mt-4" onClick={() => navigate('/')}>İlk Analizi Başlat</button>
        </div>
      )}

      {records.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-800 text-slate-400 text-xs uppercase tracking-wider">
                <th className="px-3 py-3 w-8"></th>
                <th className="text-left px-4 py-3">Repo</th>
                <th className="text-left px-4 py-3">Dil</th>
                <th className="text-center px-4 py-3">DSOMM</th>
                <th className="text-center px-4 py-3">Bulgular</th>
                <th className="text-center px-4 py-3">Platform</th>
                <th className="text-right px-4 py-3">Tarih</th>
                <th className="px-3 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => {
                const isSelected = selected.includes(r.job_id);
                const isDisabled = selected.length === 2 && !isSelected;
                return (
                  <tr
                    key={r.job_id}
                    className={`border-t border-slate-700 transition-colors ${
                      isSelected
                        ? 'bg-blue-900/20 border-l-2 border-l-blue-500'
                        : i % 2 === 0 ? 'bg-slate-900/30' : 'bg-slate-800/10'
                    } ${isDisabled ? 'opacity-40' : 'hover:bg-slate-800/50'}`}
                  >
                    <td className="px-3 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={isDisabled}
                        onChange={() => toggleSelect(r.job_id)}
                        className="w-4 h-4 accent-blue-500 cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <button
                        onClick={() => handleTrends(r.repo_url)}
                        className="text-blue-300 hover:text-blue-200 font-medium truncate block max-w-[220px] text-left"
                        title="Trend grafiğini görüntüle"
                      >
                        {r.repo_url.replace('https://github.com/', '')}
                      </button>
                      <span className={`text-xs ${STATUS_COLORS[r.status] ?? 'text-slate-500'}`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{r.language ?? '—'}</td>
                    <td className="px-4 py-3 text-center">
                      <DsommChip score={r.dsomm_total} />
                    </td>
                    <td className="px-4 py-3 text-center text-slate-300">
                      {r.total_findings ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-center text-slate-400 text-xs">
                      {r.platform?.replace('_', ' ') ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-500 text-xs whitespace-nowrap">
                      {timeAgo(r.finished_at ?? r.created_at)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="flex gap-2 justify-end">
                        {r.status === 'completed' && (
                          <button
                            onClick={() => navigate(`/result/${r.job_id}`)}
                            className="text-xs text-slate-500 hover:text-blue-300 transition-colors"
                            title="Sonucu görüntüle"
                          >
                            🔍
                          </button>
                        )}
                        <button
                          onClick={() => handleTrends(r.repo_url)}
                          className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                          title="Trend"
                        >
                          📈
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
