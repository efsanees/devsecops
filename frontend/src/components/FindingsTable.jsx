import { useState } from 'react';
import SeverityBadge from './SeverityBadge.jsx';

const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const sortBySev = (arr) =>
  [...arr].sort((a, b) => (SEV_ORDER[a.severity] ?? 4) - (SEV_ORDER[b.severity] ?? 4));

// ── Satır bileşenleri ────────────────────────────────────────────────────────

function CweBadge({ cweId }) {
  if (!cweId) return null;
  return (
    <span className="inline-block text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono mr-1">
      {cweId}
    </span>
  );
}

function OwaspBadge({ category }) {
  if (!category) return null;
  return (
    <span className="inline-block text-xs px-1.5 py-0.5 rounded bg-violet-900/50 text-violet-300 border border-violet-700/40">
      {category}
    </span>
  );
}

function SastRow({ f }) {
  const [expanded, setExpanded] = useState(false);
  const hasFix = !!f.fix_suggestion;

  return (
    <>
      <tr className="border-b border-slate-700/50 hover:bg-slate-800/40">
        <td className="py-2.5 px-3 w-24"><SeverityBadge severity={f.severity} /></td>
        <td className="py-2.5 px-3 text-slate-200 text-sm max-w-[200px]">
          <p className="truncate">{f.message || f.rule_id}</p>
          <div className="flex flex-wrap gap-1 mt-1">
            <CweBadge cweId={f.cwe_id} />
            <OwaspBadge category={f.owasp_category} />
            {hasFix && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 border border-blue-700/40 hover:bg-blue-800/70 transition-colors"
              >
                🤖 {expanded ? 'Kapat' : 'AI Fix'}
              </button>
            )}
          </div>
        </td>
        <td className="py-2.5 px-3 text-slate-400 text-xs font-mono">
          {f.file ? `${f.file}${f.line ? `:${f.line}` : ''}` : '—'}
        </td>
        <td className="py-2.5 px-3 text-slate-500 text-xs">{f.source || '—'}</td>
      </tr>
      {expanded && (
        <tr className="border-b border-slate-700/50 bg-blue-950/20">
          <td colSpan={4} className="px-4 py-3">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-xs font-mono font-semibold shrink-0 mt-0.5">AI ›</span>
              <p className="text-slate-200 text-sm leading-relaxed">{f.fix_suggestion}</p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function ScaRow({ f }) {
  const [expanded, setExpanded] = useState(false);
  const hasFix = !!f.fix_suggestion;

  return (
    <>
      <tr className="border-b border-slate-700/50 hover:bg-slate-800/40">
        <td className="py-2.5 px-3 w-24"><SeverityBadge severity={f.severity} /></td>
        <td className="py-2.5 px-3 text-slate-200 text-sm">
          <p className="font-mono text-blue-300">{f.package}<span className="text-slate-500">@{f.version}</span></p>
          <p className="text-xs text-slate-400 mt-0.5 truncate max-w-[220px]">{f.summary}</p>
          <div className="flex flex-wrap gap-1 mt-1">
            <CweBadge cweId={f.cwe_id} />
            <OwaspBadge category={f.owasp_category} />
            {hasFix && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 border border-blue-700/40 hover:bg-blue-800/70 transition-colors"
              >
                🤖 {expanded ? 'Kapat' : 'AI Fix'}
              </button>
            )}
          </div>
        </td>
        <td className="py-2.5 px-3 text-slate-400 text-xs font-mono">{f.vuln_id || '—'}</td>
        <td className="py-2.5 px-3 text-xs">
          {f.fixed_in && f.fixed_in !== 'bilinmiyor'
            ? <span className="text-green-400">→ {f.fixed_in}</span>
            : <span className="text-slate-600">—</span>}
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-slate-700/50 bg-blue-950/20">
          <td colSpan={4} className="px-4 py-3">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-xs font-mono font-semibold shrink-0 mt-0.5">AI ›</span>
              <p className="text-slate-200 text-sm leading-relaxed">{f.fix_suggestion}</p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function SecretRow({ f }) {
  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-800/40">
      <td className="py-2.5 px-3 w-24"><SeverityBadge severity={f.severity} /></td>
      <td className="py-2.5 px-3 text-slate-200 text-sm">{f.secret_type || f.rule_id}</td>
      <td className="py-2.5 px-3 text-slate-400 text-xs font-mono">
        {f.file ? `${f.file}${f.line ? `:${f.line}` : ''}` : '—'}
      </td>
      <td className="py-2.5 px-3 text-amber-300 text-xs font-mono">{f.redacted_match || '***'}</td>
    </tr>
  );
}

function PipelineRow({ f }) {
  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-800/40">
      <td className="py-2.5 px-3 w-24"><SeverityBadge severity={f.severity} /></td>
      <td className="py-2.5 px-3 text-slate-200 text-sm" colSpan={2}>{f.title}</td>
      <td className="py-2.5 px-3 text-slate-400 text-xs">{f.recommendation}</td>
    </tr>
  );
}

// ── Tablo çerçevesi ──────────────────────────────────────────────────────────

function Table({ children, headers }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full text-left">
        <thead className="bg-slate-800 text-xs text-slate-400 uppercase tracking-wider">
          <tr>
            {headers.map((h) => (
              <th key={h} className="py-2 px-3 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function EmptyState({ label }) {
  return (
    <div className="py-10 text-center">
      <p className="text-3xl mb-2">✅</p>
      <p className="text-green-400 font-semibold">Temiz</p>
      <p className="text-slate-500 text-sm mt-1">{label} bulgusu yok.</p>
    </div>
  );
}

// ── Ana bileşen ──────────────────────────────────────────────────────────────

const TABS = [
  { key: 'sast',     label: 'SAST',     icon: '🔬', desc: 'Statik kod analizi — Bandit (Python) + Semgrep (çok dilli). Kod içindeki güvenlik açıkları.' },
  { key: 'sca',      label: 'SCA',      icon: '📦', desc: 'Bağımlılık güvenliği — OSV.dev + Trivy. Kullanılan kütüphanelerdeki CVE\'ler.' },
  { key: 'secret',   label: 'Gizli',    icon: '🔑', desc: 'Hardcoded credential — Gitleaks. API key, şifre, token kod içinde sabit yazılmış mı?' },
  { key: 'pipeline', label: 'Pipeline', icon: '⚙️', desc: 'CI/CD analizi — Mevcut pipeline\'da eksik güvenlik adımları (SAST, SCA, secret scan vb.)' },
];

export default function FindingsTable({ findings = {} }) {
  const [active, setActive] = useState('sast');

  const counts = {
    sast:     (findings.sast     || []).length,
    sca:      (findings.sca      || []).length,
    secret:   (findings.secret   || []).length,
    pipeline: (findings.pipeline || []).length,
  };

  const renderTab = () => {
    if (active === 'sast') {
      const rows = sortBySev(findings.sast || []);
      if (!rows.length) return <EmptyState label="SAST" />;
      return (
        <Table headers={['Severity', 'Mesaj', 'Dosya:Satır', 'Kaynak']}>
          {rows.map((f, i) => <SastRow key={i} f={f} />)}
        </Table>
      );
    }
    if (active === 'sca') {
      const rows = sortBySev(findings.sca || []);
      if (!rows.length) return <EmptyState label="SCA" />;
      return (
        <Table headers={['Severity', 'Paket', 'CVE ID', 'Düzeltme']}>
          {rows.map((f, i) => <ScaRow key={i} f={f} />)}
        </Table>
      );
    }
    if (active === 'secret') {
      const rows = sortBySev(findings.secret || []);
      if (!rows.length) return <EmptyState label="Gizli bilgi" />;
      return (
        <Table headers={['Severity', 'Tür', 'Dosya:Satır', 'Maskeli Değer']}>
          {rows.map((f, i) => <SecretRow key={i} f={f} />)}
        </Table>
      );
    }
    if (active === 'pipeline') {
      const rows = sortBySev(findings.pipeline || []);
      if (!rows.length) return <EmptyState label="Pipeline" />;
      return (
        <Table headers={['Severity', 'Sorun', '', 'Öneri']}>
          {rows.map((f, i) => <PipelineRow key={i} f={f} />)}
        </Table>
      );
    }
    return null;
  };

  return (
    <div>
      {/* Sekmeler */}
      <div className="flex gap-1 mb-1 border-b border-slate-700">
        {TABS.map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => setActive(key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2 ${
              active === key
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>{icon}</span>
            <span>{label}</span>
            {counts[key] > 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                active === key ? 'bg-blue-900 text-blue-300' : 'bg-slate-700 text-slate-400'
              }`}>
                {counts[key]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Aktif sekmenin açıklaması */}
      {TABS.find((t) => t.key === active)?.desc && (
        <p className="text-[11px] text-slate-600 mb-3 mt-2">
          {TABS.find((t) => t.key === active).desc}
        </p>
      )}

      {renderTab()}
    </div>
  );
}
