import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHistory } from '../api/client.js';
import SeverityBadge from '../components/SeverityBadge.jsx';

function GradeChip({ grade }) {
  const colors = {
    A: 'bg-green-900/50 text-green-300 border-green-700',
    B: 'bg-blue-900/50 text-blue-300 border-blue-700',
    C: 'bg-amber-900/50 text-amber-300 border-amber-700',
    D: 'bg-red-900/50 text-red-300 border-red-700',
  };
  if (!grade) return <span className="text-slate-600">—</span>;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${colors[grade] ?? 'bg-slate-700 text-slate-300 border-slate-600'}`}>
      {grade}
    </span>
  );
}

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

export default function HistoryPage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    getHistory(50).then((res) => {
      setLoading(false);
      if (res.ok) setRecords(res.data);
      else setError(res.error);
    });
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Analiz Geçmişi</h1>
          <p className="text-slate-400 text-sm mt-1">Son {records.length} analiz kaydı</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/')}>
          + Yeni Analiz
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-20">
          <span className="text-slate-500 animate-pulse">Yükleniyor...</span>
        </div>
      )}

      {error && (
        <div className="card border-red-700 text-red-300 text-sm">
          ⚠ {error}
        </div>
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
                <th className="text-left px-4 py-3">#</th>
                <th className="text-left px-4 py-3">Repo</th>
                <th className="text-left px-4 py-3">Dil</th>
                <th className="text-left px-4 py-3">Framework</th>
                <th className="text-center px-4 py-3">Not</th>
                <th className="text-center px-4 py-3">Risk</th>
                <th className="text-right px-4 py-3">Tarih</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => (
                <tr
                  key={r.id}
                  className={`border-t border-slate-700 hover:bg-slate-800/60 cursor-pointer transition-colors ${
                    i % 2 === 0 ? 'bg-slate-900/40' : 'bg-slate-800/20'
                  }`}
                  onClick={() => navigate('/', {
                    state: { prefill: r.repo_url }
                  })}
                >
                  <td className="px-4 py-3 text-slate-500">{r.id}</td>
                  <td className="px-4 py-3 max-w-xs">
                    <p className="text-white font-medium truncate">
                      {r.repo_url.replace('https://github.com/', '')}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{r.language ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-300">{r.framework ?? '—'}</td>
                  <td className="px-4 py-3 text-center">
                    {r.score !== null && r.score !== undefined ? (
                      <div className="flex flex-col items-center gap-1">
                        <GradeChip grade={r.grade} />
                        <span className="text-xs text-slate-500">{r.score}/100</span>
                      </div>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {r.risk_level
                      ? <SeverityBadge severity={r.risk_level} count={r.risk_score} />
                      : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-500 text-xs whitespace-nowrap">
                    {timeAgo(r.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
