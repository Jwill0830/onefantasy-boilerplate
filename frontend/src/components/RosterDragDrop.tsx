/**
 * RosterDragDrop component - Drag-and-drop lineup editor
 */

import React, { useState, useCallback } from 'react';
import { Player, LineupFormation } from '../types';

// Define Lineup interface locally since it's missing from types
interface Lineup {
  starting_11: number[];
  bench: number[];
  captain: number;
  vice_captain: number;
}

interface RosterDragDropProps {
  roster: Player[];
  lineup: Lineup;
  onLineupChange: (lineup: Lineup) => void;
  locked?: boolean;
  className?: string;
}

interface DragState {
  draggedPlayer: Player | null;
  draggedFrom: 'starting' | 'bench' | null;
  draggedIndex: number | null;
}

const RosterDragDrop: React.FC<RosterDragDropProps> = ({
  roster,
  lineup,
  onLineupChange,
  locked = false,
  className = '',
}) => {
  const [dragState, setDragState] = useState<DragState>({
    draggedPlayer: null,
    draggedFrom: null,
    draggedIndex: null,
  });

  const [dragOver, setDragOver] = useState<{
    zone: 'starting' | 'bench' | null;
    index: number | null;
  }>({ zone: null, index: null });

  // Get player details from roster
  const getPlayerDetails = useCallback((playerId: number): Player | undefined => {
    return roster.find(p => p.id === playerId);
  }, [roster]);

  // Formation configuration
  const formations = {
    '3-4-3': { DEF: 3, MID: 4, FWD: 3 },
    '3-5-2': { DEF: 3, MID: 5, FWD: 2 },
    '4-3-3': { DEF: 4, MID: 3, FWD: 3 },
    '4-4-2': { DEF: 4, MID: 4, FWD: 2 },
    '4-5-1': { DEF: 4, MID: 5, FWD: 1 },
    '5-3-2': { DEF: 5, MID: 3, FWD: 2 },
    '5-4-1': { DEF: 5, MID: 4, FWD: 1 },
  };

  // Get current formation
  const getCurrentFormation = useCallback(() => {
    const starting11Players = lineup.starting_11.map(id => getPlayerDetails(id)).filter(Boolean) as Player[];
    const positions = { DEF: 0, MID: 0, FWD: 0 };
    
    starting11Players.forEach(player => {
      if (player.position_short === 'DEF') positions.DEF++;
      if (player.position_short === 'MID') positions.MID++;
      if (player.position_short === 'FWD') positions.FWD++;
    });

    const formationKey = `${positions.DEF}-${positions.MID}-${positions.FWD}`;
    return formationKey as keyof typeof formations;
  }, [lineup.starting_11, getPlayerDetails]);

  // Arrange starting 11 by formation
  const getFormationLayout = useCallback(() => {
    const starting11Players = lineup.starting_11.map(id => getPlayerDetails(id)).filter(Boolean) as Player[];
    const goalkeeper = starting11Players.find(p => p.position_short === 'GK');
    const defenders = starting11Players.filter(p => p.position_short === 'DEF');
    const midfielders = starting11Players.filter(p => p.position_short === 'MID');
    const forwards = starting11Players.filter(p => p.position_short === 'FWD');

    return {
      goalkeeper: goalkeeper ? [goalkeeper] : [],
      defenders,
      midfielders,
      forwards,
    };
  }, [lineup.starting_11, getPlayerDetails]);

  // Handle drag start
  const handleDragStart = (e: React.DragEvent, player: Player, from: 'starting' | 'bench', index: number) => {
    if (locked) return;
    
    setDragState({
      draggedPlayer: player,
      draggedFrom: from,
      draggedIndex: index,
    });
    
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', '');
  };

  // Handle drag over
  const handleDragOver = (e: React.DragEvent, zone: 'starting' | 'bench', index?: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    setDragOver({ zone, index: index ?? null });
  };

  // Handle drag leave
  const handleDragLeave = () => {
    setDragOver({ zone: null, index: null });
  };

  // Handle drop
  const handleDrop = (e: React.DragEvent, dropZone: 'starting' | 'bench', dropIndex?: number) => {
    e.preventDefault();
    
    if (!dragState.draggedPlayer || !dragState.draggedFrom) return;

    const newLineup = { ...lineup };
    const draggedPlayerId = dragState.draggedPlayer.id;

    // Remove from source
    if (dragState.draggedFrom === 'starting') {
      newLineup.starting_11 = newLineup.starting_11.filter(id => id !== draggedPlayerId);
    } else {
      newLineup.bench = newLineup.bench.filter(id => id !== draggedPlayerId);
    }

    // Add to destination
    if (dropZone === 'starting') {
      if (newLineup.starting_11.length < 11) {
        if (dropIndex !== undefined && dropIndex < newLineup.starting_11.length) {
          newLineup.starting_11.splice(dropIndex, 0, draggedPlayerId);
        } else {
          newLineup.starting_11.push(draggedPlayerId);
        }
      }
    } else {
      if (newLineup.bench.length < 4) {
        if (dropIndex !== undefined && dropIndex < newLineup.bench.length) {
          newLineup.bench.splice(dropIndex, 0, draggedPlayerId);
        } else {
          newLineup.bench.push(draggedPlayerId);
        }
      }
    }

    // Reset captain/vice captain if they're no longer in starting 11
    if (!newLineup.starting_11.includes(newLineup.captain)) {
      newLineup.captain = newLineup.starting_11[0] || 0;
    }
    if (!newLineup.starting_11.includes(newLineup.vice_captain)) {
      newLineup.vice_captain = newLineup.starting_11[1] || newLineup.starting_11[0] || 0;
    }

    onLineupChange(newLineup);
    
    // Reset drag state
    setDragState({ draggedPlayer: null, draggedFrom: null, draggedIndex: null });
    setDragOver({ zone: null, index: null });
  };

  // Handle captain selection
  const handleCaptainSelect = (playerId: number, isCaptain: boolean) => {
    if (locked) return;
    
    const newLineup = { ...lineup };
    
    if (isCaptain) {
      // If current vice captain becomes captain, clear vice captain
      if (newLineup.vice_captain === playerId) {
        newLineup.vice_captain = newLineup.captain;
      }
      newLineup.captain = playerId;
    } else {
      // If current captain becomes vice captain, clear captain
      if (newLineup.captain === playerId) {
        newLineup.captain = newLineup.vice_captain;
      }
      newLineup.vice_captain = playerId;
    }
    
    onLineupChange(newLineup);
  };

  // Player card component
  const PlayerCard = ({ 
    player, 
    zone, 
    index, 
    isCaptain = false, 
    isViceCaptain = false 
  }: { 
    player: Player; 
    zone: 'starting' | 'bench'; 
    index: number;
    isCaptain?: boolean;
    isViceCaptain?: boolean;
  }) => {
    const isBeingDragged = dragState.draggedPlayer?.id === player.id;
    const isDropTarget = dragOver.zone === zone && dragOver.index === index;

    const getPositionColor = (position: string) => {
      switch (position) {
        case 'GK': return 'bg-yellow-500 text-white';
        case 'DEF': return 'bg-green-500 text-white';
        case 'MID': return 'bg-blue-500 text-white';
        case 'FWD': return 'bg-red-500 text-white';
        default: return 'bg-gray-500 text-white';
      }
    };

    return (
      <div
        draggable={!locked}
        onDragStart={(e) => handleDragStart(e, player, zone, index)}
        onDragOver={(e) => handleDragOver(e, zone, index)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, zone, index)}
        className={`
          relative p-3 border-2 border-dashed border-gray-300 rounded-lg bg-white transition-all duration-200
          ${!locked ? 'cursor-move hover:border-blue-400 hover:shadow-md' : 'cursor-default'}
          ${isBeingDragged ? 'opacity-50 scale-95' : 'opacity-100 scale-100'}
          ${isDropTarget ? 'border-blue-500 bg-blue-50' : ''}
          ${isCaptain ? 'ring-2 ring-yellow-400' : ''}
          ${isViceCaptain ? 'ring-2 ring-gray-400' : ''}
        `}
      >
        {/* Captain/Vice Captain Badges */}
        {isCaptain && (
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
            C
          </div>
        )}
        {isViceCaptain && (
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-gray-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
            V
          </div>
        )}

        {/* Position Badge */}
        <div className={`inline-block px-2 py-1 text-xs font-bold rounded mb-2 ${getPositionColor(player.position_short)}`}>
          {player.position_short}
        </div>

        {/* Player Info */}
        <div className="text-sm font-medium text-gray-900 mb-1 truncate">
          {player.web_name}
        </div>
        <div className="text-xs text-gray-600 mb-2">
          {player.team_short}
        </div>

        {/* Stats */}
        <div className="text-xs text-gray-500">
          <div>{player.total_points} pts</div>
          <div>£{(player.now_cost / 10).toFixed(1)}m</div>
        </div>

        {/* Captain Selection (only for starting 11) */}
        {zone === 'starting' && !locked && (
          <div className="absolute bottom-1 right-1 flex gap-1">
            <button
              onClick={() => handleCaptainSelect(player.id, true)}
              className={`w-5 h-5 text-xs font-bold rounded-full transition-colors ${
                isCaptain 
                  ? 'bg-yellow-500 text-white' 
                  : 'bg-gray-200 text-gray-600 hover:bg-yellow-200'
              }`}
              title="Make Captain"
            >
              C
            </button>
            <button
              onClick={() => handleCaptainSelect(player.id, false)}
              className={`w-5 h-5 text-xs font-bold rounded-full transition-colors ${
                isViceCaptain 
                  ? 'bg-gray-500 text-white' 
                  : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
              }`}
              title="Make Vice Captain"
            >
              V
            </button>
          </div>
        )}
      </div>
    );
  };

  // Drop zone component
  const DropZone = ({ zone, label }: { zone: 'starting' | 'bench'; label: string }) => {
    const isActive = dragOver.zone === zone;
    const playerCount = zone === 'starting' ? lineup.starting_11.length : lineup.bench.length;
    const maxPlayers = zone === 'starting' ? 11 : 4;

    return (
      <div
        onDragOver={(e) => handleDragOver(e, zone)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, zone)}
        className={`
          min-h-[100px] border-2 border-dashed rounded-lg p-4 transition-all duration-200
          ${isActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
          ${playerCount >= maxPlayers ? 'bg-red-50 border-red-300' : ''}
        `}
      >
        <div className="text-center text-gray-500">
          <div className="text-sm font-medium">{label}</div>
          <div className="text-xs">
            {playerCount}/{maxPlayers} players
          </div>
          {dragState.draggedPlayer && playerCount < maxPlayers && (
            <div className="text-xs text-blue-600 mt-2">Drop here</div>
          )}
        </div>
      </div>
    );
  };

  const formationLayout = getFormationLayout();
  const benchPlayers = lineup.bench.map(id => getPlayerDetails(id)).filter(Boolean) as Player[];
  const currentFormation = getCurrentFormation();

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          Team Lineup {locked && <span className="text-sm text-red-600">(Locked)</span>}
        </h3>
        <div className="text-sm text-gray-600">
          Formation: {currentFormation}
        </div>
      </div>

      {/* Football Pitch Layout */}
      <div 
        className="relative bg-gradient-to-b from-green-400 to-green-500 rounded-lg p-6 mb-6"
        style={{ minHeight: '400px' }}
      >
        {/* Pitch Markings */}
        <div className="absolute inset-0 opacity-20">
          <div className="w-full h-full border-2 border-white rounded-lg relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-24 h-16 border-2 border-white border-t-0 rounded-b-lg"></div>
            <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-24 h-16 border-2 border-white border-b-0 rounded-t-lg"></div>
            <div className="absolute top-1/2 left-0 right-0 h-px bg-white"></div>
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-20 h-20 border-2 border-white rounded-full"></div>
          </div>
        </div>

        {/* Player Positions */}
        <div className="relative h-full flex flex-col justify-between">
          {/* Forwards */}
          <div className="flex justify-center gap-4 mb-4">
            {formationLayout.forwards.map((player, index) => (
              <PlayerCard
                key={player.id}
                player={player}
                zone="starting"
                index={lineup.starting_11.indexOf(player.id)}
                isCaptain={lineup.captain === player.id}
                isViceCaptain={lineup.vice_captain === player.id}
              />
            ))}
            {formationLayout.forwards.length === 0 && (
              <DropZone zone="starting" label="Forward" />
            )}
          </div>

          {/* Midfielders */}
          <div className="flex justify-center gap-4 mb-4">
            {formationLayout.midfielders.map((player, index) => (
              <PlayerCard
                key={player.id}
                player={player}
                zone="starting"
                index={lineup.starting_11.indexOf(player.id)}
                isCaptain={lineup.captain === player.id}
                isViceCaptain={lineup.vice_captain === player.id}
              />
            ))}
            {formationLayout.midfielders.length === 0 && (
              <DropZone zone="starting" label="Midfielder" />
            )}
          </div>

          {/* Defenders */}
          <div className="flex justify-center gap-4 mb-4">
            {formationLayout.defenders.map((player, index) => (
              <PlayerCard
                key={player.id}
                player={player}
                zone="starting"
                index={lineup.starting_11.indexOf(player.id)}
                isCaptain={lineup.captain === player.id}
                isViceCaptain={lineup.vice_captain === player.id}
              />
            ))}
            {formationLayout.defenders.length === 0 && (
              <DropZone zone="starting" label="Defender" />
            )}
          </div>

          {/* Goalkeeper */}
          <div className="flex justify-center">
            {formationLayout.goalkeeper.map((player, index) => (
              <PlayerCard
                key={player.id}
                player={player}
                zone="starting"
                index={lineup.starting_11.indexOf(player.id)}
                isCaptain={lineup.captain === player.id}
                isViceCaptain={lineup.vice_captain === player.id}
              />
            ))}
            {formationLayout.goalkeeper.length === 0 && (
              <DropZone zone="starting" label="Goalkeeper" />
            )}
          </div>
        </div>
      </div>

      {/* Bench */}
      <div className="mb-4">
        <h4 className="text-md font-medium text-gray-900 mb-3">Bench</h4>
        <div className="grid grid-cols-4 gap-4">
          {benchPlayers.map((player, index) => (
            <PlayerCard
              key={player.id}
              player={player}
              zone="bench"
              index={index}
            />
          ))}
          {Array.from({ length: 4 - benchPlayers.length }).map((_, index) => (
            <DropZone key={`bench-${index}`} zone="bench" label={`Bench ${benchPlayers.length + index + 1}`} />
          ))}
        </div>
      </div>

      {/* Lineup Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="text-lg font-bold text-gray-900">{lineup.starting_11.length}/11</div>
          <div className="text-sm text-gray-600">Starting XI</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-900">{lineup.bench.length}/4</div>
          <div className="text-sm text-gray-600">Bench</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-blue-600">
            {lineup.captain ? getPlayerDetails(lineup.captain)?.web_name || '-' : '-'}
          </div>
          <div className="text-sm text-gray-600">Captain</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-600">
            {lineup.vice_captain ? getPlayerDetails(lineup.vice_captain)?.web_name || '-' : '-'}
          </div>
          <div className="text-sm text-gray-600">Vice Captain</div>
        </div>
      </div>

      {/* Validation Messages */}
      {lineup.starting_11.length !== 11 && (
        <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
          <p className="text-sm text-orange-800">
            ⚠️ Starting XI must contain exactly 11 players
          </p>
        </div>
      )}

      {!lineup.captain && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">
            ❌ Please select a captain
          </p>
        </div>
      )}

      {!lineup.vice_captain && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">
            ❌ Please select a vice captain
          </p>
        </div>
      )}
    </div>
  );
};

export default RosterDragDrop;