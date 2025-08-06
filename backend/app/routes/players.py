"""
Players routes for searching, filtering, and managing player data.
Handles player search, trending players, leaders, and tracking functionality.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from ..services.auth_service import AuthService
from ..services.player_service import PlayerService
from ..models.player_model import PlayerModel
from ..utils.validators import validate_json
from ..utils.logger import get_logger

logger = get_logger(__name__)

players_bp = Blueprint('players', __name__)

def init_players_routes(app, db, socketio):
    """Initialize players routes with dependencies."""
    auth_service = AuthService()
    player_service = PlayerService(db)
    player_model = PlayerModel(db)

    @players_bp.route('/players/search', methods=['GET'])
    def search_players():
        """Search for players with filters."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get search parameters
            query = request.args.get('q', '').strip()
            position = request.args.get('position')
            team = request.args.get('team')
            min_price = request.args.get('min_price', type=float)
            max_price = request.args.get('max_price', type=float)
            min_points = request.args.get('min_points', type=int)
            max_points = request.args.get('max_points', type=int)
            min_form = request.args.get('min_form', type=float)
            available_only = request.args.get('available_only', 'false').lower() == 'true'
            exclude_injured = request.args.get('exclude_injured', 'false').lower() == 'true'
            limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 results

            # Build filters
            filters = {}
            if position:
                filters['position'] = position.split(',')
            if team:
                filters['team'] = team.split(',')
            if min_price is not None:
                filters['min_price'] = min_price
            if max_price is not None:
                filters['max_price'] = max_price
            if min_points is not None:
                filters['min_points'] = min_points
            if max_points is not None:
                filters['max_points'] = max_points
            if min_form is not None:
                filters['min_form'] = min_form
            if available_only:
                filters['available_only'] = True
            if exclude_injured:
                filters['exclude_injured'] = True

            # Search players
            players = player_service.search_players(query, filters, limit)

            return jsonify({
                'success': True,
                'players': players,
                'count': len(players),
                'query': query,
                'filters': filters
            })

        except Exception as e:
            logger.error(f"Error searching players: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/<int:player_fpl_id>', methods=['GET'])
    def get_player_details(player_fpl_id):
        """Get detailed player information."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get player details
            player = player_service.get_player_details(player_fpl_id)
            
            if not player:
                return jsonify({'error': 'Player not found'}), 404

            return jsonify({
                'success': True,
                'player': player
            })

        except Exception as e:
            logger.error(f"Error getting player details: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/trending', methods=['GET'])
    def get_trending_players():
        """Get trending players based on various metrics."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            timeframe = request.args.get('timeframe', 'week')  # week, gameweek, month
            metric = request.args.get('metric', 'transfers_in')  # transfers_in, form, points, etc.
            limit = min(int(request.args.get('limit', 25)), 50)

            # Validate parameters
            valid_timeframes = ['week', 'gameweek', 'month']
            valid_metrics = ['transfers_in', 'transfers_out', 'form', 'points', 'ownership', 'price_rise', 'price_fall']
            
            if timeframe not in valid_timeframes:
                return jsonify({'error': f'Invalid timeframe. Must be one of: {valid_timeframes}'}), 400
            
            if metric not in valid_metrics:
                return jsonify({'error': f'Invalid metric. Must be one of: {valid_metrics}'}), 400

            # Get trending players
            trending_players = player_service.get_trending_players(timeframe, metric)

            return jsonify({
                'success': True,
                'trending_players': trending_players[:limit],
                'timeframe': timeframe,
                'metric': metric,
                'count': len(trending_players[:limit])
            })

        except Exception as e:
            logger.error(f"Error getting trending players: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/leaders', methods=['GET'])
    def get_player_leaders():
        """Get players leading in specific statistics."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            stat = request.args.get('stat', 'points')
            position = request.args.get('position')  # Filter by position
            timeframe = request.args.get('timeframe', 'season')
            limit = min(int(request.args.get('limit', 25)), 50)

            # Validate stat parameter
            valid_stats = [
                'goals', 'assists', 'points', 'clean_sheets', 'saves', 'bonus',
                'minutes', 'form', 'points_per_game', 'influence', 'creativity',
                'threat', 'ict_index', 'expected_goals', 'expected_assists', 'value_season'
            ]
            
            if stat not in valid_stats:
                return jsonify({'error': f'Invalid stat. Must be one of: {valid_stats}'}), 400

            # Get leaders
            leaders = player_service.get_player_leaders(stat, position, timeframe)

            return jsonify({
                'success': True,
                'leaders': leaders[:limit],
                'stat': stat,
                'position': position,
                'timeframe': timeframe,
                'count': len(leaders[:limit])
            })

        except Exception as e:
            logger.error(f"Error getting player leaders: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/compare', methods=['POST'])
    @validate_json
    def compare_players():
        """Compare multiple players side by side."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            data = request.get_json()

            # Validate request
            if 'player_ids' not in data:
                return jsonify({'error': 'player_ids is required'}), 400

            player_ids = data['player_ids']
            
            if not isinstance(player_ids, list):
                return jsonify({'error': 'player_ids must be a list'}), 400

            if len(player_ids) < 2:
                return jsonify({'error': 'At least 2 players required for comparison'}), 400

            if len(player_ids) > 5:
                return jsonify({'error': 'Maximum 5 players can be compared'}), 400

            # Compare players
            comparison = player_service.get_player_comparison(player_ids)

            if not comparison:
                return jsonify({'error': 'No players found for comparison'}), 404

            return jsonify({
                'success': True,
                'comparison': comparison
            })

        except Exception as e:
            logger.error(f"Error comparing players: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/position-analysis/<position>', methods=['GET'])
    def get_position_analysis(position):
        """Get analysis for all players in a specific position."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Validate position
            valid_positions = ['GKP', 'DEF', 'MID', 'FWD']
            if position not in valid_positions:
                return jsonify({'error': f'Invalid position. Must be one of: {valid_positions}'}), 400

            # Get position analysis
            analysis = player_service.get_position_analysis(position)

            return jsonify({
                'success': True,
                'analysis': analysis,
                'position': position
            })

        except Exception as e:
            logger.error(f"Error getting position analysis: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/track', methods=['POST'])
    @validate_json
    def track_player():
        """Add a player to user's tracking list."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate request
            if 'player_fpl_id' not in data:
                return jsonify({'error': 'player_fpl_id is required'}), 400

            player_fpl_id = int(data['player_fpl_id'])

            # Track player
            success = player_service.track_player(user_id, player_fpl_id)

            if not success:
                return jsonify({'error': 'Player not found or already tracked'}), 400

            return jsonify({
                'success': True,
                'message': 'Player added to tracking list'
            })

        except Exception as e:
            logger.error(f"Error tracking player: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/track/<int:player_fpl_id>', methods=['DELETE'])
    def untrack_player(player_fpl_id):
        """Remove a player from user's tracking list."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Untrack player
            success = player_service.untrack_player(user_id, player_fpl_id)

            if not success:
                return jsonify({'error': 'Failed to untrack player'}), 500

            return jsonify({
                'success': True,
                'message': 'Player removed from tracking list'
            })

        except Exception as e:
            logger.error(f"Error untracking player: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/tracked', methods=['GET'])
    def get_tracked_players():
        """Get user's tracked players."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Get tracked players
            tracked_players = player_service.get_tracked_players(user_id)

            return jsonify({
                'success': True,
                'tracked_players': tracked_players,
                'count': len(tracked_players)
            })

        except Exception as e:
            logger.error(f"Error getting tracked players: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/refresh', methods=['POST'])
    def refresh_player_data():
        """Refresh player data from FPL API (admin only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # TODO: Add admin role check
            # For now, allow any authenticated user to refresh
            
            # Refresh player data
            refresh_summary = player_service.refresh_player_data()

            return jsonify({
                'success': True,
                'refresh_summary': refresh_summary
            })

        except Exception as e:
            logger.error(f"Error refreshing player data: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/available/<league_id>', methods=['GET'])
    def get_available_players(league_id):
        """Get players available for waiver claims in a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get search and filter parameters
            query = request.args.get('q', '').strip()
            position = request.args.get('position')
            sort_by = request.args.get('sort', 'total_points')  # total_points, form, ownership, etc.
            sort_order = request.args.get('order', 'desc')  # desc, asc
            limit = min(int(request.args.get('limit', 50)), 100)

            # Build filters for available players
            filters = {'available_only': True}
            if position:
                filters['position'] = position.split(',')

            # Search available players
            available_players = player_service.search_players(query, filters, limit * 2)

            # Get all rostered players in the league to exclude them
            from ..models.team_model import TeamModel
            team_model = TeamModel(db)
            league_teams = team_model.get_league_teams(league_id)
            
            rostered_player_ids = set()
            for team in league_teams:
                for player in team.get('roster', []):
                    rostered_player_ids.add(player.get('fpl_id'))

            # Filter out rostered players
            truly_available = [
                player for player in available_players 
                if player.get('fpl_id') not in rostered_player_ids
            ]

            # Sort players
            reverse_sort = sort_order.lower() == 'desc'
            sort_key_map = {
                'total_points': 'total_points',
                'form': 'form',
                'ownership': 'selected_by_percent',
                'price': 'now_cost',
                'name': 'web_name',
                'team': 'team',
                'points_per_game': 'points_per_game'
            }
            
            sort_key = sort_key_map.get(sort_by, 'total_points')
            
            if sort_key == 'web_name':
                truly_available.sort(key=lambda x: x.get(sort_key, ''), reverse=reverse_sort)
            else:
                truly_available.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse_sort)

            return jsonify({
                'success': True,
                'available_players': truly_available[:limit],
                'count': len(truly_available[:limit]),
                'total_available': len(truly_available),
                'league_id': league_id,
                'sort_by': sort_by,
                'sort_order': sort_order
            })

        except Exception as e:
            logger.error(f"Error getting available players: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/teams', methods=['GET'])
    def get_player_teams():
        """Get list of all Premier League teams."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get teams from cached player data or API
            teams = player_service.get_premier_league_teams()

            return jsonify({
                'success': True,
                'teams': teams
            })

        except Exception as e:
            logger.error(f"Error getting player teams: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/positions', methods=['GET'])
    def get_player_positions():
        """Get list of all player positions."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            positions = [
                {'id': 'GKP', 'name': 'Goalkeeper', 'short_name': 'GKP'},
                {'id': 'DEF', 'name': 'Defender', 'short_name': 'DEF'},
                {'id': 'MID', 'name': 'Midfielder', 'short_name': 'MID'},
                {'id': 'FWD', 'name': 'Forward', 'short_name': 'FWD'}
            ]

            return jsonify({
                'success': True,
                'positions': positions
            })

        except Exception as e:
            logger.error(f"Error getting player positions: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/stats/<int:player_fpl_id>/history', methods=['GET'])
    def get_player_history(player_fpl_id):
        """Get player's historical performance data."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            gameweeks = request.args.get('gameweeks', type=int)  # Limit to recent gameweeks
            season = request.args.get('season')  # Specific season

            # Get player history
            player_history = player_service.get_player_history(
                player_fpl_id, gameweeks, season
            )

            if not player_history:
                return jsonify({'error': 'Player history not found'}), 404

            return jsonify({
                'success': True,
                'player_history': player_history,
                'player_fpl_id': player_fpl_id
            })

        except Exception as e:
            logger.error(f"Error getting player history: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/fixtures/<int:player_fpl_id>', methods=['GET'])
    def get_player_fixtures(player_fpl_id):
        """Get upcoming fixtures for a player's team."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            limit = min(int(request.args.get('limit', 5)), 10)

            # Get player fixtures
            fixtures = player_service.get_player_fixtures(player_fpl_id, limit)

            return jsonify({
                'success': True,
                'fixtures': fixtures,
                'player_fpl_id': player_fpl_id,
                'count': len(fixtures)
            })

        except Exception as e:
            logger.error(f"Error getting player fixtures: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/search/autocomplete', methods=['GET'])
    def autocomplete_players():
        """Get autocomplete suggestions for player search."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get search query
            query = request.args.get('q', '').strip()
            limit = min(int(request.args.get('limit', 10)), 20)

            if len(query) < 2:
                return jsonify({
                    'success': True,
                    'suggestions': []
                })

            # Get autocomplete suggestions
            suggestions = player_service.get_autocomplete_suggestions(query, limit)

            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'query': query
            })

        except Exception as e:
            logger.error(f"Error getting autocomplete suggestions: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/stats/cache-status', methods=['GET'])
    def get_cache_status():
        """Get player data cache status."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            cache_status = player_service.get_cache_status()

            return jsonify({
                'success': True,
                'cache_status': cache_status
            })

        except Exception as e:
            logger.error(f"Error getting cache status: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/price-changes', methods=['GET'])
    def get_price_changes():
        """Get recent player price changes."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            change_type = request.args.get('type', 'all')  # all, rises, falls
            limit = min(int(request.args.get('limit', 20)), 50)

            # Get price changes
            price_changes = player_service.get_recent_price_changes(change_type, limit)

            return jsonify({
                'success': True,
                'price_changes': price_changes,
                'change_type': change_type,
                'count': len(price_changes)
            })

        except Exception as e:
            logger.error(f"Error getting price changes: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @players_bp.route('/players/ownership/<league_id>', methods=['GET'])
    def get_league_ownership(league_id):
        """Get player ownership statistics within a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            position = request.args.get('position')
            limit = min(int(request.args.get('limit', 25)), 50)

            # Calculate league ownership
            ownership_stats = player_service.get_league_ownership_stats(
                league_id, position, limit
            )

            return jsonify({
                'success': True,
                'ownership_stats': ownership_stats,
                'league_id': league_id,
                'position': position
            })

        except Exception as e:
            logger.error(f"Error getting league ownership: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    # Register blueprint
    app.register_blueprint(players_bp, url_prefix='/api')