"""
Teams routes for managing team operations, rosters, lineups, and settings.
Handles team CRUD operations, roster management, and transaction history.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from ..services.auth_service import AuthService
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..services.notification_service import NotificationService
from ..utils.validators import validate_json, validate_team_data
from ..utils.logger import get_logger

logger = get_logger(__name__)

teams_bp = Blueprint('teams', __name__)

def init_teams_routes(app, db, socketio):
    """Initialize teams routes with dependencies."""
    auth_service = AuthService()
    team_model = TeamModel(db)
    league_model = LeagueModel(db)
    notification_service = NotificationService(db, socketio)

    @teams_bp.route('/teams/<team_id>', methods=['GET'])
    def get_team(team_id):
        """Get team details."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            return jsonify({
                'success': True,
                'team': team
            })

        except Exception as e:
            logger.error(f"Error getting team: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>', methods=['PUT'])
    @validate_json
    def update_team(team_id):
        """Update team details."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own this team'}), 403

            # Validate update data
            validation_result = validate_team_data(data, partial=True)
            if not validation_result['valid']:
                return jsonify({'error': validation_result['message']}), 400

            # Update team
            updates = {}
            allowed_fields = ['name', 'logo_url', 'description']
            
            for field in allowed_fields:
                if field in data:
                    updates[field] = data[field]

            if updates:
                updates['updated_at'] = datetime.utcnow()
                success = team_model.update_team(team_id, updates)
                
                if not success:
                    return jsonify({'error': 'Failed to update team'}), 500

            # Get updated team
            updated_team = team_model.get_team(team_id)

            # Emit real-time update
            socketio.emit('team_updated', {
                'team_id': team_id,
                'updates': updates
            }, room=f"league_{team['league_id']}")

            return jsonify({
                'success': True,
                'team': updated_team
            })

        except Exception as e:
            logger.error(f"Error updating team: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/roster', methods=['GET'])
    def get_team_roster(team_id):
        """Get team roster."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            roster = team.get('roster', [])

            return jsonify({
                'success': True,
                'roster': roster,
                'roster_size': len(roster)
            })

        except Exception as e:
            logger.error(f"Error getting team roster: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/lineup/<int:gameweek>', methods=['GET'])
    def get_team_lineup(team_id, gameweek):
        """Get team lineup for a specific gameweek."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            lineup = team_model.get_team_lineup(team_id, gameweek)
            
            return jsonify({
                'success': True,
                'lineup': lineup,
                'gameweek': gameweek
            })

        except Exception as e:
            logger.error(f"Error getting team lineup: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/lineup/<int:gameweek>', methods=['PUT'])
    @validate_json
    def set_team_lineup(team_id, gameweek):
        """Set team lineup for a specific gameweek."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own this team'}), 403

            # Validate lineup data
            required_fields = ['starting_11', 'bench', 'captain', 'vice_captain']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            # Validate lineup composition
            starting_11 = data['starting_11']
            bench = data['bench']
            captain = data['captain']
            vice_captain = data['vice_captain']

            if len(starting_11) != 11:
                return jsonify({'error': 'Starting 11 must contain exactly 11 players'}), 400

            if len(bench) > 4:
                return jsonify({'error': 'Bench can contain maximum 4 players'}), 400

            if captain not in starting_11:
                return jsonify({'error': 'Captain must be in starting 11'}), 400

            if vice_captain not in starting_11:
                return jsonify({'error': 'Vice captain must be in starting 11'}), 400

            if captain == vice_captain:
                return jsonify({'error': 'Captain and vice captain must be different players'}), 400

            # Verify all players are on roster
            roster_player_ids = [p.get('fpl_id') for p in team.get('roster', [])]
            all_lineup_players = starting_11 + bench

            for player_id in all_lineup_players:
                if player_id not in roster_player_ids:
                    return jsonify({'error': f'Player {player_id} not found on roster'}), 400

            # Check for duplicate players
            if len(set(all_lineup_players)) != len(all_lineup_players):
                return jsonify({'error': 'Duplicate players in lineup'}), 400

            # Validate positional requirements
            validation_result = _validate_lineup_positions(team['roster'], starting_11)
            if not validation_result['valid']:
                return jsonify({'error': validation_result['message']}), 400

            # Set lineup
            lineup_data = {
                'starting_11': starting_11,
                'bench': bench,
                'captain': captain,
                'vice_captain': vice_captain,
                'set_at': datetime.utcnow()
            }

            success = team_model.set_team_lineup(team_id, gameweek, lineup_data)
            if not success:
                return jsonify({'error': 'Failed to set lineup'}), 500

            # Emit real-time update
            socketio.emit('lineup_updated', {
                'team_id': team_id,
                'gameweek': gameweek,
                'lineup': lineup_data
            }, room=f"league_{team['league_id']}")

            return jsonify({
                'success': True,
                'lineup': lineup_data,
                'message': f'Lineup set for Gameweek {gameweek}'
            })

        except Exception as e:
            logger.error(f"Error setting team lineup: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    def _validate_lineup_positions(roster, starting_11):
        """Validate lineup meets positional requirements."""
        try:
            # Count positions in starting 11
            position_counts = {'GKP': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            
            roster_lookup = {p.get('fpl_id'): p for p in roster}
            
            for player_id in starting_11:
                player = roster_lookup.get(player_id)
                if player:
                    position = player.get('position', 'Unknown')
                    if position in position_counts:
                        position_counts[position] += 1

            # Check requirements (3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1)
            gkp_count = position_counts['GKP']
            def_count = position_counts['DEF']
            mid_count = position_counts['MID']
            fwd_count = position_counts['FWD']

            if gkp_count != 1:
                return {'valid': False, 'message': 'Must have exactly 1 goalkeeper'}

            if def_count < 3 or def_count > 5:
                return {'valid': False, 'message': 'Must have 3-5 defenders'}

            if mid_count < 3 or mid_count > 5:
                return {'valid': False, 'message': 'Must have 3-5 midfielders'}

            if fwd_count < 1 or fwd_count > 3:
                return {'valid': False, 'message': 'Must have 1-3 forwards'}

            if def_count + mid_count + fwd_count != 10:
                return {'valid': False, 'message': 'Outfield players must total 10'}

            return {'valid': True, 'message': 'Valid lineup'}

        except Exception as e:
            logger.error(f"Error validating lineup positions: {str(e)}")
            return {'valid': False, 'message': 'Validation error'}

    @teams_bp.route('/teams/<team_id>/transactions', methods=['GET'])
    def get_team_transactions(team_id):
        """Get team transaction history."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            limit = int(request.args.get('limit', 50))
            transaction_type = request.args.get('type')  # 'trade', 'waiver', 'draft', etc.

            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            transactions = team_model.get_team_transactions(team_id, transaction_type, limit)

            return jsonify({
                'success': True,
                'transactions': transactions,
                'count': len(transactions)
            })

        except Exception as e:
            logger.error(f"Error getting team transactions: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/settings', methods=['GET'])
    def get_team_settings(team_id):
        """Get team settings."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own this team'}), 403

            settings = team_model.get_team_settings(team_id)

            return jsonify({
                'success': True,
                'settings': settings
            })

        except Exception as e:
            logger.error(f"Error getting team settings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/settings', methods=['PUT'])
    @validate_json
    def update_team_settings(team_id):
        """Update team settings."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own this team'}), 403

            # Update settings
            allowed_settings = [
                'auto_lineup', 'email_notifications', 'push_notifications',
                'trade_notifications', 'waiver_notifications', 'draft_notifications'
            ]

            settings_updates = {}
            for setting in allowed_settings:
                if setting in data:
                    settings_updates[setting] = data[setting]

            if settings_updates:
                success = team_model.update_team_settings(team_id, settings_updates)
                if not success:
                    return jsonify({'error': 'Failed to update settings'}), 500

            # Get updated settings
            updated_settings = team_model.get_team_settings(team_id)

            return jsonify({
                'success': True,
                'settings': updated_settings,
                'message': 'Settings updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating team settings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/co-owners', methods=['GET'])
    def get_team_co_owners(team_id):
        """Get team co-owners."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            co_owners = team.get('co_owners', [])

            return jsonify({
                'success': True,
                'co_owners': co_owners
            })

        except Exception as e:
            logger.error(f"Error getting team co-owners: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/co-owners', methods=['POST'])
    @validate_json
    def add_team_co_owner(team_id):
        """Add a co-owner to the team."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'Only the team owner can add co-owners'}), 403

            # Validate request data
            if 'user_id' not in data:
                return jsonify({'error': 'user_id is required'}), 400

            co_owner_user_id = data['user_id']

            # Check if user is already owner or co-owner
            if co_owner_user_id == user_id:
                return jsonify({'error': 'Cannot add yourself as co-owner'}), 400

            current_co_owners = team.get('co_owners', [])
            if co_owner_user_id in [co['user_id'] for co in current_co_owners]:
                return jsonify({'error': 'User is already a co-owner'}), 400

            # Add co-owner
            co_owner_data = {
                'user_id': co_owner_user_id,
                'permissions': data.get('permissions', ['lineup', 'trades']),
                'added_at': datetime.utcnow(),
                'added_by': user_id
            }

            success = team_model.add_team_co_owner(team_id, co_owner_data)
            if not success:
                return jsonify({'error': 'Failed to add co-owner'}), 500

            # Send notification to new co-owner
            if notification_service:
                notification_service.send_notification(
                    co_owner_user_id,
                    'team_co_owner_added',
                    'Added as Co-Owner',
                    f'You have been added as a co-owner of {team.get("name", "a team")}',
                    {'team_id': team_id, 'team_name': team.get('name')},
                    team.get('league_id')
                )

            return jsonify({
                'success': True,
                'co_owner': co_owner_data,
                'message': 'Co-owner added successfully'
            })

        except Exception as e:
            logger.error(f"Error adding team co-owner: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/co-owners/<co_owner_user_id>', methods=['DELETE'])
    def remove_team_co_owner(team_id, co_owner_user_id):
        """Remove a co-owner from the team."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'Only the team owner can remove co-owners'}), 403

            # Remove co-owner
            success = team_model.remove_team_co_owner(team_id, co_owner_user_id)
            if not success:
                return jsonify({'error': 'Failed to remove co-owner or co-owner not found'}), 500

            # Send notification to removed co-owner
            if notification_service:
                notification_service.send_notification(
                    co_owner_user_id,
                    'team_co_owner_removed',
                    'Removed as Co-Owner',
                    f'You have been removed as a co-owner of {team.get("name", "a team")}',
                    {'team_id': team_id, 'team_name': team.get('name')},
                    team.get('league_id')
                )

            return jsonify({
                'success': True,
                'message': 'Co-owner removed successfully'
            })

        except Exception as e:
            logger.error(f"Error removing team co-owner: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/stats', methods=['GET'])
    def get_team_stats(team_id):
        """Get team statistics."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            # Get season stats
            season_stats = team_model.get_team_season_stats(team_id)
            
            # Get recent gameweek scores
            recent_scores = team_model.get_team_recent_scores(team_id, limit=5)

            # Calculate additional metrics
            roster = team.get('roster', [])
            roster_value = sum(player.get('current_value', 0) for player in roster)
            
            stats = {
                'season_stats': season_stats,
                'recent_scores': recent_scores,
                'roster_stats': {
                    'total_players': len(roster),
                    'total_value': roster_value,
                    'average_value': roster_value / len(roster) if roster else 0,
                    'by_position': _get_roster_position_breakdown(roster)
                }
            }

            return jsonify({
                'success': True,
                'stats': stats
            })

        except Exception as e:
            logger.error(f"Error getting team stats: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    def _get_roster_position_breakdown(roster):
        """Get breakdown of roster by position."""
        try:
            breakdown = {'GKP': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            
            for player in roster:
                position = player.get('position', 'Unknown')
                if position in breakdown:
                    breakdown[position] += 1
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error getting roster breakdown: {str(e)}")
            return {'GKP': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}

    @teams_bp.route('/teams/<team_id>/optimal-lineup/<int:gameweek>', methods=['GET'])
    def get_optimal_lineup(team_id, gameweek):
        """Get optimal lineup for a gameweek."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            # Calculate optimal lineup using scoring service
            from ..services.scoring_service import ScoringService
            scoring_service = ScoringService(db, socketio)
            
            optimal_analysis = scoring_service.calculate_optimal_lineup_points(team_id, gameweek)

            return jsonify({
                'success': True,
                'optimal_lineup': optimal_analysis,
                'gameweek': gameweek
            })

        except Exception as e:
            logger.error(f"Error getting optimal lineup: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @teams_bp.route('/teams/<team_id>/auto-lineup/<int:gameweek>', methods=['POST'])
    def set_auto_lineup(team_id, gameweek):
        """Set lineup automatically based on projected points."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own this team'}), 403

            # Generate optimal lineup
            auto_lineup = _generate_auto_lineup(team['roster'])
            if not auto_lineup:
                return jsonify({'error': 'Could not generate auto lineup'}), 500

            # Set the lineup
            success = team_model.set_team_lineup(team_id, gameweek, auto_lineup)
            if not success:
                return jsonify({'error': 'Failed to set auto lineup'}), 500

            # Emit real-time update
            socketio.emit('lineup_updated', {
                'team_id': team_id,
                'gameweek': gameweek,
                'lineup': auto_lineup,
                'auto_generated': True
            }, room=f"league_{team['league_id']}")

            return jsonify({
                'success': True,
                'lineup': auto_lineup,
                'message': f'Auto lineup set for Gameweek {gameweek}'
            })

        except Exception as e:
            logger.error(f"Error setting auto lineup: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    def _generate_auto_lineup(roster):
        """Generate automatic lineup based on projected points."""
        try:
            if len(roster) < 11:
                return None

            # Group players by position
            by_position = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
            
            for player in roster:
                position = player.get('position', 'Unknown')
                if position in by_position:
                    by_position[position].append(player)

            # Sort each position by projected points (or total points as fallback)
            for position in by_position:
                by_position[position].sort(
                    key=lambda x: x.get('projected_points', x.get('total_points', 0)), 
                    reverse=True
                )

            # Build formation (4-4-2 default)
            starting_11 = []
            
            # Add best GKP
            if by_position['GKP']:
                starting_11.append(by_position['GKP'][0]['fpl_id'])

            # Add best 4 DEF
            for i in range(min(4, len(by_position['DEF']))):
                starting_11.append(by_position['DEF'][i]['fpl_id'])

            # Add best 4 MID
            for i in range(min(4, len(by_position['MID']))):
                starting_11.append(by_position['MID'][i]['fpl_id'])

            # Add best 2 FWD
            for i in range(min(2, len(by_position['FWD']))):
                starting_11.append(by_position['FWD'][i]['fpl_id'])

            # If we don't have enough players, fill from remaining
            remaining_players = []
            for position in by_position:
                used_count = {'GKP': 1, 'DEF': 4, 'MID': 4, 'FWD': 2}.get(position, 0)
                for player in by_position[position][used_count:]:
                    remaining_players.append(player)

            # Sort remaining by points and add to starting 11
            remaining_players.sort(
                key=lambda x: x.get('projected_points', x.get('total_points', 0)), 
                reverse=True
            )

            while len(starting_11) < 11 and remaining_players:
                starting_11.append(remaining_players.pop(0)['fpl_id'])

            if len(starting_11) < 11:
                return None

            # Build bench from remaining players
            bench = []
            while len(bench) < 4 and remaining_players:
                bench.append(remaining_players.pop(0)['fpl_id'])

            # Set captain and vice captain (highest scorers in starting 11)
            starting_players = [p for p in roster if p['fpl_id'] in starting_11]
            starting_players.sort(
                key=lambda x: x.get('projected_points', x.get('total_points', 0)), 
                reverse=True
            )

            captain = starting_players[0]['fpl_id'] if starting_players else starting_11[0]
            vice_captain = starting_players[1]['fpl_id'] if len(starting_players) > 1 else starting_11[1]

            return {
                'starting_11': starting_11,
                'bench': bench,
                'captain': captain,
                'vice_captain': vice_captain,
                'set_at': datetime.utcnow(),
                'auto_generated': True
            }

        except Exception as e:
            logger.error(f"Error generating auto lineup: {str(e)}")
            return None

    # Register blueprint
    app.register_blueprint(teams_bp, url_prefix='/api')