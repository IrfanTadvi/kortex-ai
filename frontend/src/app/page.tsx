'use client';

import { useState, useCallback } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { ChatPanel } from '@/components/ChatPanel';
import { AnalyticsDashboard } from '@/components/AnalyticsDashboard';
import { DocumentPanel } from '@/components/DocumentPanel';
import { SQLPanel } from '@/components/SQLPanel';

export type ViewMode = 'chat' | 'analytics' | 'documents' | 'sql';

export default function Home() {
  const [currentView, setCurrentView] = useState<ViewMode>('chat');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentRole, setCurrentRole] = useState('general');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);

  const handleNewChat = useCallback(() => {
    setCurrentSessionId(null);
    setCurrentView('chat');
  }, []);

  const handleSelectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
    setCurrentView('chat');
  }, []);

  const handleSessionCreated = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
    // Trigger sidebar refresh to show updated session title
    setSidebarRefreshKey(k => k + 1);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-dark-950">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        currentView={currentView}
        onViewChange={setCurrentView}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        currentSessionId={currentSessionId}
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        refreshKey={sidebarRefreshKey}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {currentView === 'chat' && (
          <ChatPanel
            sessionId={currentSessionId}
            onSessionCreated={handleSessionCreated}
            role={currentRole}
            sidebarOpen={sidebarOpen}
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          />
        )}
        {currentView === 'analytics' && <AnalyticsDashboard />}
        {currentView === 'documents' && <DocumentPanel />}
        {currentView === 'sql' && <SQLPanel />}
      </main>
    </div>
  );
}
