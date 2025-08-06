"""
Matchups routes for managing league matchups, schedules, and scoring.
Handles matchup creation, viewing, and score tracking.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import asyncio

from ..services.auth_service import AuthService
from ..services.scoring_service import ScoringService
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..utils.validators import validate_json
from ..utils.logger import get_logger

logger = get_logger(__name__)

matchups_bp = Blueprint('matchups', __name__)

def init_matchups_routes(app, db, socketio):
    """Initialize matchups routes with dependencies."""
    auth_service = AuthService()
    scoring_service = ScoringService(db, socketio)
    team_model = TeamModel(db)
    league_model = LeagueModel(db)

    @matchups_bp.route('/leagues/<league_id>/matchups', methods=['GET'])
    def get_league_matchups(league_id):
        """Get all matchups for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            gameweek = request.args.get('gameweek', type=int)
            status = request.args.get('status')  # scheduled, active, completed
            limit = min(int(request.args.get('limit', 50)), 100)

            # Get league matchups
            matchups = _get_league_matchups(league_id, gameweek, status, limit)

            return jsonify({
                'success': True,
                'matchups': matchups,
                'count': len(matchups),
                'league_id': league_id,
                'gameweek': gameweek
            })

        except Exception as e:
            logger.error(f"Error getting league matchups: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/matchups/gameweek/<int:gameweek>', methods=['GET'])
    def get_gameweek_matchups(league_id, gameweek):
        """Get matchups for a specific gameweek."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get gameweek matchups
            matchups = _get_gameweek_matchups(league_id, gameweek)

            return jsonify({
                'success': True,
                'matchups': matchups,
                'count': len(matchups),
                'league_id': league_id,
                'gameweek': gameweek
            })

        except Exception as e:
            logger.error(f"Error getting gameweek matchups: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/teams/<team_id>/matchups', methods=['GET'])
    def get_team_matchups(team_id):
        """Get all matchups for a specific team."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            gameweek = request.args.get('gameweek', type=int)
            status = request.args.get('status')
            limit = min(int(request.args.get('limit', 20)), 50)

            # Verify team exists
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            # Get team matchups
            matchups = _get_team_matchups(team_id, gameweek, status, limit)

            return jsonify({
                'success': True,
                'matchups': matchups,
                'count': len(matchups),
                'team_id': team_id
            })

        except Exception as e:
            logger.error(f"Error getting team matchups: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/matchups/<matchup_id>', methods=['GET'])
    def get_matchup_details(matchup_id):
        """Get detailed information about a specific matchup."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get matchup details
            matchup = _get_matchup_details(matchup_id)
            
            if not matchup:
                return jsonify({'error': 'Matchup not found'}), 404

            return jsonify({
                'success': True,
                'matchup': matchup
            })

        except Exception as e:
            logger.error(f"Error getting matchup details: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/matchups/generate', methods=['POST'])
    @validate_json
    def generate_league_schedule(league_id):
        """Generate matchup schedule for a league (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can generate matchup schedules'}), 403

            # Get parameters
            start_gameweek = data.get('start_gameweek', 1)
            end_gameweek = data.get('end_gameweek', 38)
            playoff_weeks = data.get('playoff_weeks', 3)
            schedule_type = data.get('schedule_type', 'round_robin')  # round_robin, random

            # Generate schedule
            schedule = _generate_matchup_schedule(
                league_id, start_gameweek, end_gameweek, playoff_weeks, schedule_type
            )

            return jsonify({
                'success': True,
                'schedule': schedule,
                'message': 'Matchup schedule generated successfully'
            })

        except Exception as e:
            logger.error(f"Error generating league schedule: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/matchups/<matchup_id>/scores', methods=['GET'])
    def get_matchup_scores(matchup_id):
        """Get live scores for a matchup."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get matchup scores
            scores = _get_matchup_scores(matchup_id)
            
            if not scores:
                return jsonify({'error': 'Matchup not found or scores unavailable'}), 404

            return jsonify({
                'success': True,
                'scores': scores,
                'matchup_id': matchup_id
            })

        except Exception as e:
            logger.error(f"Error getting matchup scores: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/matchups/<matchup_id>/scores', methods=['PUT'])
    @validate_json
    def update_matchup_scores(matchup_id):
        """Update matchup scores (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Get matchup to verify commissioner access
            matchup = _get_matchup_details(matchup_id)
            if not matchup:
                return jsonify({'error': 'Matchup not found'}), 404

            # Verify commissioner privileges
            league = league_model.get_league(matchup['league_id'])
            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can update matchup scores'}), 403

            # Validate score data
            if 'team1_score' not in data or 'team2_score' not in data:
                return jsonify({'error': 'Both team scores are required'}), 400

            team1_score = float(data['team1_score'])
            team2_score = float(data['team2_score'])

            # Update matchup scores
            success = _update_matchup_scores(matchup_id, team1_score, team2_score)

            if not success:
                return jsonify({'error': 'Failed to update matchup scores'}), 500

            # Get updated matchup
            updated_matchup = _get_matchup_details(matchup_id)

            # Emit real-time update
            socketio.emit('matchup_scores_updated', {
                'matchup_id': matchup_id,
                'scores': {
                    'team1_score': team1_score,
                    'team2_score': team2_score
                }
            }, room=f"league_{matchup['league_id']}")

            return jsonify({
                'success': True,
                'matchup': updated_matchup,
                'message': 'Matchup scores updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating matchup scores: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/standings', methods=['GET'])
    def get_league_standings(league_id):
        """Get current league standings."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get standings
            standings = _get_league_standings(league_id)

            return jsonify({
                'success': True,
                'standings': standings,
                'league_id': league_id,
                'count': len(standings)
            })

        except Exception as e:
            logger.error(f"Error getting league standings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/schedule', methods=['GET'])
    def get_league_schedule(league_id):
        """Get complete league schedule."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            gameweek_start = request.args.get('start', type=int)
            gameweek_end = request.args.get('end', type=int)

            # Get league schedule
            schedule = _get_league_schedule(league_id, gameweek_start, gameweek_end)

            return jsonify({
                'success': True,
                'schedule': schedule,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting league schedule: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/scoreboard', methods=['GET'])
    def get_league_scoreboard(league_id):
        """Get live scoreboard for current gameweek."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get current gameweek or specified gameweek
            gameweek = request.args.get('gameweek', type=int)
            
            if not gameweek:
                # Get current gameweek from FPL API (synchronously)
                gameweek = _get_current_gameweek()

            # Get scoreboard (synchronously)
            scoreboard = _get_league_scoreboard(league_id, gameweek)

            return jsonify({
                'success': True,
                'scoreboard': scoreboard,
                'league_id': league_id,
                'gameweek': gameweek
            })

        except Exception as e:
            logger.error(f"Error getting league scoreboard: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/playoff-bracket', methods=['GET'])
    def get_playoff_bracket(league_id):
        """Get playoff bracket for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get playoff bracket
            bracket = _get_playoff_bracket(league_id)

            return jsonify({
                'success': True,
                'bracket': bracket,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting playoff bracket: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @matchups_bp.route('/leagues/<league_id>/playoff-bracket', methods=['PUT'])
    @validate_json
    def update_playoff_bracket(league_id):
        """Update playoff bracket (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can update playoff bracket'}), 403

            # Update playoff bracket
            success = _update_playoff_bracket(league_id, data)

            if not success:
                return jsonify({'error': 'Failed to update playoff bracket'}), 500

            # Get updated bracket
            updated_bracket = _get_playoff_bracket(league_id)

            return jsonify({
                'success': True,
                'bracket': updated_bracket,
                'message': 'Playoff bracket updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating playoff bracket: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    # Helper functions

    def _get_league_matchups(league_id: str, gameweek: int = None, 
                           status: str = None, limit: int = 50):
        """Get matchups for a league with optional filters."""
        try:
            query = db.collection('leagues').document(league_id)\
                      .collection('matchups')
            
            if gameweek:
                query = query.where('gameweek', '==', gameweek)
            
            if status:
                query = query.where('status', '==', status)
            
            query = query.order_by('gameweek').limit(limit)
            
            docs = query.stream()
            matchups = []
            
            for doc in docs:
                matchup_data = doc.to_dict()
                matchup_data['id'] = doc.id
                matchups.append(matchup_data)
            
            return matchups
            
        except Exception as e:
            logger.error(f"Error getting league matchups: {str(e)}")
            return []

    def _get_gameweek_matchups(league_id: str, gameweek: int):
        """Get all matchups for a specific gameweek."""
        try:
            docs = db.collection('leagues').document(league_id)\
                     .collection('matchups')\
                     .where('gameweek', '==', gameweek)\
                     .stream()
            
            matchups = []
            for doc in docs:
                matchup_data = doc.to_dict()
                matchup_data['id'] = doc.id
                
                # Enrich with team data
                team1 = team_model.get_team(matchup_data.get('team1_id'))
                team2 = team_model.get_team(matchup_data.get('team2_id'))
                
                matchup_data['team1'] = team1
                matchup_data['team2'] = team2
                
                matchups.append(matchup_data)
            
            return matchups
            
        except Exception as e:
            logger.error(f"Error getting gameweek matchups: {str(e)}")
            return []

    def _get_team_matchups(team_id: str, gameweek: int = None, 
                         status: str = None, limit: int = 20):
        """Get matchups for a specific team."""
        try:
            # Get team to find league
            team = team_model.get_team(team_id)
            if not team:
                return []
            
            league_id = team.get('league_id')
            
            # Query matchups where team is either team1 or team2
            query1 = db.collection('leagues').document(league_id)\
                       .collection('matchups')\
                       .where('team1_id', '==', team_id)
            
            query2 = db.collection('leagues').document(league_id)\
                       .collection('matchups')\
                       .where('team2_id', '==', team_id)
            
            if gameweek:
                query1 = query1.where('gameweek', '==', gameweek)
                query2 = query2.where('gameweek', '==', gameweek)
            
            if status:
                query1 = query1.where('status', '==', status)
                query2 = query2.where('status', '==', status)
            
            # Get results from both queries
            docs1 = list(query1.limit(limit).stream())
            docs2 = list(query2.limit(limit).stream())
            
            matchups = []
            all_docs = docs1 + docs2
            
            # Sort by gameweek and remove duplicates
            seen_ids = set()
            for doc in sorted(all_docs, key=lambda x: x.to_dict().get('gameweek', 0)):
                if doc.id not in seen_ids:
                    matchup_data = doc.to_dict()
                    matchup_data['id'] = doc.id
                    
                    # Enrich with opponent data
                    opponent_id = (matchup_data.get('team2_id') if matchup_data.get('team1_id') == team_id 
                                 else matchup_data.get('team1_id'))
                    opponent = team_model.get_team(opponent_id)
                    matchup_data['opponent'] = opponent
                    
                    matchups.append(matchup_data)
                    seen_ids.add(doc.id)
            
            return matchups[:limit]
            
        except Exception as e:
            logger.error(f"Error getting team matchups: {str(e)}")
            return []

    def _get_matchup_details(matchup_id: str):
        """Get detailed information about a specific matchup."""
        try:
            # First, find which league this matchup belongs to
            # We'll need to search across leagues - this is a limitation of the current structure
            # In a production app, you'd want a global matchups collection or store league_id in matchup
            
            # For now, we'll implement a simple search
            leagues = db.collection('leagues').stream()
            
            for league_doc in leagues:
                matchup_doc = db.collection('leagues').document(league_doc.id)\
                               .collection('matchups').document(matchup_id).get()
                
                if matchup_doc.exists:
                    matchup_data = matchup_doc.to_dict()
                    matchup_data['id'] = matchup_doc.id
                    matchup_data['league_id'] = league_doc.id
                    
                    # Enrich with team data
                    team1 = team_model.get_team(matchup_data.get('team1_id'))
                    team2 = team_model.get_team(matchup_data.get('team2_id'))
                    
                    matchup_data['team1'] = team1
                    matchup_data['team2'] = team2
                    
                    # Get scores if available
                    gameweek = matchup_data.get('gameweek')
                    if gameweek:
                        team1_score = scoring_service.get_team_gameweek_score(team1['id'], gameweek)
                        team2_score = scoring_service.get_team_gameweek_score(team2['id'], gameweek)
                        
                        matchup_data['team1_score'] = team1_score.get('total_points', 0) if team1_score else 0
                        matchup_data['team2_score'] = team2_score.get('total_points', 0) if team2_score else 0
                    
                    return matchup_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting matchup details: {str(e)}")
            return None

    def _generate_matchup_schedule(league_id: str, start_gameweek: int, 
                                 end_gameweek: int, playoff_weeks: int, 
                                 schedule_type: str):
        """Generate matchup schedule for a league."""
        try:
            # Get all teams in the league
            teams = team_model.get_league_teams(league_id)
            team_count = len(teams)
            
            if team_count < 2:
                raise ValueError("At least 2 teams required for matchups")
            
            # Calculate regular season weeks
            regular_season_weeks = end_gameweek - start_gameweek + 1 - playoff_weeks
            
            schedule = []
            
            if schedule_type == 'round_robin':
                schedule = _generate_round_robin_schedule(teams, start_gameweek, regular_season_weeks)
            else:
                schedule = _generate_random_schedule(teams, start_gameweek, regular_season_weeks)
            
            # Save schedule to database
            batch = db.batch()
            
            for matchup in schedule:
                matchup_data = {
                    'team1_id': matchup['team1_id'],
                    'team2_id': matchup['team2_id'],
                    'gameweek': matchup['gameweek'],
                    'status': 'scheduled',
                    'created_at': datetime.utcnow()
                }
                
                doc_ref = db.collection('leagues').document(league_id)\
                           .collection('matchups').document()
                batch.set(doc_ref, matchup_data)
            
            batch.commit()
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error generating matchup schedule: {str(e)}")
            raise

    def _generate_round_robin_schedule(teams, start_gameweek: int, weeks: int):
        """Generate round-robin schedule."""
        team_count = len(teams)
        schedule = []
        
        # If odd number of teams, add a "bye" team
        if team_count % 2 == 1:
            teams.append({'id': 'bye', 'name': 'BYE'})
            team_count += 1
        
        # Generate round-robin matchups
        for week in range(weeks):
            gameweek = start_gameweek + week
            week_matchups = []
            
            # Rotate teams (keep first team fixed, rotate others)
            for i in range(team_count // 2):
                team1_idx = i
                team2_idx = team_count - 1 - i
                
                team1 = teams[team1_idx]
                team2 = teams[team2_idx]
                
                # Skip bye matchups
                if team1['id'] != 'bye' and team2['id'] != 'bye':
                    week_matchups.append({
                        'team1_id': team1['id'],
                        'team2_id': team2['id'],
                        'gameweek': gameweek
                    })
            
            schedule.extend(week_matchups)
            
            # Rotate teams for next week (keep first team fixed)
            if len(teams) > 2:
                teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        
        return schedule

    def _generate_random_schedule(teams, start_gameweek: int, weeks: int):
        """Generate random schedule."""
        import random
        
        team_count = len(teams)
        schedule = []
        
        for week in range(weeks):
            gameweek = start_gameweek + week
            available_teams = teams.copy()
            random.shuffle(available_teams)
            
            week_matchups = []
            
            # Pair teams randomly
            while len(available_teams) >= 2:
                team1 = available_teams.pop()
                team2 = available_teams.pop()
                
                week_matchups.append({
                    'team1_id': team1['id'],
                    'team2_id': team2['id'],
                    'gameweek': gameweek
                })
            
            schedule.extend(week_matchups)
        
        return schedule

    def _get_matchup_scores(matchup_id: str):
        """Get live scores for a matchup."""
        try:
            matchup = _get_matchup_details(matchup_id)
            if not matchup:
                return None
            
            gameweek = matchup.get('gameweek')
            team1_id = matchup.get('team1_id')
            team2_id = matchup.get('team2_id')
            
            # Get current scores
            team1_score = scoring_service.get_team_gameweek_score(team1_id, gameweek)
            team2_score = scoring_service.get_team_gameweek_score(team2_id, gameweek)
            
            return {
                'matchup_id': matchup_id,
                'gameweek': gameweek,
                'team1': {
                    'id': team1_id,
                    'name': matchup['team1']['name'],
                    'score': team1_score.get('total_points', 0) if team1_score else 0,
                    'player_scores': team1_score.get('player_scores', {}) if team1_score else {}
                },
                'team2': {
                    'id': team2_id,
                    'name': matchup['team2']['name'],
                    'score': team2_score.get('total_points', 0) if team2_score else 0,
                    'player_scores': team2_score.get('player_scores', {}) if team2_score else {}
                },
                'status': matchup.get('status', 'scheduled'),
                'last_updated': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting matchup scores: {str(e)}")
            return None

    def _update_matchup_scores(matchup_id: str, team1_score: float, team2_score: float):
        """Update matchup scores manually."""
        try:
            # Find and update the matchup
            leagues = db.collection('leagues').stream()
            
            for league_doc in leagues:
                matchup_ref = db.collection('leagues').document(league_doc.id)\
                               .collection('matchups').document(matchup_id)
                
                matchup_doc = matchup_ref.get()
                if matchup_doc.exists:
                    # Determine winner
                    winner = None
                    if team1_score > team2_score:
                        winner = matchup_doc.to_dict().get('team1_id')
                    elif team2_score > team1_score:
                        winner = matchup_doc.to_dict().get('team2_id')
                    
                    # Update matchup
                    matchup_ref.update({
                        'team1_score': team1_score,
                        'team2_score': team2_score,
                        'winner': winner,
                        'status': 'completed',
                        'completed_at': datetime.utcnow(),
                        'manually_scored': True
                    })
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating matchup scores: {str(e)}")
            return False

    def _get_league_standings(league_id: str):
        """Get current league standings."""
        try:
            standings_ref = db.collection('leagues').document(league_id)\
                              .collection('standings').document('current')
            
            doc = standings_ref.get()
            if doc.exists:
                standings_data = doc.to_dict()
                standings = standings_data.get('standings', [])
                
                # Sort by wins, then by points for
                standings.sort(key=lambda x: (x.get('wins', 0), x.get('points_for', 0)), reverse=True)
                
                # Add rank
                for i, team in enumerate(standings):
                    team['rank'] = i + 1
                
                return standings
            
            # If no standings exist, create basic ones from teams
            teams = team_model.get_league_teams(league_id)
            standings = []
            
            for team in teams:
                standings.append({
                    'team_id': team['id'],
                    'team_name': team.get('name', 'Unknown'),
                    'wins': 0,
                    'losses': 0,
                    'draws': 0,
                    'points_for': 0,
                    'points_against': 0,
                    'rank': 0
                })
            
            return standings
            
        except Exception as e:
            logger.error(f"Error getting league standings: {str(e)}")
            return []

    def _get_league_schedule(league_id: str, gameweek_start: int = None, 
                           gameweek_end: int = None):
        """Get complete league schedule."""
        try:
            query = db.collection('leagues').document(league_id)\
                      .collection('matchups')\
                      .order_by('gameweek')
            
            if gameweek_start:
                query = query.where('gameweek', '>=', gameweek_start)
            
            if gameweek_end:
                query = query.where('gameweek', '<=', gameweek_end)
            
            docs = query.stream()
            schedule = {}
            
            for doc in docs:
                matchup_data = doc.to_dict()
                matchup_data['id'] = doc.id
                
                gameweek = matchup_data.get('gameweek')
                if gameweek not in schedule:
                    schedule[gameweek] = []
                
                # Enrich with team data
                team1 = team_model.get_team(matchup_data.get('team1_id'))
                team2 = team_model.get_team(matchup_data.get('team2_id'))
                
                matchup_data['team1'] = team1
                matchup_data['team2'] = team2
                
                schedule[gameweek].append(matchup_data)
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error getting league schedule: {str(e)}")
            return {}

    def _get_league_scoreboard(league_id: str, gameweek: int):
        """Get live scoreboard for current gameweek."""
        try:
            # Get gameweek matchups
            matchups = _get_gameweek_matchups(league_id, gameweek)
            
            scoreboard = []
            
            for matchup in matchups:
                # Get live scores
                scores = _get_matchup_scores(matchup['id'])
                if scores:
                    scoreboard.append({
                        'matchup_id': matchup['id'],
                        'team1': scores['team1'],
                        'team2': scores['team2'],
                        'status': scores['status']
                    })
            
            return {
                'gameweek': gameweek,
                'matchups': scoreboard,
                'last_updated': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting league scoreboard: {str(e)}")
            return {}

    def _get_playoff_bracket(league_id: str):
        """Get playoff bracket for a league."""
        try:
            bracket_ref = db.collection('leagues').document(league_id)\
                            .collection('playoffs').document('bracket')
            
            doc = bracket_ref.get()
            if doc.exists:
                return doc.to_dict()
            
            # Generate default bracket based on standings
            standings = _get_league_standings(league_id)
            bracket = _generate_default_bracket(standings)
            
            # Save default bracket
            bracket_ref.set(bracket)
            
            return bracket
            
        except Exception as e:
            logger.error(f"Error getting playoff bracket: {str(e)}")
            return {}

    def _generate_default_bracket(standings):
        """Generate default playoff bracket from standings."""
        try:
            # Take top teams for playoffs (typically top 6 or 8)
            playoff_teams = standings[:6]  # Top 6 teams
            
            bracket = {
                'teams': playoff_teams,
                'rounds': {
                    'semifinals': [
                        {
                            'matchup_id': 'sf1',
                            'team1': playoff_teams[0] if len(playoff_teams) > 0 else None,
                            'team2': playoff_teams[3] if len(playoff_teams) > 3 else None,
                            'winner': None
                        },
                        {
                            'matchup_id': 'sf2',
                            'team1': playoff_teams[1] if len(playoff_teams) > 1 else None,
                            'team2': playoff_teams[2] if len(playoff_teams) > 2 else None,
                            'winner': None
                        }
                    ],
                    'finals': [
                        {
                            'matchup_id': 'final',
                            'team1': None,  # Winner of sf1
                            'team2': None,  # Winner of sf2
                            'winner': None
                        }
                    ]
                },
                'created_at': datetime.utcnow()
            }
            
            return bracket
            
        except Exception as e:
            logger.error(f"Error generating default bracket: {str(e)}")
            return {}

    def _update_playoff_bracket(league_id: str, bracket_data):
        """Update playoff bracket."""
        try:
            bracket_ref = db.collection('leagues').document(league_id)\
                            .collection('playoffs').document('bracket')
            
            bracket_data['updated_at'] = datetime.utcnow()
            bracket_ref.set(bracket_data, merge=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating playoff bracket: {str(e)}")
            return False

    def _get_current_gameweek():
        """Get current gameweek from FPL API (synchronous version)."""
        try:
            from ..utils.api_integrations import FPLAPIClient
            fpl_client = FPLAPIClient()
            
            # Use synchronous call instead of async
            bootstrap_data = fpl_client.get_bootstrap_static_sync()
            
            if bootstrap_data and 'events' in bootstrap_data:
                for event in bootstrap_data['events']:
                    if event.get('is_current', False):
                        return event['id']
            
            return 1  # Default to gameweek 1
            
        except Exception as e:
            logger.error(f"Error getting current gameweek: {str(e)}")
            return 1

    # Register blueprint
    app.register_blueprint(matchups_bp, url_prefix='/api')