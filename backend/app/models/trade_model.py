"""
Trade model for handling trade operations and data.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from .. import get_db, get_socketio
from ..utils.logger import get_logger

logger = get_logger('trade_model')

class TradeModel:
    """Model for managing trade data and operations."""
    
    def __init__(self):
        self.db = get_db()
        self.socketio = get_socketio()
    
    def propose_trade(self, league_id: str, proposer_team_id: str, receiver_team_id: str, 
                     proposer_players: List[int], receiver_players: List[int], 
                     proposer_picks: List[Dict] = None, receiver_picks: List[Dict] = None,
                     expiration_days: int = 3) -> Dict[str, Any]:
        """
        Propose a new trade.
        
        Args:
            league_id: League ID
            proposer_team_id: Team proposing the trade
            receiver_team_id: Team receiving the proposal
            proposer_players: List of player IDs from proposer
            receiver_players: List of player IDs from receiver
            proposer_picks: Optional draft picks from proposer
            receiver_picks: Optional draft picks from receiver
            expiration_days: Days until trade expires
            
        Returns:
            Dict with trade_id and success status
        """
        try:
            # Validate input
            if not proposer_players and not receiver_players:
                raise ValueError("Trade must include at least one player")
            
            if proposer_team_id == receiver_team_id:
                raise ValueError("Cannot trade with yourself")
            
            # Validate players belong to correct teams
            validation_result = self._validate_trade_players(
                league_id, proposer_team_id, receiver_team_id, 
                proposer_players, receiver_players
            )
            
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])
            
            trade_id = str(uuid.uuid4())
            
            # Create trade document
            trade_data = {
                'id': trade_id,
                'league_id': league_id,
                'status': 'pending',
                'proposer_team_id': proposer_team_id,
                'receiver_team_id': receiver_team_id,
                'proposer_players': proposer_players,
                'receiver_players': receiver_players,
                'proposer_picks': proposer_picks or [],
                'receiver_picks': receiver_picks or [],
                'proposed_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(days=expiration_days),
                'accepted_at': None,
                'rejected_at': None,
                'notes': ''
            }
            
            # Store in Firestore
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('trades').document(trade_id))
            doc_ref.set(trade_data)
            
            # Send real-time notification
            self.socketio.emit('trade_proposed', {
                'league_id': league_id,
                'trade_id': trade_id,
                'proposer_team_id': proposer_team_id,
                'receiver_team_id': receiver_team_id,
                'proposer_players': proposer_players,
                'receiver_players': receiver_players
            }, room=f'league_{league_id}')
            
            logger.info(f"Trade {trade_id} proposed between teams {proposer_team_id} and {receiver_team_id}")
            
            return {
                'success': True,
                'trade_id': trade_id,
                'message': 'Trade proposal sent successfully'
            }
            
        except ValueError as e:
            logger.error(f"Validation error proposing trade: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error proposing trade in league {league_id}: {e}")
            return {'success': False, 'error': 'Failed to propose trade'}
    
    def accept_trade(self, league_id: str, trade_id: str, accepting_team_id: str) -> Dict[str, Any]:
        """
        Accept a trade proposal.
        
        Args:
            league_id: League ID
            trade_id: Trade ID
            accepting_team_id: Team accepting the trade
            
        Returns:
            Dict with success status
        """
        try:
            # Get trade data
            trade = self.get_trade(league_id, trade_id)
            if not trade:
                return {'success': False, 'error': 'Trade not found'}
            
            # Validate trade can be accepted
            validation = self._validate_trade_acceptance(trade, accepting_team_id)
            if not validation['valid']:
                return {'success': False, 'error': validation['error']}
            
            # Execute the trade (swap players and picks)
            execution_result = self._execute_trade(league_id, trade)
            if not execution_result['success']:
                return execution_result
            
            # Update trade status
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('trades').document(trade_id))
            doc_ref.update({
                'status': 'accepted',
                'accepted_at': datetime.utcnow()
            })
            
            # Send real-time notification
            self.socketio.emit('trade_accepted', {
                'league_id': league_id,
                'trade_id': trade_id,
                'proposer_team_id': trade['proposer_team_id'],
                'receiver_team_id': trade['receiver_team_id']
            }, room=f'league_{league_id}')
            
            logger.info(f"Trade {trade_id} accepted in league {league_id}")
            
            return {
                'success': True,
                'message': 'Trade accepted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error accepting trade {trade_id}: {e}")
            return {'success': False, 'error': 'Failed to accept trade'}
    
    def reject_trade(self, league_id: str, trade_id: str, rejecting_team_id: str) -> Dict[str, Any]:
        """
        Reject a trade proposal.
        
        Args:
            league_id: League ID
            trade_id: Trade ID
            rejecting_team_id: Team rejecting the trade
            
        Returns:
            Dict with success status
        """
        try:
            # Get trade data
            trade = self.get_trade(league_id, trade_id)
            if not trade:
                return {'success': False, 'error': 'Trade not found'}
            
            # Validate trade can be rejected
            if trade['status'] != 'pending':
                return {'success': False, 'error': 'Trade is not pending'}
            
            if trade['receiver_team_id'] != rejecting_team_id:
                return {'success': False, 'error': 'Only the receiving team can reject this trade'}
            
            # Update trade status
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('trades').document(trade_id))
            doc_ref.update({
                'status': 'rejected',
                'rejected_at': datetime.utcnow()
            })
            
            # Send real-time notification
            self.socketio.emit('trade_rejected', {
                'league_id': league_id,
                'trade_id': trade_id,
                'proposer_team_id': trade['proposer_team_id'],
                'receiver_team_id': trade['receiver_team_id']
            }, room=f'league_{league_id}')
            
            logger.info(f"Trade {trade_id} rejected in league {league_id}")
            
            return {
                'success': True,
                'message': 'Trade rejected successfully'
            }
            
        except Exception as e:
            logger.error(f"Error rejecting trade {trade_id}: {e}")
            return {'success': False, 'error': 'Failed to reject trade'}
    
    def cancel_trade(self, league_id: str, trade_id: str, canceling_team_id: str) -> Dict[str, Any]:
        """
        Cancel a trade proposal (only proposer can cancel).
        
        Args:
            league_id: League ID
            trade_id: Trade ID
            canceling_team_id: Team canceling the trade
            
        Returns:
            Dict with success status
        """
        try:
            # Get trade data
            trade = self.get_trade(league_id, trade_id)
            if not trade:
                return {'success': False, 'error': 'Trade not found'}
            
            # Validate trade can be canceled
            if trade['status'] != 'pending':
                return {'success': False, 'error': 'Trade is not pending'}
            
            if trade['proposer_team_id'] != canceling_team_id:
                return {'success': False, 'error': 'Only the proposing team can cancel this trade'}
            
            # Update trade status
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('trades').document(trade_id))
            doc_ref.update({
                'status': 'cancelled',
                'cancelled_at': datetime.utcnow()
            })
            
            # Send real-time notification
            self.socketio.emit('trade_cancelled', {
                'league_id': league_id,
                'trade_id': trade_id,
                'proposer_team_id': trade['proposer_team_id'],
                'receiver_team_id': trade['receiver_team_id']
            }, room=f'league_{league_id}')
            
            logger.info(f"Trade {trade_id} cancelled in league {league_id}")
            
            return {
                'success': True,
                'message': 'Trade cancelled successfully'
            }
            
        except Exception as e:
            logger.error(f"Error cancelling trade {trade_id}: {e}")
            return {'success': False, 'error': 'Failed to cancel trade'}
    
    def get_trade(self, league_id: str, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trade by ID."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('trades').document(trade_id))
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting trade {trade_id}: {e}")
            return None
    
    def get_active_trades(self, league_id: str, team_id: str = None) -> List[Dict[str, Any]]:
        """
        Get active (pending) trades for a league or team.
        
        Args:
            league_id: League ID
            team_id: Optional team ID to filter by
            
        Returns:
            List of active trade dictionaries
        """
        try:
            trades_ref = (self.db.collection('leagues').document(league_id)
                         .collection('trades').where('status', '==', 'pending'))
            
            trades = []
            for doc in trades_ref.stream():
                trade_data = doc.to_dict()
                
                # Filter by team if specified
                if team_id and (trade_data['proposer_team_id'] != team_id and 
                               trade_data['receiver_team_id'] != team_id):
                    continue
                
                # Check if trade has expired
                if trade_data.get('expires_at') and trade_data['expires_at'] < datetime.utcnow():
                    # Mark as expired
                    self._expire_trade(league_id, trade_data['id'])
                    continue
                
                trades.append(trade_data)
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting active trades for league {league_id}: {e}")
            return []
    
    def get_trade_history(self, league_id: str, team_id: str = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get trade history for a league or team.
        
        Args:
            league_id: League ID
            team_id: Optional team ID to filter by
            limit: Maximum number of trades to return
            
        Returns:
            List of completed trade dictionaries
        """
        try:
            trades_ref = (self.db.collection('leagues').document(league_id)
                         .collection('trades')
                         .where('status', 'in', ['accepted', 'rejected', 'cancelled', 'expired'])
                         .order_by('proposed_at', direction='DESCENDING')
                         .limit(limit))
            
            trades = []
            for doc in trades_ref.stream():
                trade_data = doc.to_dict()
                
                # Filter by team if specified
                if team_id and (trade_data['proposer_team_id'] != team_id and 
                               trade_data['receiver_team_id'] != team_id):
                    continue
                
                trades.append(trade_data)
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trade history for league {league_id}: {e}")
            return []
    
    def get_team_trading_block(self, league_id: str, team_id: str) -> List[Dict[str, Any]]:
        """Get players that a team has put on the trading block."""
        try:
            # Get team's trading block from team document
            team_ref = (self.db.collection('leagues').document(league_id)
                       .collection('teams').document(team_id))
            team_doc = team_ref.get()
            
            if team_doc.exists:
                team_data = team_doc.to_dict()
                return team_data.get('trading_block', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting trading block for team {team_id}: {e}")
            return []
    
    def update_trading_block(self, league_id: str, team_id: str, 
                           player_ids: List[int]) -> Dict[str, Any]:
        """Update a team's trading block."""
        try:
            team_ref = (self.db.collection('leagues').document(league_id)
                       .collection('teams').document(team_id))
            
            team_ref.update({
                'trading_block': player_ids,
                'trading_block_updated_at': datetime.utcnow()
            })
            
            # Broadcast update
            self.socketio.emit('trading_block_updated', {
                'league_id': league_id,
                'team_id': team_id,
                'player_ids': player_ids
            }, room=f'league_{league_id}')
            
            return {'success': True, 'message': 'Trading block updated'}
            
        except Exception as e:
            logger.error(f"Error updating trading block for team {team_id}: {e}")
            return {'success': False, 'error': 'Failed to update trading block'}
    
    def _validate_trade_players(self, league_id: str, proposer_team_id: str, 
                               receiver_team_id: str, proposer_players: List[int], 
                               receiver_players: List[int]) -> Dict[str, Any]:
        """Validate that players belong to the correct teams."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            # Get team rosters
            proposer_team = team_model.get_team(league_id, proposer_team_id)
            receiver_team = team_model.get_team(league_id, receiver_team_id)
            
            if not proposer_team or not receiver_team:
                return {'valid': False, 'error': 'One or both teams not found'}
            
            # Get all players on each team
            proposer_roster = proposer_team.get('roster', {})
            receiver_roster = receiver_team.get('roster', {})
            
            proposer_all_players = (proposer_roster.get('starters', []) + 
                                  proposer_roster.get('bench', []))
            receiver_all_players = (receiver_roster.get('starters', []) + 
                                  receiver_roster.get('bench', []))
            
            # Validate proposer players
            for player_id in proposer_players:
                if player_id not in proposer_all_players:
                    return {
                        'valid': False, 
                        'error': f'Player {player_id} not on proposer team roster'
                    }
            
            # Validate receiver players
            for player_id in receiver_players:
                if player_id not in receiver_all_players:
                    return {
                        'valid': False, 
                        'error': f'Player {player_id} not on receiver team roster'
                    }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating trade players: {e}")
            return {'valid': False, 'error': 'Validation failed'}
    
    def _validate_trade_acceptance(self, trade: Dict[str, Any], 
                                  accepting_team_id: str) -> Dict[str, Any]:
        """Validate that a trade can be accepted."""
        try:
            # Check trade status
            if trade['status'] != 'pending':
                return {'valid': False, 'error': 'Trade is not pending'}
            
            # Check if trade has expired
            if trade.get('expires_at') and trade['expires_at'] < datetime.utcnow():
                return {'valid': False, 'error': 'Trade has expired'}
            
            # Check if accepting team is the receiver
            if trade['receiver_team_id'] != accepting_team_id:
                return {'valid': False, 'error': 'Only the receiving team can accept this trade'}
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating trade acceptance: {e}")
            return {'valid': False, 'error': 'Validation failed'}
    
    def _execute_trade(self, league_id: str, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual player and pick transfers."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            proposer_team_id = trade['proposer_team_id']
            receiver_team_id = trade['receiver_team_id']
            
            # Transfer proposer players to receiver
            for player_id in trade['proposer_players']:
                # Remove from proposer
                team_model.remove_player_from_roster(league_id, proposer_team_id, player_id)
                # Add to receiver
                team_model.add_player_to_roster(league_id, receiver_team_id, player_id, 'bench')
            
            # Transfer receiver players to proposer
            for player_id in trade['receiver_players']:
                # Remove from receiver
                team_model.remove_player_from_roster(league_id, receiver_team_id, player_id)
                # Add to proposer
                team_model.add_player_to_roster(league_id, proposer_team_id, player_id, 'bench')
            
            # Handle draft picks if any (simplified implementation)
            # TODO: Implement draft pick transfers when draft pick system is ready
            
            # Record transactions for both teams
            transaction_data = {
                'type': 'trade',
                'trade_id': trade['id'],
                'proposer_players': trade['proposer_players'],
                'receiver_players': trade['receiver_players'],
                'proposer_picks': trade.get('proposer_picks', []),
                'receiver_picks': trade.get('receiver_picks', []),
                'status': 'completed'
            }
            
            team_model.add_transaction(league_id, proposer_team_id, transaction_data)
            team_model.add_transaction(league_id, receiver_team_id, transaction_data)
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {'success': False, 'error': 'Failed to execute trade'}
    
    def _expire_trade(self, league_id: str, trade_id: str) -> None:
        """Mark a trade as expired."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('trades').document(trade_id))
            doc_ref.update({
                'status': 'expired',
                'expired_at': datetime.utcnow()
            })
            
            logger.info(f"Trade {trade_id} expired in league {league_id}")
            
        except Exception as e:
            logger.error(f"Error expiring trade {trade_id}: {e}")
    
    def cleanup_expired_trades(self, league_id: str) -> int:
        """Clean up expired trades for a league."""
        try:
            trades_ref = (self.db.collection('leagues').document(league_id)
                         .collection('trades').where('status', '==', 'pending'))
            
            expired_count = 0
            current_time = datetime.utcnow()
            
            for doc in trades_ref.stream():
                trade_data = doc.to_dict()
                
                if (trade_data.get('expires_at') and 
                    trade_data['expires_at'] < current_time):
                    self._expire_trade(league_id, trade_data['id'])
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Expired {expired_count} trades in league {league_id}")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired trades: {e}")
            return 0