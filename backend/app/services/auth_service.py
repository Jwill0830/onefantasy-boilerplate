"""
Authentication service for Firebase Auth integration.
"""
from typing import Dict, Optional, Any
from functools import wraps
from flask import request, jsonify, g
import firebase_admin
from firebase_admin import auth
from ..utils.logger import get_logger

logger = get_logger('auth_service')

class AuthService:
    """Service for handling Firebase Authentication."""
    
    def __init__(self):
        self.auth = auth
    
    def verify_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Firebase ID token and return user claims.
        
        Args:
            id_token: Firebase ID token
            
        Returns:
            User claims dict or None if invalid
        """
        try:
            # Verify the token
            decoded_token = self.auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get user data by UID."""
        try:
            user_record = self.auth.get_user(uid)
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'display_name': user_record.display_name,
                'photo_url': user_record.photo_url,
                'email_verified': user_record.email_verified,
                'disabled': user_record.disabled,
                'created_at': user_record.user_metadata.creation_timestamp,
                'last_sign_in': user_record.user_metadata.last_sign_in_timestamp
            }
        except Exception as e:
            logger.error(f"Failed to get user {uid}: {e}")
            return None
    
    def create_custom_token(self, uid: str, additional_claims: Dict[str, Any] = None) -> Optional[str]:
        """Create custom token for user."""
        try:
            custom_token = self.auth.create_custom_token(uid, additional_claims)
            return custom_token.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to create custom token for {uid}: {e}")
            return None
    
    def set_custom_user_claims(self, uid: str, custom_claims: Dict[str, Any]) -> bool:
        """Set custom claims for user."""
        try:
            self.auth.set_custom_user_claims(uid, custom_claims)
            logger.info(f"Set custom claims for user {uid}")
            return True
        except Exception as e:
            logger.error(f"Failed to set custom claims for {uid}: {e}")
            return False
    
    def revoke_refresh_tokens(self, uid: str) -> bool:
        """Revoke all refresh tokens for user."""
        try:
            self.auth.revoke_refresh_tokens(uid)
            logger.info(f"Revoked refresh tokens for user {uid}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke tokens for {uid}: {e}")
            return False

# Global instance
auth_service = AuthService()

def require_auth(f):
    """
    Decorator to require authentication for route.
    Extracts user info from Authorization header and adds to Flask g object.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.split('Bearer ')[1]
        
        # Verify token
        user_claims = auth_service.verify_token(token)
        if not user_claims:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Add user info to Flask g object
        g.user = user_claims
        g.user_id = user_claims.get('uid')
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_league_access(league_role: str = 'member'):
    """
    Decorator to require specific league access level.
    
    Args:
        league_role: 'member', 'commissioner', or 'any'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Must be authenticated first
            if not hasattr(g, 'user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            # Get league_id from request (path or body)
            league_id = kwargs.get('league_id') or request.json.get('league_id') if request.is_json else None
            
            if not league_id:
                return jsonify({'error': 'league_id required'}), 400
            
            # Check user's role in league
            if not check_league_access(g.user_id, league_id, league_role):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def check_league_access(user_id: str, league_id: str, required_role: str = 'member') -> bool:
    """
    Check if user has required access level to league.
    
    Args:
        user_id: User ID
        league_id: League ID  
        required_role: 'member', 'commissioner', or 'any'
        
    Returns:
        True if user has access
    """
    try:
        from ..models.league_model import LeagueModel
        from ..models.team_model import TeamModel
        
        league_model = LeagueModel()
        team_model = TeamModel()
        
        # Get league data
        league = league_model.get_league(league_id)
        if not league:
            return False
        
        # Check if user is commissioner
        is_commissioner = league.get('commissioner_id') == user_id
        
        if required_role == 'commissioner':
            return is_commissioner
        
        # Check if user has a team in league
        user_team = team_model.get_team_by_owner(league_id, user_id)
        has_team = user_team is not None
        
        if required_role == 'member':
            return is_commissioner or has_team
        
        # required_role == 'any'
        return True
        
    except Exception as e:
        logger.error(f"Failed to check league access for user {user_id}: {e}")
        return False

def get_auth_service() -> AuthService:
    """Get the auth service instance."""
    return auth_service