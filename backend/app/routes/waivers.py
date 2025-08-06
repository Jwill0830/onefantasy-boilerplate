"""
Waivers routes for managing waiver wire claims and bidding system.
Handles waiver claims, processing, and waiver wire management.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging

from ..services.auth_service import AuthService
from ..services.waiver_service import WaiverService
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..services.notification_service import NotificationService
from ..utils.validators import validate_json
from ..utils.logger import get_logger

logger = get_logger(__name__)

waivers_bp = Blueprint('waivers', __name__)

def init_waivers_routes(app, db, socketio):
    """Initialize waivers routes with dependencies."""
    auth_service = AuthService()
    waiver_service = WaiverService(db, socketio)
    team_model = TeamModel(db)
    league_model = LeagueModel(db)
    notification_service = NotificationService(db, socketio)

    @waivers_bp.route('/leagues/<league_id>/waivers/claims', methods=['POST'])
    @validate_json
    def submit_waiver_claim(league_id):
        """Submit a waiver wire claim."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate required fields
            required_fields = ['team_id', 'add_player_id', 'drop_player_id', 'bid_amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            team_id = data['team_id']
            add_player_id = int(data['add_player_id'])
            drop_player_id = int(data['drop_player_id'])
            bid_amount = float(data['bid_amount'])

            # Verify team ownership
            team = team_model.get_team(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404

            if team.get('owner_id') != user_id:
                return jsonify({'error': 'You do not own this team'}), 403

            if team.get('league_id') != league_id:
                return jsonify({'error': 'Team not in specified league'}), 400

            # Submit waiver claim
            claim = waiver_service.submit_waiver_claim(
                league_id=league_id,
                team_id=team_id,
                user_id=user_id,
                add_player_id=add_player_id,
                drop_player_id=drop_player_id,
                bid_amount=bid_amount,
                priority=data.get('priority')
            )

            return jsonify({
                'success': True,
                'claim': claim,
                'message': 'Waiver claim submitted successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error submitting waiver claim: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/claims/<claim_id>', methods=['PUT'])
    @validate_json
    def update_waiver_claim(league_id, claim_id):
        """Update an existing waiver claim."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Update waiver claim
            success = waiver_service.update_waiver_claim(
                claim_id=claim_id,
                user_id=user_id,
                updates=data
            )

            if not success:
                return jsonify({'error': 'Failed to update claim or claim not found'}), 400

            # Get updated claim
            updated_claim = waiver_service.get_waiver_claim(claim_id)

            return jsonify({
                'success': True,
                'claim': updated_claim,
                'message': 'Waiver claim updated successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error updating waiver claim: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/claims/<claim_id>', methods=['DELETE'])
    def cancel_waiver_claim(league_id, claim_id):
        """Cancel a waiver claim."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Cancel waiver claim
            success = waiver_service.cancel_waiver_claim(claim_id, user_id)

            if not success:
                return jsonify({'error': 'Failed to cancel claim or claim not found'}), 400

            return jsonify({
                'success': True,
                'message': 'Waiver claim cancelled successfully'
            })

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error cancelling waiver claim: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/teams/<team_id>/waivers/claims', methods=['GET'])
    def get_team_waiver_claims(team_id):
        """Get all waiver claims for a team."""
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

            # Get query parameters
            status = request.args.get('status')  # pending, processed, cancelled
            limit = min(int(request.args.get('limit', 20)), 50)

            # Get team's waiver claims
            claims = waiver_service.get_team_waiver_claims(team_id, status, limit)

            return jsonify({
                'success': True,
                'claims': claims,
                'count': len(claims),
                'team_id': team_id
            })

        except Exception as e:
            logger.error(f"Error getting team waiver claims: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/claims', methods=['GET'])
    def get_league_waiver_claims(league_id):
        """Get all waiver claims for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            status = request.args.get('status')  # pending, processed, cancelled
            limit = min(int(request.args.get('limit', 50)), 100)

            # Get league's waiver claims
            claims = waiver_service.get_league_waiver_claims(league_id, status, limit)

            return jsonify({
                'success': True,
                'claims': claims,
                'count': len(claims),
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting league waiver claims: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/order', methods=['GET'])
    def get_waiver_order(league_id):
        """Get current waiver wire order for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get waiver order
            waiver_order = waiver_service.get_waiver_order(league_id)

            return jsonify({
                'success': True,
                'waiver_order': waiver_order,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting waiver order: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/order', methods=['PUT'])
    @validate_json
    def update_waiver_order(league_id):
        """Update waiver wire order (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can update waiver order'}), 403

            # Validate new order
            if 'waiver_order' not in data:
                return jsonify({'error': 'waiver_order is required'}), 400

            new_order = data['waiver_order']
            if not isinstance(new_order, list):
                return jsonify({'error': 'waiver_order must be a list'}), 400

            # Update waiver order
            success = waiver_service.update_waiver_order(league_id, new_order)

            if not success:
                return jsonify({'error': 'Failed to update waiver order'}), 500

            # Get updated order
            updated_order = waiver_service.get_waiver_order(league_id)

            # Emit real-time update
            socketio.emit('waiver_order_updated', {
                'league_id': league_id,
                'waiver_order': updated_order
            }, room=f"league_{league_id}")

            return jsonify({
                'success': True,
                'waiver_order': updated_order,
                'message': 'Waiver order updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating waiver order: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/budget/<team_id>', methods=['GET'])
    def get_waiver_budget(league_id, team_id):
        """Get team's waiver wire budget."""
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

            # Get waiver budget
            budget_info = waiver_service.get_team_waiver_budget(team_id)

            return jsonify({
                'success': True,
                'budget_info': budget_info,
                'team_id': team_id
            })

        except Exception as e:
            logger.error(f"Error getting waiver budget: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/budget/<team_id>', methods=['PUT'])
    @validate_json
    def update_waiver_budget(league_id, team_id):
        """Update team's waiver wire budget (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can update waiver budgets'}), 403

            # Validate request
            if 'budget' not in data:
                return jsonify({'error': 'budget is required'}), 400

            new_budget = float(data['budget'])
            if new_budget < 0:
                return jsonify({'error': 'Budget cannot be negative'}), 400

            # Update budget
            success = waiver_service.update_team_waiver_budget(team_id, new_budget)

            if not success:
                return jsonify({'error': 'Failed to update waiver budget'}), 500

            # Get updated budget info
            updated_budget = waiver_service.get_team_waiver_budget(team_id)

            return jsonify({
                'success': True,
                'budget_info': updated_budget,
                'message': 'Waiver budget updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating waiver budget: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/process', methods=['POST'])
    def process_waiver_claims(league_id):
        """Process all pending waiver claims for a league (commissioner only)."""
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
                return jsonify({'error': 'Only the commissioner can process waiver claims'}), 403

            # Process waiver claims
            processing_results = waiver_service.process_waiver_claims(league_id)

            # Emit real-time update
            socketio.emit('waivers_processed', {
                'league_id': league_id,
                'results': processing_results
            }, room=f"league_{league_id}")

            return jsonify({
                'success': True,
                'processing_results': processing_results,
                'message': 'Waiver claims processed successfully'
            })

        except Exception as e:
            logger.error(f"Error processing waiver claims: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/deadline', methods=['GET'])
    def get_waiver_deadline(league_id):
        """Get next waiver wire deadline."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get waiver deadline
            deadline_info = waiver_service.get_waiver_deadline(league_id)

            return jsonify({
                'success': True,
                'deadline_info': deadline_info,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting waiver deadline: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/deadline', methods=['PUT'])
    @validate_json
    def update_waiver_deadline(league_id):
        """Update waiver wire deadline (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can update waiver deadline'}), 403

            # Validate request
            if 'deadline' not in data:
                return jsonify({'error': 'deadline is required'}), 400

            # Parse deadline
            try:
                deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid deadline format. Use ISO format.'}), 400

            # Ensure deadline is in the future
            if deadline <= datetime.utcnow():
                return jsonify({'error': 'Deadline must be in the future'}), 400

            # Update deadline
            success = waiver_service.update_waiver_deadline(league_id, deadline)

            if not success:
                return jsonify({'error': 'Failed to update waiver deadline'}), 500

            # Get updated deadline info
            updated_deadline = waiver_service.get_waiver_deadline(league_id)

            # Emit real-time update
            socketio.emit('waiver_deadline_updated', {
                'league_id': league_id,
                'deadline_info': updated_deadline
            }, room=f"league_{league_id}")

            return jsonify({
                'success': True,
                'deadline_info': updated_deadline,
                'message': 'Waiver deadline updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating waiver deadline: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/activity', methods=['GET'])
    def get_waiver_activity(league_id):
        """Get recent waiver wire activity for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            limit = min(int(request.args.get('limit', 20)), 50)
            days = min(int(request.args.get('days', 7)), 30)  # Last N days

            # Get waiver activity
            activity = waiver_service.get_waiver_activity(league_id, days, limit)

            return jsonify({
                'success': True,
                'activity': activity,
                'league_id': league_id,
                'days': days,
                'count': len(activity)
            })

        except Exception as e:
            logger.error(f"Error getting waiver activity: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/stats', methods=['GET'])
    def get_waiver_stats(league_id):
        """Get waiver wire statistics for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get waiver stats
            stats = waiver_service.get_waiver_stats(league_id)

            return jsonify({
                'success': True,
                'stats': stats,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting waiver stats: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/settings', methods=['GET'])
    def get_waiver_settings(league_id):
        """Get waiver wire settings for a league."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get waiver settings
            settings = waiver_service.get_waiver_settings(league_id)

            return jsonify({
                'success': True,
                'settings': settings,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting waiver settings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/settings', methods=['PUT'])
    @validate_json
    def update_waiver_settings(league_id):
        """Update waiver wire settings (commissioner only)."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Verify commissioner privileges
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can update waiver settings'}), 403

            # Update waiver settings
            success = waiver_service.update_waiver_settings(league_id, data)

            if not success:
                return jsonify({'error': 'Failed to update waiver settings'}), 500

            # Get updated settings
            updated_settings = waiver_service.get_waiver_settings(league_id)

            return jsonify({
                'success': True,
                'settings': updated_settings,
                'message': 'Waiver settings updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating waiver settings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/validate-claim', methods=['POST'])
    @validate_json
    def validate_waiver_claim(league_id):
        """Validate a waiver claim before submission."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate required fields
            required_fields = ['team_id', 'add_player_id', 'drop_player_id', 'bid_amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            # Validate the claim
            validation_result = waiver_service.validate_waiver_claim(
                league_id=league_id,
                team_id=data['team_id'],
                user_id=user_id,
                add_player_id=int(data['add_player_id']),
                drop_player_id=int(data['drop_player_id']),
                bid_amount=float(data['bid_amount'])
            )

            return jsonify({
                'success': True,
                'validation': validation_result
            })

        except Exception as e:
            logger.error(f"Error validating waiver claim: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/priority/<team_id>', methods=['GET'])
    def get_waiver_priority(league_id, team_id):
        """Get team's current waiver priority."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get waiver priority
            priority_info = waiver_service.get_team_waiver_priority(league_id, team_id)

            return jsonify({
                'success': True,
                'priority_info': priority_info,
                'team_id': team_id,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error getting waiver priority: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/trending', methods=['GET'])
    def get_trending_waiver_targets(league_id):
        """Get trending players on the waiver wire."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            # Get query parameters
            limit = min(int(request.args.get('limit', 20)), 50)
            position = request.args.get('position')

            # Get trending waiver targets
            trending_players = waiver_service.get_trending_waiver_targets(
                league_id, position, limit
            )

            return jsonify({
                'success': True,
                'trending_players': trending_players,
                'league_id': league_id,
                'position': position,
                'count': len(trending_players)
            })

        except Exception as e:
            logger.error(f"Error getting trending waiver targets: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/claims/bulk', methods=['POST'])
    @validate_json
    def submit_bulk_waiver_claims(league_id):
        """Submit multiple waiver claims at once."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']
            data = request.get_json()

            # Validate request
            if 'claims' not in data:
                return jsonify({'error': 'claims array is required'}), 400

            claims_data = data['claims']
            if not isinstance(claims_data, list):
                return jsonify({'error': 'claims must be an array'}), 400

            if len(claims_data) > 10:
                return jsonify({'error': 'Maximum 10 claims can be submitted at once'}), 400

            # Submit bulk claims
            results = waiver_service.submit_bulk_waiver_claims(
                league_id, user_id, claims_data
            )

            return jsonify({
                'success': True,
                'results': results,
                'total_claims': len(claims_data),
                'successful_claims': len([r for r in results if r.get('success')]),
                'failed_claims': len([r for r in results if not r.get('success')])
            })

        except Exception as e:
            logger.error(f"Error submitting bulk waiver claims: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @waivers_bp.route('/leagues/<league_id>/waivers/simulate', methods=['POST'])
    @validate_json
    def simulate_waiver_processing(league_id):
        """Simulate waiver processing to see potential outcomes."""
        try:
            # Verify authentication
            auth_result = auth_service.verify_token(request.headers.get('Authorization'))
            if not auth_result['valid']:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = auth_result['user_id']

            # Verify commissioner privileges for simulation
            league = league_model.get_league(league_id)
            if not league:
                return jsonify({'error': 'League not found'}), 404

            if league.get('commissioner_id') != user_id:
                return jsonify({'error': 'Only the commissioner can simulate waiver processing'}), 403

            # Run simulation
            simulation_results = waiver_service.simulate_waiver_processing(league_id)

            return jsonify({
                'success': True,
                'simulation_results': simulation_results,
                'league_id': league_id
            })

        except Exception as e:
            logger.error(f"Error simulating waiver processing: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    # Register blueprint
    app.register_blueprint(waivers_bp, url_prefix='/api')