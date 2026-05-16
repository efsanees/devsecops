import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const { pathname } = useLocation();

  const navLink = (to, label) => (
    <Link
      to={to}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
        pathname === to
          ? 'bg-slate-700 text-white'
          : 'text-slate-400 hover:text-white hover:bg-slate-700'
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-bold text-white">
          <span className="text-xl">🛡️</span>
          <span>DevSecOps AI</span>
        </Link>
        <nav className="flex items-center gap-1">
          {navLink('/', 'Analiz')}
          {navLink('/history', 'Geçmiş')}
        </nav>
      </div>
    </header>
  );
}
