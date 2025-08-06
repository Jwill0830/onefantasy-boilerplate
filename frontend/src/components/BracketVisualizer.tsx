// frontend/src/components/BracketVisualizer.tsx
import React from 'react';
import { PlayoffBracket, PlayoffMatchup, Team } from '../types';

interface BracketVisualizerProps {
  bracket: PlayoffBracket;
  teams: Team[];
  isCommissioner?: boolean;
  onUpdateMatchup?: (matchupId: string, winner: string, score: string) => Promise<void>;
}

export const BracketVisualizer: React.FC<BracketVisualizerProps> = ({
  bracket,
  teams,
  isCommissioner = false,
  onUpdateMatchup
}) => {
  const getTeamById = (teamId: string) => teams.find(t => t.id === teamId);

  const renderMatchup = (matchup: PlayoffMatchup, roundIndex: number) => {
    const team1 = getTeamById(matchup.team1Id);
    const team2 = getTeamById(matchup.team2Id);
    const isCompleted = matchup.winner !== null;
    
    return (
      <div 
        key={matchup.id}
        className={`bg-white rounded-lg shadow-md border-2 ${
          isCompleted ? 'border-green-500' : 'border-gray-200'
        } p-4 mb-4 min-w-[280px]`}
      >
        <div className="text-center mb-2">
          <h4 className="font-semibold text-gray-700">
            {matchup.round === 'finals' ? 'Championship' : 
             matchup.round === 'semifinals' ? 'Semifinals' : 
             'First Round'}
          </h4>
          <p className="text-sm text-gray-500">Week {matchup.week}</p>
        </div>

        <div className="space-y-2">
          {/* Team 1 */}
          <div className={`flex items-center justify-between p-3 rounded ${
            matchup.winner === matchup.team1Id 
              ? 'bg-green-100 border-2 border-green-500' 
              : 'bg-gray-50'
          }`}>
            <div className="flex items-center">
              {team1?.logo_url && (
                <img 
                  src={team1.logo_url} 
                  alt={`${team1.name} logo`}
                  className="w-6 h-6 mr-2"
                />
              )}
              <div>
                <p className="font-medium">{team1?.name}</p>
                <p className="text-sm text-gray-600">
                  ({team1?.record?.wins || 0}-{team1?.record?.losses || 0})
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold text-lg">
                {matchup.team1Score !== null ? matchup.team1Score.toFixed(1) : '-'}
              </p>
              {matchup.winner === matchup.team1Id && (
                <span className="text-green-600 text-sm font-medium">WINNER</span>
              )}
            </div>
          </div>

          {/* VS */}
          <div className="text-center text-gray-400 font-medium">VS</div>

          {/* Team 2 */}
          <div className={`flex items-center justify-between p-3 rounded ${
            matchup.winner === matchup.team2Id 
              ? 'bg-green-100 border-2 border-green-500' 
              : 'bg-gray-50'
          }`}>
            <div className="flex items-center">
              {team2?.logo_url && (
                <img 
                  src={team2.logo_url} 
                  alt={`${team2.name} logo`}
                  className="w-6 h-6 mr-2"
                />
              )}
              <div>
                <p className="font-medium">{team2?.name}</p>
                <p className="text-sm text-gray-600">
                  ({team2?.record?.wins || 0}-{team2?.record?.losses || 0})
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold text-lg">
                {matchup.team2Score !== null ? matchup.team2Score.toFixed(1) : '-'}
              </p>
              {matchup.winner === matchup.team2Id && (
                <span className="text-green-600 text-sm font-medium">WINNER</span>
              )}
            </div>
          </div>
        </div>

        {/* Commissioner Controls */}
        {isCommissioner && !isCompleted && onUpdateMatchup && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex space-x-2">
              <button
                onClick={() => onUpdateMatchup(matchup.id, matchup.team1Id, 'manual')}
                className="flex-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {team1?.name} Wins
              </button>
              <button
                onClick={() => onUpdateMatchup(matchup.id, matchup.team2Id, 'manual')}
                className="flex-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {team2?.name} Wins
              </button>
            </div>
          </div>
        )}

        {isCompleted && (
          <div className="mt-2 text-center">
            <span className="text-xs text-gray-500">
              Completed {new Date(matchup.completedAt!).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>
    );
  };

  const renderRound = (round: string, matchups: PlayoffMatchup[]) => {
    const roundMatchups = matchups.filter(m => m.round === round);
    if (roundMatchups.length === 0) return null;

    const roundTitle = round === 'finals' ? 'Championship' : 
                     round === 'semifinals' ? 'Semifinals' : 
                     'First Round';

    return (
      <div className="flex flex-col items-center min-w-[320px]">
        <h3 className="text-xl font-bold mb-4 text-gray-800">{roundTitle}</h3>
        <div className="space-y-4">
          {roundMatchups.map(matchup => renderMatchup(matchup, 0))}
        </div>
      </div>
    );
  };

  if (!bracket || !bracket.matchups || bracket.matchups.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-6xl mb-4">🏆</div>
        <h3 className="text-xl font-semibold text-gray-700 mb-2">
          Playoff Bracket Not Yet Created
        </h3>
        <p className="text-gray-500">
          The playoff bracket will be generated when the regular season ends.
        </p>
      </div>
    );
  }

  // Group matchups by round for display
  const rounds = ['quarterfinals', 'semifinals', 'finals'];
  const availableRounds = rounds.filter(round => 
    bracket.matchups.some(m => m.round === round)
  );

  return (
    <div className="overflow-x-auto">
      <div className="flex space-x-8 pb-6 min-w-max">
        {availableRounds.map(round => renderRound(round, bracket.matchups))}
      </div>

      {/* Bracket Status */}
      <div className="mt-8 bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">Bracket Status</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Format:</span>
            <span className="ml-2 font-medium">Single Elimination</span>
          </div>
          <div>
            <span className="text-gray-600">Playoff Teams:</span>
            <span className="ml-2 font-medium">{bracket.teams.length}</span>
          </div>
          <div>
            <span className="text-gray-600">Status:</span>
            <span className="ml-2 font-medium capitalize">{bracket.status}</span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <div className="flex items-center">
          <div className="w-4 h-4 bg-green-100 border-2 border-green-500 rounded mr-2"></div>
          <span>Winner</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-gray-50 border-2 border-gray-200 rounded mr-2"></div>
          <span>Pending</span>
        </div>
      </div>
    </div>
  );
};