"""
Admin routes for commissioner tools and league management.
Handles all administrative functions for league commissioners.
"""

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timedelta
from functools import wraps
import logging
from typing import Dict, List, Optional, Tuple, Any
import json

from .. import get_db, get_socketio
from ..services.auth_service import AuthService
from ..services.scoring_service import ScoringService
from ..services.trade_service import TradeService
from ..services.waiver_service import WaiverService
from ..services.player_service import PlayerService
from ..services.notification_service import NotificationService
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..utils.validators import validate_json, validate_league_id, validate_team_id
from ..utils.logger import get_logger

logger = get_logger(__name__)

admin_bp = Blueprint('admin', __name__)

# Service instances
auth_service = None
scoring_service = None
trade_service = None
waiver_service = None
player_service = None
notification_service = None
team_model = None
league_model = None


def init_admin_routes(app):
    """Initialize admin routes with dependencies."""
    global auth_service, scoring_service, trade_service, waiver_service
    global player_service, notification_service, team_model, league_model
    
    try:
        # Initialize services
        auth_service = AuthService()
        scoring_service = ScoringService()
        trade_service = TradeService()
        waiver_service = WaiverService()
        player_service = PlayerService()
        notification_service = NotificationService()
        team_model = TeamModel()
        league_model = LeagueModel()
        
        # Register blueprint
        app.register_blueprint(admin_bp, url_prefix='/api')
        logger.info("Admin routes initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize admin routes: {str(e)}")
        raise


# Custom exceptions
class ValidationError(Exception):
    """Validation error exception."""
    pass


class AuthorizationError(Exception):
    """Authorization error exception."""
    pass


class NotFoundError(Exception):
    """Resource not found exception."""
    pass


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authorization header required'}), 401
                
            # Extract token from Bearer format
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
                
            auth_result = auth_service.verify_token(token)
            if not auth_result.get('success'):
                return jsonify({'error': 'Invalid or expired token'}), 401
                
            # Use Flask 3.x compatible way to store user data
            g.user_id = auth_result.get('user_id')
            g.user_data = auth_result.get('user_data', {})
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
            
    return decorated_function


