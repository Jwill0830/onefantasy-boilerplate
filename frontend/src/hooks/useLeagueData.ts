import { useState, useEffect, useCallback } from 'react';
import { League, Team, LeagueSettings, StandingsData, MatchupData } from '../types';
import { apiClient } from '../services/api';
import { useAuth } from './useAuth';
import { useSocket } from './useSocket';

interface LeagueDataState {
  league: League | null;
  teams: Team[];
  standings: StandingsData | null;
  matchups: MatchupData[];
  settings: LeagueSettings | null;
  loading: boolean;
  error: string | null;
}

interface UseLeagueDataReturn extends LeagueDataState {
  fetchLeague: (leagueId: string) => Promise<void>;
  fetchTeams: (leagueId: string) => Promise<void>;
  fetchStandings: (leagueId: string) => Promise<void>;
  fetchMatchups: (leagueId: string, gameweek?: number) => Promise<void>;
  fetchSettings: (leagueId: string) => Promise<void>;
  updateSettings: (leagueId: string, newSettings: Partial<LeagueSettings>) => Promise<void>;
  joinLeague: (leagueId: string, inviteCode: string) => Promise<void>;
  createLeague: (leagueData: Partial<League>) => Promise<League>;
  refreshLeagueData: (leagueId: string) => Promise<void>;
  isCommissioner: boolean;
  userTeam: Team | null;
}

