import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { startJob } from '../api/client.js';

const PLATFORMS = [
  { id: 'github_actions', label: 'GitHub Actions', icon: '🐙' },
  { id: 'gitlab_ci',      label: 'GitLab CI',      icon: '🦊' },
  { id: 'jenkins',        label: 'Jenkins',         icon: '☕' },
];

const EXAMPLE_REPOS = [
  { label: 'OWASP/NodeGoat',  url: 'https://github.com/OWASP/NodeGoat',  desc: 'Kasıtlı zafiyetli Node.js' },
  { label: 'pallets/flask',   url: 'https://github.com/pallets/flask',   desc: 'Temiz Python projesi' },
  { label: 'OWASP/WebGoat',   url: 'https://github.com/WebGoat/WebGoat', desc: 'Zafiyetli Java uygulaması' },
];

// PR Review için GitHub Actions workflow YAML içeriği
const PR_REVIEW_WORKFLOW = `name: DevSecOps Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  security-review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install bandit groq requests

      - name: Run DevSecOps PR Review
        env:
          GITHUB_TOKEN: \${{ secrets.GITHUB_TOKEN }}
          GROQ_API_KEY: \${{ secrets.GROQ_API_KEY }}
          PR_NUMBER: \${{ github.event.pull_request.number }}
          REPO: \${{ github.repository }}
          HEAD_SHA: \${{ github.event.pull_request.head.sha }}
          BASE_SHA: \${{ github.event.pull_request.base.sha }}
        run: python scripts/github_pr_review.py
`;

const STEPS = [
  {
    num: '1',
    title: 'GROQ_API_KEY secret ekleyin',
    desc: 'Ücretsiz Groq API key alın ve repo secret olarak ekleyin.',
    detail: (
      <ol className="mt-3 space-y-1.5 text-xs text-slate-400 list-decimal list-inside">
        <li>
          <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer"
             className="text-indigo-400 hover:text-indigo-300 transition-colors hover:underline">console.groq.com</a>
          {' '}→ API Keys → Create key
        </li>
        <li>GitHub repo → <span className="font-mono text-slate-300">Settings → Secrets → Actions</span></li>
        <li>
          <span className="font-mono bg-slate-800/80 px-1.5 py-0.5 rounded text-slate-300">New repository secret</span>
          {' '}→ Name: <span className="font-mono text-amber-300">GROQ_API_KEY</span>
        </li>
      </ol>
    ),
  },
  {
    num: '2',
    title: 'Workflow dosyasını ekleyin',
    desc: "Aşağıdaki YAML'i indirip .github/workflows/pr-review.yml olarak kaydedin.",
    detail: null,
  },
  {
    num: '3',
    title: 'PR açın — review otomatik gelir',
    desc: "Artık her PR'da DevSecOps Assistant otomatik güvenlik analizi yapıp yorum atar.",
    detail: (
      <div className="mt-3 p-3 rounded-lg text-xs text-slate-300 font-mono leading-relaxed"
           style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)' }}>
        🔍 DevSecOps Code Review<br/>
        🟠 HIGH — shell=True ile subprocess...<br/>
        {'  > '}💡 Düzeltme: shell=False kullanın...
      </div>
    ),
  },
];

// ── Analiz sekmesi ────────────────────────────────────────────────────────────