def require_commissioner(f):
    """Decorator to require commissioner privileges."""
    @wraps(f)
    def decorated_function(league_id, *args, **kwargs):
        try:
            if not hasattr(g, 'user_id'):
                return jsonify({'error': 'Authentication required'}), 401
                
            is_commissioner, league_or_error = verify_commissioner(g.user_id, league_id)
            if not is_commissioner:
                return jsonify({'error': league_or_error}), 403
                
            g.league = league_or_error
            return f(league_id, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Commissioner verification error: {str(e)}")
            return jsonify({'error': 'Authorization failed'}), 403
            
    return decorated_function


def verify_commissioner(user_id: str, league_id: str) -> Tuple[bool, Any]:
    """Verify user is commissioner of the league."""
    try:
        if not user_id or not league_id:
            return False, "Invalid user or league ID"
            
        league = league_model.get_league(league_id)
        if not league:
            return False, "League not found"
        
        if league.get('commissioner_id') != user_id:
            return False, "Only the commissioner can perform this action"
        
        return True, league
        
    except Exception as e:
        logger.error(f"Error verifying commissioner: {str(e)}")
        return False, "Error verifying commissioner privileges"


@admin_bp.route('/admin/leagues/<league_id>/settings', methods=['GET'])
@require_auth
@require_commissioner
def get_league_settings(league_id: str):
    """Get league settings (commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")
            
        league = g.league
        
        # Get teams count
        teams = team_model.get_league_teams(league_id) or []
        
        # Build settings response with safe defaults
        settings = {
            'basic_settings': {
                'name': league.get('name', 'Unnamed League'),
                'description': league.get('description', ''),
                'max_teams': league.get('max_teams', 12),
                'current_teams': len(teams),
                'draft_date': league.get('draft_settings', {}).get('scheduled_time'),
                'season_start': league.get('season_info', {}).get('season_start'),
                'season_end': league.get('season_info', {}).get('season_end'),
                'status': league.get('status', 'created')
            },
            'scoring_settings': league.get('settings', {}).get('scoring_settings', {}),
            'roster_settings': {
                'roster_size': league.get('settings', {}).get('roster_size', 15),
                'starting_lineup_size': league.get('settings', {}).get('starting_lineup_size', 11),
            },
            'waiver_settings': league.get('waiver_settings', {}),
            'trade_settings': {
                'trade_deadline': league.get('settings', {}).get('trade_deadline'),
                'trade_review_period': league.get('settings', {}).get('trade_review_period', 24),
                'commissioner_approval_required': league.get('settings', {}).get('commissioner_approval_required', False)
            },
            'playoff_settings': {
                'playoff_teams': league.get('settings', {}).get('playoff_teams', 4),
                'playoff_weeks': league.get('settings', {}).get('playoff_weeks', [37, 38])
            },
            'draft_settings': league.get('draft_settings', {}),
            'transactions_locked': league.get('transactions_locked', False),
            'transaction_lock_reason': league.get('transaction_lock_reason', '')
        }

        return jsonify({
            'success': True,
            'settings': settings,
            'league_id': league_id
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting league settings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/leagues/<league_id>/settings', methods=['PUT'])
@require_auth
@require_commissioner
def update_league_settings(league_id: str):
    """Update league settings (commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Define allowed settings with validation
        allowed_settings = {
            'name': str,
            'description': str,
            'trade_deadline': str,
            'commissioner_approval_required': bool,
            'trade_review_period': int,
            'playoff_teams': int,
            'playoff_weeks': list,
            'waiver_budget': int,
            'auto_pick_enabled': bool,
            'pick_time_seconds': int
        }

        updates = {}
        nested_updates = {}
        
        for setting, expected_type in allowed_settings.items():
            if setting in data:
                value = data[setting]
                if not isinstance(value, expected_type):
                    return jsonify({'error': f'{setting} must be of type {expected_type.__name__}'}), 400
                
                # Handle nested settings
                if setting in ['trade_deadline', 'commissioner_approval_required', 'trade_review_period']:
                    if 'settings' not in nested_updates:
                        nested_updates['settings'] = {}
                    nested_updates['settings'][setting] = value
                elif setting in ['playoff_teams', 'playoff_weeks']:
                    if 'settings' not in nested_updates:
                        nested_updates['settings'] = {}
                    nested_updates['settings'][setting] = value
                elif setting == 'waiver_budget':
                    if 'waiver_settings' not in nested_updates:
                        nested_updates['waiver_settings'] = {}
                    nested_updates['waiver_settings']['budget_per_team'] = value
                elif setting in ['auto_pick_enabled', 'pick_time_seconds']:
                    if 'draft_settings' not in nested_updates:
                        nested_updates['draft_settings'] = {}
                    nested_updates['draft_settings'][setting] = value
                else:
                    updates[setting] = value

        # Merge nested updates
        for key, value in nested_updates.items():
            # Get current nested data
            current_league = g.league
            current_nested = current_league.get(key, {})
            
            # Merge updates
            updated_nested = {**current_nested, **value}
            updates[key] = updated_nested

        if not updates:
            return jsonify({'error': 'No valid settings provided'}), 400

        # Add metadata
        updates['updated_at'] = datetime.utcnow()

        # Update league using the result pattern
        result = league_model.update_league_settings(league_id, g.user_id, updates)
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to update league settings')}), 500

        # Log the action
        log_admin_action(g.user_id, league_id, 'settings_updated', {
            'updated_fields': list(updates.keys())
        })

        # Emit real-time update
        socketio = get_socketio()
        if socketio:
            socketio.emit('league_settings_updated', {
                'league_id': league_id,
                'updates': {k: v for k, v in updates.items() if k not in ['updated_at']}
            }, room=f"league_{league_id}")

        return jsonify({
            'success': True,
            'message': 'League settings updated successfully'
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating league settings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/leagues/<league_id>/teams', methods=['GET'])
@require_auth
@require_commissioner
def get_league_teams_admin(league_id: str):
    """Get all teams with admin details (commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")
        
        # Get teams with error handling
        teams = team_model.get_league_teams(league_id) or []
        
        admin_teams = []
        for team in teams:
            try:
                # Get additional team data
                team_waiver_info = waiver_service.get_team_waiver_info(league_id, team.get('id', ''))
                active_trades = trade_service.get_active_trades(league_id, team.get('id', ''))
                
                # Build admin team data with safe defaults
                admin_team = {
                    **team,
                    'roster_count': len(team.get('roster', {}).get('starters', [])) + len(team.get('roster', {}).get('bench', [])),
                    'waiver_budget': team_waiver_info.get('waiver_budget', 0),
                    'waiver_position': team_waiver_info.get('waiver_position', 1),
                    'pending_trades': len(active_trades),
                    'pending_waivers': team_waiver_info.get('pending_claims', 0),
                    'total_points': team.get('stats', {}).get('total_points', 0),
                    'wins': team.get('stats', {}).get('wins', 0),
                    'losses': team.get('stats', {}).get('losses', 0),
                    'ties': team.get('stats', {}).get('ties', 0)
                }
                admin_teams.append(admin_team)
                
            except Exception as e:
                logger.error(f"Error processing team {team.get('id', 'unknown')}: {str(e)}")
                # Include team with basic info even if extended data fails
                admin_teams.append({
                    **team,
                    'roster_count': len(team.get('roster', {}).get('starters', [])) + len(team.get('roster', {}).get('bench', [])),
                    'waiver_budget': 0,
                    'waiver_position': 1,
                    'pending_trades': 0,
                    'pending_waivers': 0,
                    'data_error': True
                })

        return jsonify({
            'success': True,
            'teams': admin_teams,
            'count': len(admin_teams),
            'league_id': league_id
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting league teams: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/teams/<team_id>/roster', methods=['PUT'])
@require_auth
def edit_team_roster(team_id: str):
    """Edit a team's roster (commissioner only)."""
    try:
        if not validate_team_id(team_id):
            raise ValidationError("Invalid team ID")
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Get team to find league
        team = team_model.get_team('', team_id)  # Get team by ID
        if not team:
            raise NotFoundError("Team not found")

        league_id = team.get('league_id')
        if not league_id:
            return jsonify({'error': 'Team has no associated league'}), 400

        # Verify commissioner privileges
        is_commissioner, league_or_error = verify_commissioner(g.user_id, league_id)
        if not is_commissioner:
            return jsonify({'error': league_or_error}), 403

        # Validate roster data
        if 'roster' not in data:
            return jsonify({'error': 'roster field is required'}), 400

        new_roster = data['roster']
        if not isinstance(new_roster, dict):
            return jsonify({'error': 'roster must be an object with starters and bench'}), 400

        # Validate roster structure
        required_keys = ['starters', 'bench']
        for key in required_keys:
            if key not in new_roster:
                return jsonify({'error': f'roster.{key} field is required'}), 400
            if not isinstance(new_roster[key], list):
                return jsonify({'error': f'roster.{key} must be a list'}), 400

        # Update team roster
        result = team_model.update_roster(league_id, team_id, new_roster)
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to update team roster')}), 500

        # Log the change
        log_admin_action(g.user_id, league_id, 'roster_edit', {
            'team_id': team_id,
            'team_name': team.get('name', 'Unknown Team'),
            'roster_count': len(new_roster['starters']) + len(new_roster['bench'])
        })

        return jsonify({
            'success': True,
            'message': 'Team roster updated successfully'
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error editing team roster: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/leagues/<league_id>/scores/<int:gameweek>', methods=['PUT'])
@require_auth
@require_commissioner
def edit_gameweek_scores(league_id: str, gameweek: int):
    """Edit gameweek scores (commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate gameweek
        if gameweek < 1 or gameweek > 38:  # Premier League has 38 gameweeks
            return jsonify({'error': 'Invalid gameweek number'}), 400

        # Validate score data
        if 'team_scores' not in data:
            return jsonify({'error': 'team_scores field is required'}), 400

        team_scores = data['team_scores']
        if not isinstance(team_scores, dict):
            return jsonify({'error': 'team_scores must be an object'}), 400

        # Update scores using scoring service
        result = scoring_service.update_gameweek_scores(league_id, gameweek, team_scores, g.user_id)
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to update scores')}), 500

        updated_teams = result.get('updated_teams', [])

        # Log the change
        log_admin_action(g.user_id, league_id, 'scores_edit', {
            'gameweek': gameweek,
            'teams_updated': len(updated_teams)
        })

        # Emit real-time update
        socketio = get_socketio()
        if socketio:
            socketio.emit('scores_updated', {
                'league_id': league_id,
                'gameweek': gameweek,
                'updated_by_commissioner': True
            }, room=f"league_{league_id}")

        return jsonify({
            'success': True,
            'message': f'Scores updated for {len(updated_teams)} teams',
            'updated_teams': updated_teams
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error editing gameweek scores: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/leagues/<league_id>/commissioner', methods=['PUT'])
@require_auth
@require_commissioner
def change_commissioner(league_id: str):
    """Change league commissioner (current commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate new commissioner
        if 'new_commissioner_id' not in data:
            return jsonify({'error': 'new_commissioner_id field is required'}), 400

        new_commissioner_id = data['new_commissioner_id']
        if not isinstance(new_commissioner_id, str) or not new_commissioner_id.strip():
            return jsonify({'error': 'new_commissioner_id must be a valid string'}), 400

        # Verify new commissioner is in the league
        teams = team_model.get_league_teams(league_id) or []
        team_owners = [team.get('owner_id') for team in teams if team.get('owner_id')]
        
        if new_commissioner_id not in team_owners:
            return jsonify({'error': 'New commissioner must be a team owner in the league'}), 400

        # Update league commissioner using league model
        result = league_model.update_league(league_id, {
            'commissioner_id': new_commissioner_id,
            'previous_commissioner_id': g.user_id,
            'commissioner_changed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })

        if not result:
            return jsonify({'error': 'Failed to change commissioner'}), 500

        # Log the change
        log_admin_action(g.user_id, league_id, 'commissioner_change', {
            'previous_commissioner': g.user_id,
            'new_commissioner': new_commissioner_id
        })

        # Send notifications
        try:
            notification_service.send_commissioner_notification(
                new_commissioner_id,
                league_id,
                'You are now the League Commissioner'
            )
        except Exception as e:
            logger.error(f"Error sending commissioner notification: {str(e)}")

        return jsonify({
            'success': True,
            'message': 'Commissioner changed successfully'
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error changing commissioner: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/leagues/<league_id>/transactions/lock', methods=['POST'])
@require_auth
@require_commissioner
def lock_transactions(league_id: str):
    """Lock all roster transactions (commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")
            
        data = request.get_json() or {}

        locked = data.get('locked', True)
        if not isinstance(locked, bool):
            return jsonify({'error': 'locked must be a boolean'}), 400

        reason = data.get('reason', 'Commissioner action')
        if not isinstance(reason, str):
            return jsonify({'error': 'reason must be a string'}), 400

        # Update league transaction lock
        updates = {
            'transactions_locked': locked,
            'transaction_lock_reason': reason,
            'transaction_lock_timestamp': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        success = league_model.update_league(league_id, updates)
        if not success:
            return jsonify({'error': 'Failed to update transaction lock'}), 500

        # Log the change
        action = 'transactions_locked' if locked else 'transactions_unlocked'
        log_admin_action(g.user_id, league_id, action, {'reason': reason})

        # Emit real-time update
        socketio = get_socketio()
        if socketio:
            socketio.emit('transactions_lock_updated', {
                'league_id': league_id,
                'locked': locked,
                'reason': reason
            }, room=f"league_{league_id}")

        action_text = 'locked' if locked else 'unlocked'
        return jsonify({
            'success': True,
            'message': f'Transactions {action_text} successfully'
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error locking transactions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/leagues/<league_id>/audit-log', methods=['GET'])
@require_auth
@require_commissioner
def get_audit_log(league_id: str):
    """Get audit log of admin actions (commissioner only)."""
    try:
        if not validate_league_id(league_id):
            raise ValidationError("Invalid league ID")

        # Get query parameters with validation
        try:
            limit = min(int(request.args.get('limit', 50)), 100)
        except ValueError:
            limit = 50

        action_type = request.args.get('action_type')
        
        # Validate action_type if provided
        if action_type and not isinstance(action_type, str):
            return jsonify({'error': 'action_type must be a string'}), 400

        # Get audit log
        audit_log = get_audit_log_entries(league_id, action_type, limit)

        return jsonify({
            'success': True,
            'audit_log': audit_log,
            'count': len(audit_log),
            'league_id': league_id
        }), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Helper functions

def log_admin_action(user_id: str, league_id: str, action: str, details: Dict[str, Any]) -> bool:
    """Log an admin action to the audit trail."""
    try:
        if not all([user_id, league_id, action]):
            logger.error("Missing required parameters for logging admin action")
            return False
            
        log_entry = {
            'user_id': user_id,
            'league_id': league_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.utcnow()
        }

        # Use get_db() for database access
        db = get_db()
        if db:
            db.collection('leagues').document(league_id)\
              .collection('audit_log').add(log_entry)
            return True
        else:
            logger.error("Database not initialized")
            return False

    except Exception as e:
        logger.error(f"Error logging admin action: {str(e)}")
        return False


def get_audit_log_entries(league_id: str, action_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get audit log entries for a league."""
    try:
        db = get_db()
        if not db:
            logger.error("Database not initialized")
            return []
            
        # Build query
        query = (db.collection('leagues').document(league_id)
                .collection('audit_log')
                .order_by('timestamp', direction='DESCENDING')
                .limit(limit))

        if action_type:
            query = query.where('action', '==', action_type)

        docs = query.stream()
        audit_entries = []

        for doc in docs:
            try:
                entry = doc.to_dict()
                entry['id'] = doc.id
                # Convert timestamp to ISO string for JSON serialization
                if 'timestamp' in entry and entry['timestamp']:
                    entry['timestamp'] = entry['timestamp'].isoformat()
                audit_entries.append(entry)
            except Exception as e:
                logger.error(f"Error processing audit log entry {doc.id}: {str(e)}")
                continue

        return audit_entries

    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        return []


# Error handlers
@admin_bp.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({'error': str(e)}), 400


@admin_bp.errorhandler(AuthorizationError)
def handle_authorization_error(e):
    return jsonify({'error': str(e)}), 403


@admin_bp.errorhandler(NotFoundError)
def handle_not_found_error(e):
    return jsonify({'error': str(e)}), 404


@admin_bp.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500