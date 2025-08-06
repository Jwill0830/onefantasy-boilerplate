// frontend/src/pages/PlayersView.tsx
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../store';
import { PlayerCard } from '../components/PlayerCard';
import { SearchFilter } from '../components/SearchFilter';
import { WaiverBid } from '../components/WaiverBid';
import { TradeProposal } from '../components/TradeProposal';
import { Player, WaiverBid as WaiverBidType, Trade } from '../types';
import { api } from '../services/api';
import { usePlayerSearch } from '../hooks/usePlayerSearch';

export const PlayersView: React.FC = () => {
  const { state } = useAppContext();
  const { userTeam, currentLeague } = state;
  
  const [activeTab, setActiveTab] = useState<'search' | 'trending' | 'available' | 'leaders' | 'trade'>('search');
  const [showWaiverBid, setShowWaiverBid] = useState<Player | null>(null);
  const [showTradeProposal, setShowTradeProposal] = useState<Player | null>(null);
  const [waiverBids, setWaiverBids] = useState<WaiverBidType[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [trending, setTrending] = useState<Player[]>([]);
  const [leaders, setLeaders] = useState<Player[]>([]);
  
  const {
    players,
    loading,
    error,
    searchTerm,
    setSearchTerm,
    selectedPosition,
    setSelectedPosition,
    selectedTeam,
    setSelectedTeam,
    sortBy,
    setSortBy,
    fetchPlayers
  } = usePlayerSearch();

  useEffect(() => {
    fetchPlayers();
    fetchWaiverBids();
    fetchTrades();
    if (activeTab === 'trending') fetchTrending();
    if (activeTab === 'leaders') fetchLeaders();
  }, [activeTab]);

  const fetchWaiverBids = async () => {
    try {
      if (userTeam) {
        const bids = await api.getTeamWaiverBids(userTeam.id);
        setWaiverBids(bids);
      }
    } catch (err) {
      console.error('Failed to fetch waiver bids:', err);
    }
  };

  const fetchTrades = async () => {
    try {
      if (userTeam) {
        const teamTrades = await api.getTeamTrades(userTeam.id);
        setTrades(teamTrades);
      }
    } catch (err) {
      console.error('Failed to fetch trades:', err);
    }
  };

  const fetchTrending = async () => {
    try {
      const trendingPlayers = await api.getTrendingPlayers();
      setTrending(trendingPlayers);
    } catch (err) {
      console.error('Failed to fetch trending players:', err);
    }
  };

  const fetchLeaders = async () => {
    try {
      const leaderPlayers = await api.getPlayerLeaders();
      setLeaders(leaderPlayers);
    } catch (err) {
      console.error('Failed to fetch player leaders:', err);
    }
  };

  const handleWaiverBid = async (playerId: string, bidAmount: number, dropPlayerId?: string) => {
    try {
      await api.submitWaiverBid(userTeam!.id, playerId, bidAmount, dropPlayerId);
      await fetchWaiverBids();
      setShowWaiverBid(null);
    } catch (err) {
      throw new Error('Failed to submit waiver bid');
    }
  };

  const handleTradeProposal = async (targetTeamId: string, offeredPlayers: string[], requestedPlayers: string[]) => {
    try {
      await api.proposeTrade(userTeam!.id, targetTeamId, offeredPlayers, requestedPlayers);
      await fetchTrades();
      setShowTradeProposal(null);
    } catch (err) {
      throw new Error('Failed to propose trade');
    }
  };

  const tabs = [
    { id: 'search', label: 'Search', icon: '🔍' },
    { id: 'trending', label: 'Trending', icon: '📈' },
    { id: 'available', label: 'Available', icon: '🆓' },
    { id: 'leaders', label: 'Leaders', icon: '👑' },
    { id: 'trade', label: 'Trade Block', icon: '🔄' }
  ];

  const getPlayersForTab = () => {
    switch (activeTab) {
      case 'trending':
        return trending;
      case 'available':
        return players.filter(p => p.isAvailable);
      case 'leaders':
        return leaders;
      case 'trade':
        return players.filter(p => p.onTradingBlock);
      default:
        return players;
    }
  };

  if (!userTeam || !currentLeague) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading...</span>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Players</h1>
        <p className="text-gray-600">Search, track, and manage players for your fantasy team</p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Search Filters */}
          {(activeTab === 'search' || activeTab === 'available') && (
            <div className="mb-6">
              <SearchFilter
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                selectedPosition={selectedPosition}
                onPositionChange={setSelectedPosition}
                selectedTeam={selectedTeam}
                onTeamChange={setSelectedTeam}
                sortBy={sortBy}
                onSortChange={setSortBy}
                positions={['', 'GK', 'DEF', 'MID', 'FWD']}
                showTeamFilter={true}
              />
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading players...</span>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* Players Grid */}
          {!loading && !error && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {getPlayersForTab().map((player) => {
                const existingBid = waiverBids.find(bid => bid.playerId === player.id);
                
                return (
                  <div key={player.id} className="relative">
                    <PlayerCard
                      player={player}
                      showDraftButton={false}
                      showStats={true}
                    />
                    
                    {/* Action Buttons */}
                    <div className="absolute top-2 right-2 flex flex-col space-y-1">
                      {activeTab === 'available' && (
                        <button
                          onClick={() => setShowWaiverBid(player)}
                          className={`px-3 py-1 rounded text-xs font-medium ${
                            existingBid 
                              ? 'bg-yellow-600 text-white' 
                              : 'bg-blue-600 text-white hover:bg-blue-700'
                          }`}
                        >
                          {existingBid ? `Bid: ${existingBid.bidAmount}` : 'Bid'}
                        </button>
                      )}
                      
                      {(activeTab === 'trade' || activeTab === 'search') && (
                        <button
                          onClick={() => setShowTradeProposal(player)}
                          className="px-3 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
                        >
                          Trade
                        </button>
                      )}
                      
                      <button
                        onClick={() => {/* Track player logic */}}
                        className="px-3 py-1 bg-gray-600 text-white rounded text-xs font-medium hover:bg-gray-700"
                      >
                        Track
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && getPlayersForTab().length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">👤</div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">
                No Players Found
              </h3>
              <p className="text-gray-500">
                Try adjusting your search filters or check back later.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Waiver Bid Modal */}
      {showWaiverBid && (
        <WaiverBid
          player={showWaiverBid}
          userTeam={userTeam}
          maxBid={userTeam.waiverBudget || 100}
          onSubmitBid={handleWaiverBid}
          onClose={() => setShowWaiverBid(null)}
          existingBid={waiverBids.find(bid => bid.playerId === showWaiverBid.id)}
        />
      )}

      {/* Trade Proposal Modal */}
      {showTradeProposal && (
        <TradeProposal
          targetPlayer={showTradeProposal}
          userTeam={userTeam}
          leagueTeams={currentLeague.teams}
          onProposeTrade={handleTradeProposal}
          onClose={() => setShowTradeProposal(null)}
        />
      )}
    </div>
  );
};
