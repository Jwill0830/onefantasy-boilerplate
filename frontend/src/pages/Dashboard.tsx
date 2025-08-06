/**
 * Main dashboard component with tabs for different views.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useSocket } from '../hooks/useSocket';
import { League, TabType } from '../types';
import apiService from '../services/api';
import toast from 'react-hot-toast';

// Tab components (will be created separately)
import MyTeamView from '../components/MyTeamView';
import PlayersView from '../components/PlayersView';
import LeagueView from '../components/LeagueView';
import ChatView from '../components/ChatView';
import AdminPanel from '../components/AdminPanel';
import DraftRoom from './DraftRoom';

const Dashboard: React.FC = () => {
  const { currentUser } = useAuth();
  const { joinLeague, leaveLeague } = useSocket();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [leagues, setLeagues] = useState<League[]>([]);
  const [selectedLeague, setSelectedLeague] = useState<League | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('my-team');
  const [loading, setLoading] = useState(true);
  const [showCreateLeague, setShowCreateLeague] = useState(false);
  const [showJoinLeague, setShowJoinLeague] = useState(false);

  // Get league and tab from URL params
  const leagueIdParam = searchParams.get('league');
  const tabParam = searchParams.get('tab') as TabType;

  useEffect(() => {
    loadUserLeagues();
  }, []);

  useEffect(() => {
    // Set active tab from URL
    if (tabParam && ['draft', 'my-team', 'players', 'league', 'playoffs', 'chat', 'admin'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  useEffect(() => {
    // Set selected league from URL
    if (leagueIdParam && leagues.length > 0) {
      const league = leagues.find(l => l.id === leagueIdParam);
      if (league) {
        setSelectedLeague(league);
        joinLeague(league.id);
      }
    } else if (leagues.length > 0 && !selectedLeague) {
      // Auto-select first league if none selected
      setSelectedLeague(leagues[0]);
      joinLeague(leagues[0].id);
      updateUrlParams(leagues[0].id, activeTab);
    }
  }, [leagueIdParam, leagues, selectedLeague, joinLeague, activeTab]);

  const loadUserLeagues = async () => {
    try {
      setLoading(true);
      const response = await apiService.getUserLeagues();
      if (response.data) {
        setLeagues(response.data.leagues);
      } else {
        toast.error(response.error || 'Failed to load leagues');
      }
    } catch (error) {
      console.error('Error loading leagues:', error);
      toast.error('Failed to load leagues');
    } finally {
      setLoading(false);
    }
  };

  const updateUrlParams = (leagueId: string, tab: TabType) => {
    setSearchParams({ league: leagueId, tab });
  };

  const handleLeagueChange = (league: League) => {
    if (selectedLeague) {
      leaveLeague(selectedLeague.id);
    }
    setSelectedLeague(league);
    joinLeague(league.id);
    updateUrlParams(league.id, activeTab);
  };

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    if (selectedLeague) {
      updateUrlParams(selectedLeague.id, tab);
    }
    
    // Navigate to draft room if draft tab is selected
    if (tab === 'draft' && selectedLeague) {
      navigate(`/league/${selectedLeague.id}/draft`);
    }
  };

  const isCommissioner = (league: League): boolean => {
    return league.commissioner_id === currentUser?.uid;
  };

  const canAccessAdmin = (league: League): boolean => {
    return isCommissioner(league);
  };

  const getTabTitle = (tab: TabType): string => {
    const titles: Record<TabType, string> = {
      'draft': 'Draft Room',
      'my-team': 'My Team',
      'players': 'Players',
      'league': 'League',
      'playoffs': 'Playoffs',
      'chat': 'Chat',
      'admin': 'Admin'
    };
    return titles[tab];
  };

  const getTabIcon = (tab: TabType): string => {
    const icons: Record<TabType, string> = {
      'draft': '🏁',
      'my-team': '👤',
      'players': '⚽',
      'league': '🏆',
      'playoffs': '🥇',
      'chat': '💬',
      'admin': '⚙️'
    };
    return icons[tab];
  };

  const renderTabContent = () => {
    if (!selectedLeague) return null;

    switch (activeTab) {
      case 'draft':
        return <DraftRoom />;
      case 'my-team':
        return <MyTeamView league={selectedLeague} />;
      case 'players':
        return <PlayersView league={selectedLeague} />;
      case 'league':
        return <LeagueView league={selectedLeague} />;
      case 'chat':
        return <ChatView league={selectedLeague} />;
      case 'admin':
        return canAccessAdmin(selectedLeague) ? (
          <AdminPanel league={selectedLeague} />
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500">Access denied. Only commissioners can access admin tools.</p>
          </div>
        );
      default:
        return <div className="text-center py-8"><p>Tab content not implemented yet</p></div>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (leagues.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Welcome to OneFantasy!</h2>
          <p className="text-gray-600 mb-8">You haven't joined any leagues yet.</p>
          <div className="space-x-4">
            <button
              onClick={() => setShowCreateLeague(true)}
              className="btn-primary"
            >
              Create League
            </button>
            <button
              onClick={() => setShowJoinLeague(true)}
              className="btn-secondary"
            >
              Join League
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-blue-600">OneFantasy</h1>
            </div>

            {/* League Selector */}
            <div className="flex items-center space-x-4">
              <select
                value={selectedLeague?.id || ''}
                onChange={(e) => {
                  const league = leagues.find(l => l.id === e.target.value);
                  if (league) handleLeagueChange(league);
                }}
                className="input max-w-xs"
              >
                {leagues.map(league => (
                  <option key={league.id} value={league.id}>
                    {league.name}
                  </option>
                ))}
              </select>

              {/* User Menu */}
              <div className="flex items-center space-x-2">
                <img
                  src={currentUser?.photo_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(currentUser?.display_name || 'User')}&background=3b82f6&color=fff`}
                  alt={currentUser?.display_name}
                  className="w-8 h-8 rounded-full"
                />
                <span className="text-sm text-gray-700">{currentUser?.display_name}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      {selectedLeague && (
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex space-x-8 overflow-x-auto">
              {(['my-team', 'players', 'league', 'draft', 'chat'] as TabType[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => handleTabChange(tab)}
                  className={`${
                    activeTab === tab ? 'tab-active' : 'tab'
                  } flex items-center space-x-2 py-4`}
                >
                  <span>{getTabIcon(tab)}</span>
                  <span>{getTabTitle(tab)}</span>
                </button>
              ))}
              
              {/* Admin tab - only show for commissioners */}
              {canAccessAdmin(selectedLeague) && (
                <button
                  onClick={() => handleTabChange('admin')}
                  className={`${
                    activeTab === 'admin' ? 'tab-active' : 'tab'
                  } flex items-center space-x-2 py-4`}
                >
                  <span>{getTabIcon('admin')}</span>
                  <span>{getTabTitle('admin')}</span>
                </button>
              )}
            </nav>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderTabContent()}
      </main>

      {/* Modals would go here */}
      {/* <CreateLeagueModal /> */}
      {/* <JoinLeagueModal /> */}
    </div>
  );
};

export default Dashboard;