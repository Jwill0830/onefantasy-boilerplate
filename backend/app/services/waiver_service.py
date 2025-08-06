"""
Waiver service for handling waiver wire operations.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from .. import get_db, get_socketio
from ..models.team_model import TeamModel
from ..models.player_model import PlayerModel
from ..models.chat_model import ChatModel
from ..utils.logger import get_logger

logger = get_logger('waiver_service')

class WaiverService:
    """Service for managing waiver wire operations."""
    
    def __init__(self):
        self.db = get_db()
        self.team_model = TeamModel()
        self.player_model = PlayerModel()
        self.chat_model = ChatModel()
        self.socketio = get_socketio()
    
    def submit_waiver_claim(self, league_id: str, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a waiver claim."""
        try:
            # Validate claim data
            validation = self._validate_waiver_claim(league_id, claim_data)
            if not validation['valid']:
                return {'success': False, 'error': validation['error']}
            
            claim_id = str(uuid.uuid4())
            
            # Create waiver claim document
            claim_doc = {
                'id': claim_id,
                'league_id': league_id,
                'team_id': claim_data['team_id'],
                'player_id': claim_data['player_id'],
                'drop_player_id': claim_data.get('drop_player_id'),
                'bid_amount': claim_data['bid_amount'],
                'priority': self._calculate_claim_priority(league_id, claim_data['team_id']),
                'status': 'pending',
                'claimed_at': datetime.utcnow(),
                'processed_at': None,
                'notes': claim_data.get('notes', '')
            }
            
            # Store claim
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('waiver_claims').document(claim_id))
            doc_ref.set(claim_doc)
            
            # Get team and player info for notifications
            team = self.team_model.get_team(league_id, claim_data['team_id'])
            player = self.player_model.get_player(claim_data['player_id'])
            
            team_name = team.get('name', 'Unknown Team') if team else 'Unknown Team'
            player_name = player.get('name', 'Unknown Player') if player else 'Unknown Player'
            
            # Send notification
            self.chat_model.send_waiver_notification(league_id, {
                'claim_id': claim_id,
                'team_id': claim_data['team_id'],
                'team_name': team_name,
                'player_id': claim_data['player_id'],
                'player_name': player_name,
                'bid_amount': claim_data['bid_amount'],
                'status': 'submitted'
            })
            
            # Broadcast to league
            self.socketio.emit('waiver_claim_submitted', {
                'league_id': league_id,
                'team_id': claim_data['team_id'],
                'team_name': team_name,
                'player_name': player_name,
                'claim_id': claim_id
            }, room=f'league_{league_id}')
            
            logger.info(f"Waiver claim {claim_id} submitted for player {claim_data['player_id']}")
            
            return {
                'success': True,
                'claim_id': claim_id,
                'message': f'Waiver claim submitted for {player_name}'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit waiver claim: {e}")
            return {'success': False, 'error': 'Failed to submit waiver claim'}
    
    def get_waiver_claims(self, league_id: str, team_id: str = None, 
                         status: str = None) -> List[Dict[str, Any]]:
        """Get waiver claims for a league or team."""
        try:
            claims_ref = (self.db.collection('leagues').document(league_id)
                         .collection('waiver_claims'))
            
            # Apply filters
            if team_id:
                claims_ref = claims_ref.where('team_id', '==', team_id)
            
            if status:
                claims_ref = claims_ref.where('status', '==', status)
            
            # Order by priority and time
            claims_ref = claims_ref.order_by('priority').order_by('claimed_at')
            
            claims = [doc.to_dict() for doc in claims_ref.stream()]
            
            # Enhance with player and team info
            for claim in claims:
                player = self.player_model.get_player(claim['player_id'])
                team = self.team_model.get_team(league_id, claim['team_id'])
                
                claim['player_info'] = player
                claim['team_info'] = team
                
                if claim.get('drop_player_id'):
                    drop_player = self.player_model.get_player(claim['drop_player_id'])
                    claim['drop_player_info'] = drop_player
            
            return claims
            
        except Exception as e:
            logger.error(f"Failed to get waiver claims: {e}")
            return []
    
    def cancel_waiver_claim(self, league_id: str, claim_id: str, team_id: str) -> Dict[str, Any]:
        """Cancel a pending waiver claim."""
        try:
            # Get claim
            claim = self._get_waiver_claim(league_id, claim_id)
            if not claim:
                return {'success': False, 'error': 'Claim not found'}
            
            # Verify ownership
            if claim['team_id'] != team_id:
                return {'success': False, 'error': 'Cannot cancel another team\'s claim'}
            
            # Check if still pending
            if claim['status'] != 'pending':
                return {'success': False, 'error': 'Can only cancel pending claims'}
            
            # Update claim status
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('waiver_claims').document(claim_id))
            doc_ref.update({
                'status': 'cancelled',
                'processed_at': datetime.utcnow()
            })
            
            logger.info(f"Waiver claim {claim_id} cancelled")
            
            return {
                'success': True,
                'message': 'Waiver claim cancelled'
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel waiver claim: {e}")
            return {'success': False, 'error': 'Failed to cancel claim'}
    
    def process_waivers(self, league_id: str) -> Dict[str, Any]:
        """Process all pending waiver claims for a league."""
        try:
            logger.info(f"Processing waivers for league {league_id}")
            
            # Get all pending claims sorted by priority
            pending_claims = self.get_waiver_claims(league_id, status='pending')
            
            if not pending_claims:
                return {
                    'success': True,
                    'message': 'No pending waiver claims to process',
                    'results': []
                }
            
            # Group claims by player
            claims_by_player = {}
            for claim in pending_claims:
                player_id = claim['player_id']
                if player_id not in claims_by_player:
                    claims_by_player[player_id] = []
                claims_by_player[player_id].append(claim)
            
            results = []
            
            # Process each player's claims
            for player_id, player_claims in claims_by_player.items():
                # Sort by priority (lower number = higher priority) then by bid amount
                player_claims.sort(key=lambda c: (c['priority'], -c['bid_amount']))
                
                # Award to highest priority/bidder
                winning_claim = player_claims[0]
                
                # Process winning claim
                success = self._execute_waiver_claim(league_id, winning_claim)
                
                if success:
                    results.append({
                        'claim_id': winning_claim['id'],
                        'team_id': winning_claim['team_id'],
                        'player_id': player_id,
                        'bid_amount': winning_claim['bid_amount'],
                        'status': 'successful'
                    })
                    
                    # Mark other claims for this player as failed
                    for claim in player_claims[1:]:
                        self._mark_claim_failed(league_id, claim['id'])
                        results.append({
                            'claim_id': claim['id'],
                            'team_id': claim['team_id'],
                            'player_id': player_id,
                            'bid_amount': claim['bid_amount'],
                            'status': 'failed'
                        })
                else:
                    # Mark all claims as failed if execution failed
                    for claim in player_claims:
                        self._mark_claim_failed(league_id, claim['id'])
                        results.append({
                            'claim_id': claim['id'],
                            'team_id': claim['team_id'],
                            'player_id': player_id,
                            'bid_amount': claim['bid_amount'],
                            'status': 'failed'
                        })
            
            # Update waiver priorities
            self._update_waiver_priorities(league_id, results)
            
            # Send notifications
            self._send_waiver_results_notifications(league_id, results)
            
            logger.info(f"Processed {len(results)} waiver claims for league {league_id}")
            
            return {
                'success': True,
                'message': f'Processed {len(results)} waiver claims',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to process waivers: {e}")
            return {'success': False, 'error': 'Failed to process waivers'}
    
    def get_waiver_wire_players(self, league_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get players available on the waiver wire."""
        try:
            # Get available players
            available_players = self.player_model.get_available_players(league_id, limit)
            
            # Add waiver wire specific info
            for player in available_players:
                # Check if there are pending claims for this player
                pending_claims = self._get_pending_claims_for_player(league_id, player['id'])
                player['pending_claims'] = len(pending_claims)
                player['highest_bid'] = max([c['bid_amount'] for c in pending_claims], default=0)
            
            # Sort by trending/points
            available_players.sort(key=lambda p: p.get('total_points', 0), reverse=True)
            
            return available_players
            
        except Exception as e:
            logger.error(f"Failed to get waiver wire players: {e}")
            return []
    
    def get_team_waiver_info(self, league_id: str, team_id: str) -> Dict[str, Any]:
        """Get waiver information for a team."""
        try:
            team = self.team_model.get_team(league_id, team_id)
            if not team:
                return {}
            
            # Get pending claims
            pending_claims = self.get_waiver_claims(league_id, team_id, 'pending')
            
            # Calculate total pending bids
            total_pending_bids = sum(claim['bid_amount'] for claim in pending_claims)
            
            # Get recent claim history
            recent_claims = self.get_waiver_claims(league_id, team_id)[:10]
            
            return {
                'waiver_budget': team.get('waiver_budget', 0),
                'waiver_position': team.get('waiver_position', 1),
                'pending_claims': len(pending_claims),
                'total_pending_bids': total_pending_bids,
                'available_budget': team.get('waiver_budget', 0) - total_pending_bids,
                'recent_claims': recent_claims
            }
            
        except Exception as e:
            logger.error(f"Failed to get team waiver info: {e}")
            return {}
    
    def _validate_waiver_claim(self, league_id: str, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a waiver claim."""
        errors = []
        
        try:
            # Check required fields
            required_fields = ['team_id', 'player_id', 'bid_amount']
            for field in required_fields:
                if field not in claim_data:
                    errors.append(f'{field} is required')
            
            if errors:
                return {'valid': False, 'error': '; '.join(errors)}
            
            # Get team
            team = self.team_model.get_team(league_id, claim_data['team_id'])
            if not team:
                return {'valid': False, 'error': 'Team not found'}
            
            # Check bid amount
            bid_amount = claim_data['bid_amount']
            waiver_budget = team.get('waiver_budget', 0)
            
            if bid_amount < 0:
                return {'valid': False, 'error': 'Bid amount must be positive'}
            
            if bid_amount > waiver_budget:
                return {'valid': False, 'error': 'Bid exceeds available budget'}
            
            # Check if player is available
            player = self.player_model.get_player(claim_data['player_id'])
            if not player:
                return {'valid': False, 'error': 'Player not found'}
            
            # Check if player is already on a roster
            drafted_players = self.player_model._get_drafted_players(league_id)
            if claim_data['player_id'] in drafted_players:
                return {'valid': False, 'error': 'Player is already rostered'}
            
            # Check if team already has a claim for this player
            existing_claim = self._get_team_claim_for_player(
                league_id, claim_data['team_id'], claim_data['player_id']
            )
            if existing_claim and existing_claim['status'] == 'pending':
                return {'valid': False, 'error': 'Already have pending claim for this player'}
            
            # If dropping a player, validate they own that player
            if claim_data.get('drop_player_id'):
                team_roster = team.get('roster', {})
                all_players = (team_roster.get('starters', []) + 
                             team_roster.get('bench', []))
                
                if claim_data['drop_player_id'] not in all_players:
                    return {'valid': False, 'error': 'Cannot drop player not on roster'}
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Failed to validate waiver claim: {e}")
            return {'valid': False, 'error': 'Validation failed'}
    
    def _calculate_claim_priority(self, league_id: str, team_id: str) -> int:
        """Calculate waiver claim priority for a team."""
        try:
            team = self.team_model.get_team(league_id, team_id)
            if not team:
                return 999  # Lowest priority if team not found
            
            return team.get('waiver_position', 1)
            
        except Exception as e:
            logger.error(f"Failed to calculate claim priority: {e}")
            return 999
    
    def _execute_waiver_claim(self, league_id: str, claim: Dict[str, Any]) -> bool:
        """Execute a waiver claim (add player, drop player, deduct budget)."""
        try:
            team_id = claim['team_id']
            player_id = claim['player_id']
            drop_player_id = claim.get('drop_player_id')
            bid_amount = claim['bid_amount']
            
            # Add player to roster
            success = self.team_model.add_player_to_roster(league_id, team_id, player_id, 'bench')
            if not success:
                return False
            
            # Drop player if specified
            if drop_player_id:
                self.team_model.remove_player_from_roster(league_id, team_id, drop_player_id)
            
            # Deduct bid amount from budget
            self.team_model.spend_waiver_budget(league_id, team_id, bid_amount)
            
            # Mark claim as successful
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('waiver_claims').document(claim['id']))
            doc_ref.update({
                'status': 'successful',
                'processed_at': datetime.utcnow()
            })
            
            # Record transaction
            transaction = {
                'type': 'waiver_claim',
                'player_id': player_id,
                'drop_player_id': drop_player_id,
                'bid_amount': bid_amount,
                'claim_id': claim['id'],
                'status': 'completed'
            }
            self.team_model.add_transaction(league_id, team_id, transaction)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute waiver claim: {e}")
            return False
    
    def _mark_claim_failed(self, league_id: str, claim_id: str) -> None:
        """Mark a waiver claim as failed."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('waiver_claims').document(claim_id))
            doc_ref.update({
                'status': 'failed',
                'processed_at': datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Failed to mark claim as failed: {e}")
    
    def _update_waiver_priorities(self, league_id: str, results: List[Dict[str, Any]]) -> None:
        """Update waiver priorities after processing."""
        try:
            # Teams that successfully claimed players go to end of waiver order
            successful_teams = [r['team_id'] for r in results if r['status'] == 'successful']
            
            if not successful_teams:
                return
            
            # Get all teams
            teams = self.team_model.get_league_teams(league_id)
            
            # Sort teams by current waiver position
            teams.sort(key=lambda t: t.get('waiver_position', 1))
            
            # Move successful teams to end and adjust others
            new_positions = {}
            position = 1
            
            # Assign positions to teams that didn't claim
            for team in teams:
                if team['id'] not in successful_teams:
                    new_positions[team['id']] = position
                    position += 1
            
            # Assign positions to teams that claimed (in order of original priority)
            for team in teams:
                if team['id'] in successful_teams:
                    new_positions[team['id']] = position
                    position += 1
            
            # Update team waiver positions
            for team_id, new_position in new_positions.items():
                self.team_model.update_waiver_position(league_id, team_id, new_position)
            
        except Exception as e:
            logger.error(f"Failed to update waiver priorities: {e}")
    
    def _send_waiver_results_notifications(self, league_id: str, results: List[Dict[str, Any]]) -> None:
        """Send notifications for waiver results."""
        try:
            for result in results:
                team = self.team_model.get_team(league_id, result['team_id'])
                player = self.player_model.get_player(result['player_id'])
                
                team_name = team.get('name', 'Unknown Team') if team else 'Unknown Team'
                player_name = player.get('name', 'Unknown Player') if player else 'Unknown Player'
                
                # Send chat notification
                self.chat_model.send_waiver_notification(league_id, {
                    'claim_id': result['claim_id'],
                    'team_id': result['team_id'],
                    'team_name': team_name,
                    'player_id': result['player_id'],
                    'player_name': player_name,
                    'bid_amount': result['bid_amount'],
                    'status': result['status']
                })
            
            # Broadcast waiver results
            self.socketio.emit('waiver_results_processed', {
                'league_id': league_id,
                'results_count': len(results),
                'successful_claims': len([r for r in results if r['status'] == 'successful'])
            }, room=f'league_{league_id}')
            
        except Exception as e:
            logger.error(f"Failed to send waiver notifications: {e}")
    
    def _get_waiver_claim(self, league_id: str, claim_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific waiver claim."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('waiver_claims').document(claim_id))
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to get waiver claim: {e}")
            return None
    
    def _get_pending_claims_for_player(self, league_id: str, player_id: int) -> List[Dict[str, Any]]:
        """Get pending claims for a specific player."""
        try:
            claims_ref = (self.db.collection('leagues').document(league_id)
                         .collection('waiver_claims')
                         .where('player_id', '==', player_id)
                         .where('status', '==', 'pending'))
            
            return [doc.to_dict() for doc in claims_ref.stream()]
        except Exception as e:
            logger.error(f"Failed to get pending claims for player: {e}")
            return []
    
    def _get_team_claim_for_player(self, league_id: str, team_id: str, player_id: int) -> Optional[Dict[str, Any]]:
        """Get team's claim for a specific player."""
        try:
            claims_ref = (self.db.collection('leagues').document(league_id)
                         .collection('waiver_claims')
                         .where('team_id', '==', team_id)
                         .where('player_id', '==', player_id)
                         .where('status', '==', 'pending')
                         .limit(1))
            
            claims = list(claims_ref.stream())
            if claims:
                return claims[0].to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to get team claim for player: {e}")
            return None