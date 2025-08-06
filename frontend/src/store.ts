// frontend/src/store.ts
import { createContext, useContext, useReducer, ReactNode } from 'react';
import { User, League, Team, Player, DraftState, DraftPick } from './types';

// Define NotificationState locally since it's causing import issues
interface NotificationState {
  trades: boolean;
  waivers: boolean;
  lineupReminders: boolean;
  news: boolean;
  scores: boolean;
}

// State interface
interface AppState {
  user: User | null;
  currentLeague: League | null;
  userTeam: Team | null;
  draftState: DraftState | null;
  availablePlayers: Player[];
  notifications: NotificationState;
  loading: {
    user: boolean;
    league: boolean;
    players: boolean;
    draft: boolean;
  };
  error: string | null;
}

// Action types
type AppAction =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_CURRENT_LEAGUE'; payload: League | null }
  | { type: 'SET_USER_TEAM'; payload: Team | null }
  | { type: 'SET_DRAFT_STATE'; payload: DraftState | null }
  | { type: 'SET_AVAILABLE_PLAYERS'; payload: Player[] }
  | { type: 'UPDATE_PLAYER'; payload: Player }
  | { type: 'SET_NOTIFICATIONS'; payload: NotificationState }
  | { type: 'SET_LOADING'; payload: { key: keyof AppState['loading']; value: boolean } }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'UPDATE_TEAM_ROSTER'; payload: { teamId: string; roster: Player[] } }
  | { type: 'ADD_DRAFT_PICK'; payload: { teamId: string; player: Player; pick: number } }
  | { type: 'RESET_STATE' };

// Initial state
const initialState: AppState = {
  user: null,
  currentLeague: null,
  userTeam: null,
  draftState: null,
  availablePlayers: [],
  notifications: {
    trades: true,
    waivers: true,
    lineupReminders: true,
    news: true,
    scores: true
  },
  loading: {
    user: false,
    league: false,
    players: false,
    draft: false
  },
  error: null
};

// Reducer function
const appReducer = (state: AppState, action: AppAction): AppState => {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };

    case 'SET_CURRENT_LEAGUE':
      return { ...state, currentLeague: action.payload };

    case 'SET_USER_TEAM':
      return { ...state, userTeam: action.payload };

    case 'SET_DRAFT_STATE':
      return { ...state, draftState: action.payload };

    case 'SET_AVAILABLE_PLAYERS':
      return { ...state, availablePlayers: action.payload };

    case 'UPDATE_PLAYER':
      return {
        ...state,
        availablePlayers: state.availablePlayers.map(player =>
          player.id === action.payload.id ? action.payload : player
        )
      };

    case 'SET_NOTIFICATIONS':
      return { ...state, notifications: action.payload };

    case 'SET_LOADING':
      return {
        ...state,
        loading: { ...state.loading, [action.payload.key]: action.payload.value }
      };

    case 'SET_ERROR':
      return { ...state, error: action.payload };

    case 'UPDATE_TEAM_ROSTER':
      return {
        ...state,
        currentLeague: state.currentLeague ? {
          ...state.currentLeague,
          teams: state.currentLeague.teams.map(team =>
            team.id === action.payload.teamId
              ? { ...team, roster: { starters: action.payload.roster.map(p => p.id), bench: [], injured_reserve: [] } }
              : team
          )
        } : null,
        userTeam: state.userTeam?.id === action.payload.teamId
          ? { ...state.userTeam, roster: { starters: action.payload.roster.map(p => p.id), bench: [], injured_reserve: [] } }
          : state.userTeam
      };

    case 'ADD_DRAFT_PICK':
      const { teamId, player, pick } = action.payload;
      
      return {
        ...state,
        // Update available players
        availablePlayers: state.availablePlayers.map(p =>
          p.id === player.id ? { ...p, selected_by_percent: p.selected_by_percent + 1 } : p
        ),
        // Update team roster
        currentLeague: state.currentLeague ? {
          ...state.currentLeague,
          teams: state.currentLeague.teams.map(team =>
            team.id === teamId
              ? { 
                  ...team, 
                  roster: { 
                    starters: [...team.roster.starters, player.id], 
                    bench: team.roster.bench, 
                    injured_reserve: team.roster.injured_reserve 
                  } 
                }
              : team
          )
        } : null,
        // Update user team if it's the user's pick
        userTeam: state.userTeam?.id === teamId
          ? { 
              ...state.userTeam, 
              roster: { 
                starters: [...state.userTeam.roster.starters, player.id], 
                bench: state.userTeam.roster.bench, 
                injured_reserve: state.userTeam.roster.injured_reserve 
              } 
            }
          : state.userTeam,
        // Update draft state
        draftState: state.draftState ? {
          ...state.draftState,
          currentPick: pick + 1,
          draftBoard: state.draftState.draftBoard.map((round, roundIndex) => {
            const currentRound = Math.ceil(pick / (state.currentLeague?.teams.length || 1)) - 1;
            if (roundIndex === currentRound) {
              return [
                ...round,
                {
                  id: `pick-${pick}`,
                  league_id: state.currentLeague?.id || '',
                  team_id: teamId,
                  player_id: player.id,
                  round: currentRound + 1,
                  pick_number: pick,
                  pick_in_round: ((pick - 1) % (state.currentLeague?.teams.length || 1)) + 1,
                  timestamp: new Date().toISOString()
                }
              ];
            }
            return round;
          })
        } : null
      };

    case 'RESET_STATE':
      return initialState;

    default:
      return state;
  }
};

