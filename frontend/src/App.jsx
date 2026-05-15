import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import Home from './pages/Home.jsx';
import ResultPage from './pages/ResultPage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import ProgressPage from './pages/ProgressPage.jsx';
import TrendsPage from './pages/TrendsPage.jsx';
import ComparePage from './pages/ComparePage.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/progress/:jobId" element={<ProgressPage />} />
            <Route path="/result" element={<ResultPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/trends" element={<TrendsPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
