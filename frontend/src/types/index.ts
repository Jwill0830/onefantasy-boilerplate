/**
 * TypeScript type definitions for OneFantasy application.
 */

// User and Authentication Types
export interface User {
  uid: string;
  email: string;
  display_name: string;
  photo_url?: string;
  email_verified: boolean;
  created_at: string;
  last_login: string;
  preferences: UserPreferences;
  stats: UserStats;
}

export interface UserPreferences {
  notifications: {
    email: boolean;
    push: boolean;
    trades: boolean;
    waivers: boolean;
    draft: boolean;
    scoring: boolean;
  };
  theme: 'light' | 'dark';
  timezone: string;
}

export interface UserStats {
  leagues_joined: number;
  championships: number;
  total_trades: number;
  total_waiver_claims: number;
}

// League Types
export interface League {
  id: string;
  name: string;
  commissioner_id: string;
  invite_code: string;
  status: 'created' | 'drafting' | 'active' | 'completed';
  created_at: string;
  updated_at: string;
  settings: LeagueSettings;
  teams: Team[];
  draft_settings: DraftSettings;
  season_info: SeasonInfo;
  draft_order?: string[];
}

export interface LeagueSettings {
  league_size: number;
  roster_size: number;
  starting_lineup_size: number;
  pick_time_seconds: number;
  waiver_budget: number;
  trade_deadline?: string;
  playoff_teams: number;
  playoff_weeks: number[];
  scoring_settings: ScoringSettings;
  draft_order_type: 'snake' | 'linear';
}

export interface ScoringSettings {
  goals_scored: {
    GK: number;
    DEF: number;
    MID: number;
    FWD: number;
  };
  assists: number;
  clean_sheets: {
    GK: number;
    DEF: number;
    MID: number;
    FWD: number;
  };
  saves: number;
  penalty_saves: number;
  penalty_misses: number;
  yellow_cards: number;
  red_cards: number;
  own_goals: number;
  goals_conceded: {
    GK: number;
    DEF: number;
    MID: number;
    FWD: number;
  };
  bonus_points: number;
  minutes_played: {
    '60_plus': number;
    '1_to_59': number;
    '0': number;
  };
}

export interface DraftSettings {
  scheduled_time?: string;
  started_at?: string;
  completed_at?: string;
  current_pick: number;
  current_round: number;
  auto_pick_enabled: boolean;
}

export interface SeasonInfo {
  current_gameweek: number;
  total_gameweeks: number;
  regular_season_weeks: number;
  playoff_weeks: number[];
}

// Team Types
export interface Team {
  id: string;
  league_id: string;
  owner_id: string;
  name: string;
  logo_url?: string;
  created_at: string;
  updated_at: string;
  roster: Roster;
  draft_picks: DraftPick[];
  stats: TeamStats;
  settings: TeamSettings;
  waiver_budget: number;
  waiver_position: number;
  draft_position: number;
  rank?: number;
  // Add record property for wins/losses tracking
  record?: {
    wins: number;
    losses: number;
    ties: number;
    points_for: number;
    points_against: number;
    max_points_for: number;
  };
}

export interface Roster {
  starters: number[];
  bench: number[];
  injured_reserve: number[];
}

export interface TeamStats {
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  points_against: number;
  max_points_for: number;
  waiver_claims: number;
  trades_completed: number;
}

export interface TeamSettings {
  auto_set_lineup: boolean;
  notifications: {
    trades: boolean;
    waivers: boolean;
    draft: boolean;
    scoring: boolean;
    news: boolean;
  };
  co_owners: string[];
}

// Player Types
export interface Player {
  id: number;
  name: string;
  web_name: string;
  first_name: string;
  second_name: string;
  position: string;
  position_short: 'GK' | 'DEF' | 'MID' | 'FWD';
  team: string;
  team_short: string;
  team_id: number;
  total_points: number;
  points_per_game: number;
  form: number;
  selected_by_percent: number;
  now_cost: number;
  cost_change_start: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  goals_conceded: number;
  saves: number;
  yellow_cards: number;
  red_cards: number;
  minutes: number;
  bonus: number;
  bps: number;
  influence: number;
  creativity: number;
  threat: number;
  ict_index: number;
  status: string;
  news: string;
  photo_url?: string;
  last_updated: string;
  trend_data?: {
    net_adds: number;
    total_adds: number;
    total_drops: number;
  };
}

export interface PlayerSearchFilters {
  query?: string;
  position?: string;
  team?: string;
  available_only?: boolean;
  min_points?: number;
  max_cost?: number;
  sort_by?: 'total_points' | 'points_per_game' | 'form' | 'now_cost';
  sort_order?: 'asc' | 'desc';
}

// Draft Types
export interface DraftPick {
  id: string;
  league_id: string;
  team_id: string;
  player_id: number;
  pick_number: number;
  round: number;
  timestamp: string;
  is_auto_pick: boolean;
}

export interface DraftBoard {
  picks: DraftPick[];
  current_pick: number;
  current_round: number;
  total_rounds: number;
  teams: Team[];
  draft_order: string[];
}

