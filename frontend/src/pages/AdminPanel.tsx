// frontend/src/pages/AdminPanel.tsx
import React, { useState } from 'react';
import { useAppContext } from '../store';
import { Team, Player, Matchup } from '../types';
import { api } from '../services/api';

export const AdminPanel: React.FC = () => {
  const { state } = useAppContext();
  const { currentLeague, user } = state;
  
  const [activeSection, setActiveSection] = useState<'teams' | 'rosters' | 'matchups' | 'trades' | 'waivers' | 'settings'>('teams');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Check if user is commissioner
  const isCommissioner = user?.uid === currentLeague?.commissionerId;

  if (!isCommissioner) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          You don't have permission to access this page. Only the league commissioner can access admin functions.
        </div>
      </div>
    );
  }

  const adminSections = [
    { id: 'teams', label: 'Manage Teams', icon: '👥' },
    { id: 'rosters', label: 'Edit Rosters', icon: '📝' },
    { id: 'matchups', label: 'Edit Matchups', icon: '⚔️' },
    { id: 'trades', label: 'Manage Trades', icon: '🔄' },
    { id: 'waivers', label: 'Waiver Control', icon: '📋' },
    { id: 'settings', label: 'League Settings', icon: '⚙️' }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Commissioner Panel</h1>
        <p className="text-gray-600">Manage {currentLeague?.name} league settings and operations</p>
      </div>

      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
          {success}
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Admin Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adminSections.map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id as any)}
            className={`p-6 text-left border-2 rounded-lg transition-colors ${
              activeSection === section.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="text-3xl mb-2">{section.icon}</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">{section.label}</h3>
            <p className="text-sm text-gray-600">
              {section.id === 'teams' && 'Add, remove, or modify team information'}
              {section.id === 'rosters' && 'Edit player rosters for any team'}
              {section.id === 'matchups' && 'Manually adjust scores and results'}
              {section.id === 'trades' && 'Review and manage trade proposals'}
              {section.id === 'waivers' && 'Control waiver wire and budgets'}
              {section.id === 'settings' && 'Update league rules and settings'}
            </p>
          </button>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
            Lock All Rosters
          </button>
          <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
            Unlock All Rosters
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Process Waivers
          </button>
          <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
            Generate Playoff Bracket
          </button>
        </div>
      </div>

      {/* Warning */}
      <div className="mt-6 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg">
        <p className="text-sm">
          <strong>⚠️ Commissioner Notice:</strong> These tools give you powerful control over the league. 
          Use them responsibly and communicate changes to league members when appropriate.
        </p>
      </div>
    </div>
  );
};