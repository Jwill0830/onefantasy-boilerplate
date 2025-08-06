/**
 * Socket.IO hook and context for real-time communication.
 */
import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { useAuth } from './useAuth';
import socketService from '../services/socketService';
import toast from 'react-hot-toast';

interface SocketContextType {
  isConnected: boolean;
  connectionId: string | null;
  joinLeague: (leagueId: string) => void;
  leaveLeague: (leagueId: string) => void;
  sendChatMessage: (leagueId: string, message: string) => void;
  makeDraftPick: (leagueId: string, playerId: number, pickNumber: number) => void;
  updateLineup: (leagueId: string, teamId: string) => void;
  // Event handlers
  onDraftPickMade: (handler: (data: any) => void) => () => void;
  onChatMessage: (handler: (data: any) => void) => () => void;
  onUserJoined: (handler: (data: { user_id: string; league_id: string }) => void) => () => void;
  onUserLeft: (handler: (data: { user_id: string; league_id: string }) => void) => () => void;
  onTradeProposed: (handler: (data: any) => void) => () => void;
  onWaiverClaimMade: (handler: (data: any) => void) => () => void;
  onLineupUpdated: (handler: (data: any) => void) => () => void;
  onError: (handler: (data: { message: string }) => void) => () => void;
}

const SocketContext = createContext<SocketContextType | null>(null);

export const useSocket = (): SocketContextType => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};

interface SocketProviderProps {
  children: ReactNode;
}

export const SocketProvider: React.FC<SocketProviderProps> = ({ children }) => {
  const { firebaseUser, currentUser } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState<string | null>(null);

  useEffect(() => {
    const connectSocket = async () => {
      if (firebaseUser && currentUser) {
        try {
          const idToken = await firebaseUser.getIdToken();
          await socketService.connect(idToken);
          setIsConnected(true);
          setConnectionId(socketService.getConnectionId() || null);
        } catch (error) {
          console.error('Failed to connect socket:', error);
          setIsConnected(false);
          setConnectionId(null);
        }
      }
    };

    const disconnectSocket = () => {
      socketService.disconnect();
      setIsConnected(false);
      setConnectionId(null);
    };

    if (firebaseUser && currentUser) {
      connectSocket();
    } else {
      disconnectSocket();
    }

    // Setup global error handler
    const errorHandler = (data: { message: string }) => {
      toast.error(`Socket Error: ${data.message}`);
    };

    socketService.onError(errorHandler);

    return () => {
      socketService.offError(errorHandler);
      disconnectSocket();
    };
  }, [firebaseUser, currentUser]);

  // Socket methods
  const joinLeague = useCallback((leagueId: string) => {
    socketService.joinLeague(leagueId);
  }, []);

  const leaveLeague = useCallback((leagueId: string) => {
    socketService.leaveLeague(leagueId);
  }, []);

  const sendChatMessage = useCallback((leagueId: string, message: string) => {
    socketService.sendChatMessage(leagueId, message);
  }, []);

  const makeDraftPick = useCallback((leagueId: string, playerId: number, pickNumber: number) => {
    socketService.makeDraftPick(leagueId, playerId, pickNumber);
  }, []);

  const updateLineup = useCallback((leagueId: string, teamId: string) => {
    socketService.updateLineup(leagueId, teamId);
  }, []);

  // Event handler setup methods that return cleanup functions
  const onDraftPickMade = useCallback((handler: (data: any) => void) => {
    socketService.onDraftPickMade(handler);
    return () => socketService.offDraftPickMade(handler);
  }, []);

  const onChatMessage = useCallback((handler: (data: any) => void) => {
    socketService.onChatMessage(handler);
    return () => socketService.offChatMessage(handler);
  }, []);

  const onUserJoined = useCallback((handler: (data: { user_id: string; league_id: string }) => void) => {
    socketService.onUserJoined(handler);
    return () => socketService.offUserJoined(handler);
  }, []);

  const onUserLeft = useCallback((handler: (data: { user_id: string; league_id: string }) => void) => {
    socketService.onUserLeft(handler);
    return () => socketService.offUserLeft(handler);
  }, []);

  const onTradeProposed = useCallback((handler: (data: any) => void) => {
    socketService.onTradeProposed(handler);
    return () => socketService.offTradeProposed(handler);
  }, []);

  const onWaiverClaimMade = useCallback((handler: (data: any) => void) => {
    socketService.onWaiverClaimMade(handler);
    return () => socketService.offWaiverClaimMade(handler);
  }, []);

  const onLineupUpdated = useCallback((handler: (data: any) => void) => {
    socketService.onLineupUpdated(handler);
    return () => socketService.offLineupUpdated(handler);
  }, []);

  const onError = useCallback((handler: (data: { message: string }) => void) => {
    socketService.onError(handler);
    return () => socketService.offError(handler);
  }, []);

  const value: SocketContextType = {
    isConnected,
    connectionId,
    joinLeague,
    leaveLeague,
    sendChatMessage,
    makeDraftPick,
    updateLineup,
    onDraftPickMade,
    onChatMessage,
    onUserJoined,
    onUserLeft,
    onTradeProposed,
    onWaiverClaimMade,
    onLineupUpdated,
    onError
  };

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  );
};