import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { IngestionPage } from './pages/IngestionPage';
import { ReviewPortal } from './pages/ReviewPortal';
import { RagChat } from './pages/RagChat';
import { AdminSettings } from './pages/AdminSettings';
import { Brain, Loader2 } from 'lucide-react';

/**
 * Login screen shown when no valid JWT token is present.
 * Offers Google OAuth and demo login options.
 */
const LoginScreen: React.FC = () => {
  const { loginDemo, loginGoogle, loading } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 glass-card rounded-3xl border border-slate-800 p-10 max-w-md w-full mx-4 space-y-8 text-center">
        {/* Logo */}
        <div className="flex flex-col items-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-brand-500/30">
            <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
              <Brain className="w-8 h-8 text-indigo-400 animate-pulse" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-white">AI Chief of Staff</h1>
            <p className="text-sm text-slate-400 mt-1">Executive Meeting Command Center</p>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-slate-800" />

        {/* Login Buttons */}
        <div className="space-y-4">
          <button
            onClick={loginGoogle}
            className="w-full flex items-center justify-center space-x-3 px-5 py-3.5 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-bold text-sm shadow-lg transition-all transform hover:-translate-y-0.5 cursor-pointer"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span>Sign in with Google</span>
          </button>

          <div className="flex items-center space-x-3">
            <div className="flex-1 border-t border-slate-800" />
            <span className="text-xs text-slate-500">or</span>
            <div className="flex-1 border-t border-slate-800" />
          </div>

          <button
            onClick={() => loginDemo()}
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-sm border border-slate-700 transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <span>Demo Login (Development)</span>
            )}
          </button>
        </div>

        <p className="text-[11px] text-slate-600">
          Powered by Google ADK, Lyzr SDK, Qdrant, and PostgreSQL
        </p>
      </div>
    </div>
  );
};

/**
 * Main authenticated app shell — only rendered when user has a valid JWT.
 */
const AuthenticatedApp: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-slate-950 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors duration-300">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/ingest" element={<IngestionPage />} />
            <Route path="/review" element={<ReviewPortal />} />
            <Route path="/chat" element={<RagChat />} />
            <Route path="/admin" element={<AdminSettings />} />
          </Routes>
        </main>
        
        <footer className="glass-panel border-t border-slate-200 dark:border-slate-800/80 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
          <div className="max-w-7xl mx-auto px-4">
            <p>AI Chief of Staff & Executive Meeting Command Center: Powered by Google ADK, Lyzr SDK, Qdrant, and PostgreSQL</p>
          </div>
        </footer>
      </div>
    </Router>
  );
};

/**
 * Root component: gates all content behind authentication.
 * Unauthenticated state renders ONLY the login screen.
 */
const AppContent: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          <p className="text-sm text-slate-400">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return <AuthenticatedApp />;
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
