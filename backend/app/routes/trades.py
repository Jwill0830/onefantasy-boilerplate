"""
Trades routes for managing player trades between teams.
Handles trade proposals, acceptance, rejection, and trade block functionality.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from ..services.auth_service import AuthService
from ..services.trade_service import TradeService
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..services.notification_service import NotificationService
from ..utils.validators import validate_json
from ..utils.logger import get_logger

logger = get_logger(__name__)

trades_bp = Blueprint('trades', __name__)

def init_trades_routes(app, db, socketio):
    """Initialize trades routes with dependencies."""
    auth_service = AuthService()
    trade_service = TradeService(db, socketio)
    team_model = TeamModel(db)
    league_model = LeagueModel(db)
    notification_service = NotificationService(db, socketio)

    @trades_bp.route('/trades/propose', methods=['POST'])
    @validate_json
    def propose_trade():
        """Propose a trade between two teams."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate required fields
            required_fields = ['proposer_team_id', 'target_team_id', 'proposer_players', 'target_players']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            proposer_team_id = data['proposer_team_id']
            target_team_id = data['target_team_id']
            proposer_players = data['proposer_players']
            target_players = data['target_players']
            message = data.get('message', '')

            # Verify team ownership
            proposer_team = team_model.get_team(proposer_team_id)
            if not proposer_team:
                return jsonify({'error': 'Proposer team not found'}), 404

            if proposer_team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own the proposer team'}), 403

            # Validate player lists
            if not isinstance(proposer_players, list) or not isinstance(target_players, list):
                return jsonify({'error': 'Player lists must be arrays'}), 400

            if not proposer_players and not target_players:
                return jsonify({'error': 'Trade must include at least one player'}), 400

            # Propose trade
            trade = trade_service.propose_trade(
                proposer_team_id=proposer_team_id,
                target_team_id=target_team_id,
                proposer_players=proposer_players,
                target_players=target_players,
                proposer_user_id=user_id,
                message=message
            )

            return jsonify({
                'success': True,
                'trade': trade,
                'message': 'Trade proposal submitted successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error proposing trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>/accept', methods=['POST'])
    def accept_trade(trade_id):
        """Accept a trade proposal."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Accept trade
            updated_trade = trade_service.accept_trade(trade_id, user_id)

            return jsonify({
                'success': True,
                'trade': updated_trade,
                'message': 'Trade accepted successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error accepting trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>/reject', methods=['POST'])
    @validate_json
    def reject_trade(trade_id):
        """Reject a trade proposal."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json() or {}
            reason = data.get('reason', '')

            # Reject trade
            updated_trade = trade_service.reject_trade(trade_id, user_id, reason)

            return jsonify({
                'success': True,
                'trade': updated_trade,
                'message': 'Trade rejected successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error rejecting trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>/cancel', methods=['POST'])
    def cancel_trade(trade_id):
        """Cancel a trade proposal."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Cancel trade
            updated_trade = trade_service.cancel_trade(trade_id, user_id)

            return jsonify({
                'success': True,
                'trade': updated_trade,
                'message': 'Trade cancelled successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error cancelling trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>', methods=['GET'])
    def get_trade(trade_id):
        """Get trade details."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get trade
            trade = trade_service.trade_model.get_trade(trade_id)
            if not trade:
                return jsonify({'error': 'Trade not found'}), 404

            return jsonify({
                'success': True,
                'trade': trade
            })

        except Exception as e:
            logger.error(f"Error getting trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/teams/<team_id>/trades', methods=['GET'])
    def get_team_trades(team_id):
        """Get all trades for a team."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            status = request.args.get('status')  # proposed, accepted, rejected, cancelled, completed
            limit = min(int(request.args.get('limit', 20)), 50)

            # Get team trades
            trades = trade_service.get_team_trades(team_id, status, limit)

            return jsonify({
                'success': True,
                'trades': trades,
                'count': len(trades),
                'team_id': team_id
            })

        except Exception as e:
            logger.error(f"Error getting team trades: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/leagues/<league_id>/trades', methods=['GET'])
    def get_league_trades(league_id):
        """Get all trades in a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            status = request.args.get('status')
            limit = min(int(request.args.get('limit', 50)), 100)

            # Get league trades
            trades = trade_service.get_league_trades(league_id, status, limit)

            return jsonify({
                'success': True,
                'trades': trades,
                'count': len(trades),
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting league trades: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>/approve', methods=['POST'])
    @validate_json
    def commissioner_approve_trade(trade_id):
        """Commissioner approval/rejection of a trade."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate request
            if 'approved' not in data:
                return jsonify({'error': 'approved field is required'}), 400

            approved = bool(data['approved'])
            notes = data.get('notes', '')

            # Commissioner approve/reject trade
            updated_trade = trade_service.commissioner_approve_trade(
                trade_id, user_id, approved, notes
            )

            action = 'approved' if approved else 'rejected'
            return jsonify({
                'success': True,
                'trade': updated_trade,
                'message': f'Trade {action} by commissioner'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error with commissioner trade approval: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/leagues/<league_id>/trade-block', methods=['GET'])
    def get_trade_block(league_id):
        """Get all players on the trade block in a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get trade block
            trade_block = trade_service.get_league_trade_block(league_id)

            return jsonify({
                'success': True,
                'trade_block': trade_block,
                'count': len(trade_block),
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting trade block: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/teams/<team_id>/trade-block', methods=['POST'])
    @validate_json
    def add_to_trade_block(team_id):
        """Add a player to the trade block."""
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
            asking_price = data.get('asking_price', '')

            # Add to trade block
            trade_block_entry = trade_service.add_player_to_trade_block(
                team_id, player_fpl_id, user_id, asking_price
            )

            return jsonify({
                'success': True,
                'trade_block_entry': trade_block_entry,
                'message': 'Player added to trade block'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error adding to trade block: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/leagues/<league_id>/trade-block/<entry_id>', methods=['DELETE'])
    def remove_from_trade_block(league_id, entry_id):
        """Remove a player from the trade block."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Remove from trade block
            success = trade_service.remove_player_from_trade_block(league_id, entry_id, user_id)

            if not success:
                return jsonify({'error': 'Failed to remove from trade block or entry not found'}), 400

            return jsonify({
                'success': True,
                'message': 'Player removed from trade block'
            })

        except Exception as e:
            logger.error(f"Error removing from trade block: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/validate', methods=['POST'])
    @validate_json
    def validate_trade():
        """Validate a trade proposal before submission."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            data = request.get_json()

            # Validate required fields
            required_fields = ['proposer_team_id', 'target_team_id', 'proposer_players', 'target_players']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            # Validate trade
            validation_result = trade_service._validate_trade_proposal(
                data['proposer_team_id'],
                data['target_team_id'],
                data['proposer_players'],
                data['target_players']
            )

            return jsonify({
                'success': True,
                'validation': validation_result
            })

        except Exception as e:
            logger.error(f"Error validating trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/leagues/<league_id>/trades/stats', methods=['GET'])
    def get_trade_stats(league_id):
        """Get trade statistics for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get trade statistics
            stats = trade_service.get_league_trade_stats(league_id)

            return jsonify({
                'success': True,
                'stats': stats,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting trade stats: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/expire-old', methods=['POST'])
    def expire_old_trades():
        """Expire old trade proposals (admin endpoint)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # TODO: Add admin role verification

            # Expire old trades
            expired_count = trade_service.expire_old_trades()

            return jsonify({
                'success': True,
                'expired_count': expired_count,
                'message': f'Expired {expired_count} old trades'
            })

        except Exception as e:
            logger.error(f"Error expiring old trades: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>/history', methods=['GET'])
    def get_trade_history(trade_id):
        """Get history/audit trail for a trade."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get trade history
            history = trade_service.get_trade_history(trade_id)

            return jsonify({
                'success': True,
                'history': history,
                'trade_id': trade_id
            })

        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/teams/<team_id>/trade-preferences', methods=['GET'])
    def get_trade_preferences(team_id):
        """Get team's trade preferences and settings."""
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

            # Get trade preferences
            preferences = trade_service.get_team_trade_preferences(team_id)

            return jsonify({
                'success': True,
                'preferences': preferences,
                'team_id': team_id
            })

        except Exception as e:
            logger.error(f"Error getting trade preferences: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/teams/<team_id>/trade-preferences', methods=['PUT'])
    @validate_json
    def update_trade_preferences(team_id):
        """Update team's trade preferences and settings."""
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

            # Update trade preferences
            success = trade_service.update_team_trade_preferences(team_id, data)

            if not success:
                return jsonify({'error': 'Failed to update trade preferences'}), 500

            # Get updated preferences
            updated_preferences = trade_service.get_team_trade_preferences(team_id)

            return jsonify({
                'success': True,
                'preferences': updated_preferences,
                'message': 'Trade preferences updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating trade preferences: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/leagues/<league_id>/trades/deadline', methods=['GET'])
    def get_trade_deadline(league_id):
        """Get trade deadline for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get league to check trade deadline
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            trade_deadline = league.get('trade_deadline')
            deadline_passed = False
            
            if trade_deadline:
                deadline_passed = datetime.utcnow() > trade_deadline

            return jsonify({
                'success': True,
                'trade_deadline': trade_deadline.isoformat() if trade_deadline else None,
                'deadline_passed': deadline_passed,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting trade deadline: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/search', methods=['GET'])
    def search_trades():
        """Search for trades across multiple criteria."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get search parameters
            league_id = request.args.get('league_id')
            team_id = request.args.get('team_id')
            player_name = request.args.get('player_name')
            status = request.args.get('status')
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            limit = min(int(request.args.get('limit', 20)), 50)

            # Build search criteria
            search_criteria = {}
            if league_id:
                search_criteria['league_id'] = league_id
            if team_id:
                search_criteria['team_id'] = team_id
            if player_name:
                search_criteria['player_name'] = player_name
            if status:
                search_criteria['status'] = status
            if date_from:
                search_criteria['date_from'] = date_from
            if date_to:
                search_criteria['date_to'] = date_to

            # Search trades
            trades = trade_service.search_trades(search_criteria, limit)

            return jsonify({
                'success': True,
                'trades': trades,
                'count': len(trades),
                'search_criteria': search_criteria
            })

        except Exception as e:
            logger.error(f"Error searching trades: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/analyze/<trade_id>', methods=['GET'])
    def analyze_trade(trade_id):
        """Analyze a trade's fairness and impact."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Analyze trade
            analysis = trade_service.analyze_trade(trade_id)

            if not analysis:
                return jsonify({'error': 'Trade not found or analysis unavailable'}), 404

            return jsonify({
                'success': True,
                'analysis': analysis,
                'trade_id': trade_id
            })

        except Exception as e:
            logger.error(f"Error analyzing trade: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/suggestions/<team_id>', methods=['GET'])
    def get_trade_suggestions(team_id):
        """Get trade suggestions for a team."""
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

            # Get parameters
            position_need = request.args.get('position')  # Position team needs
            limit = min(int(request.args.get('limit', 10)), 20)

            # Get trade suggestions
            suggestions = trade_service.get_trade_suggestions(team_id, position_need, limit)

            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'team_id': team_id,
                'position_need': position_need,
                'count': len(suggestions)
            })

        except Exception as e:
            logger.error(f"Error getting trade suggestions: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/activity/<league_id>', methods=['GET'])
    def get_trade_activity(league_id):
        """Get recent trade activity in a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get parameters
            days = min(int(request.args.get('days', 7)), 30)
            limit = min(int(request.args.get('limit', 20)), 50)

            # Get trade activity
            activity = trade_service.get_trade_activity(league_id, days, limit)

            return jsonify({
                'success': True,
                'activity': activity,
                'league_id': league_id,
                'days': days,
                'count': len(activity)
            })

        except Exception as e:
            logger.error(f"Error getting trade activity: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/<trade_id>/notify', methods=['POST'])
    @validate_json
    def send_trade_notification(trade_id):
        """Send a notification about a trade to involved parties."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate request
            if 'message' not in data:
                return jsonify({'error': 'message is required'}), 400

            message = data['message']
            notify_type = data.get('type', 'general')  # general, reminder, update

            # Send trade notification
            success = trade_service.send_trade_notification(trade_id, user_id, message, notify_type)

            if not success:
                return jsonify({'error': 'Failed to send notification or invalid permissions'}), 400

            return jsonify({
                'success': True,
                'message': 'Notification sent successfully'
            })

        except Exception as e:
            logger.error(f"Error sending trade notification: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/export/<league_id>', methods=['GET'])
    def export_trade_history(league_id):
        """Export trade history for a league (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can export trade history'}), 403

            # Get export format
            export_format = request.args.get('format', 'json')  # json, csv
            
            # Export trade history
            exported_data = trade_service.export_trade_history(league_id, export_format)

            if export_format == 'csv':
                return jsonify({
                    'success': True,
                    'csv_data': exported_data,
                    'format': 'csv'
                })
            else:
                return jsonify({
                    'success': True,
                    'trade_history': exported_data,
                    'format': 'json'
                })

        except Exception as e:
            logger.error(f"Error exporting trade history: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @trades_bp.route('/trades/templates', methods=['GET'])
    def get_trade_templates():
        """Get common trade templates and examples."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get trade templates
            templates = trade_service.get_trade_templates()

            return jsonify({
                'success': True,
                'templates': templates
            })

        except Exception as e:
            logger.error(f"Error getting trade templates: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    # Register blueprint
    app.register_blueprint(trades_bp, url_prefix='/api')