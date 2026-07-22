import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, 
  UploadCloud, 
  Sparkles, 
  AlertCircle, 
  Loader2,
  Lock,
  Globe,
  FolderSync,
  CheckCircle2
} from 'lucide-react';
import { apiClient } from '../api/client';

export const IngestionPage: React.FC = () => {
  const [meetingName, setMeetingName] = useState('');
  const [accessLevel, setAccessLevel] = useState<'general' | 'leadership'>('general');
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const [driveSyncing, setDriveSyncing] = useState(false);
  const [driveSyncResult, setDriveSyncResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  const handleExtract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transcript.trim() || !meetingName.trim()) return;

    setLoading(true);
    setError(null);

    const formattedDate = new Date().toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    try {
      const res = await apiClient.post('/ingest/transcript', {
        transcript,
        meeting_name: meetingName,
        default_access_level: accessLevel,
      });

      const extractedData = res.data;

      const newSession = {
        meeting_id: extractedData.meeting_id || `m-${Date.now()}`,
        meeting_name: meetingName,
        ingestion_date: formattedDate,
        decisions: extractedData.decisions || [],
        tasks: extractedData.tasks || [],
        status: extractedData.status || 'extracted',
      };

      const existingSessions = JSON.parse(localStorage.getItem('cos_meeting_sessions') || '[]');
      localStorage.setItem('cos_meeting_sessions', JSON.stringify([newSession, ...existingSessions]));

      navigate('/review');
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Failed to process transcript with Extraction Agent.';
      setError(`Extraction Error: ${errMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDriveSync = async () => {
    setDriveSyncing(true);
    setDriveSyncResult(null);
    setError(null);
    try {
      const res = await apiClient.post('/ingest/drive-sync');
      const count = res.data?.ingested_count || 0;
      if (count > 0) {
        setDriveSyncResult(`Successfully synced and ingested ${count} new transcript file(s) from Google Drive! Redirecting to review...`);
        setTimeout(() => navigate('/review'), 1500);
      } else {
        setDriveSyncResult('Google Drive scan complete: No new un-ingested files found in folder.');
      }
    } catch (e: any) {
      setError('Google Drive sync failed. Please verify that your service-account.json and GOOGLE_DRIVE_FOLDER_ID are set in .env.');
    } finally {
      setDriveSyncing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Page Header */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-brand-600 dark:text-brand-400 mb-1">
            <UploadCloud className="w-5 h-5" />
            <span className="text-xs font-bold uppercase tracking-wider">Layer 1: Ingestion Layer</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">Ingest Meeting Transcript</h1>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
            Submit raw transcript notes or automatically sync from your shared Google Drive folder.
          </p>
        </div>

        {/* 1-Click Google Drive Sync Button */}
        <button
          onClick={handleDriveSync}
          disabled={driveSyncing}
          className="px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white font-bold text-xs shadow-md border border-slate-700 flex items-center space-x-2 transition-all cursor-pointer shrink-0 disabled:opacity-50"
        >
          {driveSyncing ? (
            <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
          ) : (
            <FolderSync className="w-4 h-4 text-cyan-400" />
          )}
          <span>{driveSyncing ? 'Scanning Google Drive...' : 'Sync Google Drive Folder'}</span>
        </button>
      </div>

      {driveSyncResult && (
        <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-start space-x-3 text-cyan-700 dark:text-cyan-300 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{driveSyncResult}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-700 dark:text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">Ingestion Trigger Exception</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Manual Transcript Input Form */}
      <form onSubmit={handleExtract} className="glass-panel rounded-2xl p-6 border border-slate-200 dark:border-slate-800 space-y-6">
        
        {/* Form Inputs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Meeting Title / Session Name
            </label>
            <input
              type="text"
              required
              value={meetingName}
              onChange={(e) => setMeetingName(e.target.value)}
              placeholder="e.g. Q3 Architecture & Product Alignment Sync"
              className="w-full px-4 py-3 rounded-xl glass-input text-sm"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Default Access Control (RBAC)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setAccessLevel('general')}
                className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-xl border text-xs font-bold transition-all ${
                  accessLevel === 'general'
                    ? 'border-brand-500 bg-brand-500/10 text-brand-600 dark:text-brand-400'
                    : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:border-slate-300'
                }`}
              >
                <Globe className="w-4 h-4" />
                <span>General Access</span>
              </button>

              <button
                type="button"
                onClick={() => setAccessLevel('leadership')}
                className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-xl border text-xs font-bold transition-all ${
                  accessLevel === 'leadership'
                    ? 'border-amber-500 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                    : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:border-slate-300'
                }`}
              >
                <Lock className="w-4 h-4" />
                <span>Leadership Only</span>
              </button>
            </div>
          </div>
        </div>

        {/* Transcript Textarea */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            Raw Transcript Text Content
          </label>
          <textarea
            rows={10}
            required
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste raw transcript dialogue here... e.g.:&#10;Rohan: We agreed to migrate our backend microservices to AWS ECS by next Friday.&#10;Sneha: I will finalize the GST audit paperwork by tomorrow."
            className="w-full px-4 py-3 rounded-xl glass-input text-sm font-mono leading-relaxed"
          />
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-end space-x-4 pt-2">
          <button
            type="submit"
            disabled={loading || !transcript.trim() || !meetingName.trim()}
            className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-bold text-sm shadow-lg shadow-brand-600/30 flex items-center space-x-2 disabled:opacity-50 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Extracting Real Entities...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Extract & Create Ingestion Session</span>
              </>
            )}
          </button>
        </div>

      </form>

    </div>
  );
};
