// frontend/src/pages/ChatView.tsx
import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../store';
import { ChatFeed } from '../components/ChatFeed';
import { ChatMessage, User } from '../types';
import { useSocket } from '../hooks/useSocket';
import { api } from '../services/api';
import { formatters } from '../utils/formatters';

export const ChatView: React.FC = () => {
  const { state } = useAppContext();
  const { currentLeague, user } = state;
  const { socket, isConnected } = useSocket();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState<string[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<User[]>([]);
  const [error, setError] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (socket && currentLeague && user) {
      // Join league chat room
      socket.emit('joinLeagueChat', {
        leagueId: currentLeague.id,
        userId: user.uid,
        userName: user.displayName || 'Anonymous'
      });

      // Listen for new messages
      socket.on('newChatMessage', (message: ChatMessage) => {
        setMessages(prev => [...prev, message]);
        
        // Remove typing indicator for this user
        setIsTyping(prev => prev.filter(userId => userId !== message.userId));
      });

      // Listen for typing indicators
      socket.on('userTyping', ({ userId, userName, isTyping: typing }: {
        userId: string;
        userName: string;
        isTyping: boolean;
      }) => {
        if (userId !== user.uid) {
          setIsTyping(prev => {
            if (typing) {
              return prev.includes(userId) ? prev : [...prev, userId];
            } else {
              return prev.filter(id => id !== userId);
            }
          });
        }
      });

      // Listen for online users
      socket.on('onlineUsers', (users: User[]) => {
        setOnlineUsers(users);
      });

      // Listen for user join/leave
      socket.on('userJoinedChat', (userData: { userId: string; userName: string }) => {
        const systemMessage: ChatMessage = {
          id: `system-${Date.now()}`,
          leagueId: currentLeague.id,
          userId: 'system',
          userName: 'System',
          message: `${userData.userName} joined the chat`,
          type: 'system',
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, systemMessage]);
      });

      socket.on('userLeftChat', (userData: { userId: string; userName: string }) => {
        const systemMessage: ChatMessage = {
          id: `system-${Date.now()}`,
          leagueId: currentLeague.id,
          userId: 'system',
          userName: 'System',
          message: `${userData.userName} left the chat`,
          type: 'system',
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, systemMessage]);
      });

      // Load chat history
      fetchChatHistory();

      return () => {
        socket.off('newChatMessage');
        socket.off('userTyping');
        socket.off('onlineUsers');
        socket.off('userJoinedChat');
        socket.off('userLeftChat');
        
        // Leave chat room
        socket.emit('leaveLeagueChat', {
          leagueId: currentLeague.id,
          userId: user.uid
        });
      };
    }
  }, [socket, currentLeague, user]);

  const fetchChatHistory = async () => {
    if (!currentLeague) return;
    
    try {
      setIsLoading(true);
      setError('');
      const history = await api.getChatHistory(currentLeague.id);
      setMessages(history);
    } catch (err) {
      setError('Failed to load chat history');
      console.error('Failed to fetch chat history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = () => {
    if (newMessage.trim() && socket && user && currentLeague) {
      const messageData = {
        leagueId: currentLeague.id,
        userId: user.uid,
        userName: user.displayName || 'Anonymous',
        message: newMessage.trim(),
        type: 'message' as const
      };

      socket.emit('sendChatMessage', messageData);
      setNewMessage('');
      
      // Stop typing indicator
      socket.emit('stopTyping', {
        leagueId: currentLeague.id,
        userId: user.uid
      });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNewMessage(e.target.value);
    
    // Send typing indicator
    if (socket && user && currentLeague) {
      socket.emit('startTyping', {
        leagueId: currentLeague.id,
        userId: user.uid,
        userName: user.displayName || 'Anonymous'
      });

      // Clear previous timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      // Stop typing after 2 seconds of inactivity
      typingTimeoutRef.current = setTimeout(() => {
        socket.emit('stopTyping', {
          leagueId: currentLeague.id,
          userId: user.uid
        });
      }, 2000);
    }
  };

  const clearChat = async () => {
    if (!currentLeague || !window.confirm('Are you sure you want to clear the chat? This action cannot be undone.')) {
      return;
    }

    try {
      await api.clearChatHistory(currentLeague.id);
      setMessages([]);
    } catch (err) {
      setError('Failed to clear chat');
    }
  };

  if (!currentLeague) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading...</span>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">League Chat</h1>
            <p className="text-gray-600">{currentLeague.name}</p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-600">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Online Users Count */}
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-sm text-gray-600">
                {onlineUsers.length} online
              </span>
            </div>

            {/* Clear Chat Button (for commissioners) */}
            {user?.uid === currentLeague.commissionerId && (
              <button
                onClick={clearChat}
                className="text-red-600 hover:text-red-800 text-sm font-medium"
              >
                Clear Chat
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Chat Container */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[600px]">
            {/* Messages */}
            <div className="flex-1 overflow-hidden">
              {error && (
                <div className="p-4 bg-red-50 border-b border-red-200 text-red-700 text-sm">
                  {error}
                </div>
              )}
              
              <ChatFeed
                messages={messages}
                currentUserId={user?.uid || ''}
                loading={isLoading}
                className="h-full"
                showTimestamps={true}
                groupByTime={true}
              />
              
              {/* Typing Indicators */}
              {isTyping.length > 0 && (
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-sm text-gray-500">
                      {isTyping.length === 1 ? 'Someone is typing...' : `${isTyping.length} people are typing...`}
                    </span>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <div className="border-t border-gray-200 p-4">
              <div className="flex space-x-3">
                <div className="flex-1">
                  <textarea
                    value={newMessage}
                    onChange={handleInputChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your message... (Press Enter to send)"
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    disabled={!isConnected}
                  />
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={!newMessage.trim() || !isConnected}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Send
                </button>
              </div>
              
              {!isConnected && (
                <p className="text-red-500 text-sm mt-2">
                  ⚠️ Disconnected from chat. Attempting to reconnect...
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="space-y-6">
            {/* Online Users */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-3">
                Online Now ({onlineUsers.length})
              </h3>
              <div className="space-y-2">
                {onlineUsers.map((onlineUser) => (
                  <div key={onlineUser.uid} className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {onlineUser.displayName || 'Anonymous'}
                      </p>
                      <p className="text-xs text-gray-500">Online</p>
                    </div>
                  </div>
                ))}
                
                {onlineUsers.length === 0 && (
                  <p className="text-gray-500 text-sm">No one else is online</p>
                )}
              </div>
            </div>

            {/* League Members */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-3">
                League Members ({currentLeague.teams.length})
              </h3>
              <div className="space-y-2">
                {currentLeague.teams.map((team) => {
                  const isOnline = onlineUsers.some(u => u.uid === team.ownerId);
                  
                  return (
                    <div key={team.id} className="flex items-center space-x-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        isOnline ? 'bg-green-100' : 'bg-gray-100'
                      }`}>
                        {team.logoUrl ? (
                          <img
                            src={team.logoUrl}
                            alt={team.name}
                            className="w-8 h-8 rounded-full object-cover"
                          />
                        ) : (
                          <div className={`w-3 h-3 rounded-full ${
                            isOnline ? 'bg-green-500' : 'bg-gray-400'
                          }`}></div>
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {team.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {team.ownerName} • {team.wins}-{team.losses}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Chat Rules */}
            <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Chat Rules</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Be respectful to all league members</li>
                <li>• No spam or excessive messages</li>
                <li>• Keep discussions fantasy-related</li>
                <li>• Have fun and enjoy the competition!</li>
              </ul>
            </div>

            {/* Chat Stats */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-3">Chat Stats</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Messages:</span>
                  <span className="font-medium">{messages.filter(m => m.type === 'message').length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Today:</span>
                  <span className="font-medium">
                    {messages.filter(m => 
                      m.type === 'message' && 
                      new Date(m.timestamp).toDateString() === new Date().toDateString()
                    ).length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Most Active:</span>
                  <span className="font-medium">
                    {/* Calculate most active user */}
                    {(() => {
                      const userCounts = messages
                        .filter(m => m.type === 'message' && m.userId !== 'system')
                        .reduce((acc, m) => {
                          acc[m.userName] = (acc[m.userName] || 0) + 1;
                          return acc;
                        }, {} as Record<string, number>);
                      
                      const mostActive = Object.entries(userCounts)
                        .sort(([,a], [,b]) => b - a)[0];
                      
                      return mostActive ? mostActive[0] : 'None';
                    })()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};