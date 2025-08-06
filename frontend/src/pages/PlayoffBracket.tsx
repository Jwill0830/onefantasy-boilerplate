// frontend/src/pages/PlayoffBracket.tsx
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../store';
import { BracketVisualizer } from '../components/BracketVisualizer';
import { PlayoffBracket as PlayoffBracketType } from '../types';
import { api } from '../services/api';

export const PlayoffBracket: React.FC = () => {
  const { state } = useAppContext();
  const { currentLeague, user } = state;
  
  const [bracket, setBracket] = useState<PlayoffBracketType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const isCommissioner = user?.uid === currentLeague?.commissionerId;

  useEffect(() => {
    if (currentLeague) {
      fetchBracket();
    }
  }, [currentLeague]);

  const fetchBracket = async () => {
    try {
      setLoading(true);
      const playoffBracket = await api.getPlayoffBracket(currentLeague!.id);
      setBracket(playoffBracket);
    } catch (err) {
      setError('Failed to fetch playoff bracket');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateMatchup = async (matchupId: string, winner: string, score: string) => {
    try {
      await api.updatePlayoffMatchup(matchupId, winner, score);
      await fetchBracket();
    } catch (err) {
      setError('Failed to update matchup');
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

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading playoff bracket...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Playoff Bracket</h1>
        <p className="text-gray-600">{currentLeague.name} - Season {currentLeague.season}</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Bracket */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <BracketVisualizer
          bracket={bracket}
          teams={currentLeague.teams}
          isCommissioner={isCommissioner}
          onUpdateMatchup={handleUpdateMatchup}
        />
      </div>
    </div>
  );
};

// frontend/src/pages/ChatView.tsx
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../store';
import { ChatFeed } from '../components/ChatFeed';
import { ChatMessage } from '../types';
import { useSocket } from '../hooks/useSocket';

export const ChatView: React.FC = () => {
  const { state } = useAppContext();
  const { currentLeague, user } = state;
  const { socket, isConnected } = useSocket();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (socket && currentLeague) {
      // Join league chat room
      socket.emit('joinLeagueChat', currentLeague.id);

      // Listen for new messages
      socket.on('newChatMessage', (message: ChatMessage) => {
        setMessages(prev => [...prev, message]);
      });

      // Load chat history
      fetchChatHistory();

      return () => {
        socket.off('newChatMessage');
      };
    }
  }, [socket, currentLeague]);

  const fetchChatHistory = async () => {
    try {
      setIsLoading(true);
      // In a real app, you'd fetch from API
      // const history = await api.getChatHistory(currentLeague!.id);
      // setMessages(history);
    } catch (err) {
      console.error('Failed to fetch chat history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = () => {
    if (newMessage.trim() && socket && user && currentLeague) {
      const message: Omit<ChatMessage, 'id' | 'timestamp'> = {
        leagueId: currentLeague.id,
        userId: user.uid,
        userName: user.displayName || 'Anonymous',
        message: newMessage.trim(),
        type: 'message'
      };

      socket.emit('sendChatMessage', message);
      setNewMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
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
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">League Chat</h1>
            <p className="text-gray-600">{currentLeague.name}</p>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-96">
        {/* Messages */}
        <div className="flex-1">
          <ChatFeed
            messages={messages}
            currentUserId={user?.uid || ''}
            loading={isLoading}
          />
        </div>

        {/* Message Input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              rows={2}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
            <button
              onClick={handleSendMessage}
              disabled={!newMessage.trim() || !isConnected}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