function AnalysisTab() {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl]     = useState('');
  const [token, setToken]         = useState('');
  const [showToken, setShowToken] = useState(false);
  const [tokenOpen, setTokenOpen] = useState(false);
  const [platform, setPlatform]   = useState('github_actions');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setError('');
    setLoading(true);
    const result = await startJob(repoUrl.trim(), token.trim(), platform);
    setLoading(false);
    if (!result.ok) { setError(result.error); return; }
    navigate(`/progress/${result.data.job_id}`);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* URL girişi */}
      <div>
        <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
          GitHub Repo URL
        </label>
        <input
          type="url"
          className="input text-base"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          required
          autoFocus
        />
        {/* Örnek repolar */}
        <div className="flex gap-2 mt-3 flex-wrap items-center">
          <span className="text-[11px] font-medium" style={{ color: '#475569' }}>Örnek:</span>
          {EXAMPLE_REPOS.map((r) => (
            <button
              key={r.url}
              type="button"
              onClick={() => setRepoUrl(r.url)}
              title={r.desc}
              className="text-[11px] px-2.5 py-1 rounded-full font-medium transition-all duration-200"
              style={{
                background: 'rgba(99,102,241,0.08)',
                border: '1px solid rgba(99,102,241,0.2)',
                color: '#6366f1',
              }}
              onMouseEnter={e => {
                e.target.style.background = 'rgba(99,102,241,0.18)';
                e.target.style.borderColor = 'rgba(99,102,241,0.4)';
                e.target.style.color = '#818cf8';
              }}
              onMouseLeave={e => {
                e.target.style.background = 'rgba(99,102,241,0.08)';
                e.target.style.borderColor = 'rgba(99,102,241,0.2)';
                e.target.style.color = '#6366f1';
              }}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Token (opsiyonel) */}
      <div>
        <button
          type="button"
          onClick={() => setTokenOpen((v) => !v)}
          className="flex items-center gap-2 text-sm font-medium transition-all duration-200"
          style={{ color: tokenOpen ? '#818cf8' : '#64748b' }}
          onMouseEnter={e => e.currentTarget.style.color = '#818cf8'}
          onMouseLeave={e => e.currentTarget.style.color = tokenOpen ? '#818cf8' : '#64748b'}
        >
          <span
            className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] transition-transform duration-200"
            style={{
              background: 'rgba(99,102,241,0.15)',
              transform: tokenOpen ? 'rotate(90deg)' : 'rotate(0deg)',
              color: '#818cf8',
            }}
          >
            ▶
          </span>
          GitHub Token (özel repo veya oran limiti için)
        </button>
        {tokenOpen && (
          <div className="mt-3 relative">
            <input
              type={showToken ? 'text' : 'password'}
              className="input pr-12"
              placeholder="ghp_xxxxxxxxxxxx"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="off"
            />
            <button
              type="button"
              onClick={() => setShowToken((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-lg transition-opacity hover:opacity-80"
            >
              {showToken ? '🙈' : '👁'}
            </button>
          </div>
        )}
      </div>

      {/* Platform seçimi */}
      <div>
        <label className="block text-sm font-semibold mb-3" style={{ color: '#94a3b8' }}>
          CI/CD Platformu
        </label>
        <div className="flex gap-3">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPlatform(p.id)}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium transition-all duration-200"
              style={
                platform === p.id
                  ? {
                      background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(124,58,237,0.15) 100%)',
                      border: '1px solid rgba(99,102,241,0.5)',
                      color: '#a5b4fc',
                      boxShadow: '0 0 16px rgba(99,102,241,0.15), inset 0 1px 0 rgba(255,255,255,0.05)',
                    }
                  : {
                      background: 'rgba(14,22,40,0.6)',
                      border: '1px solid rgba(30,45,74,0.8)',
                      color: '#64748b',
                    }
              }
              onMouseEnter={e => {
                if (platform !== p.id) {
                  e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)';
                  e.currentTarget.style.color = '#94a3b8';
                }
              }}
              onMouseLeave={e => {
                if (platform !== p.id) {
                  e.currentTarget.style.borderColor = 'rgba(30,45,74,0.8)';
                  e.currentTarget.style.color = '#64748b';
                }
              }}
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div
          className="flex items-start gap-3 p-4 rounded-xl text-sm"
          style={{
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.25)',
            color: '#fca5a5',
          }}
        >
          <span className="text-lg flex-shrink-0">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !repoUrl.trim()}
        className="btn-primary w-full text-base py-3.5 flex items-center justify-center gap-2.5 rounded-xl"
      >
        {loading ? (
          <>
            <span
              className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
              style={{ animation: 'spin 0.7s linear infinite' }}
            />
            <span>Analiz başlatılıyor...</span>
          </>
        ) : (
          <>
            <span style={{ filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.3))' }}>🤖</span>
            <span>Tam Analiz Başlat</span>
          </>
        )}
      </button>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </form>
  );
}

// ── PR Review Kur sekmesi ─────────────────────────────────────────────────────

