/**
 * StandingsTable component - League standings display with sorting and details
 */

import React, { useState, useMemo } from 'react';

// Define Standing interface locally since it's not exported from types
interface Standing {
  team_id: string;
  team_name: string;
  owner_id: string;
  owner_name?: string;
  rank?: number;
  wins: number;
  losses: number;
  draws?: number;
  points_for: number;
  points_against: number;
  waiver_position?: number;
  logo_url?: string;
  streak?: string;
  recent_form?: string;
  best_week_score?: number;
  worst_week_score?: number;
}

// Extended standing with calculated fields
interface EnrichedStanding extends Standing {
  totalGames: number;
  winPercentage: number;
  avgPointsFor: number;
  avgPointsAgainst: number;
  pointsDiff: number;
}

interface StandingsTableProps {
  standings: Standing[];
  currentUserId?: string;
  showDetails?: boolean;
  interactive?: boolean;
  onTeamClick?: (teamId: string) => void;
  className?: string;
}

type SortField = 'rank' | 'wins' | 'losses' | 'points_for' | 'points_against' | 'win_percentage';
type SortDirection = 'asc' | 'desc';

const StandingsTable: React.FC<StandingsTableProps> = ({
  standings,
  currentUserId,
  showDetails = false,
  interactive = true,
  onTeamClick,
  className = '',
}) => {
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [expandedTeam, setExpandedTeam] = useState<string | null>(null);

  // Format record helper
  const formatRecord = (wins: number, losses: number, draws: number = 0) => {
    if (draws > 0) {
      return `${wins}-${losses}-${draws}`;
    }
    return `${wins}-${losses}`;
  };

  // Format win percentage helper
  const formatWinPercentage = (wins: number, totalGames: number) => {
    if (totalGames === 0) return '0.0%';
    return `${((wins / totalGames) * 100).toFixed(1)}%`;
  };

  // Calculate additional stats
  const enrichedStandings = useMemo(() => {
    return standings.map((team, index) => {
      const totalGames = team.wins + team.losses + (team.draws || 0);
      const winPercentage = totalGames > 0 ? (team.wins / totalGames) * 100 : 0;
      const avgPointsFor = totalGames > 0 ? team.points_for / totalGames : 0;
      const avgPointsAgainst = totalGames > 0 ? team.points_against / totalGames : 0;
      const pointsDiff = team.points_for - team.points_against;

      return {
        ...team,
        rank: team.rank || index + 1, // Use provided rank or calculate from position
        totalGames,
        winPercentage,
        avgPointsFor,
        avgPointsAgainst,
        pointsDiff,
      } as EnrichedStanding;
    });
  }, [standings]);

  // Sort standings
  const sortedStandings = useMemo(() => {
    const sorted = [...enrichedStandings].sort((a, b) => {
      let aValue: number;
      let bValue: number;

      switch (sortField) {
        case 'rank':
          aValue = a.rank || 0;
          bValue = b.rank || 0;
          break;
        case 'wins':
          aValue = a.wins;
          bValue = b.wins;
          break;
        case 'losses':
          aValue = a.losses;
          bValue = b.losses;
          break;
        case 'points_for':
          aValue = a.points_for;
          bValue = b.points_for;
          break;
        case 'points_against':
          aValue = a.points_against;
          bValue = b.points_against;
          break;
        case 'win_percentage':
          aValue = a.winPercentage;
          bValue = b.winPercentage;
          break;
        default:
          return 0;
      }

      if (sortDirection === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });

    return sorted;
  }, [enrichedStandings, sortField, sortDirection]);

  // Handle sort
  const handleSort = (field: SortField) => {
    if (!interactive) return;
    
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection(field === 'rank' ? 'asc' : 'desc');
    }
  };

  // Get playoff indicator
  const getPlayoffStatus = (rank: number) => {
    if (rank <= 6) return 'playoff';
    if (rank <= 8) return 'bubble';
    return 'eliminated';
  };

  const getPlayoffColor = (status: string) => {
    switch (status) {
      case 'playoff': return 'text-green-600 bg-green-50';
      case 'bubble': return 'text-orange-600 bg-orange-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  // Toggle expanded team details
  const toggleExpanded = (teamId: string) => {
    if (!interactive) return;
    setExpandedTeam(expandedTeam === teamId ? null : teamId);
  };

  // Sort icon component
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }

    return sortDirection === 'asc' ? (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-900">League Standings</h3>
        <p className="text-sm text-gray-600 mt-1">
          {standings.length} teams • Updated {new Date().toLocaleDateString()}
        </p>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('rank')}
                  className={`flex items-center gap-1 ${interactive ? 'hover:text-gray-700 cursor-pointer' : 'cursor-default'}`}
                  disabled={!interactive}
                >
                  Rank
                  {interactive && <SortIcon field="rank" />}
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Team
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('wins')}
                  className={`flex items-center gap-1 mx-auto ${interactive ? 'hover:text-gray-700 cursor-pointer' : 'cursor-default'}`}
                  disabled={!interactive}
                >
                  Record
                  {interactive && <SortIcon field="wins" />}
                </button>
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('win_percentage')}
                  className={`flex items-center gap-1 mx-auto ${interactive ? 'hover:text-gray-700 cursor-pointer' : 'cursor-default'}`}
                  disabled={!interactive}
                >
                  Win %
                  {interactive && <SortIcon field="win_percentage" />}
                </button>
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('points_for')}
                  className={`flex items-center gap-1 mx-auto ${interactive ? 'hover:text-gray-700 cursor-pointer' : 'cursor-default'}`}
                  disabled={!interactive}
                >
                  PF
                  {interactive && <SortIcon field="points_for" />}
                </button>
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('points_against')}
                  className={`flex items-center gap-1 mx-auto ${interactive ? 'hover:text-gray-700 cursor-pointer' : 'cursor-default'}`}
                  disabled={!interactive}
                >
                  PA
                  {interactive && <SortIcon field="points_against" />}
                </button>
              </th>
              {showDetails && (
                <>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Diff
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg PF
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Streak
                  </th>
                </>
              )}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              {showDetails && interactive && (
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedStandings.map((team, index) => {
              const isUserTeam = team.owner_id === currentUserId;
              const playoffStatus = getPlayoffStatus(team.rank || index + 1);
              const isExpanded = expandedTeam === team.team_id;

              return (
                <React.Fragment key={team.team_id}>
                  <tr
                    className={`
                      transition-colors duration-150
                      ${isUserTeam ? 'bg-blue-50 hover:bg-blue-100' : 'hover:bg-gray-50'}
                      ${interactive && onTeamClick ? 'cursor-pointer' : ''}
                    `}
                    onClick={() => onTeamClick?.(team.team_id)}
                  >
                    {/* Rank */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="text-lg font-bold text-gray-900">
                          {team.rank || index + 1}
                        </span>
                        {team.rank && team.rank <= 3 && (
                          <span className="ml-2">
                            {team.rank === 1 && '🥇'}
                            {team.rank === 2 && '🥈'}
                            {team.rank === 3 && '🥉'}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Team */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {team.logo_url && (
                          <img
                            src={team.logo_url}
                            alt={`${team.team_name} logo`}
                            className="w-8 h-8 rounded-full mr-3 object-cover"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                            }}
                          />
                        )}
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {team.team_name}
                            {isUserTeam && (
                              <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                                Your Team
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500">
                            {team.owner_name || 'Owner'}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Record */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm font-medium text-gray-900">
                        {formatRecord(team.wins, team.losses, team.draws || 0)}
                      </span>
                    </td>

                    {/* Win Percentage */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm text-gray-900">
                        {formatWinPercentage(team.wins, team.totalGames)}
                      </span>
                    </td>

                    {/* Points For */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm font-medium text-gray-900">
                        {team.points_for.toFixed(1)}
                      </span>
                    </td>

                    {/* Points Against */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className="text-sm text-gray-900">
                        {team.points_against.toFixed(1)}
                      </span>
                    </td>

                    {/* Details columns */}
                    {showDetails && (
                      <>
                        {/* Point Differential */}
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className={`text-sm font-medium ${
                            team.pointsDiff > 0 ? 'text-green-600' : 
                            team.pointsDiff < 0 ? 'text-red-600' : 'text-gray-600'
                          }`}>
                            {team.pointsDiff > 0 ? '+' : ''}{team.pointsDiff.toFixed(1)}
                          </span>
                        </td>

                        {/* Average Points For */}
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-gray-900">
                            {team.avgPointsFor.toFixed(1)}
                          </span>
                        </td>

                        {/* Streak */}
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-gray-900">
                            {team.streak || '-'}
                          </span>
                        </td>
                      </>
                    )}

                    {/* Playoff Status */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getPlayoffColor(playoffStatus)}`}>
                        {playoffStatus === 'playoff' && 'Playoffs'}
                        {playoffStatus === 'bubble' && 'Bubble'}
                        {playoffStatus === 'eliminated' && 'Out'}
                      </span>
                    </td>

                    {/* Expand Toggle */}
                    {showDetails && interactive && (
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpanded(team.team_id);
                          }}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          <svg 
                            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      </td>
                    )}
                  </tr>

                  {/* Expanded Details */}
                  {isExpanded && showDetails && (
                    <tr className="bg-gray-50">
                      <td colSpan={showDetails ? (interactive ? 11 : 10) : 7} className="px-6 py-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <div className="font-medium text-gray-900">Recent Form</div>
                            <div className="text-gray-600">{team.recent_form || 'N/A'}</div>
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">Best Week</div>
                            <div className="text-gray-600">{team.best_week_score ? `${team.best_week_score} pts` : 'N/A'}</div>
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">Worst Week</div>
                            <div className="text-gray-600">{team.worst_week_score ? `${team.worst_week_score} pts` : 'N/A'}</div>
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">Waiver Position</div>
                            <div className="text-gray-600">#{team.waiver_position || 'N/A'}</div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {standings.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p>No standings available</p>
          <p className="text-sm">Standings will appear after games are played</p>
        </div>
      )}

      {/* Legend */}
      {standings.length > 0 && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <div className="flex flex-wrap gap-4 text-xs text-gray-600">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-50 border border-green-200 rounded"></div>
              <span>Playoff Teams (1-6)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-orange-50 border border-orange-200 rounded"></div>
              <span>Playoff Bubble (7-8)</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">PF:</span>
              <span>Points For</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-medium">PA:</span>
              <span>Points Against</span>
            </div>
            {showDetails && (
              <div className="flex items-center gap-1">
                <span className="font-medium">Diff:</span>
                <span>Point Differential</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export { type Standing, type EnrichedStanding };
export default StandingsTable;