// Transaction Types
export interface Transaction {
  id: string;
  league_id: string;
  team_id: string;
  type: 'draft' | 'trade' | 'waiver_claim' | 'free_agent_add' | 'drop';
  player_id?: number;
  details: any;
  timestamp: string;
  status: 'pending' | 'completed' | 'rejected';
}

export interface Trade {
  id: string;
  league_id: string;
  from_team_id: string;
  to_team_id: string;
  from_players: number[];
  to_players: number[];
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
  proposed_at: string;
  expires_at: string;
  message?: string;
}

export interface WaiverClaim {
  id: string;
  league_id: string;
  team_id: string;
  player_id: number;
  drop_player_id?: number;
  bid_amount: number;
  priority: number;
  status: 'pending' | 'successful' | 'failed';
  claimed_at: string;
  processed_at?: string;
}

// Matchup Types
export interface Matchup {
  id: string;
  league_id: string;
  gameweek: number;
  team1_id: string;
  team2_id: string;
  team1_score?: number;
  team2_score?: number;
  team1_lineup?: number[];
  team2_lineup?: number[];
  status: 'upcoming' | 'active' | 'completed';
  starts_at: string;
}

// Lineup Types (ADDED for RosterDragDrop component)
export interface Lineup {
  starting_11: number[];
  bench: number[];
  captain: number;
  vice_captain: number;
}

// Playoff Types
export interface PlayoffMatchup {
  id: string;
  league_id: string;
  team1Id: string;
  team2Id: string;
  week: number;
  round: 'quarterfinals' | 'semifinals' | 'finals';
  team1Score: number | null;
  team2Score: number | null;
  winner: string | null;
  completedAt: string | null;
  scheduledDate: string;
  bracket: 'winners' | 'losers';
}

export interface PlayoffBracket {
  id: string;
  leagueId: string;
  teams: string[]; // Array of team IDs that made playoffs
  matchups: PlayoffMatchup[];
  status: 'upcoming' | 'active' | 'completed';
  createdAt: string;
  updatedAt: string;
  settings: {
    format: 'single_elimination' | 'double_elimination';
    playoffTeams: number;
    championshipWeek: number;
  };
}

// Chat Types
export interface ChatMessage {
  id: string;
  league_id: string;
  user_id: string;
  user_name: string;
  message: string;
  timestamp: string;
  type: 'message' | 'trade' | 'draft' | 'system';
}

// News Types
export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  content: string;
  category: 'injury' | 'transfer' | 'suspension' | 'lineup' | 'general';
  player_ids?: number[];
  team_ids?: number[];
  published_at: string;
  source: string;
  url?: string;
}

// Mock Draft Types
export interface MockDraft {
  id: string;
  user_id: string;
  league_settings: LeagueSettings;
  picks: DraftPick[];
  completed_at: string;
  teams: {
    id: string;
    name: string;
    is_user: boolean;
    roster: number[];
  }[];
}

// API Response Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  details?: string[];
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

// Socket Event Types
export interface SocketEvents {
  // Connection events
  connect: () => void;
  disconnect: () => void;
  connected: (data: { status: string; user_id: string }) => void;
  
  // League events
  join_league: (data: { league_id: string }) => void;
  leave_league: (data: { league_id: string }) => void;
  user_joined: (data: { user_id: string; league_id: string }) => void;
  user_left: (data: { user_id: string; league_id: string }) => void;
  
  // Draft events
  draft_pick: (data: { league_id: string; player_id: number; pick_number: number }) => void;
  draft_pick_made: (data: DraftPick) => void;
  
  // Chat events
  chat_message: (data: { league_id: string; message: string }) => void;
  new_chat_message: (data: ChatMessage) => void;
  
  // Trade events
  trade_proposal: (data: { league_id: string; to_team_id: string }) => void;
  trade_proposed: (data: Trade) => void;
  trade_updated: (data: Trade) => void;
  
  // Waiver events
  waiver_claim: (data: { league_id: string; player_id: number; bid_amount: number }) => void;
  waiver_claim_made: (data: WaiverClaim) => void;
  waiver_processed: (data: { league_id: string; claims: WaiverClaim[] }) => void;
  
  // Lineup events
  lineup_update: (data: { league_id: string; team_id: string }) => void;
  lineup_updated: (data: { league_id: string; team_id: string; user_id: string; timestamp: string }) => void;
  
  // Playoff events
  playoff_matchup_updated: (data: PlayoffMatchup) => void;
  playoff_bracket_updated: (data: PlayoffBracket) => void;
  
  // Error events
  error: (data: { message: string }) => void;
}

// Form Types
export interface CreateLeagueForm {
  name: string;
  league_size: number;
  draft_time?: string;
  pick_time_seconds: number;
  waiver_budget: number;
}

export interface JoinLeagueForm {
  invite_code: string;
  team_name: string;
  team_logo_url?: string;
}

export interface LineupFormation {
  GK: number[];
  DEF: number[];
  MID: number[];
  FWD: number[];
}

export interface TradeProposalForm {
  to_team_id: string;
  from_players: number[];
  to_players: number[];
  message?: string;
}

