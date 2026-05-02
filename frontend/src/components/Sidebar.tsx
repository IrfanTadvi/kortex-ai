'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquarePlus, LayoutDashboard, FileText, Database,
  ChevronLeft, ChevronRight, Sparkles, User, Code, Briefcase, Shield, Trash2
} from 'lucide-react';
import { api, Session } from '@/lib/api';
import { ViewMode } from '@/app/page';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  currentView: ViewMode;
  onViewChange: (view: ViewMode) => void;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  currentSessionId: string | null;
  currentRole: string;
  onRoleChange: (role: string) => void;
  refreshKey?: number;
}

const roles = [
  { id: 'general', label: 'General', icon: User, color: 'text-blue-400' },
  { id: 'engineer', label: 'Engineer', icon: Code, color: 'text-green-400' },
  { id: 'hr', label: 'HR', icon: Shield, color: 'text-pink-400' },
  { id: 'manager', label: 'Manager', icon: Briefcase, color: 'text-amber-400' },
];

const navItems = [
  { id: 'chat' as ViewMode, label: 'Chat', icon: MessageSquarePlus },
  { id: 'documents' as ViewMode, label: 'Documents', icon: FileText },
  { id: 'sql' as ViewMode, label: 'SQL Query', icon: Database },
  { id: 'analytics' as ViewMode, label: 'Analytics', icon: LayoutDashboard },
];

export function Sidebar({
  isOpen, onToggle, currentView, onViewChange,
  onNewChat, onSelectSession, currentSessionId,
  currentRole, onRoleChange, refreshKey
}: SidebarProps) {
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    loadSessions();
  }, [refreshKey]);

  const loadSessions = async () => {
    try {
      const data = await api.getSessions();
      setSessions(data.sessions || []);
    } catch {}
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    try {
      await api.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        onNewChat();
      }
    } catch {}
  };

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="glass-sidebar h-full flex flex-col overflow-hidden relative z-20"
          >
            {/* Logo */}
            <div className="p-5 border-b border-white/[0.06]">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center shadow-lg shadow-primary-500/25">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="font-bold text-white text-sm tracking-tight">Kortex AI</h1>
                  <p className="text-[10px] text-gray-500 uppercase tracking-widest">Enterprise Intelligence Platform</p>
                </div>
              </div>
            </div>

            {/* New Chat Button */}
            <div className="px-3 pt-4">
              <button
                onClick={onNewChat}
                className="w-full glass-button flex items-center justify-center gap-2 text-sm"
              >
                <MessageSquarePlus className="w-4 h-4" />
                New Chat
              </button>
            </div>

            {/* Navigation */}
            <nav className="px-3 pt-4 space-y-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onViewChange(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                    currentView === item.id
                      ? 'bg-primary-600/20 text-primary-300 border border-primary-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </button>
              ))}
            </nav>

            {/* Role Selector */}
            <div className="px-3 pt-6">
              <p className="text-[10px] uppercase tracking-widest text-gray-500 px-3 mb-2 font-medium">Response Role</p>
              <div className="grid grid-cols-2 gap-1.5">
                {roles.map((role) => (
                  <button
                    key={role.id}
                    onClick={() => onRoleChange(role.id)}
                    className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs transition-all ${
                      currentRole === role.id
                        ? 'bg-white/[0.08] border border-white/[0.15] text-white'
                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]'
                    }`}
                  >
                    <role.icon className={`w-3.5 h-3.5 ${currentRole === role.id ? role.color : ''}`} />
                    {role.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto px-3 pt-6 pb-4">
              <p className="text-[10px] uppercase tracking-widest text-gray-500 px-3 mb-2 font-medium">Recent Chats</p>
              <div className="space-y-1">
                {sessions.slice(0, 15).map((session) => (
                  <div
                    key={session.id}
                    className={`group flex items-center gap-1 rounded-lg transition-all ${
                      currentSessionId === session.id
                        ? 'bg-white/[0.08] text-white'
                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]'
                    }`}
                  >
                    <button
                      onClick={() => onSelectSession(session.id)}
                      className="flex-1 text-left px-3 py-2 text-sm truncate"
                      title={session.title}
                    >
                      {session.title}
                    </button>
                    <button
                      onClick={(e) => handleDeleteSession(e, session.id)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 mr-1 rounded hover:bg-red-500/20 hover:text-red-400 transition-all"
                      title="Delete chat"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
                {sessions.length === 0 && (
                  <p className="text-gray-600 text-xs px-3 py-4 text-center">No chats yet</p>
                )}
              </div>
            </div>

            {/* Collapse button */}
            <button
              onClick={onToggle}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 
                         w-6 h-12 bg-dark-800 border border-white/[0.1] rounded-r-lg
                         flex items-center justify-center hover:bg-dark-700 transition-colors z-30"
            >
              <ChevronLeft className="w-3.5 h-3.5 text-gray-400" />
            </button>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Open sidebar button when collapsed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-30
                     w-6 h-12 bg-dark-800 border border-white/[0.1] rounded-r-lg
                     flex items-center justify-center hover:bg-dark-700 transition-colors"
        >
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
        </button>
      )}
    </>
  );
}
