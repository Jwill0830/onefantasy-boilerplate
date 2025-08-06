/**
 * Socket.IO service for real-time communication with the backend.
 */
import io, { Socket } from 'socket.io-client';
import { SocketEvents } from '../types';

class SocketService {
  private socket: Socket | null = null;
  private authToken: string | null = null;
  private connected = false;
  private eventHandlers: Map<string, Function[]> = new Map();

  constructor() {
    // Initialize event handlers map
    this.eventHandlers = new Map();
  }

  connect(authToken: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket && this.connected) {
        resolve();
        return;
      }

      this.authToken = authToken;
      const socketUrl = process.env.REACT_APP_SOCKET_URL || 'http://localhost:5000';

      this.socket = io(socketUrl, {
        auth: {
          token: authToken
        },
        transports: ['websocket', 'polling'],
        timeout: 10000,
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000
      });

      this.socket.on('connect', () => {
        console.log('Socket connected:', this.socket?.id);
        this.connected = true;
        this.setupEventHandlers();
        resolve();
      });

      this.socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
        this.connected = false;
        reject(error);
      });

      this.socket.on('disconnect', (reason) => {
        console.log('Socket disconnected:', reason);
        this.connected = false;
      });

      this.socket.on('reconnect', (attemptNumber) => {
        console.log('Socket reconnected after', attemptNumber, 'attempts');
        this.connected = true;
      });

      this.socket.on('reconnect_error', (error) => {
        console.error('Socket reconnection error:', error);
      });

      this.socket.on('error', (error) => {
        console.error('Socket error:', error);
        this.emit('error', error);
      });
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      this.eventHandlers.clear();
    }
  }

  private setupEventHandlers(): void {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connected', (data) => {
      console.log('Socket authentication successful:', data);
      this.emit('connected', data);
    });

    // League events
    this.socket.on('user_joined', (data) => {
      this.emit('user_joined', data);
    });

    this.socket.on('user_left', (data) => {
      this.emit('user_left', data);
    });

    // Draft events
    this.socket.on('draft_pick_made', (data) => {
      this.emit('draft_pick_made', data);
    });

    // Chat events
    this.socket.on('chat_message', (data) => {
      this.emit('chat_message', data);
    });

    // Trade events
    this.socket.on('trade_proposed', (data) => {
      this.emit('trade_proposed', data);
    });

    // Waiver events
    this.socket.on('waiver_claim_made', (data) => {
      this.emit('waiver_claim_made', data);
    });

    // Lineup events
    this.socket.on('lineup_updated', (data) => {
      this.emit('lineup_updated', data);
    });

    // Error events
    this.socket.on('error', (data) => {
      console.error('Socket server error:', data);
      this.emit('error', data);
    });
  }

  // Event emission methods
  joinLeague(leagueId: string): void {
    if (this.socket && this.connected) {
      this.socket.emit('join_league', { league_id: leagueId });
    }
  }

  leaveLeague(leagueId: string): void {
    if (this.socket && this.connected) {
      this.socket.emit('leave_league', { league_id: leagueId });
    }
  }

  makeDraftPick(leagueId: string, playerId: number, pickNumber: number): void {
    if (this.socket && this.connected) {
      this.socket.emit('draft_pick', {
        league_id: leagueId,
        player_id: playerId,
        pick_number: pickNumber
      });
    }
  }

  sendChatMessage(leagueId: string, message: string): void {
    if (this.socket && this.connected) {
      this.socket.emit('chat_message', {
        league_id: leagueId,
        message: message
      });
    }
  }

  proposeTrade(leagueId: string, toTeamId: string): void {
    if (this.socket && this.connected) {
      this.socket.emit('trade_proposal', {
        league_id: leagueId,
        to_team_id: toTeamId
      });
    }
  }

  submitWaiverClaim(leagueId: string, playerId: number, bidAmount: number): void {
    if (this.socket && this.connected) {
      this.socket.emit('waiver_claim', {
        league_id: leagueId,
        player_id: playerId,
        bid_amount: bidAmount
      });
    }
  }

  updateLineup(leagueId: string, teamId: string): void {
    if (this.socket && this.connected) {
      this.socket.emit('lineup_update', {
        league_id: leagueId,
        team_id: teamId
      });
    }
  }

  // Event listener methods
  on(event: string, handler: Function): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)?.push(handler);
  }

  off(event: string, handler?: Function): void {
    if (!this.eventHandlers.has(event)) return;

    if (handler) {
      const handlers = this.eventHandlers.get(event) || [];
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    } else {
      this.eventHandlers.delete(event);
    }
  }

  private emit(event: string, data: any): void {
    const handlers = this.eventHandlers.get(event) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error(`Error in socket event handler for ${event}:`, error);
      }
    });
  }

  // Utility methods
  isConnected(): boolean {
    return this.connected && this.socket?.connected === true;
  }

  getConnectionId(): string | undefined {
    return this.socket?.id;
  }

  // Typed event listeners for better TypeScript support
  onConnected(handler: (data: { status: string; user_id: string }) => void): void {
    this.on('connected', handler);
  }

  onUserJoined(handler: (data: { user_id: string; league_id: string }) => void): void {
    this.on('user_joined', handler);
  }

  onUserLeft(handler: (data: { user_id: string; league_id: string }) => void): void {
    this.on('user_left', handler);
  }

  onDraftPickMade(handler: (data: any) => void): void {
    this.on('draft_pick_made', handler);
  }

  onChatMessage(handler: (data: any) => void): void {
    this.on('chat_message', handler);
  }

  onTradeProposed(handler: (data: any) => void): void {
    this.on('trade_proposed', handler);
  }

  onWaiverClaimMade(handler: (data: any) => void): void {
    this.on('waiver_claim_made', handler);
  }

  onLineupUpdated(handler: (data: { league_id: string; team_id: string; user_id: string; timestamp: string }) => void): void {
    this.on('lineup_updated', handler);
  }

  onError(handler: (data: { message: string }) => void): void {
    this.on('error', handler);
  }

  // Remove typed event listeners
  offConnected(handler?: Function): void {
    this.off('connected', handler);
  }

  offUserJoined(handler?: Function): void {
    this.off('user_joined', handler);
  }

  offUserLeft(handler?: Function): void {
    this.off('user_left', handler);
  }

  offDraftPickMade(handler?: Function): void {
    this.off('draft_pick_made', handler);
  }

  offChatMessage(handler?: Function): void {
    this.off('chat_message', handler);
  }

  offTradeProposed(handler?: Function): void {
    this.off('trade_proposed', handler);
  }

  offWaiverClaimMade(handler?: Function): void {
    this.off('waiver_claim_made', handler);
  }

  offLineupUpdated(handler?: Function): void {
    this.off('lineup_updated', handler);
  }

  offError(handler?: Function): void {
    this.off('error', handler);
  }
}

// Create singleton instance
const socketService = new SocketService();

export default socketService;