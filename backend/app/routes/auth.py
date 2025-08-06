"""
Authentication routes for user management.
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from typing import Dict, Optional, Any, List
import firebase_admin
from firebase_admin import firestore

from ..services.auth_service import AuthService
from ..utils.validators import validate_json, validate_league_id
from ..utils.logger import get_logger
from .. import get_db, get_socketio

logger = get_logger('auth_routes')
auth_bp = Blueprint('auth', __name__)

# Initialize auth service
auth_service = None

def init_auth_routes(app):
    """Initialize auth routes with dependencies."""
    global auth_service
    
    try:
        auth_service = AuthService()
        
        # Register blueprint
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        logger.info("Auth routes initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize auth routes: {str(e)}")
        raise


# Custom exceptions
class ValidationError(Exception):
    """Validation error exception."""
    pass


class AuthenticationError(Exception):
    """Authentication error exception."""
    pass


def require_auth(f):
    """Decorator to require authentication."""
    from functools import wraps
    
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
                
            # Store user data in Flask's g object
            g.user_id = auth_result.get('user_id')
            g.user_data = auth_result.get('user_data', {})
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
            
    return decorated_function


@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token and return user info."""
    try:
        data = request.get_json()
        if not data or 'id_token' not in data:
            return jsonify({'error': 'id_token is required'}), 400
        
        id_token = data['id_token']
        if not isinstance(id_token, str) or not id_token.strip():
            return jsonify({'error': 'Invalid id_token format'}), 400
        
        # Verify token using auth service
        auth_result = auth_service.verify_token(id_token)
        if not auth_result.get('success'):
            return jsonify({'error': auth_result.get('error', 'Invalid token')}), 401
        
        user_claims = auth_result.get('user_data', {})
        user_id = auth_result.get('user_id')
        
        # Get or create user profile
        user_profile = get_or_create_user_profile(user_id, user_claims)
        if not user_profile:
            return jsonify({'error': 'Failed to create user profile'}), 500
        
        response_data = {
            'success': True,
            'user': user_profile,
            'token_valid': True,
            'user_id': user_id
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return jsonify({'error': 'Token verification failed'}), 500


@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get current user's profile."""
    try:
        user_profile = get_user_profile(g.user_id)
        if not user_profile:
            return jsonify({'error': 'User profile not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user_profile
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get profile for {g.user_id}: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500


@auth_bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update current user's profile."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate allowed fields
        allowed_fields = ['display_name', 'photo_url', 'preferences', 'timezone']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                value = data[field]
                
                # Validate display name
                if field == 'display_name':
                    if not isinstance(value, str):
                        return jsonify({'error': 'Display name must be a string'}), 400
                    value = value.strip()
                    if not value or len(value) > 50:
                        return jsonify({'error': 'Display name must be 1-50 characters'}), 400
                
                # Validate photo URL
                elif field == 'photo_url':
                    if value and not isinstance(value, str):
                        return jsonify({'error': 'Photo URL must be a string'}), 400
                
                # Validate preferences
                elif field == 'preferences':
                    if not isinstance(value, dict):
                        return jsonify({'error': 'Preferences must be an object'}), 400
                
                # Validate timezone
                elif field == 'timezone':
                    if not isinstance(value, str):
                        return jsonify({'error': 'Timezone must be a string'}), 400
                
                update_data[field] = value
        
        if not update_data:
            return jsonify({'error': 'No valid fields provided'}), 400
        
        # Update profile
        success = update_user_profile(g.user_id, update_data)
        if not success:
            return jsonify({'error': 'Failed to update profile'}), 500
        
        # Return updated profile
        updated_profile = get_user_profile(g.user_id)
        return jsonify({
            'success': True,
            'user': updated_profile,
            'message': 'Profile updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update profile for {g.user_id}: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """Revoke user's refresh tokens."""
    try:
        # Revoke refresh tokens using auth service
        success = auth_service.revoke_refresh_tokens(g.user_id)
        if not success:
            logger.warning(f"Failed to revoke tokens for {g.user_id}")
        
        # Update last logout timestamp
        try:
            update_user_profile(g.user_id, {
                'last_logout': datetime.utcnow()
            })
        except Exception as e:
            logger.warning(f"Failed to update logout timestamp: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Logout failed for {g.user_id}: {e}")
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/delete-account', methods=['DELETE'])
@require_auth
def delete_account():
    """Delete user account and all associated data."""
    try:
        # Check if user has active leagues as commissioner
        user_leagues = get_user_leagues(g.user_id)
        active_commissioner_leagues = [
            league for league in user_leagues 
            if league.get('commissioner_id') == g.user_id and league.get('status') in ['active', 'drafting']
        ]
        
        if active_commissioner_leagues:
            return jsonify({
                'error': 'Cannot delete account while being commissioner of active leagues',
                'active_leagues': len(active_commissioner_leagues)
            }), 400
        
        # TODO: Implement full account deletion
        # This should:
        # 1. Remove user from all leagues (if not commissioner)
        # 2. Transfer commissioner role if needed
        # 3. Delete user's teams
        # 4. Clean up user's transactions
        # 5. Delete user profile
        # 6. Optionally delete Firebase user account
        
        return jsonify({
            'message': 'Account deletion not yet implemented',
            'note': 'Please contact support for account deletion'
        }), 501
        
    except Exception as e:
        logger.error(f"Account deletion failed for {g.user_id}: {e}")
        return jsonify({'error': 'Account deletion failed'}), 500


@auth_bp.route('/user-leagues', methods=['GET'])
@require_auth
def get_user_leagues_route():
    """Get all leagues where user is a member or commissioner."""
    try:
        user_leagues = get_user_leagues(g.user_id)
        
        return jsonify({
            'success': True,
            'leagues': user_leagues,
            'count': len(user_leagues)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get user leagues for {g.user_id}: {e}")
        return jsonify({'error': 'Failed to get user leagues'}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh user's authentication token."""
    try:
        data = request.get_json()
        if not data or 'refresh_token' not in data:
            return jsonify({'error': 'refresh_token is required'}), 400
        
        refresh_token = data['refresh_token']
        
        # Refresh token using auth service
        refresh_result = auth_service.refresh_token(refresh_token)
        if not refresh_result.get('success'):
            return jsonify({'error': refresh_result.get('error', 'Token refresh failed')}), 401
        
        return jsonify({
            'success': True,
            'access_token': refresh_result.get('access_token'),
            'expires_in': refresh_result.get('expires_in', 3600)
        }), 200
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500


# Helper functions

def get_or_create_user_profile(user_id: str, user_claims: dict) -> Optional[Dict[str, Any]]:
    """Get existing user profile or create new one."""
    try:
        db = get_db()
        
        # Check if profile exists
        profile_ref = db.collection('users').document(user_id)
        profile_doc = profile_ref.get()
        
        if profile_doc.exists:
            # Update last login
            profile_ref.update({
                'last_login': firestore.SERVER_TIMESTAMP
            })
            profile_data = profile_doc.to_dict()
            profile_data['id'] = user_id  # Ensure ID is included
        else:
            # Create new profile
            profile_data = {
                'id': user_id,
                'uid': user_id,  # Firebase UID
                'email': user_claims.get('email', ''),
                'display_name': (
                    user_claims.get('name') or 
                    user_claims.get('display_name') or 
                    user_claims.get('email', '').split('@')[0]
                ),
                'photo_url': user_claims.get('picture') or user_claims.get('photo_url'),
                'email_verified': user_claims.get('email_verified', False),
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_login': firestore.SERVER_TIMESTAMP,
                'last_logout': None,
                'preferences': {
                    'notifications': {
                        'email': True,
                        'push': True,
                        'trades': True,
                        'waivers': True,
                        'draft': True,
                        'scoring': True,
                        'league_updates': True
                    },
                    'theme': 'light',
                    'timezone': 'UTC',
                    'language': 'en',
                    'auto_join_public_leagues': False,
                    'show_player_news': True
                },
                'stats': {
                    'leagues_joined': 0,
                    'leagues_created': 0,
                    'championships': 0,
                    'total_trades': 0,
                    'total_waiver_claims': 0,
                    'total_draft_picks': 0,
                    'favorite_position': None,
                    'average_finish': None
                },
                'subscription': {
                    'tier': 'free',
                    'expires_at': None,
                    'features': ['basic_leagues', 'standard_draft']
                }
            }
            
            profile_ref.set(profile_data)
            logger.info(f"Created new user profile for {user_id}")
        
        return profile_data
        
    except Exception as e:
        logger.error(f"Failed to get/create user profile: {e}")
        return None


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile by ID."""
    try:
        db = get_db()
        profile_doc = db.collection('users').document(user_id).get()
        
        if profile_doc.exists:
            profile_data = profile_doc.to_dict()
            profile_data['id'] = user_id  # Ensure ID is included
            return profile_data
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user profile {user_id}: {e}")
        return None


def update_user_profile(user_id: str, update_data: Dict[str, Any]) -> bool:
    """Update user profile."""
    try:
        db = get_db()
        
        # Add timestamp
        update_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        # Update profile
        profile_ref = db.collection('users').document(user_id)
        profile_ref.update(update_data)
        
        logger.info(f"Updated profile for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update user profile {user_id}: {e}")
        return False


def get_user_leagues(user_id: str) -> List[Dict[str, Any]]:
    """Get all leagues where user is a member or commissioner."""
    try:
        from ..models.league_model import LeagueModel
        league_model = LeagueModel()
        
        return league_model.get_user_leagues(user_id)
        
    except Exception as e:
        logger.error(f"Failed to get user leagues for {user_id}: {e}")
        return []


def validate_json_request(required_fields=None, optional_fields=None):
    """Decorator to validate JSON request body."""
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Request body is required'}), 400
                
                # Check required fields
                if required_fields:
                    for field in required_fields:
                        if field not in data:
                            return jsonify({'error': f'{field} is required'}), 400
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"JSON validation error: {e}")
                return jsonify({'error': 'Invalid JSON request'}), 400
                
        return decorated_function
    return decorator


# Error handlers
@auth_bp.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({'error': str(e)}), 400


@auth_bp.errorhandler(AuthenticationError)
def handle_authentication_error(e):
    return jsonify({'error': str(e)}), 401


@auth_bp.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal server error in auth routes: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500