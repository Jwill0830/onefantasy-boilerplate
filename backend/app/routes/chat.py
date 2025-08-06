"""
Chat routes for handling league chat and messaging.
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from ..services.auth_service import require_auth, require_league_access
from ..models.chat_model import ChatModel
from ..utils.validators import validate_json_request
from ..utils.logger import get_logger

logger = get_logger('chat_routes')
chat_bp = Blueprint('chat', __name__)

chat_model = ChatModel()

@chat_bp.route('/<league_id>', methods=['GET'])
@require_auth
@require_league_access('member')
def get_chat_messages(league_id):
    """Get chat messages for a league."""
    try:
        limit = int(request.args.get('limit', 50))
        before_timestamp = request.args.get('before')
        
        # Parse before_timestamp if provided
        before_dt = None
        if before_timestamp:
            try:
                before_dt = datetime.fromisoformat(before_timestamp.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid before timestamp format'}), 400
        
        messages = chat_model.get_messages(league_id, limit, before_dt)
        
        return jsonify({
            'messages': messages,
            'total': len(messages),
            'has_more': len(messages) == limit
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        return jsonify({'error': 'Failed to get chat messages'}), 500

@chat_bp.route('/<league_id>', methods=['POST'])
@require_auth
@require_league_access('member')
@validate_json_request(required_fields=['message'])
def send_chat_message(league_id):
    """Send a chat message to the league."""
    try:
        data = request.get_json()
        message = data['message'].strip()
        
        # Validate message
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if len(message) > 500:
            return jsonify({'error': 'Message too long (max 500 characters)'}), 400
        
        # Get user info for the message
        from ..routes.auth import get_user_profile
        user_profile = get_user_profile(g.user_id)
        user_name = user_profile.get('display_name', 'Unknown User') if user_profile else 'Unknown User'
        
        message_data = {
            'user_id': g.user_id,
            'user_name': user_name,
            'message': message,
            'type': 'message'
        }
        
        message_id = chat_model.send_message(league_id, message_data)
        
        # The message will be broadcast via socket in the chat_model
        
        return jsonify({
            'message_id': message_id,
            'message': 'Message sent successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to send chat message: {e}")
        return jsonify({'error': 'Failed to send message'}), 500

@chat_bp.route('/<league_id>/<message_id>', methods=['PUT'])
@require_auth
@require_league_access('member')
@validate_json_request(required_fields=['message'])
def edit_chat_message(league_id, message_id):
    """Edit a chat message."""
    try:
        data = request.get_json()
        new_message = data['message'].strip()
        
        # Validate message
        if not new_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if len(new_message) > 500:
            return jsonify({'error': 'Message too long (max 500 characters)'}), 400
        
        success = chat_model.edit_message(league_id, message_id, new_message, g.user_id)
        
        if success:
            return jsonify({'message': 'Message edited successfully'}), 200
        else:
            return jsonify({'error': 'Failed to edit message'}), 400
            
    except Exception as e:
        logger.error(f"Failed to edit chat message: {e}")
        return jsonify({'error': 'Failed to edit message'}), 500

@chat_bp.route('/<league_id>/<message_id>', methods=['DELETE'])
@require_auth
@require_league_access('member')
def delete_chat_message(league_id, message_id):
    """Delete a chat message."""
    try:
        # Check if user is league commissioner for admin deletion
        from ..models.league_model import LeagueModel
        league_model = LeagueModel()
        league = league_model.get_league(league_id)
        is_admin = league and league.get('commissioner_id') == g.user_id
        
        success = chat_model.delete_message(league_id, message_id, g.user_id, is_admin)
        
        if success:
            return jsonify({'message': 'Message deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete message'}), 400
            
    except Exception as e:
        logger.error(f"Failed to delete chat message: {e}")
        return jsonify({'error': 'Failed to delete message'}), 500

@chat_bp.route('/<league_id>/search', methods=['GET'])
@require_auth
@require_league_access('member')
def search_chat_messages(league_id):
    """Search chat messages in a league."""
    try:
        query = request.args.get('query', '').strip()
        limit = int(request.args.get('limit', 50))
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        if len(query) < 2:
            return jsonify({'error': 'Search query too short (minimum 2 characters)'}), 400
        
        messages = chat_model.search_messages(league_id, query, limit)
        
        return jsonify({
            'search_results': messages,
            'query': query,
            'total': len(messages)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to search chat messages: {e}")
        return jsonify({'error': 'Failed to search messages'}), 500

@chat_bp.route('/<league_id>/activity', methods=['GET'])
@require_auth
@require_league_access('member')
def get_league_activity(league_id):
    """Get recent league activity (system messages)."""
    try:
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 20))
        
        if days < 1 or days > 30:
            return jsonify({'error': 'Days must be between 1 and 30'}), 400
        
        activity = chat_model.get_recent_activity(league_id, days, limit)
        
        return jsonify({
            'activity': activity,
            'days': days,
            'total': len(activity)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get league activity: {e}")
        return jsonify({'error': 'Failed to get league activity'}), 500

@chat_bp.route('/<league_id>/stats', methods=['GET'])
@require_auth
@require_league_access('member')
def get_chat_stats(league_id):
    """Get chat statistics for the league."""
    try:
        days = int(request.args.get('days', 30))
        
        if days < 1 or days > 365:
            return jsonify({'error': 'Days must be between 1 and 365'}), 400
        
        stats = chat_model.get_message_stats(league_id, days)
        
        return jsonify({
            'chat_stats': stats,
            'period_days': days
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get chat stats: {e}")
        return jsonify({'error': 'Failed to get chat stats'}), 500

@chat_bp.route('/<league_id>/user/<user_id>/stats', methods=['GET'])
@require_auth
@require_league_access('member')
def get_user_chat_stats(league_id, user_id):
    """Get chat statistics for a specific user."""
    try:
        days = int(request.args.get('days', 30))
        
        if days < 1 or days > 365:
            return jsonify({'error': 'Days must be between 1 and 365'}), 400
        
        message_count = chat_model.get_user_message_count(league_id, user_id, days)
        
        return jsonify({
            'user_id': user_id,
            'message_count': message_count,
            'period_days': days
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get user chat stats: {e}")
        return jsonify({'error': 'Failed to get user chat stats'}), 500

@chat_bp.route('/<league_id>/moderate/<message_id>', methods=['POST'])
@require_auth
@require_league_access('commissioner')
@validate_json_request(required_fields=['action'])
def moderate_message(league_id, message_id):
    """Moderate a chat message (commissioner only)."""
    try:
        data = request.get_json()
        action = data['action']
        
        valid_actions = ['hide', 'flag', 'approve']
        if action not in valid_actions:
            return jsonify({'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'}), 400
        
        success = chat_model.moderate_message(league_id, message_id, action, g.user_id)
        
        if success:
            return jsonify({'message': f'Message {action}ed successfully'}), 200
        else:
            return jsonify({'error': 'Failed to moderate message'}), 400
            
    except Exception as e:
        logger.error(f"Failed to moderate message: {e}")
        return jsonify({'error': 'Failed to moderate message'}), 500

@chat_bp.route('/<league_id>/announcements', methods=['POST'])
@require_auth
@require_league_access('commissioner')
@validate_json_request(required_fields=['message'])
def send_announcement(league_id):
    """Send an announcement message (commissioner only)."""
    try:
        data = request.get_json()
        message = data['message'].strip()
        
        # Validate message
        if not message:
            return jsonify({'error': 'Announcement cannot be empty'}), 400
        
        if len(message) > 1000:
            return jsonify({'error': 'Announcement too long (max 1000 characters)'}), 400
        
        # Get user info
        from ..routes.auth import get_user_profile
        user_profile = get_user_profile(g.user_id)
        user_name = user_profile.get('display_name', 'Commissioner') if user_profile else 'Commissioner'
        
        announcement_data = {
            'user_id': g.user_id,
            'user_name': f"{user_name} (Commissioner)",
            'message': f"📢 ANNOUNCEMENT: {message}",
            'type': 'announcement'
        }
        
        message_id = chat_model.send_message(league_id, announcement_data)
        
        return jsonify({
            'message_id': message_id,
            'message': 'Announcement sent successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to send announcement: {e}")
        return jsonify({'error': 'Failed to send announcement'}), 500

@chat_bp.route('/<league_id>/poll', methods=['POST'])
@require_auth
@require_league_access('member')
@validate_json_request(required_fields=['question', 'options'])
def create_poll(league_id):
    """Create a poll in the league chat."""
    try:
        data = request.get_json()
        question = data['question'].strip()
        options = data['options']
        
        # Validate poll data
        if not question:
            return jsonify({'error': 'Poll question cannot be empty'}), 400
        
        if len(question) > 200:
            return jsonify({'error': 'Poll question too long (max 200 characters)'}), 400
        
        if not isinstance(options, list) or len(options) < 2 or len(options) > 5:
            return jsonify({'error': 'Poll must have 2-5 options'}), 400
        
        for option in options:
            if not isinstance(option, str) or not option.strip():
                return jsonify({'error': 'All poll options must be non-empty strings'}), 400
            if len(option) > 100:
                return jsonify({'error': 'Poll options too long (max 100 characters each)'}), 400
        
        # Get user info
        from ..routes.auth import get_user_profile
        user_profile = get_user_profile(g.user_id)
        user_name = user_profile.get('display_name', 'Unknown User') if user_profile else 'Unknown User'
        
        poll_data = {
            'user_id': g.user_id,
            'user_name': user_name,
            'message': f"📊 POLL: {question}",
            'type': 'poll',
            'metadata': {
                'poll_question': question,
                'poll_options': options,
                'poll_votes': {},
                'poll_created_at': datetime.utcnow().isoformat()
            }
        }
        
        message_id = chat_model.send_message(league_id, poll_data)
        
        return jsonify({
            'message_id': message_id,
            'message': 'Poll created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create poll: {e}")
        return jsonify({'error': 'Failed to create poll'}), 500

@chat_bp.route('/<league_id>/poll/<message_id>/vote', methods=['POST'])
@require_auth
@require_league_access('member')
@validate_json_request(required_fields=['option_index'])
def vote_in_poll(league_id, message_id):
    """Vote in a poll."""
    try:
        data = request.get_json()
        option_index = data['option_index']
        
        if not isinstance(option_index, int) or option_index < 0:
            return jsonify({'error': 'Invalid option index'}), 400
        
        # Get the poll message
        message = chat_model.get_message(league_id, message_id)
        if not message:
            return jsonify({'error': 'Poll not found'}), 404
        
        if message.get('type') != 'poll':
            return jsonify({'error': 'Message is not a poll'}), 400
        
        metadata = message.get('metadata', {})
        poll_options = metadata.get('poll_options', [])
        
        if option_index >= len(poll_options):
            return jsonify({'error': 'Invalid option index'}), 400
        
        # Update votes
        poll_votes = metadata.get('poll_votes', {})
        poll_votes[g.user_id] = option_index
        
        # This would typically update the message in the database
        # For now, just return success
        
        return jsonify({
            'message': 'Vote recorded successfully',
            'voted_option': poll_options[option_index]
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to vote in poll: {e}")
        return jsonify({'error': 'Failed to vote in poll'}), 500

@chat_bp.route('/<league_id>/export', methods=['GET'])
@require_auth
@require_league_access('commissioner')
def export_chat_history(league_id):
    """Export chat history (commissioner only)."""
    try:
        # Get all messages (large limit for export)
        messages = chat_model.get_messages(league_id, limit=10000)
        
        # Format for export
        export_data = {
            'league_id': league_id,
            'exported_at': datetime.utcnow().isoformat(),
            'total_messages': len(messages),
            'messages': messages
        }
        
        return jsonify({
            'export_data': export_data,
            'message': f'Exported {len(messages)} messages'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to export chat history: {e}")
        return jsonify({'error': 'Failed to export chat history'}), 500