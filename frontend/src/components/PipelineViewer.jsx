import { useEffect, useRef, useState } from 'react';
import hljs from 'highlight.js/lib/core';
import yamlLang from 'highlight.js/lib/languages/yaml';
import 'highlight.js/styles/github-dark.css';

hljs.registerLanguage('yaml', yamlLang);

export default function PipelineViewer({ yaml }) {
  const codeRef = useRef(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.removeAttribute('data-highlighted');
      hljs.highlightElement(codeRef.current);
    }
  }, [yaml]);

  const handleCopy = () => {
    navigator.clipboard.writeText(yaml).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownload = () => {
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ci-pipeline.yml';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl overflow-hidden border border-slate-700">
      {/* Baslik + butonlar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">.github/workflows/ci-pipeline.yml</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded hover:bg-slate-700 transition-colors"
          >
            ⬇ İndir
          </button>
          <button
            onClick={handleCopy}
            className={`text-xs px-2.5 py-1 rounded transition-colors font-medium ${
              copied
                ? 'bg-green-700 text-green-200'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {copied ? '✓ Kopyalandı' : '⎘ Kopyala'}
          </button>
        </div>
      </div>
      {/* Kod blogu */}
      <div className="overflow-auto max-h-[500px] text-sm bg-[#0d1117]">
        <pre className="p-4 m-0">
          <code ref={codeRef} className="language-yaml">
            {yaml}
          </code>
        </pre>
      </div>
    </div>
  );
}