export const useLeagueData = (leagueId?: string): UseLeagueDataReturn => {
  const { user } = useAuth();
  const { socket } = useSocket();

  const [state, setState] = useState<LeagueDataState>({
    league: null,
    teams: [],
    standings: null,
    matchups: [],
    settings: null,
    loading: false,
    error: null,
  });

  // Computed values
  const isCommissioner = state.league?.commissioner_id === user?.uid;
  const userTeam = state.teams.find(team => team.owner_id === user?.uid) || null;

  // Update state helper
  const updateState = useCallback((updates: Partial<LeagueDataState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  // Set loading state
  const setLoading = useCallback((loading: boolean) => {
    updateState({ loading, error: null });
  }, [updateState]);

  // Set error state
  const setError = useCallback((error: string) => {
    updateState({ loading: false, error });
  }, [updateState]);

  // Fetch league data
  const fetchLeague = useCallback(async (leagueId: string) => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/leagues/${leagueId}`);
      
      if (response.data.success) {
        updateState({
          league: response.data.league,
          loading: false,
        });
      } else {
        setError(response.data.error || 'Failed to fetch league');
      }
    } catch (error) {
      console.error('Error fetching league:', error);
      setError('Failed to fetch league data');
    }
  }, [setLoading, setError, updateState]);

  // Fetch teams data
  const fetchTeams = useCallback(async (leagueId: string) => {
    try {
      const response = await apiClient.get(`/leagues/${leagueId}/teams`);
      
      if (response.data.success) {
        updateState({
          teams: response.data.teams || [],
        });
      } else {
        setError(response.data.error || 'Failed to fetch teams');
      }
    } catch (error) {
      console.error('Error fetching teams:', error);
      setError('Failed to fetch teams data');
    }
  }, [setError, updateState]);

  // Fetch standings data
  const fetchStandings = useCallback(async (leagueId: string) => {
    try {
      const response = await apiClient.get(`/leagues/${leagueId}/standings`);
      
      if (response.data.success) {
        updateState({
          standings: response.data.standings,
        });
      } else {
        setError(response.data.error || 'Failed to fetch standings');
      }
    } catch (error) {
      console.error('Error fetching standings:', error);
      setError('Failed to fetch standings data');
    }
  }, [setError, updateState]);

  // Fetch matchups data
  const fetchMatchups = useCallback(async (leagueId: string, gameweek?: number) => {
    try {
      const url = gameweek 
        ? `/leagues/${leagueId}/matchups?gameweek=${gameweek}`
        : `/leagues/${leagueId}/matchups`;
        
      const response = await apiClient.get(url);
      
      if (response.data.success) {
        updateState({
          matchups: response.data.matchups || [],
        });
      } else {
        setError(response.data.error || 'Failed to fetch matchups');
      }
    } catch (error) {
      console.error('Error fetching matchups:', error);
      setError('Failed to fetch matchups data');
    }
  }, [setError, updateState]);

  // Fetch league settings
  const fetchSettings = useCallback(async (leagueId: string) => {
    try {
      const response = await apiClient.get(`/leagues/${leagueId}/settings`);
      
      if (response.data.success) {
        updateState({
          settings: response.data.settings,
        });
      } else {
        setError(response.data.error || 'Failed to fetch settings');
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      setError('Failed to fetch league settings');
    }
  }, [setError, updateState]);

  // Update league settings (commissioner only)
  const updateSettings = useCallback(async (leagueId: string, newSettings: Partial<LeagueSettings>) => {
    if (!isCommissioner) {
      setError('Only the commissioner can update league settings');
      return;
    }

    try {
      setLoading(true);
      const response = await apiClient.put(`/leagues/${leagueId}/settings`, newSettings);
      
      if (response.data.success) {
        updateState({
          settings: { ...state.settings, ...newSettings } as LeagueSettings,
          loading: false,
        });
      } else {
        setError(response.data.error || 'Failed to update settings');
      }
    } catch (error) {
      console.error('Error updating settings:', error);
      setError('Failed to update league settings');
    }
  }, [isCommissioner, setLoading, setError, updateState, state.settings]);

  // Join league with invite code
  const joinLeague = useCallback(async (leagueId: string, inviteCode: string) => {
    try {
      setLoading(true);
      const response = await apiClient.post(`/leagues/${leagueId}/join`, {
        invite_code: inviteCode,
      });
      
      if (response.data.success) {
        // Refresh league data after joining
        await Promise.all([
          fetchLeague(leagueId),
          fetchTeams(leagueId),
        ]);
      } else {
        setError(response.data.error || 'Failed to join league');
      }
    } catch (error) {
      console.error('Error joining league:', error);
      setError('Failed to join league');
    }
  }, [setLoading, setError, fetchLeague, fetchTeams]);

  // Create new league
  const createLeague = useCallback(async (leagueData: Partial<League>): Promise<League> => {
    try {
      setLoading(true);
      const response = await apiClient.post('/leagues', leagueData);
      
      if (response.data.success) {
        const newLeague = response.data.league;
        updateState({
          league: newLeague,
          loading: false,
        });
        return newLeague;
      } else {
        setError(response.data.error || 'Failed to create league');
        throw new Error(response.data.error || 'Failed to create league');
      }
    } catch (error) {
      console.error('Error creating league:', error);
      setError('Failed to create league');
      throw error;
    }
  }, [setLoading, setError, updateState]);

  // Refresh all league data
  const refreshLeagueData = useCallback(async (leagueId: string) => {
    try {
      setLoading(true);
      await Promise.all([
        fetchLeague(leagueId),
        fetchTeams(leagueId),
        fetchStandings(leagueId),
        fetchMatchups(leagueId),
        fetchSettings(leagueId),
      ]);
    } catch (error) {
      console.error('Error refreshing league data:', error);
      setError('Failed to refresh league data');
    } finally {
      updateState({ loading: false });
    }
  }, [setLoading, setError, updateState, fetchLeague, fetchTeams, fetchStandings, fetchMatchups, fetchSettings]);

  // Socket event handlers
  useEffect(() => {
    if (!socket || !leagueId) return;

    const handleLeagueUpdate = (data: { league_id: string; league: League }) => {
      if (data.league_id === leagueId) {
        updateState({ league: data.league });
      }
    };

    const handleTeamsUpdate = (data: { league_id: string; teams: Team[] }) => {
      if (data.league_id === leagueId) {
        updateState({ teams: data.teams });
      }
    };

    const handleStandingsUpdate = (data: { league_id: string; standings: StandingsData }) => {
      if (data.league_id === leagueId) {
        updateState({ standings: data.standings });
      }
    };

    const handleMatchupsUpdate = (data: { league_id: string; matchups: MatchupData[] }) => {
      if (data.league_id === leagueId) {
        updateState({ matchups: data.matchups });
      }
    };

    const handleSettingsUpdate = (data: { league_id: string; settings: LeagueSettings }) => {
      if (data.league_id === leagueId) {
        updateState({ settings: data.settings });
      }
    };

    // Listen for real-time updates
    socket.on('league_updated', handleLeagueUpdate);
    socket.on('teams_updated', handleTeamsUpdate);
    socket.on('standings_updated', handleStandingsUpdate);
    socket.on('matchups_updated', handleMatchupsUpdate);
    socket.on('league_settings_updated', handleSettingsUpdate);

    // Join league room for real-time updates
    socket.emit('join_league', { league_id: leagueId });

    return () => {
      socket.off('league_updated', handleLeagueUpdate);
      socket.off('teams_updated', handleTeamsUpdate);
      socket.off('standings_updated', handleStandingsUpdate);
      socket.off('matchups_updated', handleMatchupsUpdate);
      socket.off('league_settings_updated', handleSettingsUpdate);
      
      // Leave league room
      socket.emit('leave_league', { league_id: leagueId });
    };
  }, [socket, leagueId, updateState]);

  // Auto-fetch league data when leagueId changes
  useEffect(() => {
    if (leagueId && user) {
      refreshLeagueData(leagueId);
    }
  }, [leagueId, user, refreshLeagueData]);

  // Reset state when user logs out
  useEffect(() => {
    if (!user) {
      setState({
        league: null,
        teams: [],
        standings: null,
        matchups: [],
        settings: null,
        loading: false,
        error: null,
      });
    }
  }, [user]);

  return {
    // State
    league: state.league,
    teams: state.teams,
    standings: state.standings,
    matchups: state.matchups,
    settings: state.settings,
    loading: state.loading,
    error: state.error,
    
    // Actions
    fetchLeague,
    fetchTeams,
    fetchStandings,
    fetchMatchups,
    fetchSettings,
    updateSettings,
    joinLeague,
    createLeague,
    refreshLeagueData,
    
    // Computed values
    isCommissioner,
    userTeam,
  };
};