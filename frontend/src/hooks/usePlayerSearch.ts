/**
 * Custom hook for player search functionality
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import { Player, PlayerFilters, TrendingPlayer } from '../types';

interface PlayerSearchState {
  players: Player[];
  trendingPlayers: TrendingPlayer[];
  trackedPlayers: Player[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  totalCount: number;
}

interface UsePlayerSearchReturn extends PlayerSearchState {
  searchPlayers: (query: string, filters?: PlayerFilters) => Promise<void>;
  getTrendingPlayers: (metric?: string, timeframe?: string) => Promise<void>;
  getPlayerDetails: (playerId: number) => Promise<Player | null>;
  trackPlayer: (playerId: number) => Promise<boolean>;
  untrackPlayer: (playerId: number) => Promise<boolean>;
  getTrackedPlayers: () => Promise<void>;
  comparePlayers: (playerIds: number[]) => Promise<any>;
  clearSearch: () => void;
  clearError: () => void;
}

export const usePlayerSearch = (): UsePlayerSearchReturn => {
  const [state, setState] = useState<PlayerSearchState>({
    players: [],
    trendingPlayers: [],
    trackedPlayers: [],
    loading: false,
    error: null,
    hasMore: true,
    totalCount: 0,
  });

  const setLoading = useCallback((loading: boolean) => {
    setState(prev => ({ ...prev, loading }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error, loading: false }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const clearSearch = useCallback(() => {
    setState(prev => ({
      ...prev,
      players: [],
      hasMore: true,
      totalCount: 0,
      error: null,
    }));
  }, []);

  // Search players with filters
  const searchPlayers = useCallback(async (query: string, filters?: PlayerFilters) => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (filters?.position?.length) params.append('position', filters.position.join(','));
      if (filters?.team?.length) params.append('team', filters.team.join(','));
      if (filters?.minPrice !== undefined) params.append('min_price', filters.minPrice.toString());
      if (filters?.maxPrice !== undefined) params.append('max_price', filters.maxPrice.toString());
      if (filters?.minPoints !== undefined) params.append('min_points', filters.minPoints.toString());
      if (filters?.maxPoints !== undefined) params.append('max_points', filters.maxPoints.toString());
      if (filters?.minForm !== undefined) params.append('min_form', filters.minForm.toString());
      if (filters?.availableOnly) params.append('available_only', 'true');
      if (filters?.excludeInjured) params.append('exclude_injured', 'true');
      if (filters?.limit) params.append('limit', filters.limit.toString());

      const response = await api.get(`/players/search?${params.toString()}`);
      
      if (response.data.success) {
        setState(prev => ({
          ...prev,
          players: response.data.players,
          totalCount: response.data.count,
          hasMore: response.data.players.length === (filters?.limit || 50),
          loading: false,
          error: null,
        }));
      } else {
        setError('Failed to search players');
      }
    } catch (error: any) {
      console.error('Error searching players:', error);
      setError(error.response?.data?.error || 'Failed to search players');
    }
  }, [setLoading, setError]);

  // Get trending players
  const getTrendingPlayers = useCallback(async (metric = 'transfers_in', timeframe = 'week') => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams({
        metric,
        timeframe,
        limit: '25',
      });

      const response = await api.get(`/players/trending?${params.toString()}`);
      
      if (response.data.success) {
        setState(prev => ({
          ...prev,
          trendingPlayers: response.data.trending_players,
          loading: false,
          error: null,
        }));
      } else {
        setError('Failed to fetch trending players');
      }
    } catch (error: any) {
      console.error('Error fetching trending players:', error);
      setError(error.response?.data?.error || 'Failed to fetch trending players');
    }
  }, [setLoading, setError]);

  // Get detailed player information
  const getPlayerDetails = useCallback(async (playerId: number): Promise<Player | null> => {
    try {
      const response = await api.get(`/players/${playerId}`);
      
      if (response.data.success) {
        return response.data.player;
      } else {
        setError('Failed to fetch player details');
        return null;
      }
    } catch (error: any) {
      console.error('Error fetching player details:', error);
      setError(error.response?.data?.error || 'Failed to fetch player details');
      return null;
    }
  }, [setError]);

  // Track a player
  const trackPlayer = useCallback(async (playerId: number): Promise<boolean> => {
    try {
      const response = await api.post('/players/track', { player_fpl_id: playerId });
      
      if (response.data.success) {
        // Refresh tracked players list
        await getTrackedPlayers();
        return true;
      } else {
        setError('Failed to track player');
        return false;
      }
    } catch (error: any) {
      console.error('Error tracking player:', error);
      setError(error.response?.data?.error || 'Failed to track player');
      return false;
    }
  }, [setError]);

  // Untrack a player
  const untrackPlayer = useCallback(async (playerId: number): Promise<boolean> => {
    try {
      const response = await api.delete(`/players/track/${playerId}`);
      
      if (response.data.success) {
        // Remove from tracked players list
        setState(prev => ({
          ...prev,
          trackedPlayers: prev.trackedPlayers.filter(p => p.fpl_id !== playerId),
        }));
        return true;
      } else {
        setError('Failed to untrack player');
        return false;
      }
    } catch (error: any) {
      console.error('Error untracking player:', error);
      setError(error.response?.data?.error || 'Failed to untrack player');
      return false;
    }
  }, [setError]);

  // Get tracked players
  const getTrackedPlayers = useCallback(async () => {
    try {
      const response = await api.get('/players/tracked');
      
      if (response.data.success) {
        setState(prev => ({
          ...prev,
          trackedPlayers: response.data.tracked_players.map((tp: any) => tp.current_data),
        }));
      } else {
        setError('Failed to fetch tracked players');
      }
    } catch (error: any) {
      console.error('Error fetching tracked players:', error);
      setError(error.response?.data?.error || 'Failed to fetch tracked players');
    }
  }, [setError]);

  // Compare multiple players
  const comparePlayers = useCallback(async (playerIds: number[]) => {
    try {
      const response = await api.post('/players/compare', { player_ids: playerIds });
      
      if (response.data.success) {
        return response.data.comparison;
      } else {
        setError('Failed to compare players');
        return null;
      }
    } catch (error: any) {
      console.error('Error comparing players:', error);
      setError(error.response?.data?.error || 'Failed to compare players');
      return null;
    }
  }, [setError]);

  // Load tracked players on mount
  useEffect(() => {
    getTrackedPlayers();
  }, [getTrackedPlayers]);

  // Memoized values for performance
  const trackedPlayerIds = useMemo(() => {
    return new Set(state.trackedPlayers.map(p => p.fpl_id));
  }, [state.trackedPlayers]);

  return {
    ...state,
    searchPlayers,
    getTrendingPlayers,
    getPlayerDetails,
    trackPlayer,
    untrackPlayer,
    getTrackedPlayers,
    comparePlayers,
    clearSearch,
    clearError,
    // Add convenience methods
    isPlayerTracked: (playerId: number) => trackedPlayerIds.has(playerId),
  };
};