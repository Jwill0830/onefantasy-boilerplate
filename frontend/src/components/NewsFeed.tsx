// frontend/src/components/NewsFeed.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { NewsItem, Player } from '../types';
import { formatDate, formatTime } from '../utils/formatters';

interface NewsFeedProps {
  teamId?: string;
  leagueId?: string;
  playerId?: string;
  onFetchNews: (filters?: NewsFilters) => Promise<NewsItem[]>;
  className?: string;
  maxItems?: number;
  compact?: boolean;
  showFilters?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number; // in seconds
}

interface NewsFilters {
  category?: 'all' | 'injury' | 'transfer' | 'lineup' | 'performance' | 'league' | 'suspension';
  severity?: 'all' | 'low' | 'medium' | 'high' | 'critical';
  playerId?: string;
  teamName?: string;
  dateRange?: 'today' | 'week' | 'month' | 'season';
  searchTerm?: string;
}

// Extended NewsItem interface to match usage
interface ExtendedNewsItem extends NewsItem {
  playerName?: string;
  teamName?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  isBreaking?: boolean;
  fantasyImpact?: string;
  relatedPlayers?: Player[];
  actionable?: boolean;
  playerId?: number;
}

export const NewsFeed: React.FC<NewsFeedProps> = ({
  teamId,
  leagueId,
  playerId,
  onFetchNews,
  className = '',
  maxItems = 20,
  compact = false,
  showFilters = true,
  autoRefresh = true,
  refreshInterval = 300 // 5 minutes
}) => {
  const [news, setNews] = useState<ExtendedNewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<NewsFilters>({
    category: 'all',
    severity: 'all',
    dateRange: 'week'
  });
  const [error, setError] = useState<string>('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Auto-refresh functionality
  useEffect(() => {
    fetchNews();
    
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchNews(true); // Silent refresh
      }, refreshInterval * 1000);
      
      return () => clearInterval(interval);
    }
  }, [filters, autoRefresh, refreshInterval]);

  const fetchNews = async (silent = false) => {
    try {
      if (!silent) {
        setLoading(true);
        setError('');
      }
      
      const newsFilters = {
        ...filters,
        playerId: playerId || filters.playerId,
        teamId,
        leagueId
      };
      
      const data = await onFetchNews(newsFilters);
      // Transform NewsItem to ExtendedNewsItem with fallback values
      const extendedData = data.map(item => {
        const extended = item as any; // Type assertion for transformation
        return {
          ...item,
          playerName: extended.playerName || (item.player_ids?.[0] ? `Player ${item.player_ids[0]}` : undefined),
          teamName: extended.teamName || extended.team_name || undefined,
          severity: extended.severity || 'low' as const,
          isBreaking: extended.isBreaking || false,
          fantasyImpact: extended.fantasyImpact || undefined,
          relatedPlayers: extended.relatedPlayers || [],
          actionable: extended.actionable || false,
          playerId: extended.playerId || item.player_ids?.[0]
        } as ExtendedNewsItem;
      });
      
      setNews(extendedData.slice(0, maxItems));
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  // Filter and sort news
  const filteredNews = useMemo(() => {
    let filtered = [...news];

    // Apply search term
    if (filters.searchTerm) {
      const searchLower = filters.searchTerm.toLowerCase();
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchLower) ||
        item.content.toLowerCase().includes(searchLower) ||
        item.playerName?.toLowerCase().includes(searchLower) ||
        item.teamName?.toLowerCase().includes(searchLower)
      );
    }

    // Sort by priority and recency
    return filtered.sort((a, b) => {
      // First sort by severity (critical first)
      const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      const severityDiff = (severityOrder[b.severity || 'low'] || 0) - (severityOrder[a.severity || 'low'] || 0);
      if (severityDiff !== 0) return severityDiff;

      // Then by publish date (most recent first)
      const aDate = new Date(a.published_at).getTime();
      const bDate = new Date(b.published_at).getTime();
      return bDate - aDate;
    });
  }, [news, filters.searchTerm]);

  const getCategoryIcon = (category: NewsItem['category']) => {
    const icons = {
      injury: '🏥',
      transfer: '🔄',
      suspension: '🚫',
      lineup: '📋',
      general: '📰'
    };
    return icons[category] || '📰';
  };

  const getSeverityColor = (severity: ExtendedNewsItem['severity']) => {
    const colors = {
      critical: 'text-red-600 bg-red-100 border-red-200',
      high: 'text-orange-600 bg-orange-100 border-orange-200',
      medium: 'text-yellow-600 bg-yellow-100 border-yellow-200',
      low: 'text-blue-600 bg-blue-100 border-blue-200'
    };
    return colors[severity || 'low'] || 'text-gray-600 bg-gray-100 border-gray-200';
  };

  const getTimeAgo = (date: string) => {
    const now = new Date();
    const newsDate = new Date(date);
    const diffInMinutes = Math.floor((now.getTime() - newsDate.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;
    
    return formatDate(new Date(date));
  };

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const handlePlayerAction = async (action: string, playerId: number) => {
    try {
      switch (action) {
        case 'view':
          // Navigate to player details
          window.location.href = `/players/${playerId}`;
          break;
        case 'add':
          // Add to watchlist - Using fetch API as fallback
          await fetch(`/api/players/${playerId}/watchlist`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            }
          });
          break;
        case 'trade':
          // Open trade modal
          // This would trigger a trade modal
          break;
      }
    } catch (err) {
      console.error(`Failed to ${action} player:`, err);
    }
  };

  if (loading && news.length === 0) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading news...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center">
            <span className="mr-2">📰</span>
            {compact ? 'News' : 'Fantasy News Feed'}
            {news.length > 0 && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                {filteredNews.length}
              </span>
            )}
          </h3>
          
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500">
              Updated {formatTime(lastRefresh)}
            </span>
            <button
              onClick={() => fetchNews()}
              disabled={loading}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium disabled:opacity-50"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="flex flex-wrap gap-2">
            <select
              value={filters.category || 'all'}
              onChange={(e) => setFilters(prev => ({
                ...prev,
                category: e.target.value as NewsFilters['category']
              }))}
              className="text-sm px-3 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Categories</option>
              <option value="injury">Injuries</option>
              <option value="transfer">Transfers</option>
              <option value="lineup">Lineups</option>
              <option value="suspension">Suspensions</option>
              <option value="general">General</option>
            </select>

            <select
              value={filters.severity || 'all'}
              onChange={(e) => setFilters(prev => ({
                ...prev,
                severity: e.target.value as NewsFilters['severity']
              }))}
              className="text-sm px-3 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={filters.dateRange || 'week'}
              onChange={(e) => setFilters(prev => ({
                ...prev,
                dateRange: e.target.value as NewsFilters['dateRange']
              }))}
              className="text-sm px-3 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="season">This Season</option>
            </select>

            {!compact && (
              <input
                type="text"
                placeholder="Search news..."
                value={filters.searchTerm || ''}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  searchTerm: e.target.value
                }))}
                className="text-sm px-3 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            )}
          </div>
        )}
      </div>

      {/* News Items */}
      <div className={compact ? 'max-h-64 overflow-y-auto' : 'max-h-96 overflow-y-auto'}>
        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {filteredNews.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">📰</div>
            <h4 className="text-lg font-semibold text-gray-700 mb-2">
              No News Available
            </h4>
            <p className="text-gray-500">
              {filters.searchTerm 
                ? 'No news matches your search criteria.'
                : 'Check back later for the latest updates.'
              }
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredNews.map((item) => {
              const isExpanded = expandedItems.has(item.id);
              const shouldTruncate = item.content.length > 150 && compact;
              
              return (
                <div 
                  key={item.id} 
                  className={`p-4 hover:bg-gray-50 transition-colors ${
                    item.severity === 'critical' ? 'bg-red-50' : ''
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="text-xl flex-shrink-0 mt-1">
                      {getCategoryIcon(item.category)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(item.severity)}`}>
                          {(item.severity || 'low').toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-500 capitalize">
                          {item.category}
                        </span>
                        {item.isBreaking && (
                          <span className="px-2 py-1 bg-red-600 text-white text-xs rounded-full font-medium animate-pulse">
                            BREAKING
                          </span>
                        )}
                      </div>
                      
                      <h4 className="font-medium text-gray-900 mb-2 line-clamp-2">
                        {item.title}
                      </h4>
                      
                      <p className="text-sm text-gray-600 mb-3">
                        {shouldTruncate && !isExpanded 
                          ? `${item.content.substring(0, 150)}...`
                          : item.content
                        }
                        {shouldTruncate && (
                          <button
                            onClick={() => toggleExpanded(item.id)}
                            className="ml-2 text-blue-600 hover:text-blue-800 font-medium"
                          >
                            {isExpanded ? 'Show less' : 'Read more'}
                          </button>
                        )}
                      </p>
                      
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                        <div className="flex items-center space-x-3">
                          {item.playerName && (
                            <span className="font-medium text-gray-700">
                              👤 {item.playerName}
                            </span>
                          )}
                          {item.teamName && (
                            <span className="text-gray-600">
                              🏟️ {item.teamName}
                            </span>
                          )}
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <span>{getTimeAgo(item.published_at)}</span>
                          {item.source && (
                            <span className="text-gray-400">
                              • {item.source}
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {/* Fantasy Impact */}
                      {item.fantasyImpact && (
                        <div className="mb-3 p-2 bg-blue-50 rounded-lg">
                          <p className="text-xs text-blue-700">
                            <span className="font-medium">Fantasy Impact:</span> {item.fantasyImpact}
                          </p>
                        </div>
                      )}
                      
                      {/* Related Players */}
                      {item.relatedPlayers && item.relatedPlayers.length > 0 && (
                        <div className="mb-3">
                          <div className="flex flex-wrap gap-1">
                            {item.relatedPlayers.slice(0, 3).map((player) => (
                              <button
                                key={player.id}
                                onClick={() => handlePlayerAction('view', player.id)}
                                className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
                              >
                                {player.name}
                              </button>
                            ))}
                            {item.relatedPlayers.length > 3 && (
                              <span className="text-xs text-gray-500 px-2 py-1">
                                +{item.relatedPlayers.length - 3} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      {item.actionable && item.playerName && item.playerId && (
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handlePlayerAction('view', item.playerId || 0)}
                            className="text-xs px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                          >
                            View Player
                          </button>
                          <button
                            onClick={() => handlePlayerAction('add', item.playerId || 0)}
                            className="text-xs px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                          >
                            Add to Watchlist
                          </button>
                          {(item.category === 'injury' && item.severity === 'high') && (
                            <button
                              onClick={() => handlePlayerAction('trade', item.playerId || 0)}
                              className="text-xs px-3 py-1 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
                            >
                              Find Replacement
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      {filteredNews.length > 0 && !compact && (
        <div className="p-3 border-t border-gray-200 bg-gray-50 text-center">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              Showing {filteredNews.length} of {news.length} news items
            </span>
            <span>
              Auto-refresh: {autoRefresh ? `Every ${refreshInterval}s` : 'Off'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};