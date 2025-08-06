/**
 * API service for making HTTP requests to the OneFantasy backend.
 */
import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import {
  User, League, Team, Player, PlayerSearchFilters, Trade, WaiverClaim,
  Matchup, Transaction, CreateLeagueForm, JoinLeagueForm, ApiResponse, PaginatedResponse
} from '../types';

class ApiService {
  private api: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000/api',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.clearAuthToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth methods
  setAuthToken(token: string): void {
    this.authToken = token;
  }

  clearAuthToken(): void {
    this.authToken = null;
  }

  // Authentication endpoints
  async verifyToken(idToken: string): Promise<ApiResponse<{ user: User; token_valid: boolean }>> {
    try {
      const response = await this.api.post('/auth/verify', { id_token: idToken });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getProfile(): Promise<ApiResponse<{ user: User }>> {
    try {
      const response = await this.api.get('/auth/profile');
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async updateProfile(data: Partial<User>): Promise<ApiResponse<{ user: User }>> {
    try {
      const response = await this.api.put('/auth/profile', data);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async logout(): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await this.api.post('/auth/logout');
      this.clearAuthToken();
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // League endpoints
  async createLeague(data: CreateLeagueForm): Promise<ApiResponse<{ league: League }>> {
    try {
      const response = await this.api.post('/leagues', data);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getLeague(leagueId: string): Promise<ApiResponse<{ league: League }>> {
    try {
      const response = await this.api.get(`/leagues/${leagueId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getUserLeagues(): Promise<ApiResponse<{ leagues: League[] }>> {
    try {
      const response = await this.api.get('/leagues');
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async updateLeague(leagueId: string, data: Partial<League>): Promise<ApiResponse<{ league: League }>> {
    try {
      const response = await this.api.put(`/leagues/${leagueId}`, data);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async joinLeague(data: JoinLeagueForm): Promise<ApiResponse<{ league: League; team: Team }>> {
    try {
      const response = await this.api.post('/leagues/join', data);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getLeagueTeams(leagueId: string): Promise<ApiResponse<{ teams: Team[] }>> {
    try {
      const response = await this.api.get(`/leagues/${leagueId}/teams`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getLeagueStandings(leagueId: string): Promise<ApiResponse<{ standings: Team[] }>> {
    try {
      const response = await this.api.get(`/leagues/${leagueId}/standings`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async startDraft(leagueId: string): Promise<ApiResponse<{ league: League }>> {
    try {
      const response = await this.api.post(`/leagues/${leagueId}/start-draft`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async deleteLeague(leagueId: string): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await this.api.delete(`/leagues/${leagueId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Team endpoints
  async getTeam(leagueId: string, teamId: string): Promise<ApiResponse<{ team: Team }>> {
    try {
      const response = await this.api.get(`/teams/${leagueId}/${teamId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async updateTeam(leagueId: string, teamId: string, data: Partial<Team>): Promise<ApiResponse<{ team: Team }>> {
    try {
      const response = await this.api.put(`/teams/${leagueId}/${teamId}`, data);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async updateRoster(leagueId: string, teamId: string, roster: { starters: number[]; bench: number[] }): Promise<ApiResponse<{ team: Team }>> {
    try {
      const response = await this.api.put(`/teams/${leagueId}/${teamId}/roster`, roster);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getTeamTransactions(leagueId: string, teamId: string): Promise<ApiResponse<{ transactions: Transaction[] }>> {
    try {
      const response = await this.api.get(`/teams/${leagueId}/${teamId}/transactions`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Player endpoints
  async searchPlayers(filters: PlayerSearchFilters, page = 1, perPage = 50): Promise<ApiResponse<PaginatedResponse<Player>>> {
    try {
      const params = { ...filters, page, per_page: perPage };
      const response = await this.api.get('/players/search', { params });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getPlayer(playerId: number): Promise<ApiResponse<{ player: Player }>> {
    try {
      const response = await this.api.get(`/players/${playerId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getTrendingPlayers(leagueId?: string, timeframe = 'week'): Promise<ApiResponse<{ players: Player[] }>> {
    try {
      const params = leagueId ? { league_id: leagueId, timeframe } : { timeframe };
      const response = await this.api.get('/players/trending', { params });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getPlayerLeaders(stat = 'total_points', position = '', limit = 20): Promise<ApiResponse<{ players: Player[] }>> {
    try {
      const params = { stat, position, limit };
      const response = await this.api.get('/players/leaders', { params });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getAvailablePlayers(leagueId: string, limit = 100): Promise<ApiResponse<{ players: Player[] }>> {
    try {
      const params = { league_id: leagueId, limit };
      const response = await this.api.get('/players/available', { params });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Draft endpoints
  async getDraftBoard(leagueId: string): Promise<ApiResponse<{ draft: any }>> {
    try {
      const response = await this.api.get(`/drafts/${leagueId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async makeDraftPick(leagueId: string, playerId: number): Promise<ApiResponse<{ pick: any }>> {
    try {
      const response = await this.api.post(`/drafts/${leagueId}/pick`, { player_id: playerId });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async runMockDraft(leagueId: string): Promise<ApiResponse<{ draft: any }>> {
    try {
      const response = await this.api.post(`/drafts/${leagueId}/mock`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Trade endpoints
  async getTeamTrades(leagueId: string, teamId: string): Promise<ApiResponse<{ trades: Trade[] }>> {
    try {
      const response = await this.api.get(`/trades/${leagueId}/${teamId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async proposeTrade(leagueId: string, tradeData: Partial<Trade>): Promise<ApiResponse<{ trade: Trade }>> {
    try {
      const response = await this.api.post(`/trades/${leagueId}`, tradeData);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async respondToTrade(leagueId: string, tradeId: string, action: 'accept' | 'reject'): Promise<ApiResponse<{ trade: Trade }>> {
    try {
      const response = await this.api.post(`/trades/${leagueId}/${tradeId}/${action}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getTradingBlock(leagueId: string): Promise<ApiResponse<{ players: any[] }>> {
    try {
      const response = await this.api.get(`/trades/${leagueId}/block`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Waiver endpoints
  async getWaiverClaims(leagueId: string, teamId: string): Promise<ApiResponse<{ claims: WaiverClaim[] }>> {
    try {
      const response = await this.api.get(`/waivers/${leagueId}/${teamId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async submitWaiverClaim(leagueId: string, claimData: Partial<WaiverClaim>): Promise<ApiResponse<{ claim: WaiverClaim }>> {
    try {
      const response = await this.api.post(`/waivers/${leagueId}`, claimData);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async cancelWaiverClaim(leagueId: string, claimId: string): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await this.api.delete(`/waivers/${leagueId}/${claimId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Matchup endpoints
  async getMatchups(leagueId: string, gameweek?: number): Promise<ApiResponse<{ matchups: Matchup[] }>> {
    try {
      const params = gameweek ? { gameweek } : {};
      const response = await this.api.get(`/matchups/${leagueId}`, { params });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getMatchup(leagueId: string, matchupId: string): Promise<ApiResponse<{ matchup: Matchup }>> {
    try {
      const response = await this.api.get(`/matchups/${leagueId}/${matchupId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Chat endpoints
  async getChatMessages(leagueId: string, limit = 50): Promise<ApiResponse<{ messages: any[] }>> {
    try {
      const params = { limit };
      const response = await this.api.get(`/chat/${leagueId}`, { params });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async sendChatMessage(leagueId: string, message: string): Promise<ApiResponse<{ message: any }>> {
    try {
      const response = await this.api.post(`/chat/${leagueId}`, { message });
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Admin endpoints (Commissioner only)
  async getAdminTools(leagueId: string): Promise<ApiResponse<{ tools: any }>> {
    try {
      const response = await this.api.get(`/admin/${leagueId}`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async updateLeagueSettings(leagueId: string, settings: any): Promise<ApiResponse<{ league: League }>> {
    try {
      const response = await this.api.put(`/admin/${leagueId}/settings`, settings);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async editTeamRoster(leagueId: string, teamId: string, roster: any): Promise<ApiResponse<{ team: Team }>> {
    try {
      const response = await this.api.put(`/admin/${leagueId}/teams/${teamId}/roster`, roster);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async processWaivers(leagueId: string): Promise<ApiResponse<{ results: any[] }>> {
    try {
      const response = await this.api.post(`/admin/${leagueId}/process-waivers`);
      return { data: response.data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Error handling
  private handleError(error: any): ApiResponse {
    if (error.response) {
      // Server responded with error status
      const { data, status } = error.response;
      return {
        error: data.error || `HTTP ${status}`,
        message: data.message,
        details: data.details
      };
    } else if (error.request) {
      // Request made but no response
      return {
        error: 'Network Error',
        message: 'Unable to connect to server'
      };
    } else {
      // Something else happened
      return {
        error: 'Request Error',
        message: error.message
      };
    }
  }
}

// Create singleton instance
const apiService = new ApiService();

export default apiService;