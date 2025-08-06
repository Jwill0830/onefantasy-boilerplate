"""
League management routes.
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from ..services.auth_service import require_auth, require_league_access
from ..models.league_model import LeagueModel
from ..models.team_model import TeamModel
from ..utils.validators import (
    validate_json_request, validate_league_name, validate_team_name,
    validate_league_size, sanitize_string
)
from ..utils.logger import get_logger

logger = get_logger('leagues_routes')
leagues_bp = Blueprint('leagues', __name__)

league_model = LeagueModel()
team_model = TeamModel()

@leagues_bp.route('/', methods=['POST'])
@require_auth
@validate_json_request(
    required_fields=['name'],
    optional_fields=['settings', 'draft_time']
)
def create_league():
    """Create a new league."""
    try:
        data = request.get_json()
        
        # Validate league name
        league_name = sanitize_string(data['name'], 50)
        if not validate_league_name(league_name):
            return jsonify({'error': 'Invalid league name'}), 400
        
        # Validate settings if provided
        settings = data.get('settings', {})
        if 'league_size' in settings:
            if not validate_league_size(settings['league_size']):
                return jsonify({'error': 'League size must be between 6 and 18'}), 400
        
        # Validate draft time if provided
        draft_time = data.get('draft_time')
        if draft_time:
            try:
                draft_datetime = datetime.fromisoformat(draft_time.replace('Z', '+00:00'))
                if draft_datetime <= datetime.utcnow():
                    return jsonify({'error': 'Draft time must be in the future'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid draft time format'}), 400
        
        # Create league
        league_data = {
            'name': league_name,
            'settings': settings,
            'draft_time': draft_time
        }
        
        league_id = league_model.create_league(g.user_id, league_data)
        
        # Get created league
        league = league_model.get_league(league_id)
        
        logger.info(f"User {g.user_id} created league {league_id}")
        return jsonify({'league': league}), 201
        
    except Exception as e:
        logger.error(f"Failed to create league: {e}")
        return jsonify({'error': 'Failed to create league'}), 500

@leagues_bp.route('/<league_id>', methods=['GET'])
@require_auth
@require_league_access('member')
def get_league(league_id):
    """Get league details."""
    try:
        league = league_model.get_league(league_id)
        if not league:
            return jsonify({'error': 'League not found'}), 404
        
        # Get teams in league
        teams = team_model.get_league_teams(league_id)
        league['teams'] = teams
        
        return jsonify({'league': league}), 200
        
    except Exception as e:
        logger.error(f"Failed to get league {league_id}: {e}")
        return jsonify({'error': 'Failed to get league'}), 500

@leagues_bp.route('/', methods=['GET'])
@require_auth
def get_user_leagues():
    """Get all leagues for the current user."""
    try:
        leagues = league_model.get_user_leagues(g.user_id)
        
        # Add team info for each league
        for league in leagues:
            league_id = league['id']
            user_team = team_model.get_team_by_owner(league_id, g.user_id)
            league['user_team'] = user_team
        
        return jsonify({'leagues': leagues}), 200
        
    except Exception as e:
        logger.error(f"Failed to get user leagues for {g.user_id}: {e}")
        return jsonify({'error': 'Failed to get leagues'}), 500

@leagues_bp.route('/<league_id>', methods=['PUT'])
@require_auth
@require_league_access('commissioner')
@validate_json_request(
    optional_fields=['name', 'settings', 'draft_time']
)
def update_league(league_id):
    """Update league settings (commissioner only)."""
    try:
        data = request.get_json()
        update_data = {}
        
        # Validate and update name
        if 'name' in data:
            league_name = sanitize_string(data['name'], 50)
            if not validate_league_name(league_name):
                return jsonify({'error': 'Invalid league name'}), 400
            update_data['name'] = league_name
        
        # Validate and update settings
        if 'settings' in data:
            settings = data['settings']
            if 'league_size' in settings:
                if not validate_league_size(settings['league_size']):
                    return jsonify({'error': 'League size must be between 6 and 18'}), 400
            update_data['settings'] = settings
        
        # Validate and update draft time
        if 'draft_time' in data:
            draft_time = data['draft_time']
            if draft_time:
                try:
                    draft_datetime = datetime.fromisoformat(draft_time.replace('Z', '+00:00'))
                    if draft_datetime <= datetime.utcnow():
                        return jsonify({'error': 'Draft time must be in the future'}), 400
                except ValueError:
                    return jsonify({'error': 'Invalid draft time format'}), 400
            update_data['draft_settings.scheduled_time'] = draft_time
        
        # Update league
        success = league_model.update_league(league_id, update_data)
        if not success:
            return jsonify({'error': 'Failed to update league'}), 500
        
        # Return updated league
        updated_league = league_model.get_league(league_id)
        return jsonify({'league': updated_league}), 200
        
    except Exception as e:
        logger.error(f"Failed to update league {league_id}: {e}")
        return jsonify({'error': 'Failed to update league'}), 500

@leagues_bp.route('/join', methods=['POST'])
@require_auth
@validate_json_request(
    required_fields=['invite_code', 'team_name'],
    optional_fields=['team_logo_url']
)
def join_league():
    """Join a league using invite code."""
    try:
        data = request.get_json()
        invite_code = data['invite_code'].upper().strip()
        team_name = sanitize_string(data['team_name'], 30)
        
        # Validate team name
        if not validate_team_name(team_name):
            return jsonify({'error': 'Invalid team name'}), 400
        
        # Find league by invite code
        league = league_model.get_league_by_invite_code(invite_code)
        if not league:
            return jsonify({'error': 'Invalid invite code'}), 404
        
        league_id = league['id']
        
        # Check if league is full
        current_teams = len(league.get('teams', []))
        max_teams = league.get('settings', {}).get('league_size', 10)
        
        if current_teams >= max_teams:
            return jsonify({'error': 'League is full'}), 400
        
        # Check if user already has a team in this league
        existing_team = team_model.get_team_by_owner(league_id, g.user_id)
        if existing_team:
            return jsonify({'error': 'You already have a team in this league'}), 400
        
        # Create team
        team_data = {
            'name': team_name,
            'owner_id': g.user_id,
            'logo_url': data.get('team_logo_url'),
            'draft_position': current_teams + 1,
            'waiver_position': current_teams + 1,
            'waiver_budget': league.get('settings', {}).get('waiver_budget', 100)
        }
        
        team_id = team_model.create_team(league_id, g.user_id, team_data)
        
        # Add team to league
        league_team_data = {
            'id': team_id,
            'name': team_name,
            'owner_id': g.user_id,
            'draft_position': current_teams + 1
        }
        
        success = league_model.add_team_to_league(league_id, league_team_data)
        if not success:
            return jsonify({'error': 'Failed to join league'}), 500
        
        # Get updated league and team
        updated_league = league_model.get_league(league_id)
        created_team = team_model.get_team(league_id, team_id)
        
        logger.info(f"User {g.user_id} joined league {league_id} with team {team_id}")
        
        return jsonify({
            'league': updated_league,
            'team': created_team
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to join league: {e}")
        return jsonify({'error': 'Failed to join league'}), 500

@leagues_bp.route('/<league_id>/teams', methods=['GET'])
@require_auth
@require_league_access('member')
def get_league_teams(league_id):
    """Get all teams in a league."""
    try:
        teams = team_model.get_league_teams(league_id)
        return jsonify({'teams': teams}), 200
        
    except Exception as e:
        logger.error(f"Failed to get teams for league {league_id}: {e}")
        return jsonify({'error': 'Failed to get teams'}), 500

@leagues_bp.route('/<league_id>/standings', methods=['GET'])
@require_auth
@require_league_access('member')
def get_league_standings(league_id):
    """Get league standings."""
    try:
        standings = team_model.get_team_standings(league_id)
        return jsonify({'standings': standings}), 200
        
    except Exception as e:
        logger.error(f"Failed to get standings for league {league_id}: {e}")
        return jsonify({'error': 'Failed to get standings'}), 500

@leagues_bp.route('/<league_id>/start-draft', methods=['POST'])
@require_auth
@require_league_access('commissioner')
def start_draft(league_id):
    """Start the draft for a league."""
    try:
        league = league_model.get_league(league_id)
        if not league:
            return jsonify({'error': 'League not found'}), 404
        
        # Check if draft can be started
        if league.get('status') != 'created':
            return jsonify({'error': 'Draft already started or completed'}), 400
        
        # Check if league has enough teams
        teams = team_model.get_league_teams(league_id)
        min_teams = 2  # Minimum teams to start draft
        
        if len(teams) < min_teams:
            return jsonify({'error': f'Need at least {min_teams} teams to start draft'}), 400
        
        # Start draft
        success = league_model.start_draft(league_id)
        if not success:
            return jsonify({'error': 'Failed to start draft'}), 500
        
        # Get updated league
        updated_league = league_model.get_league(league_id)
        
        logger.info(f"Draft started for league {league_id} by {g.user_id}")
        return jsonify({'league': updated_league}), 200
        
    except Exception as e:
        logger.error(f"Failed to start draft for league {league_id}: {e}")
        return jsonify({'error': 'Failed to start draft'}), 500

@leagues_bp.route('/<league_id>', methods=['DELETE'])
@require_auth
@require_league_access('commissioner')
def delete_league(league_id):
    """Delete a league (commissioner only)."""
    try:
        # Check if league can be deleted
        league = league_model.get_league(league_id)
        if not league:
            return jsonify({'error': 'League not found'}), 404
        
        # Only allow deletion if draft hasn't started or league is empty
        if league.get('status') not in ['created'] and len(league.get('teams', [])) > 1:
            return jsonify({'error': 'Cannot delete active league with multiple teams'}), 400
        
        # Delete league
        success = league_model.delete_league(league_id)
        if not success:
            return jsonify({'error': 'Failed to delete league'}), 500
        
        logger.info(f"League {league_id} deleted by {g.user_id}")
        return jsonify({'message': 'League deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Failed to delete league {league_id}: {e}")
        return jsonify({'error': 'Failed to delete league'}), 500