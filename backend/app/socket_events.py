"""
SocketIO event handlers for real-time functionality.
"""
from flask_socketio import emit, join_room, leave_room, disconnect
from flask import request
from datetime import datetime
from . import get_socketio, get_logger
from .services.auth_service import get_auth_service

logger = get_logger('socket_events')
socketio = get_socketio()
auth_service = get_auth_service()

# Store connected users
connected_users = {}

@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection."""
    try:
        # Verify authentication
        if not auth or 'token' not in auth:
            logger.warning("Connection attempt without token")
            disconnect()
            return False
        
        # Verify token
        user_claims = auth_service.verify_token(auth['token'])
        if not user_claims:
            logger.warning("Connection attempt with invalid token")
            disconnect()
            return False
        
        user_id = user_claims.get('uid')
        session_id = request.sid
        
        # Store user connection
        connected_users[session_id] = {
            'user_id': user_id,
            'connected_at': datetime.utcnow(),
            'leagues': []
        }
        
        logger.info(f"User {user_id} connected with session {session_id}")
        emit('connected', {'status': 'success', 'user_id': user_id})
        
    except Exception as e:
        logger.error(f"Connection error: {e}")
        disconnect()
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    try:
        session_id = request.sid
        if session_id in connected_users:
            user_id = connected_users[session_id]['user_id']
            
            # Leave all league rooms
            leagues = connected_users[session_id].get('leagues', [])
            for league_id in leagues:
                leave_room(f'league_{league_id}')
                emit('user_left', {'user_id': user_id}, room=f'league_{league_id}')
            
            # Remove from connected users
            del connected_users[session_id]
            
            logger.info(f"User {user_id} disconnected")
    
    except Exception as e:
        logger.error(f"Disconnect error: {e}")

@socketio.on('join_league')
def handle_join_league(data):
    """Join a league room for real-time updates."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        league_id = data.get('league_id')
        if not league_id:
            emit('error', {'message': 'league_id required'})
            return
        
        user_id = connected_users[session_id]['user_id']
        
        # TODO: Verify user has access to league
        
        # Join league room
        join_room(f'league_{league_id}')
        
        # Add to user's league list
        if league_id not in connected_users[session_id]['leagues']:
            connected_users[session_id]['leagues'].append(league_id)
        
        # Notify others in league
        emit('user_joined', {
            'user_id': user_id,
            'league_id': league_id
        }, room=f'league_{league_id}', include_self=False)
        
        emit('joined_league', {'league_id': league_id})
        logger.info(f"User {user_id} joined league room {league_id}")
        
    except Exception as e:
        logger.error(f"Join league error: {e}")
        emit('error', {'message': 'Failed to join league'})

