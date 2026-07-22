import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Brain, 
  FileText, 
  CheckSquare, 
  MessageSquare, 
  Settings, 
  Sparkles, 
  Sun,
  Moon,
  Shield,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-200 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-brand-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Brain className="w-5 h-5 text-indigo-400 animate-pulse-slow" />
              </div>
            </div>
            <div>
              <span className="font-extrabold text-lg bg-gradient-to-r from-brand-600 via-indigo-500 to-cyan-500 dark:from-white dark:via-slate-200 dark:to-indigo-300 bg-clip-text text-transparent">
                AI Chief of Staff
              </span>
              <span className="ml-2 text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-600 dark:text-brand-400 border border-brand-500/30">
                Executive Portal
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-600 dark:text-brand-400 border border-brand-500/30 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/50'
                }`
              }
            >
              <Sparkles className="w-4 h-4" />
              <span>Dashboard</span>
            </NavLink>

            <NavLink
              to="/ingest"
              className={({ isActive }) =>
                `flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-600 dark:text-brand-400 border border-brand-500/30 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/50'
                }`
              }
            >
              <FileText className="w-4 h-4" />
              <span>Ingest Transcript</span>
            </NavLink>

            <NavLink
              to="/review"
              className={({ isActive }) =>
                `flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-600 dark:text-brand-400 border border-brand-500/30 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/50'
                }`
              }
            >
              <CheckSquare className="w-4 h-4" />
              <span>HITL Review</span>
            </NavLink>

            <NavLink
              to="/chat"
              className={({ isActive }) =>
                `flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-600 dark:text-brand-400 border border-brand-500/30 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/50'
                }`
              }
            >
              <MessageSquare className="w-4 h-4" />
              <span>Memory Chat</span>
            </NavLink>

            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-600 dark:text-brand-400 border border-brand-500/30 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/50'
                }`
              }
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </NavLink>
          </nav>

          {/* Right Controls: Theme Toggle, RBAC Badge, User Info & Sign Out */}
          <div className="flex items-center space-x-3">
            
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl glass-card text-slate-700 dark:text-slate-300 hover:text-brand-600 dark:hover:text-brand-400 transition-all cursor-pointer"
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-600" />}
            </button>

            {/* RBAC Role Badge (read-only, from JWT) */}
            <div className="flex items-center space-x-2 bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl px-2.5 py-1.5">
              <Shield className="w-4 h-4 text-cyan-500" />
              <span className="text-xs font-bold text-cyan-600 dark:text-cyan-300 capitalize">
                {user?.role || 'employee'}
              </span>
            </div>

            {/* User Info & Sign Out */}
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-200 dark:border-slate-800">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt="Avatar"
                  className="w-8 h-8 rounded-full border border-indigo-500/40"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-600 to-indigo-600 flex items-center justify-center text-white text-xs font-bold">
                  {(user?.name || user?.email || '?').charAt(0).toUpperCase()}
                </div>
              )}
              <div className="hidden lg:block text-left">
                <p className="text-xs font-bold text-slate-900 dark:text-slate-200">{user?.email || 'Unknown'}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">{user?.name || 'User'}</p>
              </div>

              {/* Sign Out Button */}
              <button
                onClick={logout}
                className="p-2 rounded-xl text-slate-500 hover:text-rose-500 dark:text-slate-400 dark:hover:text-rose-400 transition-colors cursor-pointer"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>

          </div>

        </div>
      </div>
    </header>
  );
};
