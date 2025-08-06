// frontend/src/pages/DraftRoom.tsx - Complete implementation
/**
 * DraftRoom page - Live draft interface with grid, available players, and chat
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useDraftState } from '../hooks/useDraftState';
import { usePlayerSearch } from '../hooks/usePlayerSearch';
import DraftGrid from '../components/DraftGrid';
import PlayerCard from '../components/PlayerCard';
import CountdownTimer from '../components/CountdownTimer';
import ChatFeed from '../components/ChatFeed';
import SearchFilter from '../components/SearchFilter';
import { PlayerFilters } from '../types';

const DraftRoom: React.FC = () => {
  const { draftId } = useParams<{ draftId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'board' | 'players' | 'queue'>('board');
  const [playerFilters, setPlayerFilters] = useState<PlayerFilters>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [playerQueue, setPlayerQueue] = useState<number[]>([]);
  const [showFullPagePlayers, setShowFullPagePlayers] = useState(false);

  // Draft state management
  const {
    draft,
    availablePlayers,
    draftPicks,
    currentPick,
    currentTeam,
    isMyTurn,
    timeRemaining,
    loading,
    error,
    makePick,
    startDraft,
    pauseDraft,
    resumeDraft,
    searchAvailablePlayers,
    clearError,
  } = useDraftState(draftId || null, user?.uid || null);

  // Player search for additional functionality
  const { getPlayerDetails } = usePlayerSearch();

  // Filter available players
  const filteredPlayers = useMemo(() => {
    let filtered = [...availablePlayers];

    // Apply search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(player =>
        player.web_name.toLowerCase().includes(query) ||
        player.team.toLowerCase().includes(query)
      );
    }

    // Apply filters
    if (playerFilters.position?.length) {
      filtered = filtered.filter(player => 
        playerFilters.position!.includes(player.position)
      );
    }

    if (playerFilters.team?.length) {
      filtered = filtered.filter(player =>
        playerFilters.team!.includes(player.team)
      );
    }

    if (playerFilters.minPrice) {
      filtered = filtered.filter(player => player.now_cost >= playerFilters.minPrice!);
    }

    if (playerFilters.maxPrice) {
      filtered = filtered.filter(player => player.now_cost <= playerFilters.maxPrice!);
    }

    // Sort by draft rank
    return filtered.sort((a, b) => (b.draft_rank || 0) - (a.draft_rank || 0));
  }, [availablePlayers, searchQuery, playerFilters]);

  // Queue management
  const addToQueue = (playerId: number) => {
    if (!playerQueue.includes(playerId)) {
      setPlayerQueue(prev => [...prev, playerId]);
    }
  };

  const removeFromQueue = (playerId: number) => {
    setPlayerQueue(prev => prev.filter(id => id !== playerId));
  };

  const moveInQueue = (playerId: number, direction: 'up' | 'down') => {
    setPlayerQueue(prev => {
      const index = prev.indexOf(playerId);
      if (index === -1) return prev;

      const newQueue = [...prev];
      if (direction === 'up' && index > 0) {
        [newQueue[index - 1], newQueue[index]] = [newQueue[index], newQueue[index - 1]];
      } else if (direction === 'down' && index < newQueue.length - 1) {
        [newQueue[index], newQueue[index + 1]] = [newQueue[index + 1], newQueue[index]];
      }
      return newQueue;
    });
  };

  // Handle pick
  const handleMakePick = async (playerId: number) => {
    if (!isMyTurn) return;

    const success = await makePick(playerId);
    if (success) {
      // Remove from queue if it was queued
      removeFromQueue(playerId);
    }
  };

  // Auto-pick from queue
  const pickFromQueue = async () => {
    if (playerQueue.length === 0 || !isMyTurn) return;

    const nextPlayerId = playerQueue[0];
    await handleMakePick(nextPlayerId);
  };

  // Handle draft actions
  const handleStartDraft = async () => {
    await startDraft();
  };

  const handlePauseDraft = async () => {
    await pauseDraft();
  };

  const handleResumeDraft = async () => {
    await resumeDraft();
  };

  // Redirect if no draft ID
  useEffect(() => {
    if (!draftId) {
      navigate('/dashboard');
    }
  }, [draftId, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading draft room...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">⚠️ Draft Error</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => {
              clearError();
              navigate('/dashboard');
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Draft not found</p>
        </div>
      </div>
    );
  }

  // Full page players view
  if (showFullPagePlayers) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Available Players</h1>
            <button
              onClick={() => setShowFullPagePlayers(false)}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              Back to Draft
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Search and Filters */}
            <div className="lg:col-span-1">
              <SearchFilter
                onFiltersChange={setPlayerFilters}
                onSearch={setSearchQuery}
                initialFilters={playerFilters}
              />
              
              {/* Queue */}
              {playerQueue.length > 0 && (
                <div className="mt-6 bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="font-medium text-gray-900 mb-3">
                    Your Queue ({playerQueue.length})
                  </h3>
                  <div className="space-y-2">
                    {playerQueue.map((playerId, index) => {
                      const player = availablePlayers.find(p => p.fpl_id === playerId);
                      if (!player) return null;

                      return (
                        <div key={playerId} className="flex items-center gap-2 p-2 bg-blue-50 rounded">
                          <span className="text-sm font-medium text-blue-800">
                            {index + 1}.
                          </span>
                          <span className="flex-1 text-sm">{player.web_name}</span>
                          <div className="flex gap-1">
                            <button
                              onClick={() => moveInQueue(playerId, 'up')}
                              disabled={index === 0}
                              className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                            >
                              ↑
                            </button>
                            <button
                              onClick={() => moveInQueue(playerId, 'down')}
                              disabled={index === playerQueue.length - 1}
                              className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                            >
                              ↓
                            </button>
                            <button
                              onClick={() => removeFromQueue(playerId)}
                              className="text-red-600 hover:text-red-800"
                            >
                              ×
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Players Grid */}
            <div className="lg:col-span-3">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredPlayers.map(player => (
                  <PlayerCard
                    key={player.fpl_id}
                    player={player}
                    variant="draft"
                    showActions={true}
                    onDraft={isMyTurn ? handleMakePick : addToQueue}
                    className="h-full"
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Draft Room</h1>
            <p className="text-sm text-gray-600">
              {draft.league_name} • {draft.draft_type} Draft
            </p>
          </div>

          {/* Draft Controls */}
          <div className="flex items-center gap-4">
            {draft.status === 'scheduled' && (
              <button
                onClick={handleStartDraft}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Start Draft
              </button>
            )}

            {draft.status === 'active' && (
              <button
                onClick={handlePauseDraft}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
              >
                Pause Draft
              </button>
            )}

            {draft.status === 'paused' && (
              <button
                onClick={handleResumeDraft}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Resume Draft
              </button>
            )}

            <button
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Exit Draft
            </button>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          {/* Main Content */}
          <div className="xl:col-span-3">
            {/* Current Pick Status */}
            {draft.status === 'active' && (
              <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">
                      {isMyTurn ? "It's Your Turn!" : `${currentTeam?.name} is picking`}
                    </h3>
                    <p className="text-sm text-gray-600">
                      Pick {currentPick} of {draft.total_picks} • Round {Math.ceil(currentPick / (draft.draft_order?.length || 1))}
                    </p>
                  </div>

                  {/* Timer */}
                  {timeRemaining > 0 && (
                    <CountdownTimer
                      duration={timeRemaining}
                      format="compact"
                      urgentThreshold={30}
                    />
                  )}

                  {/* Quick Actions */}
                  {isMyTurn && playerQueue.length > 0 && (
                    <button
                      onClick={pickFromQueue}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Pick from Queue
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Tab Navigation */}
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="border-b border-gray-200">
                <nav className="flex">
                  <button
                    onClick={() => setActiveTab('board')}
                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'board'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Draft Board
                  </button>
                  <button
                    onClick={() => setActiveTab('players')}
                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'players'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Available Players ({filteredPlayers.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('queue')}
                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'queue'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    My Queue ({playerQueue.length})
                  </button>
                </nav>
              </div>

              <div className="p-6">
                {/* Draft Board Tab */}
                {activeTab === 'board' && (
                  <DraftGrid
                    teams={draft.draft_order || []}
                    picks={draftPicks}
                    totalRounds={draft.rounds || 15}
                    currentPick={currentPick}
                    isSnakeDraft={draft.draft_type === 'snake'}
                  />
                )}

                {/* Available Players Tab */}
                {activeTab === 'players' && (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <SearchFilter
                        onFiltersChange={setPlayerFilters}
                        onSearch={setSearchQuery}
                        initialFilters={playerFilters}
                        showAdvanced={false}
                        className="flex-1 mr-4"
                      />
                      <button
                        onClick={() => setShowFullPagePlayers(true)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 whitespace-nowrap"
                      >
                        Full Page View
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
                      {filteredPlayers.slice(0, 12).map(player => (
                        <PlayerCard
                          key={player.fpl_id}
                          player={player}
                          variant="compact"
                          onClick={() => {
                            if (isMyTurn) {
                              handleMakePick(player.fpl_id);
                            } else {
                              addToQueue(player.fpl_id);
                            }
                          }}
                        />
                      ))}
                    </div>

                    {filteredPlayers.length > 12 && (
                      <div className="mt-4 text-center">
                        <button
                          onClick={() => setShowFullPagePlayers(true)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          View all {filteredPlayers.length} players →
                        </button>
                      </div>
                    )}

                    {filteredPlayers.length === 0 && (
                      <div className="text-center py-8 text-gray-500">
                        <div className="text-4xl mb-2">🔍</div>
                        <p>No players match your current filters.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Queue Tab */}
                {activeTab === 'queue' && (
                  <div>
                    {playerQueue.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <div className="text-4xl mb-2">📋</div>
                        <p className="mb-2">Your draft queue is empty.</p>
                        <p className="text-sm">Add players from the Available Players tab to queue them for drafting.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="font-medium text-gray-900">
                            Draft Queue ({playerQueue.length} players)
                          </h3>
                          {isMyTurn && (
                            <button
                              onClick={pickFromQueue}
                              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                              Draft Next Player
                            </button>
                          )}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {playerQueue.map((playerId, index) => {
                            const player = availablePlayers.find(p => p.fpl_id === playerId);
                            if (!player) return null;

                            return (
                              <div
                                key={playerId}
                                className={`bg-white border-2 rounded-lg p-4 ${
                                  index === 0 ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                                }`}
                              >
                                <div className="flex items-center gap-3">
                                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                                    index === 0 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                                  }`}>
                                    {index + 1}
                                  </div>
                                  
                                  <div className="flex-1">
                                    <h4 className="font-medium text-gray-900">{player.web_name}</h4>
                                    <p className="text-sm text-gray-600">
                                      {player.position} • {player.team} • £{player.now_cost / 10}m
                                    </p>
                                  </div>

                                  <div className="flex flex-col gap-1">
                                    <button
                                      onClick={() => moveInQueue(playerId, 'up')}
                                      disabled={index === 0}
                                      className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
                                    >
                                      ↑
                                    </button>
                                    <button
                                      onClick={() => moveInQueue(playerId, 'down')}
                                      disabled={index === playerQueue.length - 1}
                                      className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
                                    >
                                      ↓
                                    </button>
                                  </div>

                                  <button
                                    onClick={() => removeFromQueue(playerId)}
                                    className="px-2 py-1 text-xs bg-red-100 text-red-600 rounded hover:bg-red-200"
                                  >
                                    Remove
                                  </button>
                                </div>

                                {index === 0 && isMyTurn && (
                                  <div className="mt-2 text-xs text-blue-600 font-medium">
                                    ⭐ Next to be drafted
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="xl:col-span-1">
            <div className="space-y-6">
              {/* Draft Progress */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 mb-3">Draft Progress</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Current Pick:</span>
                    <span className="font-medium">{currentPick} / {draft.total_picks}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Round:</span>
                    <span className="font-medium">
                      {Math.ceil(currentPick / (draft.draft_order?.length || 1))} / {draft.rounds}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className={`font-medium capitalize ${
                      draft.status === 'active' ? 'text-green-600' : 
                      draft.status === 'completed' ? 'text-blue-600' : 
                      'text-yellow-600'
                    }`}>
                      {draft.status}
                    </span>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div className="mt-3">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(currentPick / draft.total_picks) * 100}%`
                      }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {Math.round((currentPick / draft.total_picks) * 100)}% complete
                  </p>
                </div>
              </div>

              {/* My Team Summary */}
              {draft.draft_order && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="font-medium text-gray-900 mb-3">My Team</h3>
                  <div className="space-y-2">
                    {draft.draft_order
                      .find(team => team.user_id === user?.uid)
                      ?.drafted_players?.map((pick, index) => (
                        <div key={pick.player_id} className="flex items-center gap-2 text-sm">
                          <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">
                            {index + 1}
                          </span>
                          <span className="flex-1">{pick.player_name}</span>
                          <span className="text-gray-500">{pick.position}</span>
                        </div>
                      )) || <p className="text-gray-500 text-sm">No picks yet</p>}
                  </div>
                </div>
              )}

              {/* Recent Picks */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 mb-3">Recent Picks</h3>
                <div className="space-y-2">
                  {draftPicks
                    .slice(-5)
                    .reverse()
                    .map((pick, index) => (
                      <div key={pick.id || index} className="flex items-center gap-2 text-sm">
                        <span className="text-gray-500">#{pick.overall_pick}</span>
                        <span className="flex-1 font-medium">{pick.player_name}</span>
                        <span className="text-gray-500">{pick.team_name}</span>
                      </div>
                    ))}
                  
                  {draftPicks.length === 0 && (
                    <p className="text-gray-500 text-sm">No picks yet</p>
                  )}
                </div>
              </div>

              {/* Chat */}
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h3 className="font-medium text-gray-900">Draft Chat</h3>
                </div>
                <div className="h-64">
                  <ChatFeed
                    messages={[]} // Messages would come from draft state
                    currentUserId={user?.uid || ''}
                    loading={false}
                    className="h-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DraftRoom;