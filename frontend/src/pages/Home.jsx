import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeRepo, generatePipeline, fullAnalysis, securityAnalysis } from '../api/client.js';

const MODES = [
  {
    id: 'analyze',
    icon: '🔍',
    label: 'Hızlı Analiz',
    desc: 'Dil, framework, test ve Docker tespiti',
    hasPlatform: false,
  },
  {
    id: 'auto',
    icon: '⚙️',
    label: 'Pipeline Üret',
    desc: 'Repo analizi + CI/CD YAML otomatik üretimi',
    hasPlatform: true,
  },
  {
    id: 'full',
    icon: '📊',
    label: 'Tam Analiz',
    desc: 'Pipeline + uyum skoru (A/B/C/D)',
    hasPlatform: true,
  },
  {
    id: 'security',
    icon: '🛡️',
    label: 'Güvenlik Taraması',
    desc: 'SAST + SCA + CVE tarama + OWASP raporu',
    hasPlatform: false,
  },
];

const PLATFORMS = [
  { id: 'github_actions', label: 'GitHub Actions', icon: '🐙' },
  { id: 'gitlab_ci',      label: 'GitLab CI',      icon: '🦊' },
  { id: 'jenkins',        label: 'Jenkins',         icon: '☕' },
];

export default function Home() {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl]     = useState('');
  const [token, setToken]         = useState('');
  const [showToken, setShowToken] = useState(false);
  const [tokenOpen, setTokenOpen] = useState(false);
  const [mode, setMode]           = useState('full');
  const [platform, setPlatform]   = useState('github_actions');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  const selectedMode = MODES.find((m) => m.id === mode);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setError('');
    setLoading(true);

    let result;
    const url = repoUrl.trim();
    const tok  = token.trim();

    if (mode === 'analyze')  result = await analyzeRepo(url, tok);
    else if (mode === 'auto')     result = await generatePipeline(url, tok, platform);
    else if (mode === 'full')     result = await fullAnalysis(url, tok, platform);
    else                          result = await securityAnalysis(url, tok);

    setLoading(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    navigate('/result', {
      state: { type: mode, data: result.data, repoUrl: url, platform },
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="text-6xl mb-4">🛡️</div>
        <h1 className="text-3xl font-bold text-white mb-3">DevSecOps AI</h1>
        <p className="text-slate-400 text-lg">
          GitHub reponuzu analiz edin, CI/CD pipeline üretin, güvenlik zaafiyetlerini tespit edin.
        </p>
      </div>

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

        {/* Mod seçimi */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">Analiz Modu</label>
          <div className="grid grid-cols-2 gap-3">
            {MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setMode(m.id)}
                className={`text-left p-4 rounded-xl border transition-all ${
                  mode === m.id
                    ? 'bg-blue-900/40 border-blue-500 text-white'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                }`}
              >
                <div className="text-xl mb-1">{m.icon}</div>
                <div className="font-semibold text-sm">{m.label}</div>
                <div className="text-xs mt-0.5 opacity-70">{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Platform seçimi — yalnızca pipeline modlarında */}
        {selectedMode?.hasPlatform && (
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
        )}

        {/* Hata */}
        {error && (
          <div className="flex items-start gap-3 p-4 bg-red-900/30 border border-red-700 rounded-xl text-red-300 text-sm">
            <span className="text-lg">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Gönder */}
        <button
          type="submit"
          disabled={loading || !repoUrl.trim()}
          className="btn-primary w-full text-base py-3 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="animate-spin">⟳</span>
              <span>
                {mode === 'security' ? 'Güvenlik taranıyor...' :
                 mode === 'full'     ? 'Analiz ediliyor...' :
                 mode === 'auto'     ? 'Pipeline üretiliyor...' :
                                      'Analiz ediliyor...'}
              </span>
            </>
          ) : (
            <>
              <span>{selectedMode?.icon}</span>
              <span>{selectedMode?.label} Başlat</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