// Context type
interface AppContextType {
  state: AppState;
  dispatch: (action: AppAction) => void;
}

// Context
const AppContext = createContext<AppContextType | undefined>(undefined);

// Provider component
interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

// Hook to use the context
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

// Action creators (helper functions)
export const actions = {
  setUser: (user: User | null): AppAction => ({ type: 'SET_USER', payload: user }),
  
  setCurrentLeague: (league: League | null): AppAction => ({ 
    type: 'SET_CURRENT_LEAGUE', 
    payload: league 
  }),
  
  setUserTeam: (team: Team | null): AppAction => ({ type: 'SET_USER_TEAM', payload: team }),
  
  setDraftState: (draftState: DraftState | null): AppAction => ({ 
    type: 'SET_DRAFT_STATE', 
    payload: draftState 
  }),
  
  setAvailablePlayers: (players: Player[]): AppAction => ({ 
    type: 'SET_AVAILABLE_PLAYERS', 
    payload: players 
  }),
  
  updatePlayer: (player: Player): AppAction => ({ type: 'UPDATE_PLAYER', payload: player }),
  
  setNotifications: (notifications: NotificationState): AppAction => ({ 
    type: 'SET_NOTIFICATIONS', 
    payload: notifications 
  }),
  
  setLoading: (key: keyof AppState['loading'], value: boolean): AppAction => ({ 
    type: 'SET_LOADING', 
    payload: { key, value } 
  }),
  
  setError: (error: string | null): AppAction => ({ type: 'SET_ERROR', payload: error }),
  
  updateTeamRoster: (teamId: string, roster: Player[]): AppAction => ({ 
    type: 'UPDATE_TEAM_ROSTER', 
    payload: { teamId, roster } 
  }),
  
  addDraftPick: (teamId: string, player: Player, pick: number): AppAction => ({ 
    type: 'ADD_DRAFT_PICK', 
    payload: { teamId, player, pick } 
  }),
  
  resetState: (): AppAction => ({ type: 'RESET_STATE' })
};

// Helper function to check if player is available
const isPlayerAvailable = (player: Player, allPlayers: Player[]): boolean => {
  return allPlayers.some(p => p.id === player.id);
};

// Selectors (helper functions to get derived state)
export const selectors = {
  getCurrentUser: (state: AppState) => state.user,
  
  getCurrentLeague: (state: AppState) => state.currentLeague,
  
  getUserTeam: (state: AppState) => state.userTeam,
  
  getAvailablePlayers: (state: AppState) => 
    state.availablePlayers.filter(p => isPlayerAvailable(p, state.availablePlayers)),
  
  getDraftedPlayers: (state: AppState) => 
    state.availablePlayers.filter(p => !isPlayerAvailable(p, state.availablePlayers)),
  
  getTeamRoster: (state: AppState, teamId: string): Player[] => {
    const team = state.currentLeague?.teams.find(t => t.id === teamId);
    if (!team) return [];
    
    // Get players from availablePlayers array using roster IDs
    return team.roster.starters
      .map(playerId => state.availablePlayers.find(p => p.id === playerId))
      .filter((player): player is Player => player !== undefined);
  },
  
  getCurrentDraftPick: (state: AppState) => state.draftState?.currentPick || 1,
  
  getCurrentDraftTeam: (state: AppState) => {
    if (!state.draftState || !state.currentLeague) return null;
    
    const currentPick = state.draftState.currentPick;
    const teamCount = state.currentLeague.teams.length;
    const round = Math.ceil(currentPick / teamCount);
    const isSnake = round % 2 === 0;
    const positionInRound = ((currentPick - 1) % teamCount);
    const teamIndex = isSnake ? teamCount - 1 - positionInRound : positionInRound;
    
    return state.currentLeague.teams[teamIndex] || null;
  },
  
  isUserTurn: (state: AppState) => {
    const currentTeam = selectors.getCurrentDraftTeam(state);
    return currentTeam?.id === state.userTeam?.id;
  },
  
  getLeagueStandings: (state: AppState) => {
    if (!state.currentLeague) return [];
    
    return [...state.currentLeague.teams].sort((a, b) => {
      // Sort by stats if available
      const aWins = a.stats?.wins || 0;
      const bWins = b.stats?.wins || 0;
      const aPointsFor = a.stats?.points_for || 0;
      const bPointsFor = b.stats?.points_for || 0;
      
      if (aWins !== bWins) return bWins - aWins;
      return bPointsFor - aPointsFor;
    });
  },
  
  getPlayersByPosition: (state: AppState, position: string) => 
    state.availablePlayers.filter(p => p.position === position && isPlayerAvailable(p, state.availablePlayers)),
  
  getTopPerformers: (state: AppState, limit: number = 10) => 
    [...state.availablePlayers]
      .filter(p => isPlayerAvailable(p, state.availablePlayers))
      .sort((a, b) => (b.total_points || 0) - (a.total_points || 0))
      .slice(0, limit),
  
  getRecentTransactions: (state: AppState, limit: number = 5) => {
    // This would need to be implemented when transaction data is available
    return [];
  }
};