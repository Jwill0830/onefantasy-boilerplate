/**
 * ChatFeed component - Real-time messaging component for league chat
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useSocket } from '../hooks/useSocket';
import { ChatMessage } from '../types';

interface ChatFeedProps {
  leagueId: string;
  type?: 'league' | 'draft' | 'trade';
  height?: string;
  showHeader?: boolean;
  placeholder?: string;
  className?: string;
}

const ChatFeed: React.FC<ChatFeedProps> = ({
  leagueId,
  type = 'league',
  height = 'h-96',
  showHeader = true,
  placeholder = 'Type your message...',
  className = '',
}) => {
  const auth = useAuth();
  const socketContext = useSocket();
  
  // Extract properties safely with fallbacks
  const user = (auth as any)?.user || null;
  const socket = (socketContext as any)?.socket || null;
  const isConnected = (socketContext as any)?.isConnected || false;
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom of messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Load chat messages using fetch API as fallback
  const loadMessages = useCallback(async () => {
    if (!leagueId) return;

    try {
      setLoading(true);
      setError(null);
      
      // Using fetch API as fallback
      const response = await fetch(`/api/chat/league/${leagueId}/messages?limit=50`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          // Add auth headers if needed
          ...(user?.token && { 'Authorization': `Bearer ${user.token}` })
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setMessages(data.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp).toISOString()
        })));
      }
    } catch (error: any) {
      console.error('Error loading messages:', error);
      setError('Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [leagueId, user]);

  // Send message using fetch API
  const sendMessage = useCallback(async () => {
    if (!newMessage.trim() || !user || sending) return;

    try {
      setSending(true);
      setError(null);

      const response = await fetch(`/api/chat/league/${leagueId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(user?.token && { 'Authorization': `Bearer ${user.token}` })
        },
        body: JSON.stringify({
          message: newMessage.trim(),
          message_type: type,
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setNewMessage('');
        // Message will be added via socket event
      }
    } catch (error: any) {
      console.error('Error sending message:', error);
      setError('Failed to send message');
    } finally {
      setSending(false);
    }
  }, [newMessage, user, leagueId, type, sending]);

  // Handle socket events
  useEffect(() => {
    if (!socket || !isConnected) return;

    const handleNewMessage = (data: any) => {
      if (data.league_id === leagueId) {
        const message: ChatMessage = {
          ...data.message,
          timestamp: new Date(data.message.timestamp).toISOString()
        };
        
        setMessages(prev => [...prev, message]);
      }
    };

    const handleMessageReaction = (data: any) => {
      if (data.league_id === leagueId) {
        setMessages(prev => prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, reactions: data.reactions }
            : msg
        ));
      }
    };

    const handleMessageEdit = (data: any) => {
      if (data.league_id === leagueId) {
        setMessages(prev => prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, message: data.new_message, edited: true }
            : msg
        ));
      }
    };

    socket.on('new_chat_message', handleNewMessage);
    socket.on('message_reaction', handleMessageReaction);
    socket.on('message_edited', handleMessageEdit);

    return () => {
      socket.off('new_chat_message', handleNewMessage);
      socket.off('message_reaction', handleMessageReaction);
      socket.off('message_edited', handleMessageEdit);
    };
  }, [socket, isConnected, leagueId]);

  // Load messages on mount
  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Add reaction to message
  const addReaction = async (messageId: string, emoji: string) => {
    try {
      await fetch(`/api/chat/league/${leagueId}/messages/${messageId}/reaction`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(user?.token && { 'Authorization': `Bearer ${user.token}` })
        },
        body: JSON.stringify({ emoji })
      });
    } catch (error) {
      console.error('Error adding reaction:', error);
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const messageDate = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - messageDate.getTime();
    const diffMinutes = Math.floor(diff / (1000 * 60));
    const diffHours = Math.floor(diff / (1000 * 60 * 60));
    const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) {
      return 'Just now';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return messageDate.toLocaleDateString();
    }
  };

  // Get message type styling
  const getMessageTypeStyle = (messageType: string) => {
    switch (messageType) {
      case 'draft':
        return 'border-l-4 border-l-blue-500 bg-blue-50 text-blue-800';
      case 'trade':
        return 'border-l-4 border-l-green-500 bg-green-50 text-green-800';
      case 'waiver':
        return 'border-l-4 border-l-orange-500 bg-orange-50 text-orange-800';
      case 'system':
        return 'border-l-4 border-l-gray-500 bg-gray-50 text-gray-800';
      default:
        return '';
    }
  };

  return (
    <div className={`flex flex-col bg-white border border-gray-200 rounded-lg ${className}`}>
      {/* Header */}
      {showHeader && (
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900">League Chat</h3>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </div>
          <div className="text-sm text-gray-500">
            {messages.length} messages
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className={`flex-1 overflow-y-auto p-4 space-y-3 ${height}`}>
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p>No messages yet</p>
              <p className="text-sm">Be the first to start the conversation!</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`p-3 rounded-lg ${getMessageTypeStyle(message.type)}`}>
              <div className="flex items-start justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">
                    {message.user_name}
                    {message.user_id === user?.uid && ' (You)'}
                  </span>
                  {message.type !== 'message' && (
                    <span className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded">
                      {message.type}
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-500">
                  {formatTimestamp(message.timestamp)}
                </span>
              </div>
              
              <p className="text-sm mb-2 whitespace-pre-wrap">{message.message}</p>
              
              {/* Reactions - Simple implementation for now */}
              <div className="flex flex-wrap gap-1 mt-2">
                <button
                  onClick={() => addReaction(message.id, '👍')}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200"
                >
                  <span>👍</span>
                </button>
                <button
                  onClick={() => addReaction(message.id, '😄')}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200"
                >
                  <span>😄</span>
                </button>
                <button
                  onClick={() => addReaction(message.id, '🔥')}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200"
                >
                  <span>🔥</span>
                </button>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Message Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={sending || !isConnected}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            onClick={sendMessage}
            disabled={!newMessage.trim() || sending || !isConnected}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {sending ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
        
        {!isConnected && (
          <p className="text-xs text-red-500 mt-1">
            Not connected to chat server
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatFeed;