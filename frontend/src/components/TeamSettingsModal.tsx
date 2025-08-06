// frontend/src/components/TeamSettingsModal.tsx
import React, { useState, useRef } from 'react';
import { Team } from '../types';

// Define local interfaces for missing types
interface NotificationSettings {
  trades: boolean;
  waivers: boolean;
  lineupReminders: boolean;
  news: boolean;
  scores: boolean;
}

interface CoOwner {
  userId: string;
  name: string;
  email: string;
}

interface TeamSettingsModalProps {
  team: Team;
  isOpen: boolean;
  onClose: () => void;
  onUpdateTeam: (updates: Partial<Team>) => Promise<void>;
  onUpdateNotifications: (settings: NotificationSettings) => Promise<void>;
  onAddCoOwner: (email: string) => Promise<void>;
  onRemoveCoOwner: (userId: string) => Promise<void>;
}

export const TeamSettingsModal: React.FC<TeamSettingsModalProps> = ({
  team,
  isOpen,
  onClose,
  onUpdateTeam,
  onUpdateNotifications,
  onAddCoOwner,
  onRemoveCoOwner
}) => {
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'coowners'>('profile');
  const [teamName, setTeamName] = useState(team.name);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string>(team.logo_url || '');
  const [notifications, setNotifications] = useState<NotificationSettings>(
    // Map from team settings to notification settings
    {
      trades: team.settings?.notifications?.trades ?? true,
      waivers: team.settings?.notifications?.waivers ?? true,
      lineupReminders: true, // Default value
      news: team.settings?.notifications?.news ?? true,
      scores: true // Default value
    }
  );
  const [coOwnerEmail, setCoOwnerEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Mock co-owners data (since it's not in Team interface)
  const coOwners: CoOwner[] = team.settings?.co_owners?.map((id, index) => ({
    userId: id,
    name: `Co-Owner ${index + 1}`,
    email: `coowner${index + 1}@example.com`
  })) || [];

  if (!isOpen) return null;

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setError('Logo file must be less than 5MB');
        return;
      }
      
      setLogoFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setLogoPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSaveProfile = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      const updates: Partial<Team> = {
        name: teamName
      };

      if (logoFile) {
        // In a real app, you'd upload the file to storage and get a URL
        // For now, we'll use the preview as the URL
        updates.logo_url = logoPreview;
      }

      await onUpdateTeam(updates);
      setSuccess('Team profile updated successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveNotifications = async () => {
    try {
      setIsLoading(true);
      setError('');
      await onUpdateNotifications(notifications);
      setSuccess('Notification settings updated successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update notifications');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddCoOwner = async () => {
    if (!coOwnerEmail.trim()) return;
    
    try {
      setIsLoading(true);
      setError('');
      await onAddCoOwner(coOwnerEmail.trim());
      setCoOwnerEmail('');
      setSuccess('Co-owner invitation sent successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add co-owner');
    } finally {
      setIsLoading(false);
    }
  };

  const tabs = [
    { id: 'profile', label: 'Team Profile', icon: '👤' },
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'coowners', label: 'Co-Owners', icon: '👥' }
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold">Team Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 px-4 py-3 text-sm font-medium ${
                activeTab === tab.id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-96">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg">
              {success}
            </div>
          )}

          {/* Team Profile Tab */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Team Name
                </label>
                <input
                  type="text"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Team Logo
                </label>
                <div className="flex items-center space-x-4">
                  {logoPreview && (
                    <img
                      src={logoPreview}
                      alt="Team logo preview"
                      className="w-16 h-16 rounded-full object-cover"
                    />
                  )}
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleLogoChange}
                      className="hidden"
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Upload Logo
                    </button>
                    <p className="text-xs text-gray-500 mt-1">Max 5MB</p>
                  </div>
                </div>
              </div>

              <button
                onClick={handleSaveProfile}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-4">
              {Object.entries(notifications).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-2">
                  <div>
                    <p className="font-medium capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </p>
                    <p className="text-sm text-gray-500">
                      {key === 'trades' && 'Get notified about trade proposals and completions'}
                      {key === 'waivers' && 'Get notified about waiver claims and results'}
                      {key === 'lineupReminders' && 'Get reminded to set your lineup'}
                      {key === 'news' && 'Get player news and injury updates'}
                      {key === 'scores' && 'Get live score updates during games'}
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={value as boolean}
                      onChange={(e) => setNotifications({
                        ...notifications,
                        [key]: e.target.checked
                      })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              ))}

              <button
                onClick={handleSaveNotifications}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Notifications'}
              </button>
            </div>
          )}

          {/* Co-Owners Tab */}
          {activeTab === 'coowners' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Add Co-Owner
                </label>
                <div className="flex space-x-2">
                  <input
                    type="email"
                    placeholder="Enter email address"
                    value={coOwnerEmail}
                    onChange={(e) => setCoOwnerEmail(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    onClick={handleAddCoOwner}
                    disabled={isLoading || !coOwnerEmail.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    Add
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Co-owners can manage your team and make lineup changes
                </p>
              </div>

              {coOwners && coOwners.length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Current Co-Owners</h4>
                  <div className="space-y-2">
                    {coOwners.map((coOwner) => (
                      <div key={coOwner.userId} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium">{coOwner.name}</p>
                          <p className="text-sm text-gray-500">{coOwner.email}</p>
                        </div>
                        <button
                          onClick={() => onRemoveCoOwner(coOwner.userId)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {coOwners.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">👥</div>
                  <p>No co-owners added yet</p>
                  <p className="text-sm">Invite someone to help manage your team</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};