export interface WaiverClaimForm {
  player_id: number;
  drop_player_id?: number;
  bid_amount: number;
}

export interface TeamSettingsForm {
  team_name: string;
  logo_url?: string;
  notifications: {
    trades: boolean;
    waivers: boolean;
    draft: boolean;
    scoring: boolean;
    news: boolean;
  };
  auto_set_lineup: boolean;
}

// UI State Types
export interface DraftState {
  isActive: boolean;
  currentPick: number;
  currentRound: number;
  timeRemaining: number;
  isMyTurn: boolean;
  availablePlayers: Player[];
  draftBoard: DraftPick[][];
  queuedPlayers: Player[];
}

export interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
}

export interface Notification {
  id: string;
  type: 'trade' | 'waiver' | 'draft' | 'scoring' | 'general';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  league_id?: string;
}

// Filter and Search Types
export interface LeaderboardFilters {
  position?: PlayerPosition;
  timeframe: 'season' | 'week_1' | 'week_2' | 'week_3' | 'recent';
  sort_by: 'total_points' | 'average_points' | 'form' | 'selected_by_percent';
  team_filter?: string;
}

export interface TrendingPlayer {
  player: Player;
  net_transfers: number;
  ownership_change: number;
  trending_direction: 'up' | 'down' | 'stable';
}

export interface AvailablePlayersFilters extends PlayerSearchFilters {
  show_rostered?: boolean;
  min_form?: number;
  max_ownership?: number;
  injury_status?: 'available' | 'doubtful' | 'injured' | 'suspended';
}

// Transaction History Types
export interface TransactionHistoryItem {
  id: string;
  type: 'draft' | 'trade' | 'waiver_add' | 'waiver_drop' | 'free_agent_add' | 'free_agent_drop';
  players_involved: Player[];
  teams_involved?: Team[];
  timestamp: string;
  details: string;
  success: boolean;
}

// Standings Types
export interface StandingsRow {
  team: Team;
  rank: number;
  record: {
    wins: number;
    losses: number;
    ties: number;
  };
  points_for: number;
  points_against: number;
  max_points_for: number;
  waiver_position: number;
  waiver_budget: number;
}

// Utility Types
export type TabType = 'draft' | 'my-team' | 'players' | 'league' | 'playoffs' | 'chat' | 'admin';

export type PlayerPosition = 'GK' | 'DEF' | 'MID' | 'FWD';

export type LeagueStatus = 'created' | 'drafting' | 'active' | 'completed';

export type TradeStatus = 'pending' | 'accepted' | 'rejected' | 'expired';

export type MatchupStatus = 'upcoming' | 'active' | 'completed';

export type PlayoffRound = 'quarterfinals' | 'semifinals' | 'finals';

export type BracketType = 'winners' | 'losers';

export type SortDirection = 'asc' | 'desc';

export type PlayerTab = 'search' | 'available' | 'trending' | 'leaders' | 'trade_block';

export type NotificationType = 'trade' | 'waiver' | 'draft' | 'scoring' | 'general' | 'injury' | 'news';

// Component Props Types
export interface PlayerCardProps {
  player: Player;
  showDraftButton?: boolean;
  showAddDropButton?: boolean;
  showTradeButton?: boolean;
  onDraft?: (playerId: number) => void;
  onAdd?: (playerId: number) => void;
  onDrop?: (playerId: number) => void;
  onTrade?: (playerId: number) => void;
  compact?: boolean;
  selected?: boolean;
}

export interface SearchFilterProps {
  filters: PlayerSearchFilters;
  onFiltersChange: (filters: PlayerSearchFilters) => void;
  availablePositions: PlayerPosition[];
  availableTeams: string[];
}

export interface CountdownTimerProps {
  targetDate: string;
  onComplete?: () => void;
  showDays?: boolean;
  compact?: boolean;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

// Context Types
export interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName: string) => Promise<void>;
  signOut: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
}

export interface LeagueContextType {
  currentLeague: League | null;
  userTeam: Team | null;
  loading: boolean;
  error: string | null;
  refreshLeague: () => Promise<void>;
  updateTeam: (updates: Partial<Team>) => Promise<void>;
}

// Socket Context Type (ADDED - was missing)
export interface SocketContextType {
  socket: any; // Socket.IO client instance
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
  joinRoom: (roomId: string) => void;
  leaveRoom: (roomId: string) => void;
}

// Constants
export const PLAYER_POSITIONS: PlayerPosition[] = ['GK', 'DEF', 'MID', 'FWD'];

export const ROSTER_REQUIREMENTS = {
  GK: { min: 1, max: 2 },
  DEF: { min: 3, max: 5 },
  MID: { min: 3, max: 5 },
  FWD: { min: 1, max: 3 }
};

export const DEFAULT_LEAGUE_SETTINGS: Partial<LeagueSettings> = {
  league_size: 10,
  roster_size: 15,
  starting_lineup_size: 11,
  pick_time_seconds: 90,
  waiver_budget: 100,
  playoff_teams: 4,
  draft_order_type: 'snake'
};