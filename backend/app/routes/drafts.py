"""
Draft routes for handling draft operations.
"""
from flask import Blueprint, request, jsonify, g
from ..services.auth_service import require_auth, require_league_access
from ..services.draft_service import DraftService
from ..services.player_service import PlayerService
from ..utils.validators import validate_json_request
from ..utils.logger import get_logger

logger = get_logger('drafts_routes')
drafts_bp = Blueprint('drafts', __name__)

draft_service = DraftService()
player_service = PlayerService()

@drafts_bp.route('/<league_id>', methods=['GET'])
@require_auth
@require_league_access('member')
def get_draft_board(league_id):
    """Get the current draft board state."""
    try:
        draft_board = draft_service.get_draft_board(league_id)
        
        if not draft_board:
            return jsonify({'error': 'Failed to get draft board'}), 500
        
        return jsonify({'draft_board': draft_board}), 200
        
    except Exception as e:
        logger.error(f"Failed to get draft board: {e}")
        return jsonify({'error': 'Failed to get draft board'}), 500

@drafts_bp.route('/<league_id>/pick', methods=['POST'])
@require_auth
@require_league_access('member')
@validate_json_request(required_fields=['player_id', 'team_id'])
def make_draft_pick(league_id):
    """Make a draft pick."""
    try:
        data = request.get_json()
        
        result = draft_service.make_draft_pick(
            league_id=league_id,
            team_id=data['team_id'],
            player_id=data['player_id'],
            user_id=g.user_id
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Failed to make draft pick: {e}")
        return jsonify({'error': 'Failed to make draft pick'}), 500

@drafts_bp.route('/<league_id>/auto-pick', methods=['POST'])
@require_auth
@require_league_access('member')
@validate_json_request(required_fields=['team_id'])
def make_auto_pick(league_id):
    """Make an automatic draft pick."""
    try:
        data = request.get_json()
        
        result = draft_service.auto_pick(
            league_id=league_id,
            team_id=data['team_id']
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Failed to make auto pick: {e}")
        return jsonify({'error': 'Failed to make auto pick'}), 500

@drafts_bp.route('/<league_id>/available-players', methods=['GET'])
@require_auth
@require_league_access('member')
def get_available_players(league_id):
    """Get players available for drafting."""
    try:
        # Get query parameters
        position = request.args.get('position', '')
        team = request.args.get('team', '')
        search = request.args.get('search', '')
        limit = int(request.args.get('limit', 100))
        
        filters = {
            'position': position,
            'team': team,
            'search': search
        }
        
        # Remove empty filters
        filters = {k: v for k, v in filters.items() if v}
        
        available_players = draft_service.get_available_players(league_id, filters)
        
        return jsonify({
            'available_players': available_players[:limit],
            'total': len(available_players)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get available players: {e}")
        return jsonify({'error': 'Failed to get available players'}), 500

@drafts_bp.route('/<league_id>/mock', methods=['POST'])
@require_auth
@require_league_access('member')
def create_mock_draft(league_id):
    """Create a mock draft simulation."""
    try:
        mock_draft = draft_service.create_mock_draft(league_id)
        
        if not mock_draft:
            return jsonify({'error': 'Failed to create mock draft'}), 500
        
        return jsonify({'mock_draft': mock_draft}), 200
        
    except Exception as e:
        logger.error(f"Failed to create mock draft: {e}")
        return jsonify({'error': 'Failed to create mock draft'}), 500

@drafts_bp.route('/<league_id>/timer', methods=['GET'])
@require_auth
@require_league_access('member')
def get_pick_timer_status(league_id):
    """Get the current pick timer status."""
    try:
        timer_status = draft_service.get_pick_timer_status(league_id)
        
        return jsonify({'timer': timer_status}), 200
        
    except Exception as e:
        logger.error(f"Failed to get timer status: {e}")
        return jsonify({'error': 'Failed to get timer status'}), 500

@drafts_bp.route('/<league_id>/start', methods=['POST'])
@require_auth
@require_league_access('commissioner')
def start_draft(league_id):
    """Start the draft for a league (commissioner only)."""
    try:
        result = draft_service.start_draft(league_id, g.user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Failed to start draft: {e}")
        return jsonify({'error': 'Failed to start draft'}), 500

@drafts_bp.route('/<league_id>/player-search', methods=['GET'])
@require_auth
@require_league_access('member')
def search_players_for_draft(league_id):
    """Search players available for drafting with filters."""
    try:
        # Get search parameters
        query = request.args.get('query', '')
        position = request.args.get('position', '')
        team = request.args.get('team', '')
        sort_by = request.args.get('sort_by', 'total_points')
        sort_order = request.args.get('sort_order', 'desc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Search players with availability filter
        result = player_service.search_players(
            query=query,
            position=position,
            team=team,
            available_only=True,
            league_id=league_id,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Failed to search players: {e}")
        return jsonify({'error': 'Failed to search players'}), 500

@drafts_bp.route('/<league_id>/player/<int:player_id>/details', methods=['GET'])
@require_auth
@require_league_access('member')
def get_player_details_for_draft(league_id, player_id):
    """Get detailed player information for draft decisions."""
    try:
        result = player_service.get_player_details(
            player_id=player_id,
            include_news=True,
            include_fixtures=True
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Failed to get player details: {e}")
        return jsonify({'error': 'Failed to get player details'}), 500

@drafts_bp.route('/<league_id>/recommendations', methods=['GET'])
@require_auth
@require_league_access('member')
def get_draft_recommendations(league_id):
    """Get draft recommendations for a team."""
    try:
        team_id = request.args.get('team_id')
        position = request.args.get('position', '')
        
        if not team_id:
            return jsonify({'error': 'team_id parameter required'}), 400
        
        # Get available players with recommendations
        filters = {'position': position} if position else {}
        available_players = draft_service.get_available_players(league_id, filters)
        
        # Get position analysis for recommendations
        if position:
            analysis_result = player_service.get_position_analysis(position, league_id)
            
            if analysis_result.get('success'):
                recommendations = {
                    'available_players': available_players[:20],
                    'position_analysis': analysis_result,
                    'top_recommendations': available_players[:5]
                }
            else:
                recommendations = {
                    'available_players': available_players[:20],
                    'top_recommendations': available_players[:5]
                }
        else:
            recommendations = {
                'available_players': available_players[:20],
                'top_recommendations': available_players[:5]
            }
        
        return jsonify({'recommendations': recommendations}), 200
        
    except Exception as e:
        logger.error(f"Failed to get draft recommendations: {e}")
        return jsonify({'error': 'Failed to get recommendations'}), 500

@drafts_bp.route('/<league_id>/history', methods=['GET'])
@require_auth
@require_league_access('member')
def get_draft_history(league_id):
    """Get draft pick history for the league."""
    try:
        from ..models.draft_model import DraftModel
        
        draft_model = DraftModel()
        picks = draft_model.get_draft_picks(league_id)
        
        # Enhance picks with player and team info
        from ..models.player_model import PlayerModel
        from ..models.team_model import TeamModel
        
        player_model = PlayerModel()
        team_model = TeamModel()
        
        enhanced_picks = []
        for pick in picks:
            player = player_model.get_player(pick['player_id'])
            team = team_model.get_team(league_id, pick['team_id'])
            
            enhanced_pick = {
                **pick,
                'player_info': player,
                'team_info': team
            }
            enhanced_picks.append(enhanced_pick)
        
        return jsonify({
            'draft_picks': enhanced_picks,
            'total_picks': len(enhanced_picks)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get draft history: {e}")
        return jsonify({'error': 'Failed to get draft history'}), 500

@drafts_bp.route('/<league_id>/status', methods=['GET'])
@require_auth
@require_league_access('member')
def get_draft_status(league_id):
    """Get current draft status and information."""
    try:
        from ..models.draft_model import DraftModel
        from ..models.league_model import LeagueModel
        
        draft_model = DraftModel()
        league_model = LeagueModel()
        
        # Get league info
        league = league_model.get_league(league_id)
        if not league:
            return jsonify({'error': 'League not found'}), 404
        
        # Get current pick info
        current_pick_info = draft_model.get_current_pick_info(league_id)
        
        # Get timer status
        timer_status = draft_service.get_pick_timer_status(league_id)
        
        # Get draft completion status
        is_complete = draft_model.is_draft_complete(league_id)
        
        draft_status = {
            'league_status': league.get('status'),
            'draft_started': league.get('status') in ['drafting', 'active', 'completed'],
            'draft_completed': is_complete,
            'current_pick_info': current_pick_info,
            'timer_status': timer_status,
            'draft_settings': league.get('draft_settings', {}),
            'total_picks_needed': len(league.get('teams', [])) * league.get('settings', {}).get('roster_size', 15)
        }
        
        return jsonify({'draft_status': draft_status}), 200
        
    except Exception as e:
        logger.error(f"Failed to get draft status: {e}")
        return jsonify({'error': 'Failed to get draft status'}), 500