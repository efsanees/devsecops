import { useState } from 'react';

const CATEGORY_META = {
  build_deployment: {
    label: 'Build & Deployment',
    max: 30,
    icon: '🏗️',
    desc: 'CI/CD pipeline varlığı, Docker kullanımı, build ve deploy adımları',
    checks: {
      pipeline_exists: 'CI/CD pipeline dosyası var (.github/workflows, .gitlab-ci.yml vb.)',
      docker_present:  'Dockerfile veya docker-compose.yml mevcut',
      build_step:      "Pipeline'da build/install adımı tanımlı",
      deploy_step:     "Pipeline'da deploy adımı tanımlı",
    },
  },
  testing: {
    label: 'Test & Tarama',
    max: 25,
    icon: '🧪',
    desc: 'Test dosyaları ve pipeline\'daki güvenlik tarama adımları',
    checks: {
      has_test_files:           'Repoda test dosyası mevcut',
      sast_in_pipeline:         "Pipeline'da SAST (Bandit, Semgrep, CodeQL vb.) adımı var",
      sca_in_pipeline:          "Pipeline'da SCA (Trivy, Snyk, Dependabot vb.) adımı var",
      secret_scan_in_pipeline:  "Pipeline'da secret tarama (Gitleaks, TruffleHog vb.) adımı var",
    },
  },
  implementation: {
    label: 'Implementation',
    max: 25,
    icon: '💻',
    desc: 'Kodun güvenlik durumu: SAST ve SCA bulgularının ağırlığı',
    checks: null, // detaylar sayısal, aşağıda özel render
  },
  information_gathering: {
    label: 'Bilgi Toplama',
    max: 10,
    icon: '🔍',
    desc: 'Hardcoded credential / secret tespiti (Gitleaks tarafından)',
    checks: {
      no_hardcoded_secrets: 'Kod içinde hardcoded API key, şifre veya token bulunmaması',
    },
  },
  culture_org: {
    label: 'Kültür & Org',
    max: 10,
    icon: '📚',
    desc: 'Güvenlik kültürünü yansıtan dokümantasyon dosyaları',
    checks: {
      has_readme:        'README.md var (4 puan)',
      has_security_md:   'SECURITY.md var — açık güvenlik politikası (3 puan)',
      has_contributing:  'CONTRIBUTING.md var — katkı rehberi (3 puan)',
    },
  },
};

const LEVEL_COLOR = {
  'Başlangıç': 'text-red-400 bg-red-900/30 border-red-700',
  'Gelişen':   'text-amber-400 bg-amber-900/30 border-amber-700',
  'Olgun':     'text-green-400 bg-green-900/30 border-green-700',
};

const LEVEL_DESC = {
  'Başlangıç': 'Temel güvenlik önlemleri henüz uygulanmamış.',
  'Gelişen':   'Bazı güvenlik pratikleri var, ama önemli eksikler mevcut.',
  'Olgun':     'Güvenlik uygulamaları büyük ölçüde yerleşmiş durumda.',
};

function barColor(pct) {
  if (pct >= 70) return 'bg-green-500';
  if (pct >= 40) return 'bg-amber-500';
  return 'bg-red-500';
}

function CheckItem({ label, passed }) {
  return (
    <div className="flex items-start gap-2 text-xs py-0.5">
      <span className={`mt-0.5 shrink-0 font-bold ${passed ? 'text-green-400' : 'text-slate-600'}`}>
        {passed ? '✓' : '○'}
      </span>
      <span className={passed ? 'text-slate-300' : 'text-slate-500'}>{label}</span>
    </div>
  );
}

function CategoryRow({ catKey, meta, score, details }) {
  const [open, setOpen] = useState(false);
  const pct = Math.round((score / meta.max) * 100);
  const catDetails = details?.[catKey] ?? {};

  return (
    <div>
      {/* Başlık + bar */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left group"
      >
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-slate-300 flex items-center gap-1.5">
            <span>{meta.icon}</span>
            <span className="font-medium">{meta.label}</span>
            <span className="text-slate-600 group-hover:text-slate-400 transition-colors text-[10px]">
              {open ? '▲' : '▼'}
            </span>
          </span>
          <span className="text-xs font-mono">
            <span className={pct >= 70 ? 'text-green-400' : pct >= 40 ? 'text-amber-400' : 'text-red-400'}>
              {score}
            </span>
            <span className="text-slate-600">/{meta.max}</span>
          </span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor(pct)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {/* Kısa açıklama her zaman görünür */}
        <p className="text-[11px] text-slate-500 mt-1">{meta.desc}</p>
      </button>

      {/* Genişletilmiş kontroller */}
      {open && (
        <div className="mt-2 ml-1 pl-3 border-l border-slate-700 space-y-0.5">
          {catKey === 'implementation' ? (
            // Implementation için sayısal detaylar
            <div className="space-y-1 text-xs text-slate-400">
              <div>
                SAST yüksek bulgular:{' '}
                <span className={catDetails.sast_high_count > 0 ? 'text-red-400 font-semibold' : 'text-green-400'}>
                  {catDetails.sast_high_count ?? 0}
                </span>
                {' '}({catDetails.sast_points ?? 0}/15 puan)
              </div>
              <div>
                SCA kritik/yüksek CVE:{' '}
                <span className={catDetails.sca_critical_high_count > 0 ? 'text-red-400 font-semibold' : 'text-green-400'}>
                  {catDetails.sca_critical_high_count ?? 0}
                </span>
                {' '}({catDetails.sca_points ?? 0}/10 puan)
              </div>
              {catDetails.note && (
                <p className="text-amber-400 text-[11px]">ℹ {catDetails.note}</p>
              )}
            </div>
          ) : meta.checks ? (
            Object.entries(meta.checks).map(([checkKey, checkLabel]) => (
              <CheckItem key={checkKey} label={checkLabel} passed={!!catDetails[checkKey]} />
            ))
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function DsommDashboard({ dsomm }) {
  if (!dsomm) return null;
  const { total_score = 0, level = 'Başlangıç', categories = {}, details = {} } = dsomm;
  const levelCls  = LEVEL_COLOR[level]  ?? LEVEL_COLOR['Başlangıç'];
  const levelDesc = LEVEL_DESC[level]   ?? '';

  return (
    <div className="space-y-5">
      {/* Genel skor + seviye */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-bold text-white">{total_score}</span>
            <span className="text-slate-500 text-lg">/100</span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 max-w-[260px]">{levelDesc}</p>
        </div>
        <div className="text-right">
          <span className={`px-3 py-1.5 rounded-full border text-sm font-semibold ${levelCls}`}>
            {level}
          </span>
          <p className="text-[11px] text-slate-600 mt-1">Başlangıç · Gelişen · Olgun</p>
        </div>
      </div>

      <p className="text-[11px] text-slate-600 -mt-2">
        ▼ tıklayarak her kategorinin detaylı kriterlerini görün
      </p>

      {/* Kategori bar'ları */}
      <div className="space-y-4">
        {Object.entries(CATEGORY_META).map(([key, meta]) => (
          <CategoryRow
            key={key}
            catKey={key}
            meta={meta}
            score={categories[key] ?? 0}
            details={details}
          />
        ))}
      </div>
    </div>
  );
}
