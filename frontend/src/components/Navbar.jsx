import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const { pathname } = useLocation();

  const navLink = (to, label) => (
    <Link
      to={to}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
        pathname === to
          ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
          : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header
      style={{
        background: 'rgba(6, 9, 26, 0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(99, 102, 241, 0.12)',
      }}
      className="sticky top-0 z-50"
    >
      <div className="max-w-5xl mx-auto px-5 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <span
            className="text-xl transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3"
            style={{ filter: 'drop-shadow(0 0 8px rgba(99,102,241,0.5))' }}
          >
            🛡️
          </span>
          <span
            className="font-bold text-sm tracking-wide"
            style={{
              background: 'linear-gradient(135deg, #a5b4fc 0%, #818cf8 50%, #c4b5fd 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            DevSecOps Assistant
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {navLink('/', 'Analiz')}
          {navLink('/history', 'Geçmiş')}
        </nav>
      </div>
    </header>
  );
}
