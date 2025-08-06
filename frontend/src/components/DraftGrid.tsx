/**
 * DraftGrid component - Interactive draft board showing picks in grid format
 */

import React, { useMemo } from 'react';
import { DraftPick, Team, Player } from '../types';

interface DraftGridProps {
  teams: Team[];
  picks: DraftPick[];
  players?: Player[]; // Add players array to get player details
  totalRounds: number;
  currentPick: number;
  isSnakeDraft?: boolean;
  onPickClick?: (pick: DraftPick) => void;
  className?: string;
}

const DraftGrid: React.FC<DraftGridProps> = ({
  teams,
  picks,
  players = [],
  totalRounds,
  currentPick,
  isSnakeDraft = true,
  onPickClick,
  className = '',
}) => {
  // Helper function to get player details
  const getPlayerDetails = (playerId: number) => {
    return players.find(p => p.id === playerId);
  };

  // Helper function to get team owner name
  const getTeamOwnerName = (team: Team) => {
    // Use the team name directly, no team_name in settings
    return team.name || `Team ${team.id}`;
  };

  // Create grid structure
  const gridData = useMemo(() => {
    const grid: (DraftPick | null)[][] = [];
    const picksByNumber = picks.reduce((acc, pick) => {
      acc[pick.pick_number] = pick;
      return acc;
    }, {} as Record<number, DraftPick>);

    for (let round = 1; round <= totalRounds; round++) {
      const roundPicks: (DraftPick | null)[] = [];
      
      for (let teamIndex = 0; teamIndex < teams.length; teamIndex++) {
        let pickNumber: number;
        
        if (isSnakeDraft && round % 2 === 0) {
          // Even rounds: reverse order for snake draft
          pickNumber = (round - 1) * teams.length + (teams.length - teamIndex);
        } else {
          // Odd rounds: normal order
          pickNumber = (round - 1) * teams.length + (teamIndex + 1);
        }
        
        roundPicks.push(picksByNumber[pickNumber] || null);
      }
      
      grid.push(roundPicks);
    }
    
    return grid;
  }, [teams, picks, totalRounds, isSnakeDraft]);

  const getPickStatus = (pickNumber: number) => {
    if (pickNumber < currentPick) return 'completed';
    if (pickNumber === currentPick) return 'current';
    return 'upcoming';
  };

  const getPickStyles = (status: string, pick: DraftPick | null) => {
    const baseStyles = 'relative p-2 border rounded-lg text-center transition-all duration-200 cursor-pointer hover:shadow-md';
    
    switch (status) {
      case 'completed':
        return `${baseStyles} bg-green-50 border-green-200 text-green-900`;
      case 'current':
        return `${baseStyles} bg-blue-100 border-blue-400 text-blue-900 ring-2 ring-blue-300 animate-pulse`;
      case 'upcoming':
        return `${baseStyles} bg-gray-50 border-gray-200 text-gray-600`;
      default:
        return baseStyles;
    }
  };

  const getPositionColor = (position?: string) => {
    switch (position) {
      case 'GK':
      case 'GKP': 
        return 'bg-yellow-500';
      case 'DEF': 
        return 'bg-green-500';
      case 'MID': 
        return 'bg-blue-500';
      case 'FWD': 
        return 'bg-red-500';
      default: 
        return 'bg-gray-500';
    }
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Draft Board</h3>
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>Round {Math.ceil(currentPick / teams.length)} of {totalRounds}</span>
          <span>Pick {currentPick} of {teams.length * totalRounds}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-50 border border-green-200 rounded"></div>
          <span>Completed</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-blue-100 border border-blue-400 rounded"></div>
          <span>Current</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-gray-50 border border-gray-200 rounded"></div>
          <span>Upcoming</span>
        </div>
        <div className="ml-auto flex gap-2">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <span>GK</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>DEF</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span>MID</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span>FWD</span>
          </div>
        </div>
      </div>

      {/* Grid Container */}
      <div className="overflow-x-auto">
        <div className="min-w-max">
          {/* Team Headers */}
          <div className="grid gap-1 mb-2" style={{ gridTemplateColumns: `repeat(${teams.length}, 1fr)` }}>
            {teams.map((team, index) => (
              <div
                key={team.id}
                className="p-2 bg-gray-100 border border-gray-200 rounded text-center text-sm font-medium"
              >
                <div className="truncate" title={team.name}>
                  {team.name}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {getTeamOwnerName(team)}
                </div>
              </div>
            ))}
          </div>

          {/* Draft Grid */}
          <div className="space-y-1">
            {gridData.map((round, roundIndex) => (
              <div key={roundIndex} className="flex gap-1">
                {/* Round Number */}
                <div className="flex items-center justify-center w-8 text-xs font-medium text-gray-600 bg-gray-100 rounded">
                  {roundIndex + 1}
                </div>
                
                {/* Round Picks */}
                <div className="grid gap-1 flex-1" style={{ gridTemplateColumns: `repeat(${teams.length}, 1fr)` }}>
                  {round.map((pick, teamIndex) => {
                    const pickNumber = isSnakeDraft && (roundIndex + 1) % 2 === 0
                      ? roundIndex * teams.length + (teams.length - teamIndex)
                      : roundIndex * teams.length + (teamIndex + 1);
                    
                    const status = getPickStatus(pickNumber);
                    const playerDetails = pick ? getPlayerDetails(pick.player_id) : null;
                    
                    return (
                      <div
                        key={`${roundIndex}-${teamIndex}`}
                        className={getPickStyles(status, pick)}
                        onClick={() => pick && onPickClick?.(pick)}
                        style={{ minHeight: '80px' }}
                      >
                        {/* Pick Number */}
                        <div className="absolute top-1 left-1 text-xs font-bold opacity-60">
                          {pickNumber}
                        </div>

                        {pick ? (
                          <div className="h-full flex flex-col justify-center">
                            {/* Position Indicator */}
                            <div className={`w-4 h-4 rounded-full mx-auto mb-1 ${getPositionColor(playerDetails?.position_short)}`}></div>
                            
                            {/* Player Name */}
                            <div className="font-medium text-xs leading-tight mb-1 px-1">
                              {playerDetails?.web_name || playerDetails?.name || 'Unknown Player'}
                            </div>
                            
                            {/* Team */}
                            <div className="text-xs opacity-75">
                              {playerDetails?.team_short || playerDetails?.team || 'UNK'}
                            </div>

                            {/* Auto Pick Indicator */}
                            {pick.is_auto_pick && (
                              <div className="absolute top-1 right-1">
                                <div className="w-2 h-2 bg-orange-400 rounded-full" title="Auto Pick"></div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="h-full flex items-center justify-center">
                            {status === 'current' && (
                              <div className="text-lg">⏰</div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pick Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{picks.length}</div>
            <div className="text-gray-600">Picks Made</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {teams.length * totalRounds - picks.length}
            </div>
            <div className="text-gray-600">Remaining</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {picks.filter(p => p.is_auto_pick).length}
            </div>
            <div className="text-gray-600">Auto Picks</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {Math.ceil(currentPick / teams.length)}
            </div>
            <div className="text-gray-600">Current Round</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DraftGrid;