'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Loader2, Sparkles, Menu, BookOpen,
  ChevronDown, ThumbsUp, ThumbsDown, Copy, Check
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api, ChatMessage, SourceReference, ChatResponse } from '@/lib/api';

interface ChatPanelProps {
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
  role: string;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export function ChatPanel({ sessionId, onSessionCreated, role, sidebarOpen, onToggleSidebar }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([]);
  const [expandedSources, setExpandedSources] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load session history
  useEffect(() => {
    if (sessionId) {
      loadHistory(sessionId);
    } else {
      setMessages([]);
      setFollowUpQuestions([]);
    }
  }, [sessionId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const loadHistory = async (sid: string) => {
    try {
      const data = await api.getSessionHistory(sid);
      setMessages(data.messages || []);
    } catch {}
  };

  const handleSend = useCallback(async (messageText?: string) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    setInput('');
    setFollowUpQuestions([]);

    // Add user message
    const userMessage: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setStreamingContent('');

    try {
      // Use streaming
      let fullContent = '';
      let currentSessionId = sessionId;

      await api.sendMessageStream(
        text,
        sessionId || undefined,
        role,
        // onToken
        (token) => {
          fullContent += token;
          setStreamingContent(fullContent);
        },
        // onDone
        (data) => {
          if (data.session_id && !currentSessionId) {
            currentSessionId = data.session_id;
            onSessionCreated(data.session_id);
          }
        },
        // onAction
        (actionData) => {
          // Handle action results
          if (actionData) {
            fullContent += `\n\n**Action Result:**\n${actionData.message || JSON.stringify(actionData)}`;
            setStreamingContent(fullContent);
          }
        }
      );

      // Add assistant message
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: fullContent || 'No response received. Please try again.',
      };
      setMessages(prev => [...prev, assistantMessage]);
      setStreamingContent('');

    } catch (error: any) {
      // Fallback to non-streaming
      try {
        const response = await api.sendMessage(text, sessionId || undefined, role);
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.message,
          sources: response.sources,
          confidence_score: response.confidence_score,
        };
        setMessages(prev => [...prev, assistantMessage]);
        setFollowUpQuestions(response.follow_up_questions || []);
        if (response.session_id && !sessionId) {
          onSessionCreated(response.session_id);
        }
      } catch (err: any) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${err.message}. Please check that the backend is running.`,
        }]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, sessionId, role, onSessionCreated]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <header className="glass border-b border-white/[0.06] px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {!sidebarOpen && (
            <button onClick={onToggleSidebar} className="p-2 hover:bg-white/5 rounded-lg">
              <Menu className="w-5 h-5 text-gray-400" />
            </button>
          )}
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary-400" />
            <h2 className="font-semibold text-white">AI Knowledge Copilot</h2>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-300 border border-primary-500/20 capitalize">
            {role}
          </span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && !streamingContent && (
          <WelcomeScreen onSendMessage={handleSend} />
        )}

        <AnimatePresence mode="popLayout">
          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : ''}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-lg shadow-primary-500/20">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
              )}

              <div className={`flex-1 max-w-[85%] ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-block text-left ${
                  msg.role === 'user'
                    ? 'bg-primary-600/30 border border-primary-500/20 rounded-2xl rounded-tr-md px-5 py-3'
                    : 'glass-card px-5 py-4'
                }`}>
                  <div className="prose-chat">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>

                {/* Sources */}
                {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3">
                    <button
                      onClick={() => setExpandedSources(expandedSources === `${idx}` ? null : `${idx}`)}
                      className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-primary-400 transition-colors"
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                      <ChevronDown className={`w-3 h-3 transition-transform ${expandedSources === `${idx}` ? 'rotate-180' : ''}`} />
                    </button>

                    <AnimatePresence>
                      {expandedSources === `${idx}` && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-2 space-y-2 overflow-hidden"
                        >
                          {msg.sources.map((source, sIdx) => (
                            <div key={sIdx} className="glass-card p-3 text-xs">
                              <div className="flex items-center justify-between mb-1.5">
                                <span className="text-primary-400 font-medium">{source.filename}</span>
                                <span className="text-gray-500">
                                  Score: {(source.score * 100).toFixed(0)}%
                                  {source.page && ` • Page ${source.page}`}
                                </span>
                              </div>
                              <p className="text-gray-400 line-clamp-2">{source.content}</p>
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {/* Confidence Score */}
                {msg.role === 'assistant' && msg.confidence_score !== undefined && msg.confidence_score > 0 && (
                  <div className="mt-2 flex items-center gap-3">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-20 bg-dark-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            msg.confidence_score > 0.7 ? 'bg-green-500' :
                            msg.confidence_score > 0.4 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${msg.confidence_score * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500">
                        {(msg.confidence_score * 100).toFixed(0)}% confidence
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyToClipboard(msg.content, `${idx}`)}
                        className="p-1 hover:bg-white/5 rounded transition-colors"
                      >
                        {copiedId === `${idx}` ? (
                          <Check className="w-3.5 h-3.5 text-green-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5 text-gray-500" />
                        )}
                      </button>
                      <button className="p-1 hover:bg-white/5 rounded transition-colors">
                        <ThumbsUp className="w-3.5 h-3.5 text-gray-500 hover:text-green-400" />
                      </button>
                      <button className="p-1 hover:bg-white/5 rounded transition-colors">
                        <ThumbsDown className="w-3.5 h-3.5 text-gray-500 hover:text-red-400" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-dark-700 flex items-center justify-center flex-shrink-0 mt-1">
                  <span className="text-sm font-medium text-gray-300">U</span>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming indicator */}
        {streamingContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-4 max-w-4xl mx-auto"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="glass-card px-5 py-4 flex-1">
              <div className="prose-chat">
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
              <span className="inline-block w-2 h-5 bg-primary-400 animate-pulse ml-1" />
            </div>
          </motion.div>
        )}

        {/* Loading indicator */}
        {isLoading && !streamingContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-4 max-w-4xl mx-auto"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="glass-card px-5 py-4">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
                <div className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
                <div className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
              </div>
            </div>
          </motion.div>
        )}

        {/* Follow-up questions */}
        {followUpQuestions.length > 0 && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto"
          >
            <p className="text-xs text-gray-500 mb-2 ml-12">Suggested follow-ups:</p>
            <div className="flex flex-wrap gap-2 ml-12">
              {followUpQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q)}
                  className="text-sm glass-button-secondary text-gray-300 hover:text-white"
                >
                  {q}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-white/[0.06] p-4">
        <div className="max-w-4xl mx-auto">
          <div className="glass-card p-2 flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your knowledge base..."
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none text-white placeholder-gray-500 px-3 py-2.5 text-sm max-h-32"
              style={{ height: 'auto', minHeight: '40px' }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = Math.min(target.scrollHeight, 128) + 'px';
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className={`p-2.5 rounded-xl transition-all duration-200 flex-shrink-0 ${
                input.trim() && !isLoading
                  ? 'bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/25'
                  : 'bg-white/5 text-gray-600 cursor-not-allowed'
              }`}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-[10px] text-gray-600 text-center mt-2">
            AI Knowledge Copilot can make mistakes. Verify important information.
          </p>
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({ onSendMessage }: { onSendMessage: (msg: string) => void }) {
  const suggestions = [
    "What is our company's PTO policy?",
    "Explain the incident response playbook",
    "Show me engineering best practices",
    "Create a support ticket for login issues",
    "How many employees are in Engineering?",
    "Summarize the onboarding process",
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center h-full text-center px-4"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', delay: 0.1 }}
        className="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mb-6 shadow-2xl shadow-primary-500/25"
      >
        <Sparkles className="w-10 h-10 text-white" />
      </motion.div>

      <h2 className="text-3xl font-bold text-white mb-2">AI Knowledge Copilot</h2>
      <p className="text-gray-400 mb-8 max-w-md">
        Your enterprise knowledge assistant. Ask questions, get source-grounded answers,
        and take actions — all from your company's knowledge base.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full">
        {suggestions.map((suggestion, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.05 }}
            onClick={() => onSendMessage(suggestion)}
            className="glass-card p-4 text-left hover:bg-white/[0.06] hover:border-primary-500/20 transition-all group"
          >
            <p className="text-sm text-gray-300 group-hover:text-white transition-colors">
              {suggestion}
            </p>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
