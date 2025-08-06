/**
 * TradeProposal component - Trade creation and management interface
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Player, Team, Trade } from '../types';
import PlayerCard from './PlayerCard';

// Extended interfaces for properties that might not be in base types
interface ExtendedPlayer extends Omit<Player, 'web_name'> {
  fpl_id?: string;
  web_name?: string; // Override to make optional
}

interface ExtendedTeam extends Team {
  owner_name?: string;
}

interface ExtendedTrade extends Trade {
  target_team_id?: string;
  proposer_players?: ExtendedPlayer[];
  target_players?: ExtendedPlayer[];
  message?: string;
}

interface TradeProposalProps {
  userTeam: ExtendedTeam;
  allTeams: ExtendedTeam[];
  allPlayers: ExtendedPlayer[];
  existingTrade?: ExtendedTrade;
  onSubmit: (trade: TradeData) => Promise<boolean>;
  onCancel: () => void;
  className?: string;
}

interface TradeData {
  target_team_id: string;
  proposer_players: string[];
  target_players: string[];
  message?: string;
}

const TradeProposal: React.FC<TradeProposalProps> = ({
  userTeam,
  allTeams,
  allPlayers,
  existingTrade,
  onSubmit,
  onCancel,
  className = '',
}) => {
  const [selectedTargetTeam, setSelectedTargetTeam] = useState<string>(
    existingTrade?.target_team_id || ''
  );
  const [proposerPlayers, setProposerPlayers] = useState<string[]>(
    existingTrade?.proposer_players?.map(p => getPlayerId(p)) || []
  );
  const [targetPlayers, setTargetPlayers] = useState<string[]>(
    existingTrade?.target_players?.map(p => getPlayerId(p)) || []
  );
  const [tradeMessage, setTradeMessage] = useState(existingTrade?.message || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Helper function to get player ID
  function getPlayerId(player: ExtendedPlayer): string {
    return player.fpl_id || player.id.toString();
  }

  // Get target team details
  const targetTeam = useMemo(() => {
    return allTeams.find(team => team.id === selectedTargetTeam);
  }, [allTeams, selectedTargetTeam]);

  // Get player details
  const getPlayerDetails = useCallback((playerId: string): ExtendedPlayer | undefined => {
    return allPlayers.find(p => getPlayerId(p) === playerId);
  }, [allPlayers]);

  // Get team roster
  const getTeamRoster = useCallback((teamId: string): ExtendedPlayer[] => {
    const team = allTeams.find(t => t.id === teamId);
    if (!team || !team.roster) return [];
    
    // Handle roster as array of players
    if (Array.isArray(team.roster)) {
      return team.roster.map((rosterPlayer: any) => {
        // If roster contains player objects directly
        if (rosterPlayer.id || rosterPlayer.fpl_id) {
          return allPlayers.find(p => 
            getPlayerId(p) === getPlayerId(rosterPlayer)
          );
        }
        // If roster contains just IDs
        return allPlayers.find(p => getPlayerId(p) === rosterPlayer.toString());
      }).filter(Boolean) as ExtendedPlayer[];
    }
    
    return [];
  }, [allTeams, allPlayers]);

  // Available teams (excluding user's team)
  const availableTeams = useMemo(() => {
    return allTeams.filter(team => team.id !== userTeam.id);
  }, [allTeams, userTeam.id]);

  // User's roster
  const userRoster = useMemo(() => {
    return getTeamRoster(userTeam.id);
  }, [getTeamRoster, userTeam.id]);

  // Target team's roster
  const targetRoster = useMemo(() => {
    return selectedTargetTeam ? getTeamRoster(selectedTargetTeam) : [];
  }, [getTeamRoster, selectedTargetTeam]);

  // Available players for selection
  const availableProposerPlayers = useMemo(() => {
    return userRoster.filter(player => !proposerPlayers.includes(getPlayerId(player)));
  }, [userRoster, proposerPlayers]);

  const availableTargetPlayers = useMemo(() => {
    return targetRoster.filter(player => !targetPlayers.includes(getPlayerId(player)));
  }, [targetRoster, targetPlayers]);

  // Selected player details
  const selectedProposerPlayers = useMemo(() => {
    return proposerPlayers.map(id => getPlayerDetails(id)).filter(Boolean) as ExtendedPlayer[];
  }, [proposerPlayers, getPlayerDetails]);

  const selectedTargetPlayers = useMemo(() => {
    return targetPlayers.map(id => getPlayerDetails(id)).filter(Boolean) as ExtendedPlayer[];
  }, [targetPlayers, getPlayerDetails]);

  // Validate trade
  const validateTrade = useCallback((): string[] => {
    const errors: string[] = [];

    if (!selectedTargetTeam) {
      errors.push('Please select a team to trade with');
    }

    if (proposerPlayers.length === 0 && targetPlayers.length === 0) {
      errors.push('Trade must include at least one player');
    }

    if (proposerPlayers.length > 5) {
      errors.push('Maximum 5 players per team in trade');
    }

    if (targetPlayers.length > 5) {
      errors.push('Maximum 5 players per team in trade');
    }

    // Check for roster size limits after trade
    const userRosterAfter = userRoster.length - proposerPlayers.length + targetPlayers.length;
    const targetRosterAfter = targetRoster.length - targetPlayers.length + proposerPlayers.length;

    if (userRosterAfter > 15) {
      errors.push('Your roster would exceed 15 players after trade');
    }

    if (targetRosterAfter > 15) {
      errors.push('Target team roster would exceed 15 players after trade');
    }

    if (userRosterAfter < 11) {
      errors.push('Your roster would be below 11 players after trade');
    }

    if (targetRosterAfter < 11) {
      errors.push('Target team roster would be below 11 players after trade');
    }

    return errors;
  }, [selectedTargetTeam, proposerPlayers, targetPlayers, userRoster, targetRoster]);

  // Handle player selection
  const handlePlayerSelect = (playerId: string, isProposer: boolean) => {
    if (isProposer) {
      if (proposerPlayers.includes(playerId)) {
        setProposerPlayers(prev => prev.filter(id => id !== playerId));
      } else if (proposerPlayers.length < 5) {
        setProposerPlayers(prev => [...prev, playerId]);
      }
    } else {
      if (targetPlayers.includes(playerId)) {
        setTargetPlayers(prev => prev.filter(id => id !== playerId));
      } else if (targetPlayers.length < 5) {
        setTargetPlayers(prev => [...prev, playerId]);
      }
    }
  };

  // Handle submit
  const handleSubmit = async () => {
    const errors = validateTrade();
    setValidationErrors(errors);

    if (errors.length > 0) return;

    setIsSubmitting(true);
    try {
      const tradeData: TradeData = {
        target_team_id: selectedTargetTeam,
        proposer_players: proposerPlayers,
        target_players: targetPlayers,
        message: tradeMessage.trim() || undefined,
      };

      const success = await onSubmit(tradeData);
      if (success) {
        // Reset form or close modal
        onCancel();
      }
    } catch (error) {
      console.error('Error submitting trade:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Calculate trade value
  const calculateTradeValue = () => {
    const proposerValue = selectedProposerPlayers.reduce((sum, player) => sum + (player.now_cost || 0), 0);
    const targetValue = selectedTargetPlayers.reduce((sum, player) => sum + (player.now_cost || 0), 0);
    return { proposerValue, targetValue, difference: Math.abs(proposerValue - targetValue) };
  };

  const tradeValue = calculateTradeValue();

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {existingTrade ? 'Edit Trade Proposal' : 'Propose Trade'}
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Team Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Team to Trade With
        </label>
        <select
          value={selectedTargetTeam}
          onChange={(e) => {
            setSelectedTargetTeam(e.target.value);
            setTargetPlayers([]); // Reset target players when team changes
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={!!existingTrade}
        >
          <option value="">Choose a team...</option>
          {availableTeams.map(team => (
            <option key={team.id} value={team.id}>
              {team.name} ({team.owner_name || 'Owner'})
            </option>
          ))}
        </select>
      </div>

      {/* Trade Overview */}
      {selectedTargetTeam && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Your Team Section */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-4 flex items-center">
              <span className="w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
              {userTeam.name} (You)
            </h4>

            {/* Selected Players to Trade Away */}
            <div className="mb-4">
              <div className="text-sm font-medium text-gray-700 mb-2">
                Trading Away ({selectedProposerPlayers.length}/5)
              </div>
              <div className="space-y-2 mb-4">
                {selectedProposerPlayers.map(player => (
                  <div key={getPlayerId(player)} className="flex items-center justify-between p-2 bg-red-50 border border-red-200 rounded">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{player.web_name || player.name}</span>
                      <span className="text-xs text-gray-600">{player.position} - {player.team}</span>
                    </div>
                    <button
                      onClick={() => handlePlayerSelect(getPlayerId(player), true)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
                {selectedProposerPlayers.length === 0 && (
                  <div className="text-sm text-gray-500 italic">No players selected</div>
                )}
              </div>

              {/* Available Players */}
              <div className="text-sm font-medium text-gray-700 mb-2">Available Players</div>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {availableProposerPlayers.map(player => (
                  <button
                    key={getPlayerId(player)}
                    onClick={() => handlePlayerSelect(getPlayerId(player), true)}
                    disabled={proposerPlayers.length >= 5}
                    className={`
                      w-full text-left p-2 rounded border transition-colors
                      ${proposerPlayers.length >= 5 
                        ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed' 
                        : 'bg-white border-gray-200 hover:bg-blue-50 hover:border-blue-300'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">{player.web_name || player.name}</div>
                        <div className="text-xs text-gray-600">{player.position} - {player.team}</div>
                      </div>
                      <div className="text-xs text-gray-500">
                        £{((player.now_cost || 0) / 10).toFixed(1)}m
                      </div>
                    </div>
                  </button>
                ))}
                {availableProposerPlayers.length === 0 && (
                  <div className="text-sm text-gray-500 italic p-2">No available players</div>
                )}
              </div>
            </div>
          </div>

          {/* Target Team Section */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-4 flex items-center">
              <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
              {targetTeam?.name}
            </h4>

            {/* Selected Players to Receive */}
            <div className="mb-4">
              <div className="text-sm font-medium text-gray-700 mb-2">
                Receiving ({selectedTargetPlayers.length}/5)
              </div>
              <div className="space-y-2 mb-4">
                {selectedTargetPlayers.map(player => (
                  <div key={getPlayerId(player)} className="flex items-center justify-between p-2 bg-green-50 border border-green-200 rounded">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{player.web_name || player.name}</span>
                      <span className="text-xs text-gray-600">{player.position} - {player.team}</span>
                    </div>
                    <button
                      onClick={() => handlePlayerSelect(getPlayerId(player), false)}
                      className="text-green-600 hover:text-green-800"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
                {selectedTargetPlayers.length === 0 && (
                  <div className="text-sm text-gray-500 italic">No players selected</div>
                )}
              </div>

              {/* Available Players */}
              <div className="text-sm font-medium text-gray-700 mb-2">Available Players</div>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {availableTargetPlayers.map(player => (
                  <button
                    key={getPlayerId(player)}
                    onClick={() => handlePlayerSelect(getPlayerId(player), false)}
                    disabled={targetPlayers.length >= 5}
                    className={`
                      w-full text-left p-2 rounded border transition-colors
                      ${targetPlayers.length >= 5 
                        ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed' 
                        : 'bg-white border-gray-200 hover:bg-green-50 hover:border-green-300'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">{player.web_name || player.name}</div>
                        <div className="text-xs text-gray-600">{player.position} - {player.team}</div>
                      </div>
                      <div className="text-xs text-gray-500">
                        £{((player.now_cost || 0) / 10).toFixed(1)}m
                      </div>
                    </div>
                  </button>
                ))}
                {availableTargetPlayers.length === 0 && (
                  <div className="text-sm text-gray-500 italic p-2">No available players</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Trade Analysis */}
      {(selectedProposerPlayers.length > 0 || selectedTargetPlayers.length > 0) && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h5 className="font-medium text-gray-900 mb-3">Trade Analysis</h5>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="text-center">
              <div className="text-lg font-bold text-blue-600">
                £{(tradeValue.proposerValue / 10).toFixed(1)}m
              </div>
              <div className="text-gray-600">You're Trading</div>
              <div className="text-xs text-gray-500 mt-1">
                {selectedProposerPlayers.length} player{selectedProposerPlayers.length !== 1 ? 's' : ''}
              </div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-600">
                £{(tradeValue.difference / 10).toFixed(1)}m
              </div>
              <div className="text-gray-600">Value Difference</div>
              <div className="text-xs text-gray-500 mt-1">
                {tradeValue.proposerValue > tradeValue.targetValue ? 'You give more' : 
                 tradeValue.targetValue > tradeValue.proposerValue ? 'You get more' : 'Equal value'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-green-600">
                £{(tradeValue.targetValue / 10).toFixed(1)}m
              </div>
              <div className="text-gray-600">You're Receiving</div>
              <div className="text-xs text-gray-500 mt-1">
                {selectedTargetPlayers.length} player{selectedTargetPlayers.length !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
          
          {tradeValue.difference > 50 && (
            <div className="mt-3 p-2 bg-orange-100 border border-orange-200 rounded text-sm text-orange-800">
              ⚠️ Significant value difference in this trade (£{(tradeValue.difference / 10).toFixed(1)}m)
            </div>
          )}
        </div>
      )}

      {/* Trade Message */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Message to {targetTeam?.name || 'other team'} (Optional)
        </label>
        <textarea
          value={tradeMessage}
          onChange={(e) => setTradeMessage(e.target.value)}
          placeholder="Add a message to explain your trade proposal..."
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          maxLength={500}
        />
        <div className="text-xs text-gray-500 mt-1">
          {tradeMessage.length}/500 characters
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <h5 className="font-medium text-red-800 mb-2">Please fix the following issues:</h5>
          <ul className="list-disc list-inside space-y-1 text-sm text-red-700">
            {validationErrors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || validationErrors.length > 0}
          className={`
            flex-1 px-4 py-2 rounded-lg font-medium transition-colors
            ${isSubmitting || validationErrors.length > 0
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
            }
          `}
        >
          {isSubmitting ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Submitting...
            </div>
          ) : (
            existingTrade ? 'Update Trade' : 'Propose Trade'
          )}
        </button>
        
        <button
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default TradeProposal;