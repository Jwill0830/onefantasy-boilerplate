"""
Trade service for managing player trades between teams.
Handles trade proposals, validation, execution, and trade blocks.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from enum import Enum
from firebase_admin import firestore

from .. import get_db, get_socketio
from ..models.trade_model import TradeModel
from ..models.team_model import TeamModel
from ..models.league_model import LeagueModel
from ..services.notification_service import NotificationService
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TradeStatus(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    COMPLETED = "completed"

class TradeService:
    """Service for managing player trades between teams."""
    
    def __init__(self):
        """Initialize trade service with database and socketio clients."""
        self.db = get_db()
        self.socketio = get_socketio()
        self.trade_model = TradeModel()
        self.team_model = TeamModel()
        self.league_model = LeagueModel()
        self.notification_service = NotificationService()

    def propose_trade(self, league_id: str, proposer_team_id: str, target_team_id: str,
                     proposer_players: List[int], target_players: List[int],
                     proposer_user_id: str, message: str = None) -> Dict[str, Any]:
        """
        Propose a trade between two teams.
        
        Args:
            league_id: League identifier
            proposer_team_id: Team making the proposal
            target_team_id: Team receiving the proposal
            proposer_players: List of player FPL IDs from proposer
            target_players: List of player FPL IDs from target team
            proposer_user_id: User ID of proposer
            message: Optional message with trade proposal
            
        Returns:
            Trade proposal result
        """
        try:
            # Validate trade proposal
            validation_result = self._validate_trade_proposal(
                league_id, proposer_team_id, target_team_id, proposer_players, target_players
            )
            
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['reason']}
            
            # Get team details
            proposer_team = self.team_model.get_team(league_id, proposer_team_id)
            target_team = self.team_model.get_team(league_id, target_team_id)
            
            if not proposer_team or not target_team:
                return {'success': False, 'error': 'One or both teams not found'}
            
            # Use trade model to create the trade
            result = self.trade_model.propose_trade(
                league_id, proposer_team_id, target_team_id,
                proposer_players, target_players
            )
            
            if result.get('success'):
                trade_id = result.get('trade_id')
                
                # Send notification to target team
                if self.notification_service and target_team.get('owner_id'):
                    try:
                        # Note: Using sync call - notification service will handle async internally
                        self.notification_service.send_trade_proposal_notification(
                            target_team['owner_id'], {
                                'id': trade_id,
                                'proposer_team_name': proposer_team.get('name', 'Unknown Team'),
                                'league_id': league_id
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error sending trade notification: {str(e)}")
                
                # Emit real-time event
                if self.socketio:
                    self.socketio.emit('trade_proposed', {
                        'trade_id': trade_id,
                        'league_id': league_id,
                        'proposer_team': proposer_team.get('name', 'Unknown Team'),
                        'target_team': target_team.get('name', 'Unknown Team'),
                        'proposer_players': proposer_players,
                        'target_players': target_players
                    }, room=f"league_{league_id}")
                
                logger.info(f"Trade proposed: {proposer_team.get('name')} to {target_team.get('name')}")
                return result
            else:
                return result
            
        except Exception as e:
            logger.error(f"Error proposing trade: {str(e)}")
            return {'success': False, 'error': 'Failed to propose trade'}

    def _validate_trade_proposal(self, league_id: str, proposer_team_id: str, target_team_id: str,
                               proposer_players: List[int], target_players: List[int]) -> Dict[str, Any]:
        """
        Validate a trade proposal.
        
        Args:
            league_id: League identifier
            proposer_team_id: Proposer team ID
            target_team_id: Target team ID
            proposer_players: Player IDs from proposer
            target_players: Player IDs from target
            
        Returns:
            Validation result with status and reason
        """
        try:
            # Basic validation
            if proposer_team_id == target_team_id:
                return {'valid': False, 'reason': 'Cannot trade with yourself'}
            
            if not proposer_players and not target_players:
                return {'valid': False, 'reason': 'Trade must include at least one player'}
            
            if len(proposer_players) > 5 or len(target_players) > 5:
                return {'valid': False, 'reason': 'Maximum 5 players per side in trade'}
            
            # Get teams
            proposer_team = self.team_model.get_team(league_id, proposer_team_id)
            target_team = self.team_model.get_team(league_id, target_team_id)
            
            if not proposer_team or not target_team:
                return {'valid': False, 'reason': 'One or both teams not found'}
            
            # Check trade deadline
            league = self.league_model.get_league(league_id)
            if league and league.get('settings', {}).get('trade_deadline'):
                trade_deadline = league['settings']['trade_deadline']
                if isinstance(trade_deadline, str):
                    trade_deadline = datetime.fromisoformat(trade_deadline)
                if datetime.utcnow() > trade_deadline:
                    return {'valid': False, 'reason': 'Trade deadline has passed'}
            
            # Check if transactions are locked
            if league and league.get('transactions_locked'):
                return {'valid': False, 'reason': 'Transactions are currently locked by commissioner'}
            
            # Validate player ownership
            proposer_roster = proposer_team.get('roster', {})
            target_roster = target_team.get('roster', {})
            
            proposer_all_players = (proposer_roster.get('starters', []) + 
                                  proposer_roster.get('bench', []))
            target_all_players = (target_roster.get('starters', []) + 
                                target_roster.get('bench', []))
            
            for player_id in proposer_players:
                if player_id not in proposer_all_players:
                    return {'valid': False, 'reason': f'Proposer does not own player {player_id}'}
            
            for player_id in target_players:
                if player_id not in target_all_players:
                    return {'valid': False, 'reason': f'Target team does not own player {player_id}'}
            
            # Check roster limits after trade
            roster_check = self._validate_post_trade_rosters(
                proposer_team, target_team, proposer_players, target_players
            )
            
            if not roster_check['valid']:
                return roster_check
            
            return {'valid': True, 'reason': 'Trade proposal is valid'}
            
        except Exception as e:
            logger.error(f"Error validating trade proposal: {str(e)}")
            return {'valid': False, 'reason': f'Validation error: {str(e)}'}

    def _validate_post_trade_rosters(self, proposer_team: Dict, target_team: Dict,
                                   proposer_players: List[int], target_players: List[int]) -> Dict[str, Any]:
        """
        Validate that both teams will have valid rosters after the trade.
        
        Args:
            proposer_team: Proposer team data
            target_team: Target team data
            proposer_players: Players leaving proposer team
            target_players: Players leaving target team
            
        Returns:
            Validation result
        """
        try:
            # Get current rosters
            proposer_roster = proposer_team.get('roster', {})
            target_roster = target_team.get('roster', {})
            
            proposer_all_players = (proposer_roster.get('starters', []) + 
                                  proposer_roster.get('bench', []))
            target_all_players = (target_roster.get('starters', []) + 
                                target_roster.get('bench', []))
            
            # Simulate trade
            new_proposer_players = [p for p in proposer_all_players if p not in proposer_players]
            new_proposer_players.extend([p for p in target_all_players if p in target_players])
            
            new_target_players = [p for p in target_all_players if p not in target_players]
            new_target_players.extend([p for p in proposer_all_players if p in proposer_players])
            
            # Check roster size limits
            max_roster_size = 15  # Standard FPL roster size
            min_roster_size = 11
            
            if len(new_proposer_players) > max_roster_size:
                return {'valid': False, 'reason': 'Proposer roster would exceed maximum size'}
            
            if len(new_target_players) > max_roster_size:
                return {'valid': False, 'reason': 'Target roster would exceed maximum size'}
            
            if len(new_proposer_players) < min_roster_size:
                return {'valid': False, 'reason': 'Proposer roster would be below minimum size'}
            
            if len(new_target_players) < min_roster_size:
                return {'valid': False, 'reason': 'Target roster would be below minimum size'}
            
            # Note: Position validation would require player position data
            # This is a simplified version - full implementation would check GK/DEF/MID/FWD limits
            
            return {'valid': True, 'reason': 'Post-trade rosters are valid'}
            
        except Exception as e:
            logger.error(f"Error validating post-trade rosters: {str(e)}")
            return {'valid': False, 'reason': f'Roster validation error: {str(e)}'}

    def accept_trade(self, league_id: str, trade_id: str, user_id: str) -> Dict[str, Any]:
        """
        Accept a trade proposal.
        
        Args:
            league_id: League identifier
            trade_id: Trade identifier
            user_id: User accepting the trade
            
        Returns:
            Trade acceptance result
        """
        try:
            # Use trade model to accept the trade
            result = self.trade_model.accept_trade(league_id, trade_id, user_id)
            
            if result.get('success'):
                # Send notifications
                trade = self.trade_model.get_trade(league_id, trade_id)
                if trade and self.notification_service:
                    try:
                        # Notify the proposer
                        self.notification_service.send_trade_acceptance_notification(
                            trade.get('proposer_team_id'), trade_id, league_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending acceptance notification: {str(e)}")
                
                # Emit real-time event
                if self.socketio:
                    self.socketio.emit('trade_accepted', {
                        'trade_id': trade_id,
                        'league_id': league_id,
                        'message': 'Trade has been accepted'
                    }, room=f"league_{league_id}")
                
                logger.info(f"Trade {trade_id} accepted by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error accepting trade: {str(e)}")
            return {'success': False, 'error': 'Failed to accept trade'}

    def reject_trade(self, league_id: str, trade_id: str, user_id: str, 
                    reason: str = None) -> Dict[str, Any]:
        """
        Reject a trade proposal.
        
        Args:
            league_id: League identifier
            trade_id: Trade identifier
            user_id: User rejecting the trade
            reason: Optional rejection reason
            
        Returns:
            Trade rejection result
        """
        try:
            # Use trade model to reject the trade
            result = self.trade_model.reject_trade(league_id, trade_id, user_id)
            
            if result.get('success'):
                # Send notification
                trade = self.trade_model.get_trade(league_id, trade_id)
                if trade and self.notification_service:
                    try:
                        # Notify the proposer
                        self.notification_service.send_trade_rejection_notification(
                            trade.get('proposer_team_id'), trade_id, reason, league_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending rejection notification: {str(e)}")
                
                # Emit real-time event
                if self.socketio:
                    self.socketio.emit('trade_rejected', {
                        'trade_id': trade_id,
                        'league_id': league_id,
                        'reason': reason,
                        'message': 'Trade has been rejected'
                    }, room=f"league_{league_id}")
                
                logger.info(f"Trade {trade_id} rejected by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error rejecting trade: {str(e)}")
            return {'success': False, 'error': 'Failed to reject trade'}

    def cancel_trade(self, league_id: str, trade_id: str, user_id: str) -> Dict[str, Any]:
        """
        Cancel a trade proposal (by proposer).
        
        Args:
            league_id: League identifier
            trade_id: Trade identifier
            user_id: User cancelling the trade
            
        Returns:
            Trade cancellation result
        """
        try:
            # Use trade model to cancel the trade
            result = self.trade_model.cancel_trade(league_id, trade_id, user_id)
            
            if result.get('success'):
                # Send notification
                trade = self.trade_model.get_trade(league_id, trade_id)
                if trade and self.notification_service:
                    try:
                        # Notify the target team
                        self.notification_service.send_trade_cancellation_notification(
                            trade.get('receiver_team_id'), trade_id, league_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending cancellation notification: {str(e)}")
                
                # Emit real-time event
                if self.socketio:
                    self.socketio.emit('trade_cancelled', {
                        'trade_id': trade_id,
                        'league_id': league_id,
                        'message': 'Trade has been cancelled'
                    }, room=f"league_{league_id}")
                
                logger.info(f"Trade {trade_id} cancelled by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error cancelling trade: {str(e)}")
            return {'success': False, 'error': 'Failed to cancel trade'}

    def get_active_trades(self, league_id: str, team_id: str = None) -> List[Dict[str, Any]]:
        """
        Get active trades for a league or team.
        
        Args:
            league_id: League identifier
            team_id: Optional team filter
            
        Returns:
            List of active trades
        """
        try:
            return self.trade_model.get_active_trades(league_id, team_id)
        except Exception as e:
            logger.error(f"Error getting active trades: {str(e)}")
            return []

    def get_trade_history(self, league_id: str, team_id: str = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get trade history for a league or team.
        
        Args:
            league_id: League identifier
            team_id: Optional team filter
            limit: Maximum number of trades
            
        Returns:
            List of historical trades
        """
        try:
            return self.trade_model.get_trade_history(league_id, team_id, limit)
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return []

    def get_trading_block(self, league_id: str, team_id: str) -> List[Dict[str, Any]]:
        """Get players on a team's trading block."""
        try:
            return self.trade_model.get_team_trading_block(league_id, team_id)
        except Exception as e:
            logger.error(f"Error getting trading block: {str(e)}")
            return []

    def update_trading_block(self, league_id: str, team_id: str, 
                           player_ids: List[int], user_id: str) -> Dict[str, Any]:
        """
        Update a team's trading block.
        
        Args:
            league_id: League identifier
            team_id: Team identifier
            player_ids: List of player IDs on trading block
            user_id: User updating the trading block
            
        Returns:
            Update result
        """
        try:
            # Verify user owns the team
            team = self.team_model.get_team(league_id, team_id)
            if not team or team.get('owner_id') != user_id:
                return {'success': False, 'error': 'You do not own this team'}
            
            # Update trading block using trade model
            result = self.trade_model.update_trading_block(league_id, team_id, player_ids)
            
            if result.get('success') and self.socketio:
                # Emit real-time update
                self.socketio.emit('trading_block_updated', {
                    'league_id': league_id,
                    'team_id': team_id,
                    'player_ids': player_ids,
                    'team_name': team.get('name', 'Unknown Team')
                }, room=f"league_{league_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating trading block: {str(e)}")
            return {'success': False, 'error': 'Failed to update trading block'}

    def get_league_trading_block(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get all players on trading blocks in a league.
        
        Args:
            league_id: League identifier
            
        Returns:
            List of players on trading blocks
        """
        try:
            # Get all teams in league
            teams = self.team_model.get_league_teams(league_id)
            if not teams:
                return []
            
            all_trading_block_players = []
            
            for team in teams:
                team_id = team['id']
                trading_block = self.trade_model.get_team_trading_block(league_id, team_id)
                
                # Add team info to each player
                for player_id in trading_block:
                    # Get player details from team roster
                    roster = team.get('roster', {})
                    all_players = roster.get('starters', []) + roster.get('bench', [])
                    
                    for player in all_players:
                        if player == player_id:  # Assuming player_id is the actual player data
                            player_info = {
                                'team_id': team_id,
                                'team_name': team.get('name', 'Unknown Team'),
                                'owner_id': team.get('owner_id'),
                                'player_id': player_id,
                                'added_to_block': datetime.utcnow()  # This would be stored in a real implementation
                            }
                            all_trading_block_players.append(player_info)
                            break
            
            return all_trading_block_players
            
        except Exception as e:
            logger.error(f"Error getting league trading block: {str(e)}")
            return []

    def process_trade_deadlines(self) -> Dict[str, Any]:
        """
        Process trade deadline enforcement across all leagues.
        
        Returns:
            Processing summary
        """
        try:
            current_time = datetime.utcnow()
            leagues_processed = 0
            trades_cancelled = 0
            
            # This would be more sophisticated in a real implementation
            # For now, just log that the process ran
            logger.info("Trade deadline processing completed")
            
            return {
                'success': True,
                'leagues_processed': leagues_processed,
                'trades_cancelled': trades_cancelled,
                'processed_at': current_time
            }
            
        except Exception as e:
            logger.error(f"Error processing trade deadlines: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_trade_analytics(self, league_id: str) -> Dict[str, Any]:
        """
        Get trade analytics for a league.
        
        Args:
            league_id: League identifier
            
        Returns:
            Trade analytics data
        """
        try:
            # Get all trades in league
            all_trades = self.trade_model.get_trade_history(league_id, limit=1000)
            
            # Calculate analytics
            total_trades = len(all_trades)
            completed_trades = len([t for t in all_trades if t.get('status') == 'accepted'])
            pending_trades = len([t for t in all_trades if t.get('status') == 'pending'])
            rejected_trades = len([t for t in all_trades if t.get('status') == 'rejected'])
            
            # Calculate success rate
            proposed_trades = completed_trades + rejected_trades
            success_rate = (completed_trades / proposed_trades * 100) if proposed_trades > 0 else 0
            
            # Most active traders
            trader_activity = {}
            for trade in all_trades:
                proposer = trade.get('proposer_team_id')
                if proposer:
                    trader_activity[proposer] = trader_activity.get(proposer, 0) + 1
            
            most_active = sorted(trader_activity.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'total_trades': total_trades,
                'completed_trades': completed_trades,
                'pending_trades': pending_trades,
                'rejected_trades': rejected_trades,
                'success_rate': round(success_rate, 1),
                'most_active_traders': most_active,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting trade analytics: {str(e)}")
            return {'error': str(e)}

    def validate_trade_fairness(self, league_id: str, proposer_players: List[int], 
                               target_players: List[int]) -> Dict[str, Any]:
        """
        Validate trade fairness based on player values (basic implementation).
        
        Args:
            league_id: League identifier
            proposer_players: Players from proposer
            target_players: Players from target
            
        Returns:
            Fairness assessment
        """
        try:
            # This is a simplified implementation
            # In a real system, you'd calculate actual player values
            
            proposer_value = len(proposer_players) * 50  # Dummy calculation
            target_value = len(target_players) * 50
            
            value_difference = abs(proposer_value - target_value)
            percentage_difference = (value_difference / max(proposer_value, target_value)) * 100
            
            is_fair = percentage_difference <= 20  # 20% threshold
            
            return {
                'is_fair': is_fair,
                'proposer_value': proposer_value,
                'target_value': target_value,
                'value_difference': value_difference,
                'percentage_difference': round(percentage_difference, 1),
                'fairness_threshold': 20
            }
            
        except Exception as e:
            logger.error(f"Error validating trade fairness: {str(e)}")
            return {'error': str(e)}

    def cleanup_expired_trades(self) -> int:
        """
        Clean up expired trades.
        
        Returns:
            Number of trades cleaned up
        """
        try:
            current_time = datetime.utcnow()
            expired_count = 0
            
            # Get all active trades
            # This would need to be implemented in the trade model
            # For now, just return 0
            
            logger.info(f"Cleaned up {expired_count} expired trades")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired trades: {str(e)}")
            return 0