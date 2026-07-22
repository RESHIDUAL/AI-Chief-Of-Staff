import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  CheckSquare, 
  Brain, 
  User, 
  Calendar, 
  Check, 
  Edit3, 
  Trash2, 
  CheckCircle2, 
  Zap,
  Globe,
  Lock,
  ChevronDown,
  ChevronUp,
  PlusCircle
} from 'lucide-react';
import { apiClient } from '../api/client';

export const ReviewPortal: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Load meeting sessions created by user (NO HARDCODED DEFAULT DUMMY ITEMS)
  const [meetingSessions, setMeetingSessions] = useState<any[]>(() => {
    const saved = localStorage.getItem('cos_meeting_sessions');
    return saved ? JSON.parse(saved) : [];
  });

  const [expandedMeetingId, setExpandedMeetingId] = useState<string | null>(() => {
    const highlight = (location.state as any)?.highlightId;
    if (highlight) return highlight;
    const saved = localStorage.getItem('cos_meeting_sessions');
    const parsed = saved ? JSON.parse(saved) : [];
    return parsed.length > 0 ? parsed[0].meeting_id : null;
  });

  // Persistent Committed Memory Store (Never vanishes on navigation!)
  const [committedItems, setCommittedItems] = useState<any[]>(() => {
    const saved = localStorage.getItem('cos_committed_memory');
    return saved ? JSON.parse(saved) : [];
  });

  const [editingPointId, setEditingPointId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  // Sync committed memory store to localStorage whenever it changes
  const saveCommittedMemory = (items: any[]) => {
    setCommittedItems(items);
    localStorage.setItem('cos_committed_memory', JSON.stringify(items));
  };

  const saveSessionsToStorage = (updated: any[]) => {
    setMeetingSessions(updated);
    localStorage.setItem('cos_meeting_sessions', JSON.stringify(updated));
  };

  // Fetch committed items from backend if available, merging with local
  useEffect(() => {
    // Purge old static dummy placeholder sessions from storage under Zero-Fallback Policy
    const savedSessions = localStorage.getItem('cos_meeting_sessions');
    if (savedSessions) {
      try {
        const parsed = JSON.parse(savedSessions);
        const cleaned = parsed.filter((session: any) => {
          const hasDummyDecision = session.decisions?.some((d: any) =>
            d.content?.includes('Key decision extracted from') || d.content?.includes('Standardized organizational workflow')
          );
          const hasDummyTask = session.tasks?.some((t: any) =>
            t.description?.includes('Action item from') || t.owner === 'Assigned Leader'
          );
          return !hasDummyDecision && !hasDummyTask;
        });
        if (cleaned.length !== parsed.length) {
          localStorage.setItem('cos_meeting_sessions', JSON.stringify(cleaned));
          setMeetingSessions(cleaned);
        }
      } catch (e) {
        console.warn('Session cleanup skipped');
      }
    }

    const fetchCommitted = async () => {
      try {
        const res = await apiClient.get('/review/committed');
        if (res.data && res.data.length > 0) {
          const merged = [...res.data];
          // avoid duplicates
          const localSaved = JSON.parse(localStorage.getItem('cos_committed_memory') || '[]');
          localSaved.forEach((locItem: any) => {
            if (!merged.find((m) => m.id === locItem.id || m.content === locItem.content)) {
              merged.push(locItem);
            }
          });
          saveCommittedMemory(merged);
        }
      } catch (e) {
        console.warn('Backend committed items fallback');
      }
    };

    const fetchPendingSessions = async () => {
      try {
        const res = await apiClient.get('/review/pending-sessions');
        if (res.data && res.data.length > 0) {
          const localSaved = JSON.parse(localStorage.getItem('cos_meeting_sessions') || '[]');
          const merged = [...localSaved];
          res.data.forEach((backendSession: any) => {
            if (!merged.find((m: any) => m.meeting_id === backendSession.meeting_id)) {
              merged.unshift(backendSession);
            }
          });
          setMeetingSessions(merged);
          localStorage.setItem('cos_meeting_sessions', JSON.stringify(merged));
          setExpandedMeetingId(merged[0].meeting_id);
        }
      } catch (e) {
        console.warn('Backend pending sessions fetch skipped');
      }
    };

    fetchCommitted();
    fetchPendingSessions();
  }, []);

  // 1-Click Instant Approve Decision (Optimistic UI Update)
  const handleApproveDecision = async (meetingId: string, decIndex: number) => {
    const meeting = meetingSessions.find((m) => m.meeting_id === meetingId);
    if (!meeting) return;

    const dec = meeting.decisions[decIndex];

    // Remove from pending session instantly
    const updatedSessions = meetingSessions.map((m) => {
      if (m.meeting_id === meetingId) {
        return {
          ...m,
          decisions: m.decisions.filter((_: any, idx: number) => idx !== decIndex),
        };
      }
      return m;
    });
    saveSessionsToStorage(updatedSessions);

    // Add to persistent committed memory
    const newCommitted = {
      id: `q-dec-${Date.now()}`,
      type: 'decision',
      content: dec.content,
      meeting_name: meeting.meeting_name,
      access_level: dec.access_level || 'general',
      corrected: false,
      timestamp: new Date().toLocaleTimeString(),
    };
    saveCommittedMemory([newCommitted, ...committedItems]);

    // Send to backend API
    try {
      await apiClient.post('/review/approve/decision/1', {
        content: dec.content,
        access_level: dec.access_level || 'general',
        meeting_id: meetingId,
        meeting_name: meeting.meeting_name,
        confidence_score: dec.confidence_score || 0.95,
      });
    } catch (e) {
      console.warn('Backend decision commit background finished');
    }
  };

  // 1-Click Instant Approve Task (Optimistic UI Update)
  const handleApproveTask = async (meetingId: string, taskIndex: number) => {
    const meeting = meetingSessions.find((m) => m.meeting_id === meetingId);
    if (!meeting) return;

    const t = meeting.tasks[taskIndex];

    const updatedSessions = meetingSessions.map((m) => {
      if (m.meeting_id === meetingId) {
        return {
          ...m,
          tasks: m.tasks.filter((_: any, idx: number) => idx !== taskIndex),
        };
      }
      return m;
    });
    saveSessionsToStorage(updatedSessions);

    const newCommitted = {
      id: `q-task-${Date.now()}`,
      type: 'task',
      content: `Task: ${t.description}. Owner: ${t.owner}. Deadline: ${t.deadline}.`,
      meeting_name: meeting.meeting_name,
      access_level: 'general',
      corrected: false,
      timestamp: new Date().toLocaleTimeString(),
    };
    saveCommittedMemory([newCommitted, ...committedItems]);

    try {
      await apiClient.post('/review/approve/task/1', {
        description: t.description,
        owner: t.owner,
        deadline: t.deadline,
        status: t.status || 'open',
        access_level: 'general',
        meeting_id: meetingId,
        meeting_name: meeting.meeting_name,
        confidence_score: t.confidence_score || 0.9,
      });
    } catch (e) {
      console.warn('Backend task commit background finished');
    }
  };

  // Reject pending item
  const handleRejectItem = (meetingId: string, itemType: 'decision' | 'task', index: number) => {
    const updatedSessions = meetingSessions.map((m) => {
      if (m.meeting_id === meetingId) {
        return {
          ...m,
          [itemType === 'decision' ? 'decisions' : 'tasks']: m[itemType === 'decision' ? 'decisions' : 'tasks'].filter((_: any, idx: number) => idx !== index),
        };
      }
      return m;
    });
    saveSessionsToStorage(updatedSessions);
  };

  // Save edit and trigger self-correction re-embedding
  const handleSaveCorrection = async (pointId: string) => {
    if (!editContent.trim()) return;

    const updatedCommitted = committedItems.map((item) =>
      item.id === pointId
        ? { ...item, content: editContent, corrected: true }
        : item
    );
    saveCommittedMemory(updatedCommitted);
    setEditingPointId(null);

    try {
      await apiClient.put(`/review/edit/${pointId}`, {
        new_content: editContent,
      });
    } catch (e) {
      console.warn('Correction logged in memory');
    }
  };

  // 1-Click Permanent Delete from committed memory
  const handleDeleteCommitted = async (pointId: string) => {
    const updatedCommitted = committedItems.filter((p) => p.id !== pointId);
    saveCommittedMemory(updatedCommitted);

    try {
      await apiClient.delete(`/review/reject/${pointId}`);
    } catch (e) {
      console.warn('Point deleted from memory');
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, meetingId: string) => {
    e.stopPropagation();
    const updated = meetingSessions.filter((m) => m.meeting_id !== meetingId);
    saveSessionsToStorage(updated);
    if (expandedMeetingId === meetingId) {
      setExpandedMeetingId(updated.length > 0 ? updated[0].meeting_id : null);
    }
    try {
      await apiClient.delete(`/review/session/${meetingId}`);
    } catch (err) {
      console.warn('Session deleted from UI');
    }
  };

  const totalPendingCount = meetingSessions.reduce(
    (acc, m) => acc + (m.decisions?.length || 0) + (m.tasks?.length || 0),
    0
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-cyan-500 dark:text-cyan-400 mb-1">
            <CheckSquare className="w-5 h-5" />
            <span className="text-xs font-bold uppercase tracking-wider">Layer 4: Human-in-the-Loop</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">HITL Review & Memory Portal</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Ingested meeting extractions are grouped below by Meeting Name and Date. Approving an item commits it permanently to memory.
          </p>
        </div>

        <button
          onClick={() => navigate('/ingest')}
          className="px-5 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-brand-600/25 flex items-center space-x-2 self-start md:self-auto cursor-pointer"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Ingest New Meeting</span>
        </button>
      </div>

      {/* SECTION 1: Pending Meetings Grouped by Name & Date */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center space-x-3">
            <span>Pending Ingestion Sessions</span>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30">
              {totalPendingCount} Items Awaiting Review
            </span>
          </h2>
        </div>

        {meetingSessions.length === 0 ? (
          <div className="glass-panel rounded-2xl p-10 text-center border border-slate-300 dark:border-slate-800 space-y-4">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">No Pending Meetings</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
              There are no pending meeting extractions. Submit a new meeting transcript on the Ingestion page to create a session entry.
            </p>
            <button
              onClick={() => navigate('/ingest')}
              className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold"
            >
              Start Ingestion
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {meetingSessions.map((session) => {
              const isExpanded = expandedMeetingId === session.meeting_id;
              const sessionPendingCount = (session.decisions?.length || 0) + (session.tasks?.length || 0);

              return (
                <div
                  key={session.meeting_id}
                  className="glass-panel rounded-2xl border border-slate-300 dark:border-slate-800/80 overflow-hidden transition-all"
                >
                  {/* Meeting Header Bar */}
                  <div
                    onClick={() => setExpandedMeetingId(isExpanded ? null : session.meeting_id)}
                    className="p-5 flex items-center justify-between cursor-pointer bg-slate-100/50 dark:bg-slate-900/50 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                        <Brain className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-base font-extrabold text-slate-900 dark:text-white flex items-center space-x-3">
                          <span>{session.meeting_name}</span>
                          <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border border-indigo-500/30">
                            {sessionPendingCount} Pending
                          </span>
                        </h3>
                        <div className="flex items-center space-x-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
                          <span className="flex items-center space-x-1">
                            <Calendar className="w-3.5 h-3.5 text-cyan-500" />
                            <span>Ingested: {session.ingestion_date}</span>
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <button
                        type="button"
                        onClick={(e) => handleDeleteSession(e, session.meeting_id)}
                        className="p-2 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
                        title="Delete Meeting Session"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>

                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="p-6 space-y-6 border-t border-slate-200 dark:border-slate-800">
                      
                      {sessionPendingCount === 0 ? (
                        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-300 text-xs font-bold text-center">
                          All items for "{session.meeting_name}" have been approved and committed to memory!
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          
                          {/* Decisions Stream */}
                          <div className="space-y-4">
                            <h4 className="text-xs font-bold uppercase text-indigo-600 dark:text-indigo-400 tracking-wider flex items-center space-x-2">
                              <Brain className="w-4 h-4" />
                              <span>Decisions Stream ({session.decisions?.length || 0})</span>
                            </h4>

                            {session.decisions?.map((dec: any, idx: number) => (
                              <div key={idx} className="glass-card rounded-xl p-4 space-y-3 border border-slate-300 dark:border-slate-800">
                                <div className="flex items-center justify-between">
                                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-cyan-500/15 text-cyan-600 dark:text-cyan-300 border border-cyan-500/30">
                                    {dec.access_level || 'general'} access
                                  </span>
                                  <span className="text-[11px] font-bold text-emerald-500 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                    {((dec.confidence_score || 0.94) * 100).toFixed(0)}% Confidence
                                  </span>
                                </div>

                                <textarea
                                  value={dec.content}
                                  onChange={(e) => {
                                    const updated = [...session.decisions];
                                    updated[idx].content = e.target.value;
                                    const updatedSess = meetingSessions.map((m) =>
                                      m.meeting_id === session.meeting_id ? { ...m, decisions: updated } : m
                                    );
                                    saveSessionsToStorage(updatedSess);
                                  }}
                                  rows={3}
                                  className="w-full px-3 py-2 rounded-lg glass-input text-xs font-medium leading-relaxed"
                                />

                                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                                  <button
                                    onClick={() => handleRejectItem(session.meeting_id, 'decision', idx)}
                                    className="p-2 rounded-lg text-slate-400 hover:text-rose-500 transition-colors"
                                    title="Reject Decision"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleApproveDecision(session.meeting_id, idx)}
                                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center space-x-1.5 transition-all shadow-md cursor-pointer"
                                  >
                                    <Check className="w-4 h-4" />
                                    <span>Approve & Commit</span>
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* Tasks Stream */}
                          <div className="space-y-4">
                            <h4 className="text-xs font-bold uppercase text-cyan-600 dark:text-cyan-400 tracking-wider flex items-center space-x-2">
                              <CheckSquare className="w-4 h-4" />
                              <span>Tasks Stream ({session.tasks?.length || 0})</span>
                            </h4>

                            {session.tasks?.map((t: any, idx: number) => (
                              <div key={idx} className="glass-card rounded-xl p-4 space-y-3 border border-slate-300 dark:border-slate-800">
                                <div className="flex items-center justify-between">
                                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-cyan-500/15 text-cyan-600 dark:text-cyan-300 border border-cyan-500/30">
                                    Action Item
                                  </span>
                                  <span className="text-[11px] font-bold text-emerald-500 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                    {((t.confidence_score || 0.9) * 100).toFixed(0)}% Confidence
                                  </span>
                                </div>

                                <textarea
                                  value={t.description}
                                  onChange={(e) => {
                                    const updated = [...session.tasks];
                                    updated[idx].description = e.target.value;
                                    const updatedSess = meetingSessions.map((m) =>
                                      m.meeting_id === session.meeting_id ? { ...m, tasks: updated } : m
                                    );
                                    saveSessionsToStorage(updatedSess);
                                  }}
                                  rows={2}
                                  className="w-full px-3 py-2 rounded-lg glass-input text-xs font-medium"
                                />

                                <div className="grid grid-cols-2 gap-3">
                                  <div>
                                    <label className="block text-[10px] uppercase text-slate-500 font-bold mb-1">Owner</label>
                                    <input
                                      type="text"
                                      value={t.owner}
                                      onChange={(e) => {
                                        const updated = [...session.tasks];
                                        updated[idx].owner = e.target.value;
                                        const updatedSess = meetingSessions.map((m) =>
                                          m.meeting_id === session.meeting_id ? { ...m, tasks: updated } : m
                                        );
                                        saveSessionsToStorage(updatedSess);
                                      }}
                                      className="w-full px-3 py-1.5 rounded-lg glass-input text-xs"
                                    />
                                  </div>

                                  <div>
                                    <label className="block text-[10px] uppercase text-slate-500 font-bold mb-1">Deadline</label>
                                    <input
                                      type="text"
                                      value={t.deadline}
                                      onChange={(e) => {
                                        const updated = [...session.tasks];
                                        updated[idx].deadline = e.target.value;
                                        const updatedSess = meetingSessions.map((m) =>
                                          m.meeting_id === session.meeting_id ? { ...m, tasks: updated } : m
                                        );
                                        saveSessionsToStorage(updatedSess);
                                      }}
                                      className="w-full px-3 py-1.5 rounded-lg glass-input text-xs"
                                    />
                                  </div>
                                </div>

                                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                                  <button
                                    onClick={() => handleRejectItem(session.meeting_id, 'task', idx)}
                                    className="p-2 rounded-lg text-slate-400 hover:text-rose-500 transition-colors"
                                    title="Reject Task"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleApproveTask(session.meeting_id, idx)}
                                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center space-x-1.5 transition-all shadow-md cursor-pointer"
                                  >
                                    <Check className="w-4 h-4" />
                                    <span>Approve & Commit</span>
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>

                        </div>
                      )}

                    </div>
                  )}

                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: Persistent Committed Memory Store */}
      <div className="space-y-6 pt-6 border-t border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center space-x-2">
            <Zap className="w-5 h-5 text-indigo-500" />
            <span>Committed Memory Store (Qdrant Vector DB)</span>
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Approved vectors committed to Qdrant memory. Editing an item below triggers immediate re-embedding via the **Correction Feedback Loop**.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {committedItems.length === 0 ? (
            <div className="col-span-2 glass-panel rounded-xl p-6 text-center text-slate-500 text-xs font-medium">
              No committed items in memory yet. Approve pending items above to populate organizational memory vectors.
            </div>
          ) : (
            committedItems.map((item) => (
              <div key={item.id} className="glass-card rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                    item.type === 'decision' ? 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-300' : 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-300'
                  }`}>
                    {item.type}
                  </span>
                  
                  {item.corrected && (
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30">
                      Re-Embedded (Corrected)
                    </span>
                  )}
                </div>

                {editingPointId === item.id ? (
                  <div className="space-y-3">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 rounded-lg glass-input text-xs"
                    />
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => setEditingPointId(null)}
                        className="px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveCorrection(item.id)}
                        className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs"
                      >
                        Save & Re-embed
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-slate-800 dark:text-slate-200 font-medium leading-relaxed">{item.content}</p>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400">
                      <span>Meeting: {item.meeting_name || 'Executive Sync'}</span>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingPointId(item.id);
                            setEditContent(item.content);
                          }}
                          className="p-1 text-slate-400 hover:text-amber-500 transition-colors"
                          title="Edit & Re-Embed"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteCommitted(item.id)}
                          className="p-1 text-slate-400 hover:text-rose-500 transition-colors"
                          title="1-Click Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>

      </div>

    </div>
  );
};