@socketio.on('leave_league')
def handle_leave_league(data):
    """Leave a league room."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            return
        
        league_id = data.get('league_id')
        if not league_id:
            return
        
        user_id = connected_users[session_id]['user_id']
        
        # Leave league room
        leave_room(f'league_{league_id}')
        
        # Remove from user's league list
        if league_id in connected_users[session_id]['leagues']:
            connected_users[session_id]['leagues'].remove(league_id)
        
        # Notify others in league
        emit('user_left', {
            'user_id': user_id,
            'league_id': league_id
        }, room=f'league_{league_id}')
        
        emit('left_league', {'league_id': league_id})
        logger.info(f"User {user_id} left league room {league_id}")
        
    except Exception as e:
        logger.error(f"Leave league error: {e}")

@socketio.on('draft_pick')
def handle_draft_pick(data):
    """Handle draft pick selection."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_users[session_id]['user_id']
        league_id = data.get('league_id')
        player_id = data.get('player_id')
        pick_number = data.get('pick_number')
        
        if not all([league_id, player_id, pick_number]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        # TODO: Validate draft pick and process
        
        # Broadcast pick to league
        pick_data = {
            'league_id': league_id,
            'player_id': player_id,
            'pick_number': pick_number,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('draft_pick_made', pick_data, room=f'league_{league_id}')
        logger.info(f"Draft pick made: {pick_data}")
        
    except Exception as e:
        logger.error(f"Draft pick error: {e}")
        emit('error', {'message': 'Failed to process draft pick'})

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat message in league."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_users[session_id]['user_id']
        league_id = data.get('league_id')
        message = data.get('message', '').strip()
        
        if not league_id or not message:
            emit('error', {'message': 'league_id and message required'})
            return
        
        if len(message) > 500:
            emit('error', {'message': 'Message too long'})
            return
        
        # TODO: Store message in database and validate user access
        
        # Broadcast message to league
        message_data = {
            'id': str(datetime.utcnow().timestamp()),
            'league_id': league_id,
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('chat_message', message_data, room=f'league_{league_id}')
        logger.info(f"Chat message sent in league {league_id}")
        
    except Exception as e:
        logger.error(f"Chat message error: {e}")
        emit('error', {'message': 'Failed to send message'})

@socketio.on('trade_proposal')
def handle_trade_proposal(data):
    """Handle trade proposal notification."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_users[session_id]['user_id']
        league_id = data.get('league_id')
        to_team_id = data.get('to_team_id')
        
        if not all([league_id, to_team_id]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        # TODO: Process trade proposal and validate
        
        # Broadcast to league
        trade_data = {
            'league_id': league_id,
            'from_user_id': user_id,
            'to_team_id': to_team_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('trade_proposed', trade_data, room=f'league_{league_id}')
        logger.info(f"Trade proposed in league {league_id}")
        
    except Exception as e:
        logger.error(f"Trade proposal error: {e}")
        emit('error', {'message': 'Failed to process trade proposal'})

@socketio.on('waiver_claim')
def handle_waiver_claim(data):
    """Handle waiver claim notification."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_users[session_id]['user_id']
        league_id = data.get('league_id')
        player_id = data.get('player_id')
        bid_amount = data.get('bid_amount')
        
        if not all([league_id, player_id, bid_amount]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        # TODO: Process waiver claim and validate
        
        # Broadcast to league (without showing bid amount to others)
        claim_data = {
            'league_id': league_id,
            'user_id': user_id,
            'player_id': player_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('waiver_claim_made', claim_data, room=f'league_{league_id}')
        logger.info(f"Waiver claim made in league {league_id}")
        
    except Exception as e:
        logger.error(f"Waiver claim error: {e}")
        emit('error', {'message': 'Failed to process waiver claim'})

@socketio.on('lineup_update')
def handle_lineup_update(data):
    """Handle lineup update notification."""
    try:
        session_id = request.sid
        if session_id not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        user_id = connected_users[session_id]['user_id']
        league_id = data.get('league_id')
        team_id = data.get('team_id')
        
        if not all([league_id, team_id]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        # TODO: Validate lineup update
        
        # Broadcast to league
        update_data = {
            'league_id': league_id,
            'team_id': team_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('lineup_updated', update_data, room=f'league_{league_id}')
        logger.info(f"Lineup updated in league {league_id}")
        
    except Exception as e:
        logger.error(f"Lineup update error: {e}")
        emit('error', {'message': 'Failed to process lineup update'})

# Utility functions for emitting events
def broadcast_to_league(league_id: str, event: str, data: dict):
    """Broadcast event to all users in a league."""
    try:
        socketio.emit(event, data, room=f'league_{league_id}')
        logger.debug(f"Broadcasted {event} to league {league_id}")
    except Exception as e:
        logger.error(f"Failed to broadcast to league {league_id}: {e}")

def send_to_user(user_id: str, event: str, data: dict):
    """Send event to a specific user if connected."""
    try:
        # Find user's session
        for session_id, user_info in connected_users.items():
            if user_info['user_id'] == user_id:
                socketio.emit(event, data, room=session_id)
                logger.debug(f"Sent {event} to user {user_id}")
                return True
        
        logger.debug(f"User {user_id} not connected for event {event}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to send to user {user_id}: {e}")
        return False

def get_connected_users_in_league(league_id: str):
    """Get list of connected users in a league."""
    try:
        users = []
        for session_id, user_info in connected_users.items():
            if league_id in user_info.get('leagues', []):
                users.append(user_info['user_id'])
        return users
    except Exception as e:
        logger.error(f"Failed to get connected users for league {league_id}: {e}")
        return []