// frontend/src/pages/MyTeam.tsx
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../store';
import { RosterDragDrop } from '../components/RosterDragDrop';
import { TeamSettingsModal } from '../components/TeamSettingsModal';
import { TransactionHistory } from '../components/TransactionHistory';
import { NewsFeed } from '../components/NewsFeed';
import { Player, Team, NotificationSettings, Transaction, NewsItem } from '../types';
import { api } from '../services/api';
import { formatters } from '../utils/formatters';

export const MyTeam: React.FC = () => {
  const { state } = useAppContext();
  const { userTeam, currentLeague, user } = state;
  
  const [activeTab, setActiveTab] = useState<'roster' | 'settings' | 'transactions' | 'news'>('roster');
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Redirect if no team
  useEffect(() => {
    if (!userTeam && !state.loading.league) {
      // Redirect to league selection or creation
      window.location.href = '/dashboard';
    }
  }, [userTeam, state.loading.league]);

  if (!userTeam || !currentLeague) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading your team...</span>
      </div>
    );
  }

  const handleUpdateRoster = async (newRoster: Player[]) => {
    try {
      setIsLoading(true);
      setError('');
      
      await api.updateTeamRoster(userTeam.id, newRoster);
      
      setSuccess('Roster updated successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update roster');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateTeam = async (updates: Partial<Team>) => {
    try {
      await api.updateTeam(userTeam.id, updates);
      setSuccess('Team updated successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update team');
    }
  };

  const handleUpdateNotifications = async (settings: NotificationSettings) => {
    try {
      await api.updateNotificationSettings(userTeam.id, settings);
      setSuccess('Notification settings updated!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update notifications');
    }
  };

  const handleAddCoOwner = async (email: string) => {
    try {
      await api.addCoOwner(userTeam.id, email);
      setSuccess('Co-owner invitation sent!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add co-owner');
    }
  };

  const handleRemoveCoOwner = async (userId: string) => {
    try {
      await api.removeCoOwner(userTeam.id, userId);
      setSuccess('Co-owner removed!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove co-owner');
    }
  };

  const fetchTransactions = async (filters?: any): Promise<Transaction[]> => {
    try {
      return await api.getTeamTransactions(userTeam.id, filters);
    } catch (err) {
      throw new Error('Failed to fetch transactions');
    }
  };

  const fetchNews = async (filters?: any): Promise<NewsItem[]> => {
    try {
      return await api.getTeamNews(userTeam.id, filters);
    } catch (err) {
      throw new Error('Failed to fetch news');
    }
  };

  const tabs = [
    { id: 'roster', label: 'My Roster', icon: '👥' },
    { id: 'transactions', label: 'Transactions', icon: '📋' },
    { id: 'news', label: 'Team News', icon: '📰' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Team Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {userTeam.logoUrl && (
              <img
                src={userTeam.logoUrl}
                alt="Team logo"
                className="w-16 h-16 rounded-full object-cover"
              />
            )}
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{userTeam.name}</h1>
              <p className="text-lg text-gray-600">Owned by {userTeam.ownerName}</p>
              <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                <span>Record: {userTeam.wins}-{userTeam.losses}</span>
                <span>Points For: {formatters.formatNumber(userTeam.pointsFor || 0)}</span>
                <span>Points Against: {formatters.formatNumber(userTeam.pointsAgainst || 0)}</span>
                <span>Waiver Budget: ${userTeam.waiverBudget || 100}</span>
              </div>
            </div>
          </div>
          
          {/* Quick Actions */}
          <div className="flex space-x-2">
            <button
              onClick={() => window.location.href = '/players?tab=available'}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Waiver Wire
            </button>
            <button
              onClick={() => window.location.href = '/players?tab=trade'}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              Trade
            </button>
            <button
              onClick={() => setShowSettingsModal(true)}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Team Settings
            </button>
          </div>
        </div>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
          {success}
        </div>
      )}

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
          {activeTab === 'roster' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">Starting Lineup & Bench</h2>
                <div className="text-sm text-gray-500">
                  Drag players to set your lineup for this week
                </div>
              </div>
              
              <RosterDragDrop
                team={userTeam}
                onUpdateRoster={handleUpdateRoster}
                isLoading={isLoading}
              />
              
              {/* Roster Stats */}
              <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {userTeam.roster.length}
                  </div>
                  <div className="text-sm text-gray-600">Total Players</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {userTeam.roster.filter(p => p.position === 'FWD').length}
                  </div>
                  <div className="text-sm text-gray-600">Forwards</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">
                    {userTeam.roster.filter(p => p.position === 'MID').length}
                  </div>
                  <div className="text-sm text-gray-600">Midfielders</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {userTeam.roster.filter(p => p.position === 'DEF').length}
                  </div>
                  <div className="text-sm text-gray-600">Defenders</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'transactions' && (
            <TransactionHistory
              teamId={userTeam.id}
              leagueId={currentLeague.id}
              onFetchTransactions={fetchTransactions}
            />
          )}

          {activeTab === 'news' && (
            <NewsFeed
              teamId={userTeam.id}
              leagueId={currentLeague.id}
              onFetchNews={fetchNews}
              maxItems={50}
            />
          )}

          {activeTab === 'settings' && (
            <div className="space-y-6">
              {/* Team Profile Card */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Team Profile</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Team Name
                    </label>
                    <div className="text-gray-900">{userTeam.name}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Owner Name
                    </label>
                    <div className="text-gray-900">{userTeam.ownerName}</div>
                  </div>
                </div>
                <button
                  onClick={() => setShowSettingsModal(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Edit Team Profile
                </button>
              </div>

              {/* Co-Owners Card */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Co-Owners</h3>
                {userTeam.coOwners && userTeam.coOwners.length > 0 ? (
                  <div className="space-y-2">
                    {userTeam.coOwners.map((coOwner) => (
                      <div key={coOwner.userId} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <div className="font-medium">{coOwner.name}</div>
                          <div className="text-sm text-gray-500">{coOwner.email}</div>
                        </div>
                        <button
                          onClick={() => handleRemoveCoOwner(coOwner.userId)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 mb-4">No co-owners added yet.</p>
                )}
                <button
                  onClick={() => setShowSettingsModal(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Add Co-Owner
                </button>
              </div>

              {/* League Information */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">League Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">League:</span>
                    <span className="ml-2 font-medium">{currentLeague.name}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Season:</span>
                    <span className="ml-2 font-medium">{currentLeague.season}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Teams:</span>
                    <span className="ml-2 font-medium">{currentLeague.teams.length}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Commissioner:</span>
                    <span className="ml-2 font-medium">{currentLeague.commissionerName}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Team Settings Modal */}
      <TeamSettingsModal
        team={userTeam}
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        onUpdateTeam={handleUpdateTeam}
        onUpdateNotifications={handleUpdateNotifications}
        onAddCoOwner={handleAddCoOwner}
        onRemoveCoOwner={handleRemoveCoOwner}
      />
    </div>
  );
};