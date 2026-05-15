const OWASP_LABELS = {
  'A01:2021': 'A01 Broken Access Control',
  'A02:2021': 'A02 Cryptographic Failures',
  'A03:2021': 'A03 Injection',
  'A04:2021': 'A04 Insecure Design',
  'A05:2021': 'A05 Security Misconfiguration',
  'A06:2021': 'A06 Vulnerable Components',
  'A07:2021': 'A07 Auth Failures',
  'A08:2021': 'A08 Software & Data Integrity',
  'A09:2021': 'A09 Logging & Monitoring',
  'A10:2021': 'A10 SSRF',
};

const OWASP_ORDER = Object.keys(OWASP_LABELS);

function countByOwasp(findings) {
  const counts = {};
  for (const f of findings) {
    const cat = f.owasp_category;
    if (cat) counts[cat] = (counts[cat] ?? 0) + 1;
  }
  return counts;
}

export default function OwaspChart({ findings = {} }) {
  const all = [
    ...(findings.sast     || []),
    ...(findings.sca      || []),
    ...(findings.secret   || []),
    ...(findings.pipeline || []),
  ];

  const counts = countByOwasp(all);
  const presentCategories = OWASP_ORDER.filter((k) => counts[k]);

  if (presentCategories.length === 0) {
    return (
      <div className="py-6 text-center text-slate-500 text-sm">
        OWASP kategorisi eşleşen bulgu yok.
      </div>
    );
  }

  const maxCount = Math.max(...presentCategories.map((k) => counts[k]));

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">
        OWASP Top 10 (2021) Dağılımı
      </p>
      {OWASP_ORDER.map((cat) => {
        const count = counts[cat] ?? 0;
        if (count === 0) return null;
        const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
        return (
          <div key={cat} className="flex items-center gap-3">
            <span className="w-40 text-xs text-slate-400 shrink-0 truncate">
              {OWASP_LABELS[cat]}
            </span>
            <div className="flex-1 h-5 bg-slate-800 rounded overflow-hidden">
              <div
                className="h-full bg-violet-600/70 rounded transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-5 text-right text-xs font-semibold text-slate-300 shrink-0">
              {count}
            </span>
          </div>
        );
      })}
    </div>
  );
}