function PrReviewTab() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(PR_REVIEW_WORKFLOW).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  };

  const handleDownload = () => {
    const blob = new Blob([PR_REVIEW_WORKFLOW], { type: 'text/yaml' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'pr-review.yml';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Açıklama */}
      <div
        className="p-4 rounded-xl text-sm leading-relaxed"
        style={{
          background: 'rgba(59,130,246,0.07)',
          border: '1px solid rgba(59,130,246,0.2)',
          color: '#93c5fd',
        }}
      >
        <span className="mr-2">ℹ️</span>
        PR açıldığında otomatik güvenlik analizi yapılır: SAST (Bandit), SCA (OSV.dev),
        LLM false positive filtresi, Türkçe düzeltme önerileri ve baseline karşılaştırma.
      </div>

      {/* Adımlar */}
      <div className="space-y-5">
        {STEPS.map((step) => (
          <div key={step.num} className="flex gap-4">
            {/* Numara */}
            <div
              className="flex-shrink-0 w-8 h-8 rounded-full text-white text-sm font-bold flex items-center justify-center mt-0.5"
              style={{
                background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                boxShadow: '0 0 12px rgba(99,102,241,0.35)',
              }}
            >
              {step.num}
            </div>
            {/* İçerik */}
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-200">{step.title}</p>
              <p className="text-xs mt-1" style={{ color: '#64748b' }}>{step.desc}</p>
              {step.detail}
            </div>
          </div>
        ))}
      </div>

      {/* Workflow YAML önizleme + butonlar */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>
            .github/workflows/pr-review.yml
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all duration-200"
              style={
                copied
                  ? { background: 'rgba(34,197,94,0.15)', color: '#86efac', border: '1px solid rgba(34,197,94,0.25)' }
                  : { background: 'rgba(30,45,74,0.8)', color: '#94a3b8', border: '1px solid rgba(99,102,241,0.15)' }
              }
            >
              {copied ? '✓ Kopyalandı' : '⎘ Kopyala'}
            </button>
            <button
              onClick={handleDownload}
              className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all duration-200"
              style={{
                background: 'linear-gradient(135deg, rgba(79,70,229,0.8) 0%, rgba(124,58,237,0.8) 100%)',
                color: 'white',
                border: '1px solid rgba(99,102,241,0.4)',
                boxShadow: '0 2px 8px rgba(79,70,229,0.3)',
              }}
              onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(79,70,229,0.5)'}
              onMouseLeave={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(79,70,229,0.3)'}
            >
              ⬇ İndir
            </button>
          </div>
        </div>
        <div
          className="overflow-hidden rounded-xl"
          style={{ border: '1px solid rgba(99,102,241,0.12)', background: 'rgba(4,6,16,0.8)' }}
        >
          <pre className="p-4 text-xs overflow-x-auto max-h-48 leading-relaxed" style={{ color: '#7dd3fc' }}>
            {PR_REVIEW_WORKFLOW}
          </pre>
        </div>
      </div>

      {/* Bilgi notu */}
      <div
        className="p-3.5 rounded-xl flex items-center gap-3 text-xs"
        style={{
          background: 'rgba(14,22,40,0.6)',
          border: '1px solid rgba(30,45,74,0.8)',
          color: '#64748b',
        }}
      >
        <span className="text-lg">💡</span>
        <span>
          Workflow çalıştığında PR'a otomatik yorum atılır.{' '}
          <strong style={{ color: '#94a3b8' }}>GITHUB_TOKEN</strong> GitHub tarafından otomatik sağlanır, ek ayar gerekmez.
        </span>
      </div>
    </div>
  );
}

// ── Ana sayfa ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'analyze',   label: '🔍 Repo Analizi' },
  { id: 'pr-review', label: '🔄 PR Review Kur' },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState('analyze');

  return (
    <div className="max-w-2xl mx-auto px-4 py-14">
      {/* Hero */}
      <div className="text-center mb-12">
        {/* Shield icon with glow */}
        <div className="inline-flex items-center justify-center mb-6" style={{ animation: 'float 5s ease-in-out infinite' }}>
          <div
            className="relative text-6xl"
            style={{ filter: 'drop-shadow(0 0 24px rgba(99,102,241,0.6)) drop-shadow(0 0 48px rgba(124,58,237,0.3))' }}
          >
            🛡️
          </div>
        </div>

        <h1 className="text-4xl font-bold mb-4 tracking-tight">
          <span
            style={{
              background: 'linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 40%, #c4b5fd 70%, #93c5fd 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            DevSecOps Assistant
          </span>
        </h1>

        <p className="text-base leading-relaxed max-w-md mx-auto" style={{ color: '#64748b' }}>
          GitHub reponuzu analiz edin, güvenlik açıklarını tespit edin,{' '}
          <span style={{ color: '#818cf8' }}>DSOMM olgunluk skoru</span> alın.
        </p>
      </div>

      {/* Kart */}
      <div
        className="rounded-2xl overflow-hidden"
        style={{
          background: 'rgba(10, 16, 34, 0.75)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(99,102,241,0.15)',
          boxShadow: '0 8px 40px rgba(0,0,0,0.5), 0 0 60px rgba(99,102,241,0.05), inset 0 1px 0 rgba(255,255,255,0.04)',
        }}
      >
        {/* Sekme başlıkları */}
        <div
          className="flex"
          style={{ borderBottom: '1px solid rgba(99,102,241,0.1)' }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="px-6 py-3.5 text-sm font-medium transition-all duration-200 relative flex-1 sm:flex-none"
              style={
                activeTab === tab.id
                  ? { color: '#a5b4fc' }
                  : { color: '#475569' }
              }
              onMouseEnter={e => { if (activeTab !== tab.id) e.currentTarget.style.color = '#64748b'; }}
              onMouseLeave={e => { if (activeTab !== tab.id) e.currentTarget.style.color = '#475569'; }}
            >
              {tab.label}
              {/* Active indicator */}
              <span
                className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full transition-all duration-300"
                style={{
                  background: activeTab === tab.id
                    ? 'linear-gradient(90deg, #4f46e5, #7c3aed)'
                    : 'transparent',
                  boxShadow: activeTab === tab.id ? '0 0 8px rgba(99,102,241,0.6)' : 'none',
                }}
              />
            </button>
          ))}
        </div>

        {/* Sekme içeriği */}
        <div className="p-6 sm:p-8">
          {activeTab === 'analyze'   && <AnalysisTab />}
          {activeTab === 'pr-review' && <PrReviewTab />}
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
}
