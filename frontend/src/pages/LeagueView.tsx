// frontend/src/pages/LeagueView.tsx
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../store';
import { StandingsTable } from '../components/StandingsTable';
import { Team, Matchup, LeagueSettings } from '../types';
import { api } from '../services/api';
import { formatters } from '../utils/formatters';

export const LeagueView: React.FC = () => {
  const { state } = useAppContext();
  const { currentLeague } = state;
  
  const [activeTab, setActiveTab] = useState<'standings' | 'schedule' | 'settings'>('standings');
  const [matchups, setMatchups] = useState<Matchup[]>([]);
  const [currentWeek, setCurrentWeek] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (currentLeague) {
      fetchMatchups();
    }
  }, [currentLeague, currentWeek]);

  const fetchMatchups = async () => {
    try {
      setLoading(true);
      const weekMatchups = await api.getWeekMatchups(currentLeague!.id, currentWeek);
      setMatchups(weekMatchups);
    } catch (err) {
      setError('Failed to fetch matchups');
    } finally {
      setLoading(false);
    }
  };

  if (!currentLeague) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading league...</span>
      </div>
    );
  }

  const tabs = [
    { id: 'standings', label: 'Standings', icon: '🏆' },
    { id: 'schedule', label: 'Schedule', icon: '📅' },
    { id: 'settings', label: 'League Settings', icon: '⚙️' }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* League Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{currentLeague.name}</h1>
            <p className="text-lg text-gray-600">Season {currentLeague.season}</p>
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
              <span>{currentLeague.teams.length} Teams</span>
              <span>Commissioner: {currentLeague.commissionerName}</span>
              <span>Week {currentWeek}</span>
            </div>
          </div>
          
          <div className="text-right">
            <div className="text-sm text-gray-500">League ID</div>
            <div className="font-mono text-lg">{currentLeague.id}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
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
          {activeTab === 'standings' && (
            <div>
              <StandingsTable
                teams={currentLeague.teams}
                showDetails={true}
              />
              
              {/* League Stats */}
              <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatters.formatNumber(
                      currentLeague.teams.reduce((sum, team) => sum + (team.pointsFor || 0), 0) / currentLeague.teams.length
                    )}
                  </div>
                  <div className="text-sm text-gray-600">Average Points/Team</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {Math.max(...currentLeague.teams.map(t => t.pointsFor || 0))}
                  </div>
                  <div className="text-sm text-gray-600">Highest Weekly Score</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {Math.min(...currentLeague.teams.map(t => t.pointsFor || 0))}
                  </div>
                  <div className="text-sm text-gray-600">Lowest Weekly Score</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {currentWeek}
                  </div>
                  <div className="text-sm text-gray-600">Current Week</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'schedule' && (
            <div>
              {/* Week Selector */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">Week {currentWeek} Matchups</h2>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentWeek(Math.max(1, currentWeek - 1))}
                    disabled={currentWeek <= 1}
                    className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-1 bg-blue-100 text-blue-800 rounded">
                    Week {currentWeek}
                  </span>
                  <button
                    onClick={() => setCurrentWeek(currentWeek + 1)}
                    className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                  >
                    Next
                  </button>
                </div>
              </div>

              {/* Matchups */}
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  <span className="ml-2 text-gray-600">Loading matchups...</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {matchups.map((matchup) => (
                    <div key={matchup.id} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="font-medium">{matchup.team1.name}</div>
                          <div className="text-sm text-gray-500">
                            {matchup.team1.wins}-{matchup.team1.losses}
                          </div>
                        </div>
                        <div className="text-center px-4">
                          <div className="text-lg font-bold">
                            {matchup.team1Score?.toFixed(1) || '-'} - {matchup.team2Score?.toFixed(1) || '-'}
                          </div>
                          <div className="text-xs text-gray-500">VS</div>
                        </div>
                        <div className="flex-1 text-right">
                          <div className="font-medium">{matchup.team2.name}</div>
                          <div className="text-sm text-gray-500">
                            {matchup.team2.wins}-{matchup.team2.losses}
                          </div>
                        </div>
                      </div>
                      
                      {matchup.status === 'completed' && (
                        <div className="mt-2 text-center text-sm">
                          <span className={`font-medium ${
                            (matchup.team1Score || 0) > (matchup.team2Score || 0) 
                              ? 'text-green-600' 
                              : 'text-red-600'
                          }`}>
                            {(matchup.team1Score || 0) > (matchup.team2Score || 0) 
                              ? matchup.team1.name 
                              : matchup.team2.name} wins
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-6">
              {/* Scoring Settings */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Scoring Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Goals:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.scoring?.goals || 4} pts</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Assists:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.scoring?.assists || 3} pts</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Clean Sheets:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.scoring?.cleanSheets || 4} pts</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Yellow Cards:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.scoring?.yellowCards || -1} pts</span>
                  </div>
                </div>
              </div>

              {/* League Rules */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">League Rules</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Roster Size:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.rosterSize || 15}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Starting Lineup:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.startingLineupSize || 11}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Waiver Budget:</span>
                    <span className="ml-2 font-medium">${currentLeague.settings?.waiverBudget || 100}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Trade Deadline:</span>
                    <span className="ml-2 font-medium">
                      {currentLeague.settings?.tradeDeadline 
                        ? formatters.formatDate(currentLeague.settings.tradeDeadline)
                        : 'None'
                      }
                    </span>
                  </div>
                </div>
              </div>

              {/* Playoff Settings */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Playoff Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Playoff Teams:</span>
                    <span className="ml-2 font-medium">{currentLeague.settings?.playoffTeams || 4}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Playoff Weeks:</span>
                    <span className="ml-2 font-medium">
                      {currentLeague.settings?.playoffStartWeek || 14} - {currentLeague.settings?.playoffEndWeek || 16}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
