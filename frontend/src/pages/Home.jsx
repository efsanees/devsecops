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
      <ol className="mt-2 space-y-1 text-xs text-slate-400 list-decimal list-inside">
        <li>
          <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer"
             className="text-blue-400 hover:underline">console.groq.com</a>
          {' '}→ API Keys → Create key
        </li>
        <li>GitHub repo → <span className="font-mono">Settings → Secrets → Actions</span></li>
        <li>
          <span className="font-mono bg-slate-700 px-1 rounded">New repository secret</span>
          {' '}→ Name: <span className="font-mono text-amber-300">GROQ_API_KEY</span>
        </li>
      </ol>
    ),
  },
  {
    num: '2',
    title: 'Workflow dosyasını ekleyin',
    desc: 'Aşağıdaki YAML\'i indirip .github/workflows/pr-review.yml olarak kaydedin.',
    detail: null,
  },
  {
    num: '3',
    title: 'PR açın — review otomatik gelir',
    desc: 'Artık her PR\'da DevSecOps AI otomatik güvenlik analizi yapıp yorum atar.',
    detail: (
      <div className="mt-2 p-2 bg-slate-700/50 rounded text-xs text-slate-300 font-mono">
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
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* URL girişi */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
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
        <div className="flex gap-2 mt-2 flex-wrap">
          <span className="text-[11px] text-slate-600 self-center">Örnek:</span>
          {EXAMPLE_REPOS.map((r) => (
            <button
              key={r.url}
              type="button"
              onClick={() => setRepoUrl(r.url)}
              title={r.desc}
              className="text-[11px] px-2 py-0.5 rounded border border-slate-700 text-slate-500 hover:text-slate-300 hover:border-slate-500 transition-colors"
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
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <span className={`transition-transform ${tokenOpen ? 'rotate-90' : ''}`}>▶</span>
          GitHub Token (özel repo veya oran limiti için)
        </button>
        {tokenOpen && (
          <div className="mt-2 relative">
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
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              {showToken ? '🙈' : '👁'}
            </button>
          </div>
        )}
      </div>

      {/* Platform seçimi */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-3">CI/CD Platformu</label>
        <div className="flex gap-3">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPlatform(p.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl border text-sm font-medium transition-all ${
                platform === p.id
                  ? 'bg-violet-900/40 border-violet-500 text-white'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'
              }`}
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-900/30 border border-red-700 rounded-xl text-red-300 text-sm">
          <span className="text-lg">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !repoUrl.trim()}
        className="btn-primary w-full text-base py-3 flex items-center justify-center gap-2"
      >
        {loading ? (
          <><span className="animate-spin">⟳</span><span>Analiz başlatılıyor...</span></>
        ) : (
          <><span>🤖</span><span>Tam Analiz Başlat</span></>
        )}
      </button>
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
      <div className="p-4 bg-blue-900/20 border border-blue-700/40 rounded-xl text-sm text-blue-200">
        PR açıldığında otomatik güvenlik analizi yapılır: SAST (Bandit), SCA (OSV.dev),
        LLM false positive filtresi, Türkçe düzeltme önerileri ve baseline karşılaştırma.
      </div>

      {/* Adımlar */}
      <div className="space-y-4">
        {STEPS.map((step) => (
          <div key={step.num} className="flex gap-4">
            {/* Numara */}
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-violet-700 text-white text-sm font-bold flex items-center justify-center mt-0.5">
              {step.num}
            </div>
            {/* İçerik */}
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">{step.title}</p>
              <p className="text-xs text-slate-400 mt-0.5">{step.desc}</p>
              {step.detail}
            </div>
          </div>
        ))}
      </div>

      {/* Workflow YAML önizleme + butonlar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            .github/workflows/pr-review.yml
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className={`text-xs px-3 py-1 rounded-lg font-medium transition-colors ${
                copied
                  ? 'bg-green-700 text-green-100'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {copied ? '✓ Kopyalandı' : '⎘ Kopyala'}
            </button>
            <button
              onClick={handleDownload}
              className="text-xs px-3 py-1 rounded-lg bg-violet-700 hover:bg-violet-600 text-white font-medium transition-colors"
            >
              ⬇ İndir
            </button>
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
          <pre className="p-4 text-xs text-slate-300 overflow-x-auto max-h-48 leading-relaxed">
            {PR_REVIEW_WORKFLOW}
          </pre>
        </div>
      </div>

      {/* GitHub Actions badge örneği */}
      <div className="p-3 bg-slate-800/60 border border-slate-700 rounded-xl flex items-center gap-3 text-xs text-slate-400">
        <span className="text-lg">💡</span>
        <span>
          Workflow çalıştığında PR'a otomatik yorum atılır.
          {' '}<strong className="text-slate-200">GITHUB_TOKEN</strong> GitHub tarafından otomatik sağlanır, ek ayar gerekmez.
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
    <div className="max-w-2xl mx-auto px-4 py-12">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="text-6xl mb-4">🛡️</div>
        <h1 className="text-3xl font-bold text-white mb-3">DevSecOps AI</h1>
        <p className="text-slate-400 text-lg">
          GitHub reponuzu analiz edin, güvenlik açıklarını tespit edin, DSOMM olgunluk skoru alın.
        </p>
      </div>

      {/* Sekme başlıkları */}
      <div className="flex border-b border-slate-700 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px border-b-2 ${
              activeTab === tab.id
                ? 'border-violet-500 text-violet-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sekme içeriği */}
      {activeTab === 'analyze'   && <AnalysisTab />}
      {activeTab === 'pr-review' && <PrReviewTab />}
    </div>
  );
}
