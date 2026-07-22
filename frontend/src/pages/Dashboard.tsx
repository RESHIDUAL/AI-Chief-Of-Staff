import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  Clock, 
  Brain, 
  FileText, 
  Zap, 
  Layers, 
  ShieldCheck, 
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';

/**
 * Compute live stats from localStorage meeting sessions and committed memory.
 * This is the single source of truth when PostgreSQL is not available.
 */
function computeLocalStats() {
  const sessions = JSON.parse(localStorage.getItem('cos_meeting_sessions') || '[]');
  const committed = JSON.parse(localStorage.getItem('cos_committed_memory') || '[]');

  let pendingDecisions = 0;
  let pendingTasks = 0;
  for (const s of sessions) {
    pendingDecisions += (s.decisions?.length || 0);
    pendingTasks += (s.tasks?.length || 0);
  }

  const committedDecisions = committed.filter((c: any) => c.type === 'decision').length;
  const committedTasks = committed.filter((c: any) => c.type === 'task').length;

  return {
    total_decisions: committedDecisions,
    total_tasks: committedTasks,
    pending_decisions: pendingDecisions,
    pending_tasks: pendingTasks,
    open_tasks: committedTasks,
    total_meetings: sessions.length,
  };
}

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState(() => computeLocalStats());
  const [loading, setLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/review/stats');
      const serverStats = res.data;

      // Merge with local reality: local counts take priority for pending
      const local = computeLocalStats();
      setStats({
        total_decisions: Math.max(serverStats.total_decisions || 0, local.total_decisions),
        total_tasks: Math.max(serverStats.total_tasks || 0, local.total_tasks),
        pending_decisions: local.pending_decisions,
        pending_tasks: local.pending_tasks,
        open_tasks: Math.max(serverStats.open_tasks || 0, local.open_tasks),
        total_meetings: Math.max(serverStats.total_meetings || 0, local.total_meetings),
      });
    } catch (e) {
      // Backend unavailable: use pure local stats
      setStats(computeLocalStats());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();

    // Listen for localStorage changes (cross-tab sync)
    const handleStorage = () => setStats(computeLocalStats());
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [fetchStats]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Header Banner */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 relative overflow-hidden border border-slate-200 dark:border-slate-800">
        <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-gradient-to-br from-brand-600/20 via-cyan-500/10 to-transparent rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center space-x-2 text-indigo-600 dark:text-indigo-400 mb-2">
              <Zap className="w-5 h-5" />
              <span className="text-xs font-bold uppercase tracking-wider">Organizational Memory Intelligence</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white">
              Executive Command Center
            </h1>
            <p className="mt-2 text-slate-600 dark:text-slate-300 max-w-2xl text-sm sm:text-base">
              Capturing, categorizing, and serving organizational decision intelligence. Powered by Google ADK, Lyzr SDK agents, and self-correcting Qdrant vector memory.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={fetchStats}
              className="p-2.5 glass-card rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all cursor-pointer"
              title="Refresh Stats"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <Link
              to="/ingest"
              className="flex items-center space-x-2 px-5 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-bold text-sm shadow-lg shadow-brand-600/25 transition-all transform hover:-translate-y-0.5"
            >
              <FileText className="w-5 h-5" />
              <span>Ingest Transcript</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* Card 1: Decisions Committed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Decisions Committed</span>
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              <Brain className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">{stats.total_decisions}</span>
            <span className="ml-2 text-xs font-bold text-emerald-600 dark:text-emerald-400">In Memory</span>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Approved decisions in Qdrant vector store</p>
        </motion.div>

        {/* Card 2: Tasks Committed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Action Items</span>
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">{stats.total_tasks}</span>
            <span className="ml-2 text-xs font-bold text-cyan-600 dark:text-cyan-400">Committed</span>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Approved action items with assigned owners</p>
        </motion.div>

        {/* Card 3: Pending Reviews */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Pending HITL Review</span>
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline">
            <span className={`text-3xl font-extrabold ${(stats.pending_decisions + stats.pending_tasks) > 0 ? 'text-amber-500 dark:text-amber-400' : 'text-emerald-500 dark:text-emerald-400'}`}>
              {stats.pending_decisions + stats.pending_tasks}
            </span>
            <span className="ml-2 text-xs font-bold text-slate-500 dark:text-slate-400">
              {(stats.pending_decisions + stats.pending_tasks) === 0 ? 'All Clear' : 'Awaiting Review'}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Human verification queue</p>
        </motion.div>

        {/* Card 4: Total Meetings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Ingested Meetings</span>
            <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">{stats.total_meetings}</span>
            <span className="ml-2 text-xs font-bold text-emerald-600 dark:text-emerald-400">Sessions</span>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Meeting transcripts processed</p>
        </motion.div>

      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <Link
          to="/ingest"
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 hover:border-brand-500/50 transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-brand-600/15 text-brand-600 dark:text-brand-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-300 transition-colors flex items-center justify-between">
            <span>Automated Ingestion</span>
            <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h3>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Enter meeting transcript text to generate dual stream extractions tagged with Meeting Name and Ingestion Date.
          </p>
        </Link>

        <Link
          to="/review"
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 hover:border-cyan-500/50 transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-cyan-600/15 text-cyan-600 dark:text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-300 transition-colors flex items-center justify-between">
            <span>HITL Review Portal</span>
            <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h3>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Approve meeting extractions grouped by session. Edit committed vectors to trigger self-correcting re-embedding.
          </p>
        </Link>

        <Link
          to="/chat"
          className="glass-card rounded-2xl p-6 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Brain className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-300 transition-colors flex items-center justify-between">
            <span>RAG Memory Chat</span>
            <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h3>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Ask natural language questions against past meetings with active role-based authorization filtering.
          </p>
        </Link>

      </div>

    </div>
  );
};
