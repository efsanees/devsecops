const OWASP_META = {
  'A01:2021': { label: 'A01 Broken Access Control',    desc: 'Yetkisiz kaynak erişimi',              color: 'bg-red-600/70'    },
  'A02:2021': { label: 'A02 Cryptographic Failures',   desc: 'Zayıf şifreleme (MD5, SHA1...)',        color: 'bg-orange-600/70' },
  'A03:2021': { label: 'A03 Injection',                desc: 'SQL/komut enjeksiyonu, XSS',            color: 'bg-amber-600/70'  },
  'A04:2021': { label: 'A04 Insecure Design',          desc: 'Tasarım düzeyinde güvenlik açıkları',   color: 'bg-yellow-600/70' },
  'A05:2021': { label: 'A05 Security Misconfiguration',desc: 'Hatalı yapılandırma, debug modu',       color: 'bg-lime-600/70'   },
  'A06:2021': { label: 'A06 Vulnerable Components',    desc: 'CVE\'li eski bağımlılıklar',            color: 'bg-violet-600/70' },
  'A07:2021': { label: 'A07 Auth Failures',            desc: 'Hardcoded şifre, zayıf kimlik doğrulama', color: 'bg-blue-600/70' },
  'A08:2021': { label: 'A08 Software & Data Integrity',desc: 'Güvensiz deserializasyon (pickle...)',  color: 'bg-indigo-600/70' },
  'A09:2021': { label: 'A09 Logging & Monitoring',     desc: 'Eksik loglama, olaylar tespit edilemiyor', color: 'bg-cyan-600/70'},
  'A10:2021': { label: 'A10 SSRF',                     desc: 'Sunucu tarafı istek sahteciliği',       color: 'bg-teal-600/70'   },
};

const OWASP_ORDER = Object.keys(OWASP_META);

function countByOwasp(findings) {
  const counts = {};
  const bySource = {};   // {cat: {sast: N, sca: N, secret: N}}
  const bySev    = {};   // {cat: {HIGH: N, MEDIUM: N, LOW: N}}

  for (const f of findings) {
    const cat = f.owasp_category;
    if (!cat) continue;
    counts[cat]   = (counts[cat]   ?? 0) + 1;

    if (!bySource[cat]) bySource[cat] = {};
    const src = f.source === 'osv' || f.source === 'trivy' || f.source === 'both' ? 'sca'
              : f.type === 'SECRET' ? 'secret'
              : 'sast';
    bySource[cat][src] = (bySource[cat][src] ?? 0) + 1;

    if (!bySev[cat]) bySev[cat] = {};
    const sev = f.severity ?? 'LOW';
    bySev[cat][sev] = (bySev[cat][sev] ?? 0) + 1;
  }
  return { counts, bySource, bySev };
}

function SevDots({ bySev }) {
  if (!bySev) return null;
  return (
    <span className="flex gap-1 items-center">
      {(bySev['CRITICAL'] ?? 0) > 0 && (
        <span className="text-[10px] font-bold text-red-400">{bySev['CRITICAL']}C</span>
      )}
      {(bySev['HIGH'] ?? 0) > 0 && (
        <span className="text-[10px] font-bold text-orange-400">{bySev['HIGH']}H</span>
      )}
      {(bySev['MEDIUM'] ?? 0) > 0 && (
        <span className="text-[10px] font-semibold text-amber-400">{bySev['MEDIUM']}M</span>
      )}
      {(bySev['LOW'] ?? 0) > 0 && (
        <span className="text-[10px] text-blue-400">{bySev['LOW']}L</span>
      )}
    </span>
  );
}

function SourceTags({ bySource }) {
  if (!bySource) return null;
  const tags = [];
  if (bySource.sast)   tags.push({ label: 'SAST',   cls: 'text-emerald-400' });
  if (bySource.sca)    tags.push({ label: 'SCA',    cls: 'text-violet-400' });
  if (bySource.secret) tags.push({ label: 'Secret', cls: 'text-amber-400' });
  return (
    <span className="flex gap-1">
      {tags.map(({ label, cls }) => (
        <span key={label} className={`text-[10px] font-medium ${cls}`}>{label}</span>
      ))}
    </span>
  );
}

export default function OwaspChart({ findings = {} }) {
  const all = [
    ...(findings.sast     || []),
    ...(findings.sca      || []),
    ...(findings.secret   || []),
    ...(findings.pipeline || []),
  ];

  const { counts, bySource, bySev } = countByOwasp(all);
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
    <div className="space-y-1">
      {/* Başlık açıklaması */}
      <div className="mb-4">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
          OWASP Top 10 (2021) Dağılımı
        </p>
        <p className="text-xs text-slate-600 mt-1">
          Tespit edilen bulgular OWASP Top 10 güvenlik kategorilerine haritalandı.
          Bar uzunluğu o kategorideki bulgu sayısını gösterir.
          <span className="text-emerald-400"> SAST</span> = kod analizi ·
          <span className="text-violet-400"> SCA</span> = bağımlılık ·
          Harf rengi: <span className="text-red-400">C</span>ritical
          <span className="text-orange-400"> H</span>igh
          <span className="text-amber-400"> M</span>edium
          <span className="text-blue-400"> L</span>ow
        </p>
      </div>

      {/* Kategoriler */}
      {OWASP_ORDER.map((cat) => {
        const count = counts[cat] ?? 0;
        if (count === 0) return null;

        const meta = OWASP_META[cat];
        const pct  = maxCount > 0 ? (count / maxCount) * 100 : 0;

        return (
          <div key={cat} className="group">
            {/* Bar satırı */}
            <div className="flex items-center gap-2">
              {/* Kategori adı */}
              <span className="w-44 text-xs text-slate-300 shrink-0 font-medium truncate">
                {meta.label}
              </span>
              {/* Bar */}
              <div className="flex-1 h-5 bg-slate-800 rounded overflow-hidden relative">
                <div
                  className={`h-full rounded transition-all duration-500 ${meta.color}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {/* Sayı */}
              <span className="w-5 text-right text-xs font-bold text-slate-200 shrink-0">
                {count}
              </span>
            </div>
            {/* Açıklama + severity + kaynak */}
            <div className="flex items-center justify-between ml-[11.5rem] mt-0.5 mb-2">
              <span className="text-[11px] text-slate-600 truncate max-w-[280px]">
                {meta.desc}
              </span>
              <div className="flex items-center gap-2 shrink-0 ml-2">
                <SevDots bySev={bySev[cat]} />
                <SourceTags bySource={bySource[cat]} />
              </div>
            </div>
          </div>
        );
      })}

      {/* Kapsam notu */}
      <p className="text-[11px] text-slate-600 pt-2 border-t border-slate-800 mt-2">
        * Tüm bulgular OWASP kategorisine haritalanmayabilir. Özellikle SCA bulguları
        A06:2021 (Vulnerable Components) kapsamına girer.
      </p>
    </div>
  );
}
