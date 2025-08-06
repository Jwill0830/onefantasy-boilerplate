/**
 * PlayerCard component - Reusable player display component
 */

import React from 'react';
import { Player } from '../types';

interface PlayerCardProps {
  player: Player;
  variant?: 'default' | 'compact' | 'detailed' | 'draft';
  isSelected?: boolean;
  isTracked?: boolean;
  showActions?: boolean;
  showStats?: string[]; // Array of stat keys to display
  onClick?: (player: Player) => void;
  onTrack?: (playerId: string) => void;
  onUntrack?: (playerId: string) => void;
  onDraft?: (playerId: string) => void;
  className?: string;
}

// Extended player interface for properties that might not be in base Player type
interface ExtendedPlayer extends Player {
  chance_of_playing_this_round?: number | null;
  chance_of_playing_next_round?: number | null;
  draft_rank?: number;
  fpl_id?: string;
  cost_change_event?: number;
}

const PlayerCard: React.FC<PlayerCardProps> = ({
  player,
  variant = 'default',
  isSelected = false,
  isTracked = false,
  showActions = true,
  showStats = ['total_points', 'form', 'selected_by_percent'],
  onClick,
  onTrack,
  onUntrack,
  onDraft,
  className = '',
}) => {
  // Cast player to extended type for accessing additional properties
  const extendedPlayer = player as ExtendedPlayer;
  
  const getPositionColor = (position: string) => {
    switch (position) {
      case 'GKP': return 'bg-yellow-100 text-yellow-800';
      case 'DEF': return 'bg-green-100 text-green-800';
      case 'MID': return 'bg-blue-100 text-blue-800';
      case 'FWD': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatPrice = (price: number) => {
    return `£${(price / 10).toFixed(1)}m`;
  };

  const formatStat = (statKey: string, value: any) => {
    switch (statKey) {
      case 'now_cost':
        return formatPrice(value);
      case 'selected_by_percent':
        return `${value}%`;
      case 'form':
      case 'points_per_game':
        return parseFloat(value).toFixed(1);
      default:
        return value?.toString() || '0';
    }
  };

  const getStatLabel = (statKey: string) => {
    const labels: Record<string, string> = {
      total_points: 'Points',
      form: 'Form',
      selected_by_percent: 'Selected',
      now_cost: 'Price',
      points_per_game: 'PPG',
      goals_scored: 'Goals',
      assists: 'Assists',
      clean_sheets: 'CS',
      saves: 'Saves',
      bonus: 'Bonus',
      minutes: 'Minutes',
      ict_index: 'ICT',
    };
    return labels[statKey] || statKey;
  };

  const getAvailabilityStatus = () => {
    const chanceThisRound = extendedPlayer.chance_of_playing_this_round;
    const chanceNextRound = extendedPlayer.chance_of_playing_next_round;
    
    if (chanceThisRound === null || chanceThisRound === undefined || chanceThisRound === 100) {
      return { status: 'available', color: 'text-green-600', text: 'Available' };
    } else if (chanceThisRound === 0) {
      return { status: 'unavailable', color: 'text-red-600', text: 'Unavailable' };
    } else if (chanceThisRound <= 25) {
      return { status: 'doubtful', color: 'text-red-500', text: 'Doubtful' };
    } else if (chanceThisRound <= 75) {
      return { status: 'uncertain', color: 'text-yellow-600', text: 'Uncertain' };
    } else {
      return { status: 'likely', color: 'text-green-500', text: 'Likely' };
    }
  };

  // Get player ID - fallback to string version of id if fpl_id doesn't exist
  const getPlayerId = (): string => {
    return extendedPlayer.fpl_id || player.id.toString();
  };

  const availability = getAvailabilityStatus();

  if (variant === 'compact') {
    return (
      <div
        className={`
          flex items-center p-2 bg-white border rounded-lg cursor-pointer transition-all duration-200
          ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}
          ${className}
        `}
        onClick={() => onClick?.(player)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 text-xs font-medium rounded ${getPositionColor(player.position)}`}>
              {player.position}
            </span>
            <span className="font-medium text-gray-900 truncate">{player.name}</span>
            <span className="text-sm text-gray-500">{player.team}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="font-medium">{player.total_points}pts</span>
          <span className="text-gray-600">{formatPrice(player.now_cost)}</span>
        </div>
      </div>
    );
  }

  if (variant === 'draft') {
    return (
      <div
        className={`
          relative p-4 bg-white border-2 rounded-xl shadow-sm transition-all duration-200
          ${isSelected ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-gray-300 hover:shadow-md'}
          ${className}
        `}
      >
        {/* Draft Rank Badge */}
        {extendedPlayer.draft_rank && (
          <div className="absolute top-2 right-2 px-2 py-1 bg-purple-100 text-purple-800 text-xs font-bold rounded">
            #{Math.round(extendedPlayer.draft_rank)}
          </div>
        )}

        <div className="flex items-start gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-1 text-xs font-medium rounded ${getPositionColor(player.position)}`}>
                {player.position}
              </span>
              <span className={`text-xs font-medium ${availability.color}`}>
                {availability.text}
              </span>
            </div>
            
            <h3 className="font-bold text-gray-900 mb-1">{player.name}</h3>
            <p className="text-sm text-gray-600 mb-3">{player.team}</p>
            
            <div className="grid grid-cols-2 gap-2 text-sm">
              {showStats.map(statKey => (
                <div key={statKey} className="flex justify-between">
                  <span className="text-gray-600">{getStatLabel(statKey)}:</span>
                  <span className="font-medium">{formatStat(statKey, (player as any)[statKey])}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {showActions && (
          <div className="flex gap-2 mt-4">
            {onDraft && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDraft(getPlayerId());
                }}
                className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Draft
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClick?.(player);
              }}
              className="px-3 py-2 text-gray-600 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Details
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`
        relative p-4 bg-white border rounded-xl shadow-sm transition-all duration-200 cursor-pointer
        ${isSelected ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-gray-300 hover:shadow-md'}
        ${className}
      `}
      onClick={() => onClick?.(player)}
    >
      {/* Tracked indicator */}
      {isTracked && (
        <div className="absolute top-2 right-2 w-3 h-3 bg-blue-500 rounded-full"></div>
      )}

      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 text-xs font-medium rounded ${getPositionColor(player.position)}`}>
            {player.position}
          </span>
          <span className={`text-xs font-medium ${availability.color}`}>
            {availability.text}
          </span>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-gray-900">{formatPrice(player.now_cost)}</div>
          {extendedPlayer.cost_change_event !== undefined && extendedPlayer.cost_change_event !== 0 && (
            <div className={`text-xs ${extendedPlayer.cost_change_event > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {extendedPlayer.cost_change_event > 0 ? '+' : ''}{formatPrice(extendedPlayer.cost_change_event)}
            </div>
          )}
        </div>
      </div>

      <div className="mb-3">
        <h3 className="font-bold text-lg text-gray-900 mb-1">{player.name}</h3>
        <p className="text-sm text-gray-600">{player.team}</p>
        {player.news && (
          <p className="text-xs text-orange-600 mt-1 line-clamp-2">{player.news}</p>
        )}
      </div>

      {variant === 'detailed' && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{player.total_points}</div>
            <div className="text-xs text-gray-600">Total Points</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{parseFloat(player.form.toString()).toFixed(1)}</div>
            <div className="text-xs text-gray-600">Form</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{player.selected_by_percent}%</div>
            <div className="text-xs text-gray-600">Selected</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-sm mb-4">
        {showStats.map(statKey => (
          <div key={statKey} className="flex justify-between">
            <span className="text-gray-600">{getStatLabel(statKey)}:</span>
            <span className="font-medium">{formatStat(statKey, (player as any)[statKey])}</span>
          </div>
        ))}
      </div>

      {showActions && (
        <div className="flex gap-2">
          {onTrack && onUntrack && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                isTracked ? onUntrack(getPlayerId()) : onTrack(getPlayerId());
              }}
              className={`
                px-3 py-2 text-sm font-medium rounded-lg transition-colors
                ${isTracked 
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }
              `}
            >
              {isTracked ? 'Untrack' : 'Track'}
            </button>
          )}
          
          {onDraft && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDraft(getPlayerId());
              }}
              className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Draft Player
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default PlayerCard;