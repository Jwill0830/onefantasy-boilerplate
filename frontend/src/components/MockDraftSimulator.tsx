// frontend/src/components/MockDraftSimulator.tsx
import React, { useState, useEffect } from 'react';
import { Player, Team, DraftPick, League } from '../types';
import DraftGrid from './DraftGrid';
import PlayerCard from './PlayerCard';
import SearchFilter from './SearchFilter';

interface MockDraftSimulatorProps {
  league: League;
  availablePlayers: Player[];
  onSaveMockDraft: (draftPicks: DraftPick[]) => Promise<void>;
  onFetchPlayers: (filters?: any) => Promise<Player[]>;
}

interface MockTeam extends Omit<Team, 'roster'> {
  draftedPlayers: Player[];
  currentPick?: number;
}

// Extended Player interface for mock draft
interface MockPlayer extends Player {
  isAvailable: boolean;
  projectedPoints?: number;
}

export const MockDraftSimulator: React.FC<MockDraftSimulatorProps> = ({
  league,
  availablePlayers: initialPlayers,
  onSaveMockDraft,
  onFetchPlayers
}) => {
  const [isActive, setIsActive] = useState(false);
  const [currentPick, setCurrentPick] = useState(1);
  const [currentTeamIndex, setCurrentTeamIndex] = useState(0);
  const [draftPicks, setDraftPicks] = useState<DraftPick[]>([]);
  const [mockTeams, setMockTeams] = useState<MockTeam[]>([]);
  const [availablePlayers, setAvailablePlayers] = useState<MockPlayer[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<MockPlayer[]>([]);
  const [userQueue, setUserQueue] = useState<MockPlayer[]>([]);
  const [autoPickDelay, setAutoPickDelay] = useState(3); // seconds
  const [isAutoPicking, setIsAutoPicking] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPosition, setSelectedPosition] = useState<string>('');
  const [isDraftComplete, setIsDraftComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Initialize mock teams and players
  useEffect(() => {
    const teams: MockTeam[] = league.teams.map(team => ({
      ...team,
      draftedPlayers: []
    }));
    setMockTeams(teams);

    // Initialize players with mock-specific properties
    const mockPlayers: MockPlayer[] = initialPlayers.map(player => ({
      ...player,
      isAvailable: true,
      projectedPoints: player.total_points + Math.random() * 20 // Add some randomness for projection
    }));
    setAvailablePlayers(mockPlayers);
    setFilteredPlayers(mockPlayers);
  }, [league.teams, initialPlayers]);

  // Calculate draft order (snake draft)
  const getDraftOrder = (pick: number, totalTeams: number) => {
    const round = Math.ceil(pick / totalTeams);
    const isEvenRound = round % 2 === 0;
    const positionInRound = ((pick - 1) % totalTeams) + 1;
    
    return isEvenRound 
      ? totalTeams - positionInRound 
      : positionInRound - 1;
  };

  // Start mock draft
  const startMockDraft = () => {
    setIsActive(true);
    setCurrentPick(1);
    setCurrentTeamIndex(0);
    setDraftPicks([]);
    setIsDraftComplete(false);
    
    // Reset teams
    const resetTeams = mockTeams.map(team => ({
      ...team,
      draftedPlayers: []
    }));
    setMockTeams(resetTeams);
    
    // Reset players availability
    const resetPlayers = availablePlayers.map(player => ({
      ...player,
      isAvailable: true
    }));
    setAvailablePlayers(resetPlayers);
    setFilteredPlayers(resetPlayers);
  };

  // Reset mock draft
  const resetMockDraft = () => {
    setIsActive(false);
    setCurrentPick(1);
    setCurrentTeamIndex(0);
    setDraftPicks([]);
    setUserQueue([]);
    setIsDraftComplete(false);
    setIsAutoPicking(false);
    
    const resetTeams = mockTeams.map(team => ({
      ...team,
      draftedPlayers: []
    }));
    setMockTeams(resetTeams);
    
    const resetPlayers = availablePlayers.map(player => ({
      ...player,
      isAvailable: true
    }));
    setAvailablePlayers(resetPlayers);
    setFilteredPlayers(resetPlayers);
  };

  // Auto pick for CPU teams
  const autoPickForCPU = async (teamIndex: number) => {
    setIsAutoPicking(true);
    
    await new Promise(resolve => setTimeout(resolve, autoPickDelay * 1000));
    
    // Simple CPU logic: pick best available player by projected points
    const availableByPosition = availablePlayers
      .filter(player => player.isAvailable)
      .sort((a, b) => (b.projectedPoints || 0) - (a.projectedPoints || 0));
    
    const team = mockTeams[teamIndex];
    const teamPositionCounts = team.draftedPlayers.reduce((acc, player) => {
      acc[player.position_short] = (acc[player.position_short] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    // Prioritize positions based on scarcity and team needs
    let selectedPlayer: MockPlayer | null = null;
    
    // Early rounds: prioritize premium positions
    if (currentPick <= mockTeams.length * 3) {
      const premiumPositions = ['GK', 'DEF', 'MID', 'FWD'];
      for (const position of premiumPositions) {
        const positionPlayers = availableByPosition.filter(p => p.position_short === position);
        if (positionPlayers.length > 0 && (teamPositionCounts[position] || 0) < 2) {
          selectedPlayer = positionPlayers[0];
          break;
        }
      }
    }
    
    // Fallback: best available player
    if (!selectedPlayer && availableByPosition.length > 0) {
      selectedPlayer = availableByPosition[0];
    }
    
    if (selectedPlayer) {
      draftPlayer(selectedPlayer, teamIndex);
    }
    
    setIsAutoPicking(false);
  };

  // Draft a player
  const draftPlayer = (player: MockPlayer, teamIndex: number) => {
    const pick: DraftPick = {
      id: `mock-${currentPick}`,
      league_id: league.id,
      team_id: mockTeams[teamIndex].id,
      player_id: player.id,
      pick_number: currentPick,
      round: Math.ceil(currentPick / mockTeams.length),
      timestamp: new Date().toISOString(),
      is_auto_pick: teamIndex !== 0 // User is team 0, others are auto
    };

    // Update draft picks
    setDraftPicks(prev => [...prev, pick]);

    // Update team rosters
    const updatedTeams = mockTeams.map((team, index) => {
      if (index === teamIndex) {
        return {
          ...team,
          draftedPlayers: [...team.draftedPlayers, player]
        };
      }
      return team;
    });
    setMockTeams(updatedTeams);

    // Remove player from available players
    const updatedPlayers = availablePlayers.map(p => 
      p.id === player.id ? { ...p, isAvailable: false } : p
    );
    setAvailablePlayers(updatedPlayers);
    setFilteredPlayers(updatedPlayers.filter(p => p.isAvailable));

    // Remove from user queue if present
    setUserQueue(prev => prev.filter(p => p.id !== player.id));

    // Move to next pick
    const totalPicks = mockTeams.length * league.settings.roster_size;
    if (currentPick >= totalPicks) {
      setIsDraftComplete(true);
      setIsActive(false);
    } else {
      const nextPick = currentPick + 1;
      const nextTeamIndex = getDraftOrder(nextPick, mockTeams.length);
      setCurrentPick(nextPick);
      setCurrentTeamIndex(nextTeamIndex);

      // Auto pick for CPU teams after delay
      if (nextTeamIndex !== 0) { // Assuming user is team 0
        setTimeout(() => autoPickForCPU(nextTeamIndex), 1000);
      }
    }
  };

  // Handle user draft pick
  const handleUserDraftPick = (player: MockPlayer) => {
    if (!isActive || currentTeamIndex !== 0 || isAutoPicking) return;
    draftPlayer(player, 0);
  };

  // Add to user queue
  const addToQueue = (player: MockPlayer) => {
    if (userQueue.find(p => p.id === player.id)) return;
    setUserQueue(prev => [...prev, player]);
  };

  // Remove from user queue
  const removeFromQueue = (playerId: number) => {
    setUserQueue(prev => prev.filter(p => p.id !== playerId));
  };

  // Auto pick from queue for user
  const autoPickFromQueue = () => {
    if (userQueue.length > 0 && currentTeamIndex === 0) {
      const nextPlayer = userQueue[0];
      handleUserDraftPick(nextPlayer);
    }
  };

  // Save mock draft results
  const saveMockDraft = async () => {
    try {
      setIsLoading(true);
      await onSaveMockDraft(draftPicks);
    } catch (error) {
      console.error('Failed to save mock draft:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter players
  useEffect(() => {
    let filtered = availablePlayers.filter(player => player.isAvailable);

    if (searchTerm) {
      filtered = filtered.filter(player =>
        player.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        player.team.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (selectedPosition) {
      filtered = filtered.filter(player => player.position_short === selectedPosition);
    }

    setFilteredPlayers(filtered);
  }, [availablePlayers, searchTerm, selectedPosition]);

  const currentTeam = mockTeams[currentTeamIndex];
  const isUserTurn = currentTeamIndex === 0 && isActive && !isDraftComplete;
  const currentRound = Math.ceil(currentPick / mockTeams.length);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Mock Draft Simulator</h2>
          <div className="flex space-x-2">
            {!isActive && !isDraftComplete && (
              <button
                onClick={startMockDraft}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Start Mock Draft
              </button>
            )}
            {isActive && (
              <button
                onClick={resetMockDraft}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Reset Draft
              </button>
            )}
            {isDraftComplete && (
              <button
                onClick={saveMockDraft}
                disabled={isLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Mock Draft'}
              </button>
            )}
          </div>
        </div>

        {isActive && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Current Pick:</span>
              <span className="ml-2 font-bold">{currentPick}</span>
            </div>
            <div>
              <span className="text-gray-600">Round:</span>
              <span className="ml-2 font-bold">{currentRound}</span>
            </div>
            <div>
              <span className="text-gray-600">On the Clock:</span>
              <span className="ml-2 font-bold">{currentTeam?.name}</span>
            </div>
            <div>
              <span className="text-gray-600">Available Players:</span>
              <span className="ml-2 font-bold">{availablePlayers.filter(p => p.isAvailable).length}</span>
            </div>
          </div>
        )}

        {isUserTurn && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-blue-700 font-medium">
              🎯 It's your turn to pick! Select a player from the available list below.
            </p>
          </div>
        )}

        {isAutoPicking && (
          <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
            <p className="text-yellow-700 font-medium">
              ⏱️ CPU is making a selection... ({autoPickDelay}s delay)
            </p>
          </div>
        )}

        {isDraftComplete && (
          <div className="mt-4 p-3 bg-green-50 rounded-lg">
            <p className="text-green-700 font-medium">
              🎉 Mock draft complete! Review your team and save the results.
            </p>
          </div>
        )}
      </div>

      {/* Draft Grid */}
      {isActive && (
        <DraftGrid
          teams={mockTeams.map(team => ({
            ...team,
            roster: {
              starters: team.draftedPlayers.map(p => p.id),
              bench: [],
              injured_reserve: []
            }
          }))}
          picks={draftPicks}
          players={availablePlayers}
          currentPick={currentPick}
          totalRounds={league.settings.roster_size}
        />
      )}

      {/* User Queue */}
      {isActive && userQueue.length > 0 && (
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Your Draft Queue ({userQueue.length})</h3>
            <button
              onClick={autoPickFromQueue}
              disabled={!isUserTurn || userQueue.length === 0}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              Pick Next in Queue
            </button>
          </div>
          <div className="flex space-x-2 overflow-x-auto pb-2">
            {userQueue.map((player, index) => (
              <div key={player.id} className="flex-shrink-0 relative">
                <PlayerCard
                  player={player}
                />
                <button
                  onClick={() => removeFromQueue(player.id)}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full text-xs hover:bg-red-600"
                >
                  ×
                </button>
                <div className="absolute -top-2 -left-2 w-6 h-6 bg-blue-500 text-white rounded-full text-xs flex items-center justify-center">
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Available Players */}
      {isActive && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold mb-4">Available Players</h3>
            <div className="space-y-4">
              <div>
                <input
                  type="text"
                  placeholder="Search players..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <select
                  value={selectedPosition}
                  onChange={(e) => setSelectedPosition(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">All Positions</option>
                  <option value="GK">Goalkeeper</option>
                  <option value="DEF">Defender</option>
                  <option value="MID">Midfielder</option>
                  <option value="FWD">Forward</option>
                </select>
              </div>
            </div>
          </div>
          <div className="p-4 max-h-96 overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredPlayers.slice(0, 50).map((player) => (
                <div key={player.id} className="relative">
                  <PlayerCard
                    player={player}
                    onDraft={() => handleUserDraftPick(player)}
                  />
                  <div className="absolute top-2 right-2 flex space-x-1">
                    <button
                      onClick={() => addToQueue(player)}
                      disabled={userQueue.find(p => p.id === player.id) !== undefined}
                      className="w-8 h-8 bg-blue-600 text-white rounded-full text-xs hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Add to queue"
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
            {filteredPlayers.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No players match your current filters.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Settings */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <h3 className="font-semibold mb-3">Mock Draft Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Auto Pick Delay (seconds)
            </label>
            <select
              value={autoPickDelay}
              onChange={(e) => setAutoPickDelay(parseInt(e.target.value))}
              disabled={isActive}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            >
              <option value={1}>1 second</option>
              <option value={3}>3 seconds</option>
              <option value={5}>5 seconds</option>
              <option value={10}>10 seconds</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Draft Format
            </label>
            <select
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
            >
              <option>Snake Draft</option>
            </select>
          </div>
        </div>
      </div>

      {/* Instructions */}
      {!isActive && !isDraftComplete && (
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <h3 className="font-semibold text-blue-800 mb-2">How Mock Draft Works</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Practice your draft strategy with simulated CPU opponents</li>
            <li>• Add players to your queue to automatically draft them</li>
            <li>• CPU teams will make picks based on player rankings and positional needs</li>
            <li>• Save your mock draft results to reference during the real draft</li>
            <li>• Reset anytime to try different strategies</li>
          </ul>
        </div>
      )}
    </div>
  );
};