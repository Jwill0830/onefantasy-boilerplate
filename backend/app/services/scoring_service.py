"""
Scoring service for calculating player points, team scores, and league standings.
Handles FPL-style scoring rules and weekly score updates.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from firebase_admin import firestore

from .. import get_db, get_socketio
from ..models.player_model import PlayerModel
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..utils.logger import get_logger
from ..utils.api_integrations import FPLAPIClient

logger = get_logger(__name__)

class ScoringService:
    """Service for managing scoring calculations and league standings."""
    
    def __init__(self):
        """Initialize scoring service with database and API clients."""
        self.db = get_db()
        self.socketio = get_socketio()
        self.player_model = PlayerModel()
        self.team_model = TeamModel()
        self.league_model = LeagueModel()
        self.fpl_client = FPLAPIClient()

    def calculate_player_points(self, player_id: int, gameweek: int, 
                               league_id: str) -> Dict[str, Any]:
        """
        Calculate points for a player based on league scoring rules.
        
        Args:
            player_id: FPL player ID
            gameweek: Gameweek number
            league_id: League ID for scoring rules
            
        Returns:
            Dict with points breakdown and total
        """
        try:
            # Get player data
            player = self.player_model.get_player(player_id)
            if not player:
                return {'total_points': 0, 'breakdown': {}, 'error': 'Player not found'}
            
            # Get league scoring rules
            league = self.league_model.get_league(league_id)
            if not league:
                return {'total_points': 0, 'breakdown': {}, 'error': 'League not found'}
            
            scoring_rules = league.get('settings', {}).get('scoring_settings', {})
            if not scoring_rules:
                scoring_rules = self._get_default_scoring_rules()
            
            # Fetch player stats for the gameweek
            stats = self._fetch_player_stats(player_id, gameweek)
            if not stats:
                return {'total_points': 0, 'breakdown': {}, 'error': 'No stats available'}
            
            # Calculate points based on scoring rules
            points_breakdown = self._calculate_points_breakdown(stats, scoring_rules, player)
            total_points = sum(points_breakdown.values())
            
            return {
                'total_points': total_points,
                'breakdown': points_breakdown,
                'player_id': player_id,
                'gameweek': gameweek,
                'calculated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error calculating player points for {player_id}: {str(e)}")
            return {'total_points': 0, 'breakdown': {}, 'error': str(e)}

    def _fetch_player_stats(self, player_id: int, gameweek: int) -> Optional[Dict[str, Any]]:
        """
        Fetch player stats from FPL API or Firestore cache.
        
        Args:
            player_id: FPL player ID
            gameweek: Gameweek number
            
        Returns:
            Player stats dictionary or None
        """
        try:
            # Try to get cached stats first
            cached_stats = self._get_cached_player_stats(player_id, gameweek)
            if cached_stats:
                return cached_stats
            
            # Fetch from FPL API
            api_stats = self.fpl_client.get_player_gameweek_stats(player_id, gameweek)
            if api_stats:
                # Cache the stats
                self._cache_player_stats(player_id, gameweek, api_stats)
                return api_stats
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching player stats for {player_id}, GW{gameweek}: {str(e)}")
            return None

    def _get_cached_player_stats(self, player_id: int, gameweek: int) -> Optional[Dict[str, Any]]:
        """Get cached player stats from Firestore."""
        try:
            doc_ref = (self.db.collection('player_stats')
                      .document(f'{player_id}_{gameweek}'))
            doc = doc_ref.get()
            
            if doc.exists:
                stats = doc.to_dict()
                # Check if stats are recent (within 1 hour)
                cached_at = stats.get('cached_at')
                if cached_at and (datetime.utcnow() - cached_at).total_seconds() < 3600:
                    return stats.get('stats')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached stats: {str(e)}")
            return None

    def _cache_player_stats(self, player_id: int, gameweek: int, stats: Dict[str, Any]) -> None:
        """Cache player stats in Firestore."""
        try:
            doc_ref = (self.db.collection('player_stats')
                      .document(f'{player_id}_{gameweek}'))
            
            cache_data = {
                'player_id': player_id,
                'gameweek': gameweek,
                'stats': stats,
                'cached_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.set(cache_data)
            
        except Exception as e:
            logger.error(f"Error caching player stats: {str(e)}")

    def _calculate_points_breakdown(self, stats: Dict[str, Any], scoring_rules: Dict[str, Any], 
                                   player: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate detailed points breakdown based on stats and scoring rules.
        
        Args:
            stats: Player statistics
            scoring_rules: League scoring rules
            player: Player information
            
        Returns:
            Points breakdown dictionary
        """
        breakdown = {}
        position = player.get('element_type', 1)  # 1=GKP, 2=DEF, 3=MID, 4=FWD
        position_name = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}.get(position, 'FWD')
        
        try:
            # Goals scored
            goals = stats.get('goals_scored', 0)
            if goals > 0:
                goal_points = scoring_rules.get('goals_scored', {}).get(position_name, 0)
                breakdown['goals'] = goals * goal_points
            
            # Assists
            assists = stats.get('assists', 0)
            if assists > 0:
                breakdown['assists'] = assists * scoring_rules.get('assists', 3)
            
            # Clean sheets
            clean_sheet = stats.get('clean_sheets', 0)
            if clean_sheet > 0:
                cs_points = scoring_rules.get('clean_sheets', {}).get(position_name, 0)
                breakdown['clean_sheet'] = clean_sheet * cs_points
            
            # Saves (for goalkeepers)
            saves = stats.get('saves', 0)
            if saves > 0 and position == 1:  # GKP only
                saves_rule = scoring_rules.get('saves', {})
                saves_per_point = saves_rule.get('saves_required', 3)
                points_per_save = saves_rule.get('points_per_save', 1)
                breakdown['saves'] = (saves // saves_per_point) * points_per_save
            
            # Penalty saves
            penalty_saves = stats.get('penalties_saved', 0)
            if penalty_saves > 0:
                breakdown['penalty_saves'] = penalty_saves * scoring_rules.get('penalty_saves', 5)
            
            # Penalty misses
            penalty_misses = stats.get('penalties_missed', 0)
            if penalty_misses > 0:
                breakdown['penalty_misses'] = penalty_misses * scoring_rules.get('penalty_misses', -2)
            
            # Yellow cards
            yellow_cards = stats.get('yellow_cards', 0)
            if yellow_cards > 0:
                breakdown['yellow_cards'] = yellow_cards * scoring_rules.get('yellow_cards', -1)
            
            # Red cards
            red_cards = stats.get('red_cards', 0)
            if red_cards > 0:
                breakdown['red_cards'] = red_cards * scoring_rules.get('red_cards', -3)
            
            # Own goals
            own_goals = stats.get('own_goals', 0)
            if own_goals > 0:
                breakdown['own_goals'] = own_goals * scoring_rules.get('own_goals', -2)
            
            # Goals conceded (for GKP and DEF)
            goals_conceded = stats.get('goals_conceded', 0)
            if goals_conceded > 0 and position in [1, 2]:  # GKP or DEF
                gc_rule = scoring_rules.get('goals_conceded', {})
                if position_name in gc_rule:
                    # Typically -1 point per 2 goals conceded
                    breakdown['goals_conceded'] = -(goals_conceded // 2) * abs(gc_rule[position_name])
            
            # Minutes played
            minutes = stats.get('minutes', 0)
            minutes_rule = scoring_rules.get('minutes_played', {})
            if minutes >= 60:
                breakdown['minutes'] = minutes_rule.get('60_plus', 2)
            elif minutes > 0:
                breakdown['minutes'] = minutes_rule.get('1_to_59', 1)
            
            # Bonus points
            bonus = stats.get('bonus', 0)
            if bonus > 0:
                breakdown['bonus'] = bonus * scoring_rules.get('bonus_points', 1)
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error calculating points breakdown: {str(e)}")
            return {}

    def calculate_team_points(self, league_id: str, team_id: str, 
                             gameweek: int) -> Dict[str, Any]:
        """
        Calculate total points for a team in a gameweek.
        
        Args:
            league_id: League ID
            team_id: Team ID
            gameweek: Gameweek number
            
        Returns:
            Team scoring summary
        """
        try:
            # Get team roster
            team = self.team_model.get_team(league_id, team_id)
            if not team:
                return {'total_points': 0, 'error': 'Team not found'}
            
            roster = team.get('roster', {})
            starters = roster.get('starters', [])
            bench = roster.get('bench', [])
            
            # Calculate points for starting lineup
            starting_points = 0
            starting_breakdown = {}
            
            for player_id in starters:
                player_points = self.calculate_player_points(player_id, gameweek, league_id)
                starting_points += player_points['total_points']
                starting_breakdown[player_id] = player_points
            
            # Calculate bench points
            bench_points = 0
            bench_breakdown = {}
            
            for player_id in bench:
                player_points = self.calculate_player_points(player_id, gameweek, league_id)
                bench_points += player_points['total_points']
                bench_breakdown[player_id] = player_points
            
            # Auto-substitute logic (basic implementation)
            # TODO: Implement proper auto-sub rules
            substitution_points = 0
            
            total_points = starting_points + substitution_points
            
            # Store team gameweek score
            self._store_team_gameweek_score(league_id, team_id, gameweek, {
                'total_points': total_points,
                'starting_points': starting_points,
                'bench_points': bench_points,
                'substitution_points': substitution_points,
                'starting_breakdown': starting_breakdown,
                'bench_breakdown': bench_breakdown,
                'calculated_at': datetime.utcnow()
            })
            
            return {
                'total_points': total_points,
                'starting_points': starting_points,
                'bench_points': bench_points,
                'substitution_points': substitution_points,
                'starting_breakdown': starting_breakdown,
                'bench_breakdown': bench_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error calculating team points for {team_id}: {str(e)}")
            return {'total_points': 0, 'error': str(e)}

    def _store_team_gameweek_score(self, league_id: str, team_id: str, gameweek: int, 
                                  score_data: Dict[str, Any]) -> None:
        """Store team's gameweek score in Firestore."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('teams').document(team_id)
                      .collection('gameweek_scores').document(str(gameweek)))
            
            doc_ref.set(score_data)
            
        except Exception as e:
            logger.error(f"Error storing team gameweek score: {str(e)}")

    def update_gameweek_scores(self, league_id: str, gameweek: int, 
                              team_scores: Dict[str, Dict[str, Any]] = None,
                              commissioner_id: str = None) -> Dict[str, Any]:
        """
        Update gameweek scores for all teams in a league.
        
        Args:
            league_id: League ID
            gameweek: Gameweek number
            team_scores: Optional manual score overrides
            commissioner_id: User ID if manually updated by commissioner
            
        Returns:
            Update result
        """
        try:
            # Get all teams in league
            teams = self.team_model.get_league_teams(league_id)
            if not teams:
                return {'success': False, 'error': 'No teams found in league'}
            
            updated_teams = []
            
            for team in teams:
                team_id = team['id']
                
                try:
                    if team_scores and team_id in team_scores:
                        # Use manual scores provided by commissioner
                        manual_score = team_scores[team_id]
                        self._store_team_gameweek_score(league_id, team_id, gameweek, {
                            **manual_score,
                            'manually_updated': True,
                            'updated_by': commissioner_id,
                            'updated_at': datetime.utcnow()
                        })
                        updated_teams.append(team_id)
                    else:
                        # Calculate scores automatically
                        team_score = self.calculate_team_points(league_id, team_id, gameweek)
                        if team_score.get('total_points', 0) > 0:
                            updated_teams.append(team_id)
                            
                except Exception as e:
                    logger.error(f"Error updating score for team {team_id}: {str(e)}")
                    continue
            
            # Update league standings
            self.update_league_standings(league_id, gameweek)
            
            # Emit real-time update
            if self.socketio:
                self.socketio.emit('gameweek_scores_updated', {
                    'league_id': league_id,
                    'gameweek': gameweek,
                    'updated_teams': updated_teams,
                    'manually_updated': bool(team_scores)
                }, room=f'league_{league_id}')
            
            return {
                'success': True,
                'updated_teams': updated_teams,
                'message': f'Updated scores for {len(updated_teams)} teams'
            }
            
        except Exception as e:
            logger.error(f"Error updating gameweek scores: {str(e)}")
            return {'success': False, 'error': str(e)}

    def update_league_standings(self, league_id: str, gameweek: int) -> Dict[str, Any]:
        """
        Update league standings after a gameweek.
        
        Args:
            league_id: League ID
            gameweek: Gameweek number
            
        Returns:
            Updated standings
        """
        try:
            # Get all teams
            teams = self.team_model.get_league_teams(league_id)
            if not teams:
                return {'success': False, 'error': 'No teams found'}
            
            # Get matchups for this gameweek
            matchups = self._get_gameweek_matchups(league_id, gameweek)
            
            # Process matchups and update team records
            for matchup in matchups:
                team1_id = matchup['team1_id']
                team2_id = matchup['team2_id']
                
                # Get team scores
                team1_score = self._get_team_gameweek_score(league_id, team1_id, gameweek)
                team2_score = self._get_team_gameweek_score(league_id, team2_id, gameweek)
                
                # Determine winner and update records
                if team1_score > team2_score:
                    self._update_team_record(league_id, team1_id, 'win', team1_score, team2_score)
                    self._update_team_record(league_id, team2_id, 'loss', team2_score, team1_score)
                elif team2_score > team1_score:
                    self._update_team_record(league_id, team2_id, 'win', team2_score, team1_score)
                    self._update_team_record(league_id, team1_id, 'loss', team1_score, team2_score)
                else:
                    # Tie
                    self._update_team_record(league_id, team1_id, 'tie', team1_score, team2_score)
                    self._update_team_record(league_id, team2_id, 'tie', team2_score, team1_score)
            
            # Get updated standings
            standings = self.league_model.get_league_standings(league_id)
            
            return {'success': True, 'standings': standings}
            
        except Exception as e:
            logger.error(f"Error updating league standings: {str(e)}")
            return {'success': False, 'error': str(e)}

    def calculate_optimal_lineup(self, league_id: str, team_id: str, 
                                gameweek: int) -> Dict[str, Any]:
        """
        Calculate maximum points if optimal lineup was set.
        
        Args:
            league_id: League ID
            team_id: Team ID
            gameweek: Gameweek number
            
        Returns:
            Optimal lineup and max points
        """
        try:
            # Get team roster
            team = self.team_model.get_team(league_id, team_id)
            if not team:
                return {'max_points': 0, 'error': 'Team not found'}
            
            roster = team.get('roster', {})
            all_players = roster.get('starters', []) + roster.get('bench', [])
            
            # Get points for all players
            player_points = {}
            for player_id in all_players:
                points_data = self.calculate_player_points(player_id, gameweek, league_id)
                player_points[player_id] = points_data['total_points']
            
            # Sort players by points (descending)
            sorted_players = sorted(player_points.items(), key=lambda x: x[1], reverse=True)
            
            # Select optimal lineup (basic implementation)
            # TODO: Implement proper formation constraints (GK, DEF, MID, FWD limits)
            optimal_starters = [p[0] for p in sorted_players[:11]]  # Top 11 players
            optimal_bench = [p[0] for p in sorted_players[11:]]
            
            max_points = sum(player_points[p] for p in optimal_starters)
            
            return {
                'max_points': max_points,
                'optimal_starters': optimal_starters,
                'optimal_bench': optimal_bench,
                'actual_points': sum(player_points[p] for p in roster.get('starters', [])),
                'points_left_on_bench': max_points - sum(player_points[p] for p in roster.get('starters', []))
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimal lineup: {str(e)}")
            return {'max_points': 0, 'error': str(e)}

    def get_player_season_stats(self, player_id: int, league_id: str) -> Dict[str, Any]:
        """Get comprehensive season statistics for a player."""
        try:
            # Get all gameweek scores for the player
            total_points = 0
            games_played = 0
            goals = 0
            assists = 0
            
            # TODO: Aggregate from cached gameweek data
            # This would loop through all gameweeks and sum up stats
            
            return {
                'player_id': player_id,
                'total_points': total_points,
                'games_played': games_played,
                'average_points': total_points / max(games_played, 1),
                'goals': goals,
                'assists': assists
            }
            
        except Exception as e:
            logger.error(f"Error getting player season stats: {str(e)}")
            return {}

    def _get_default_scoring_rules(self) -> Dict[str, Any]:
        """Get default FPL scoring rules."""
        return {
            'goals_scored': {
                'GK': 6, 'DEF': 6, 'MID': 5, 'FWD': 4
            },
            'assists': 3,
            'clean_sheets': {
                'GK': 4, 'DEF': 4, 'MID': 1, 'FWD': 0
            },
            'saves': {
                'points_per_save': 1,
                'saves_required': 3
            },
            'penalty_saves': 5,
            'penalty_misses': -2,
            'yellow_cards': -1,
            'red_cards': -3,
            'own_goals': -2,
            'goals_conceded': {
                'GK': -1, 'DEF': -1, 'MID': 0, 'FWD': 0
            },
            'bonus_points': 1,
            'minutes_played': {
                '60_plus': 2,
                '1_to_59': 1,
                '0': 0
            }
        }

    def _get_gameweek_matchups(self, league_id: str, gameweek: int) -> List[Dict[str, Any]]:
        """Get matchups for a specific gameweek."""
        try:
            # Get league schedule
            league = self.league_model.get_league(league_id)
            schedule = league.get('matchup_schedule', [])
            
            # Filter for this gameweek
            return [m for m in schedule if m.get('week') == gameweek]
            
        except Exception as e:
            logger.error(f"Error getting gameweek matchups: {str(e)}")
            return []

    def _get_team_gameweek_score(self, league_id: str, team_id: str, gameweek: int) -> float:
        """Get a team's total score for a gameweek."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('teams').document(team_id)
                      .collection('gameweek_scores').document(str(gameweek)))
            
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get('total_points', 0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting team gameweek score: {str(e)}")
            return 0.0

    def _update_team_record(self, league_id: str, team_id: str, result: str, 
                           points_for: float, points_against: float) -> None:
        """Update team's win/loss record and points."""
        try:
            team_ref = (self.db.collection('leagues').document(league_id)
                       .collection('teams').document(team_id))
            
            # Get current stats
            team_doc = team_ref.get()
            if team_doc.exists:
                stats = team_doc.to_dict().get('stats', {})
            else:
                stats = {'wins': 0, 'losses': 0, 'ties': 0, 'points_for': 0, 'points_against': 0}
            
            # Update based on result
            if result == 'win':
                stats['wins'] = stats.get('wins', 0) + 1
            elif result == 'loss':
                stats['losses'] = stats.get('losses', 0) + 1
            elif result == 'tie':
                stats['ties'] = stats.get('ties', 0) + 1
            
            stats['points_for'] = stats.get('points_for', 0) + points_for
            stats['points_against'] = stats.get('points_against', 0) + points_against
            
            # Update team document
            team_ref.update({
                'stats': stats,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            logger.error(f"Error updating team record: {str(e)}")