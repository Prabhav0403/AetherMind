import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import ResearchPage from './pages/ResearchPage';
import DocumentsPage from './pages/DocumentsPage';
import SessionsPage from './pages/SessionsPage';
import MonitorPage from './pages/MonitorPage';
import EvaluatePage from './pages/EvaluatePage';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontSize: '13px',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#06192b' } },
          error:   { iconTheme: { primary: '#f43f5e', secondary: '#06192b' } },
        }}
      />
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
          <Routes>
            <Route path="/"               element={<ResearchPage />} />
            <Route path="/documents"      element={<DocumentsPage />} />
            <Route path="/sessions"       element={<SessionsPage />} />
            <Route path="/monitor"        element={<SessionsPage />} />
            <Route path="/monitor/:id"    element={<MonitorPage />} />
            <Route path="/evaluate"       element={<EvaluatePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
