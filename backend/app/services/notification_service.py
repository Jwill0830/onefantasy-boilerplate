"""
Notification service for managing user notifications across the platform.
Handles real-time notifications, email alerts, and notification preferences.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from enum import Enum
import json
from firebase_admin import firestore

from .. import get_db, get_socketio
from ..utils.logger import get_logger

logger = get_logger(__name__)

class NotificationType(Enum):
    TRADE_PROPOSAL = "trade_proposal"
    TRADE_ACCEPTED = "trade_accepted"
    TRADE_REJECTED = "trade_rejected"
    TRADE_CANCELLED = "trade_cancelled"
    TRADE_EXPIRED = "trade_expired"
    TRADE_EXECUTED = "trade_executed"
    COMMISSIONER_DECISION = "commissioner_decision"
    DRAFT_STARTING = "draft_starting"
    DRAFT_PICK_TURN = "draft_pick_turn"
    DRAFT_COMPLETED = "draft_completed"
    WAIVER_CLAIM_WON = "waiver_claim_won"
    WAIVER_CLAIM_LOST = "waiver_claim_lost"
    MATCHUP_REMINDER = "matchup_reminder"
    LINEUP_REMINDER = "lineup_reminder"
    SCORING_UPDATE = "scoring_update"
    LEAGUE_INVITE = "league_invite"
    LEAGUE_UPDATE = "league_update"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    DIRECT_MESSAGE = "direct_message"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationService:
    """Service for managing user notifications and preferences."""
    
    def __init__(self):
        """Initialize notification service with database and socketio clients."""
        self.db = get_db()
        self.socketio = get_socketio()
        
        # Default notification preferences
        self.default_preferences = {
            NotificationType.TRADE_PROPOSAL.value: {'push': True, 'email': True},
            NotificationType.TRADE_ACCEPTED.value: {'push': True, 'email': True},
            NotificationType.TRADE_REJECTED.value: {'push': True, 'email': False},
            NotificationType.TRADE_CANCELLED.value: {'push': True, 'email': False},
            NotificationType.TRADE_EXPIRED.value: {'push': True, 'email': False},
            NotificationType.TRADE_EXECUTED.value: {'push': True, 'email': True},
            NotificationType.COMMISSIONER_DECISION.value: {'push': True, 'email': True},
            NotificationType.DRAFT_STARTING.value: {'push': True, 'email': True},
            NotificationType.DRAFT_PICK_TURN.value: {'push': True, 'email': False},
            NotificationType.DRAFT_COMPLETED.value: {'push': True, 'email': True},
            NotificationType.WAIVER_CLAIM_WON.value: {'push': True, 'email': True},
            NotificationType.WAIVER_CLAIM_LOST.value: {'push': True, 'email': False},
            NotificationType.MATCHUP_REMINDER.value: {'push': True, 'email': True},
            NotificationType.LINEUP_REMINDER.value: {'push': True, 'email': True},
            NotificationType.SCORING_UPDATE.value: {'push': False, 'email': False},
            NotificationType.LEAGUE_INVITE.value: {'push': True, 'email': True},
            NotificationType.LEAGUE_UPDATE.value: {'push': True, 'email': False},
            NotificationType.SYSTEM_ANNOUNCEMENT.value: {'push': True, 'email': True},
            NotificationType.DIRECT_MESSAGE.value: {'push': True, 'email': False}
        }

    async def send_notification(self, user_id: str, notification_type: NotificationType,
                              title: str, message: str, data: Dict[str, Any] = None,
                              priority: NotificationPriority = NotificationPriority.MEDIUM,
                              league_id: str = None) -> str:
        """
        Send a notification to a user.
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional notification data
            priority: Notification priority
            league_id: Associated league (optional)
            
        Returns:
            Notification ID
        """
        try:
            # Check user notification preferences
            preferences = await self._get_user_preferences(user_id)
            type_preferences = preferences.get(notification_type.value, 
                                             self.default_preferences.get(notification_type.value, {}))
            
            # Create notification document
            notification_data = {
                'user_id': user_id,
                'type': notification_type.value,
                'title': title,
                'message': message,
                'data': data or {},
                'priority': priority.value,
                'league_id': league_id,
                'read': False,
                'created_at': firestore.SERVER_TIMESTAMP,
                'expires_at': datetime.utcnow() + timedelta(days=30)  # 30 day expiry
            }
            
            # Save to database
            doc_ref = (self.db.collection('users').document(user_id)
                      .collection('notifications').document())
            doc_ref.set(notification_data)
            notification_id = doc_ref.id
            
            # Add ID to notification data for real-time emission
            notification_data['id'] = notification_id
            
            # Send real-time notification if enabled
            if type_preferences.get('push', True) and self.socketio:
                await self._send_realtime_notification(user_id, notification_data)
            
            # Send email notification if enabled
            if type_preferences.get('email', False):
                await self._send_email_notification(user_id, notification_data)
            
            logger.info(f"Sent {notification_type.value} notification to user {user_id}")
            return notification_id
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            raise

    async def _send_realtime_notification(self, user_id: str, notification_data: Dict[str, Any]) -> None:
        """Send real-time notification via SocketIO."""
        try:
            if self.socketio:
                # Prepare data for real-time emission
                realtime_data = {
                    'id': notification_data.get('id'),
                    'type': notification_data['type'],
                    'title': notification_data['title'],
                    'message': notification_data['message'],
                    'priority': notification_data['priority'],
                    'data': notification_data['data'],
                    'league_id': notification_data.get('league_id'),
                    'created_at': datetime.utcnow().isoformat()
                }
                
                self.socketio.emit('notification', realtime_data, room=f"user_{user_id}")
                
                # Also emit to league room if applicable
                if notification_data.get('league_id'):
                    self.socketio.emit('league_notification', realtime_data, 
                                     room=f"league_{notification_data['league_id']}")
                
        except Exception as e:
            logger.error(f"Error sending real-time notification: {str(e)}")

    async def _send_email_notification(self, user_id: str, notification_data: Dict[str, Any]) -> None:
        """Send email notification (placeholder for email service integration)."""
        try:
            # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
            # For now, just log the email notification
            logger.info(f"Email notification queued for user {user_id}: {notification_data['title']}")
            
            # Store email notification task for later processing
            email_task = {
                'user_id': user_id,
                'notification_data': notification_data,
                'created_at': firestore.SERVER_TIMESTAMP,
                'status': 'queued',
                'attempts': 0,
                'max_attempts': 3
            }
            
            self.db.collection('email_queue').document().set(email_task)
            
        except Exception as e:
            logger.error(f"Error queueing email notification: {str(e)}")

    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user notification preferences."""
        try:
            doc = (self.db.collection('users').document(user_id)
                  .collection('settings').document('notifications').get())
            
            if doc.exists:
                return doc.to_dict().get('preferences', {})
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return {}

    def get_user_notifications(self, user_id: str, unread_only: bool = False,
                             limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User identifier
            unread_only: Only return unread notifications
            limit: Maximum number of notifications
            
        Returns:
            List of notifications
        """
        try:
            query = (self.db.collection('users').document(user_id)
                    .collection('notifications')
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            if unread_only:
                query = query.where('read', '==', False)
            
            docs = query.stream()
            notifications = []
            
            for doc in docs:
                notification_data = doc.to_dict()
                notification_data['id'] = doc.id
                
                # Convert timestamps to ISO format for JSON serialization
                if 'created_at' in notification_data and notification_data['created_at']:
                    notification_data['created_at'] = notification_data['created_at'].isoformat()
                if 'expires_at' in notification_data and notification_data['expires_at']:
                    notification_data['expires_at'] = notification_data['expires_at'].isoformat()
                if 'read_at' in notification_data and notification_data['read_at']:
                    notification_data['read_at'] = notification_data['read_at'].isoformat()
                
                notifications.append(notification_data)
            
            logger.info(f"Retrieved {len(notifications)} notifications for user {user_id}")
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return []

    def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """
        Mark a notification as read.
        
        Args:
            user_id: User identifier
            notification_id: Notification identifier
            
        Returns:
            Success status
        """
        try:
            (self.db.collection('users').document(user_id)
             .collection('notifications').document(notification_id)
             .update({'read': True, 'read_at': firestore.SERVER_TIMESTAMP}))
            
            logger.info(f"Marked notification {notification_id} as read for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False

    def mark_all_notifications_read(self, user_id: str) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of notifications marked as read
        """
        try:
            unread_notifications = (self.db.collection('users').document(user_id)
                                   .collection('notifications')
                                   .where('read', '==', False).stream())
            
            batch = self.db.batch()
            count = 0
            
            for doc in unread_notifications:
                batch.update(doc.reference, {
                    'read': True,
                    'read_at': firestore.SERVER_TIMESTAMP
                })
                count += 1
                
                # Commit in batches of 500
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining updates
            if count % 500 != 0:
                batch.commit()
            
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0

    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """
        Delete a notification.
        
        Args:
            user_id: User identifier
            notification_id: Notification identifier
            
        Returns:
            Success status
        """
        try:
            (self.db.collection('users').document(user_id)
             .collection('notifications').document(notification_id).delete())
            
            logger.info(f"Deleted notification {notification_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return False

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user notification preferences.
        
        Args:
            user_id: User identifier
            preferences: New preference settings
            
        Returns:
            Success status
        """
        try:
            settings_data = {
                'preferences': preferences,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            (self.db.collection('users').document(user_id)
             .collection('settings').document('notifications')
             .set(settings_data, merge=True))
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {str(e)}")
            return False

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user notification preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            User preferences with defaults
        """
        try:
            doc = (self.db.collection('users').document(user_id)
                  .collection('settings').document('notifications').get())
            
            if doc.exists:
                user_prefs = doc.to_dict().get('preferences', {})
            else:
                user_prefs = {}
            
            # Merge with defaults
            merged_prefs = {}
            for notif_type, default_settings in self.default_preferences.items():
                merged_prefs[notif_type] = user_prefs.get(notif_type, default_settings)
            
            return merged_prefs
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return self.default_preferences.copy()

    # Specific notification methods

    async def send_trade_proposal_notification(self, target_user_id: str, trade: Dict[str, Any]) -> str:
        """Send trade proposal notification."""
        return await self.send_notification(
            target_user_id,
            NotificationType.TRADE_PROPOSAL,
            "New Trade Proposal",
            f"{trade.get('proposer_team_name', 'A team')} has proposed a trade",
            {'trade_id': trade.get('id'), 'proposer_team': trade.get('proposer_team_name')},
            NotificationPriority.HIGH,
            trade.get('league_id')
        )

    async def send_trade_acceptance_notification(self, proposer_user_id: str, trade_id: str, 
                                               league_id: str = None) -> str:
        """Send trade acceptance notification."""
        return await self.send_notification(
            proposer_user_id,
            NotificationType.TRADE_ACCEPTED,
            "Trade Accepted",
            "Your trade proposal has been accepted",
            {'trade_id': trade_id},
            NotificationPriority.HIGH,
            league_id
        )

    async def send_trade_rejection_notification(self, proposer_user_id: str, 
                                              trade_id: str, reason: str = None,
                                              league_id: str = None) -> str:
        """Send trade rejection notification."""
        message = "Your trade proposal has been rejected"
        if reason:
            message += f": {reason}"
            
        return await self.send_notification(
            proposer_user_id,
            NotificationType.TRADE_REJECTED,
            "Trade Rejected",
            message,
            {'trade_id': trade_id, 'reason': reason},
            NotificationPriority.MEDIUM,
            league_id
        )

    async def send_trade_cancellation_notification(self, target_user_id: str, trade_id: str,
                                                  league_id: str = None) -> str:
        """Send trade cancellation notification."""
        return await self.send_notification(
            target_user_id,
            NotificationType.TRADE_CANCELLED,
            "Trade Cancelled",
            "A trade proposal has been cancelled",
            {'trade_id': trade_id},
            NotificationPriority.MEDIUM,
            league_id
        )

    async def send_trade_expiry_notification(self, proposer_user_id: str, trade_id: str,
                                           league_id: str = None) -> str:
        """Send trade expiry notification."""
        return await self.send_notification(
            proposer_user_id,
            NotificationType.TRADE_EXPIRED,
            "Trade Expired",
            "Your trade proposal has expired",
            {'trade_id': trade_id},
            NotificationPriority.LOW,
            league_id
        )

    async def send_trade_execution_notification(self, user_id: str, trade: Dict[str, Any]) -> str:
        """Send trade execution notification."""
        return await self.send_notification(
            user_id,
            NotificationType.TRADE_EXECUTED,
            "Trade Completed",
            f"Trade with {trade.get('other_team_name', 'another team')} has been completed",
            {'trade_id': trade.get('id')},
            NotificationPriority.HIGH,
            trade.get('league_id')
        )

    async def send_trade_approval_notification(self, commissioner_id: str, trade_id: str,
                                             league_id: str = None) -> str:
        """Send trade approval request to commissioner."""
        return await self.send_notification(
            commissioner_id,
            NotificationType.COMMISSIONER_DECISION,
            "Trade Approval Required",
            "A trade requires your approval as commissioner",
            {'trade_id': trade_id, 'action_required': True},
            NotificationPriority.HIGH,
            league_id
        )

    async def send_commissioner_decision_notification(self, user_id: str, trade_id: str,
                                                    approved: bool, notes: str = None,
                                                    league_id: str = None) -> str:
        """Send commissioner decision notification."""
        title = "Trade Approved" if approved else "Trade Rejected"
        message = f"Commissioner has {'approved' if approved else 'rejected'} the trade"
        if notes:
            message += f": {notes}"
            
        return await self.send_notification(
            user_id,
            NotificationType.COMMISSIONER_DECISION,
            title,
            message,
            {'trade_id': trade_id, 'approved': approved, 'notes': notes},
            NotificationPriority.HIGH,
            league_id
        )

    async def send_commissioner_notification(self, user_id: str, league_id: str, message: str) -> str:
        """Send general commissioner notification."""
        return await self.send_notification(
            user_id,
            NotificationType.COMMISSIONER_DECISION,
            "Commissioner Update",
            message,
            {'league_id': league_id},
            NotificationPriority.HIGH,
            league_id
        )

    async def send_draft_starting_notification(self, user_id: str, draft_id: str, 
                                             league_id: str, start_time: datetime) -> str:
        """Send draft starting notification."""
        return await self.send_notification(
            user_id,
            NotificationType.DRAFT_STARTING,
            "Draft Starting Soon",
            f"Your draft starts at {start_time.strftime('%Y-%m-%d %H:%M')}",
            {'draft_id': draft_id, 'start_time': start_time.isoformat()},
            NotificationPriority.HIGH,
            league_id
        )

    async def send_draft_pick_notification(self, user_id: str, draft_id: str, 
                                         pick_number: int, league_id: str) -> str:
        """Send draft pick turn notification."""
        return await self.send_notification(
            user_id,
            NotificationType.DRAFT_PICK_TURN,
            "Your Turn to Pick",
            f"It's your turn to make pick #{pick_number}",
            {'draft_id': draft_id, 'pick_number': pick_number},
            NotificationPriority.URGENT,
            league_id
        )

    async def send_draft_completed_notification(self, user_id: str, draft_id: str, 
                                              league_id: str) -> str:
        """Send draft completion notification."""
        return await self.send_notification(
            user_id,
            NotificationType.DRAFT_COMPLETED,
            "Draft Completed",
            "Your league draft has been completed",
            {'draft_id': draft_id},
            NotificationPriority.MEDIUM,
            league_id
        )

    async def send_waiver_claim_result_notification(self, user_id: str, player_name: str,
                                                   won: bool, league_id: str) -> str:
        """Send waiver claim result notification."""
        if won:
            return await self.send_notification(
                user_id,
                NotificationType.WAIVER_CLAIM_WON,
                "Waiver Claim Won",
                f"You successfully claimed {player_name}",
                {'player_name': player_name, 'result': 'won'},
                NotificationPriority.HIGH,
                league_id
            )
        else:
            return await self.send_notification(
                user_id,
                NotificationType.WAIVER_CLAIM_LOST,
                "Waiver Claim Lost",
                f"Your claim for {player_name} was unsuccessful",
                {'player_name': player_name, 'result': 'lost'},
                NotificationPriority.MEDIUM,
                league_id
            )

    async def send_lineup_reminder_notification(self, user_id: str, league_id: str, 
                                              gameweek: int, deadline: datetime) -> str:
        """Send lineup reminder notification."""
        return await self.send_notification(
            user_id,
            NotificationType.LINEUP_REMINDER,
            "Set Your Lineup",
            f"Don't forget to set your lineup for Gameweek {gameweek}",
            {'gameweek': gameweek, 'deadline': deadline.isoformat()},
            NotificationPriority.HIGH,
            league_id
        )

    async def send_matchup_reminder_notification(self, user_id: str, opponent_team: str,
                                               league_id: str, gameweek: int) -> str:
        """Send matchup reminder notification."""
        return await self.send_notification(
            user_id,
            NotificationType.MATCHUP_REMINDER,
            "Matchup This Week",
            f"You're playing against {opponent_team} in Gameweek {gameweek}",
            {'opponent_team': opponent_team, 'gameweek': gameweek},
            NotificationPriority.MEDIUM,
            league_id
        )

    async def send_scoring_update_notification(self, user_id: str, points: int,
                                             league_id: str, gameweek: int) -> str:
        """Send scoring update notification."""
        return await self.send_notification(
            user_id,
            NotificationType.SCORING_UPDATE,
            "Scoring Update",
            f"You scored {points} points in Gameweek {gameweek}",
            {'points': points, 'gameweek': gameweek},
            NotificationPriority.LOW,
            league_id
        )

    async def send_league_invite_notification(self, user_id: str, league_name: str,
                                            inviter_name: str, league_id: str) -> str:
        """Send league invitation notification."""
        return await self.send_notification(
            user_id,
            NotificationType.LEAGUE_INVITE,
            "League Invitation",
            f"{inviter_name} invited you to join {league_name}",
            {'league_name': league_name, 'inviter_name': inviter_name, 'league_id': league_id},
            NotificationPriority.HIGH
        )

    async def send_direct_message_notification(self, user_id: str, sender_name: str,
                                             message_preview: str, sender_id: str = None) -> str:
        """Send direct message notification."""
        return await self.send_notification(
            user_id,
            NotificationType.DIRECT_MESSAGE,
            f"Message from {sender_name}",
            message_preview[:100] + "..." if len(message_preview) > 100 else message_preview,
            {'sender_name': sender_name, 'sender_id': sender_id},
            NotificationPriority.MEDIUM
        )

    async def send_system_announcement(self, user_id: str, title: str, message: str,
                                     data: Dict[str, Any] = None) -> str:
        """Send system announcement notification."""
        return await self.send_notification(
            user_id,
            NotificationType.SYSTEM_ANNOUNCEMENT,
            title,
            message,
            data,
            NotificationPriority.MEDIUM
        )

    async def broadcast_league_notification(self, league_id: str, notification_type: NotificationType,
                                          title: str, message: str, data: Dict[str, Any] = None,
                                          exclude_user_ids: List[str] = None) -> List[str]:
        """
        Send notification to all members of a league.
        
        Args:
            league_id: League identifier
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data
            exclude_user_ids: User IDs to exclude from broadcast
            
        Returns:
            List of notification IDs
        """
        try:
            # Get all league members
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            teams = team_model.get_league_teams(league_id)
            
            notification_ids = []
            exclude_user_ids = exclude_user_ids or []
            
            for team in teams:
                owner_id = team.get('owner_id')
                if owner_id and owner_id not in exclude_user_ids:
                    try:
                        notification_id = await self.send_notification(
                            owner_id,
                            notification_type,
                            title,
                            message,
                            data,
                            NotificationPriority.MEDIUM,
                            league_id
                        )
                        notification_ids.append(notification_id)
                    except Exception as e:
                        logger.error(f"Error sending notification to user {owner_id}: {str(e)}")
            
            logger.info(f"Broadcast {len(notification_ids)} notifications to league {league_id}")
            return notification_ids
            
        except Exception as e:
            logger.error(f"Error broadcasting league notification: {str(e)}")
            return []

    def cleanup_expired_notifications(self, days_old: int = 30) -> int:
        """
        Clean up expired notifications.
        
        Args:
            days_old: Remove notifications older than this many days
            
        Returns:
            Number of notifications cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # This is a simplified version - in production, you'd want to batch this
            # across all users to avoid timeouts
            deleted_count = 0
            
            # Get all users (limit for performance)
            users = self.db.collection('users').limit(100).stream()
            
            for user_doc in users:
                user_id = user_doc.id
                
                # Get expired notifications for this user
                expired_notifications = (self.db.collection('users').document(user_id)
                                        .collection('notifications')
                                        .where('created_at', '<', cutoff_date).stream())
                
                batch = self.db.batch()
                user_deleted = 0
                
                for notification_doc in expired_notifications:
                    batch.delete(notification_doc.reference)
                    user_deleted += 1
                    
                    # Commit in batches of 500
                    if user_deleted % 500 == 0:
                        batch.commit()
                        batch = self.db.batch()
                
                # Commit remaining deletions for this user
                if user_deleted % 500 != 0:
                    batch.commit()
                
                deleted_count += user_deleted
            
            logger.info(f"Cleaned up {deleted_count} expired notifications")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired notifications: {str(e)}")
            return 0

    def get_notification_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get notification statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Notification statistics
        """
        try:
            # Get total notifications
            total_query = (self.db.collection('users').document(user_id)
                          .collection('notifications'))
            total_docs = list(total_query.stream())
            total_count = len(total_docs)
            
            # Get unread count
            unread_count = len([doc for doc in total_docs 
                              if not doc.to_dict().get('read', False)])
            
            # Get recent notifications (last 7 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_count = len([doc for doc in total_docs 
                              if doc.to_dict().get('created_at', datetime.min) >= recent_cutoff])
            
            # Group by type
            type_counts = {}
            for doc in total_docs:
                notif_type = doc.to_dict().get('type', 'unknown')
                type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
            
            return {
                'total_notifications': total_count,
                'unread_count': unread_count,
                'recent_count': recent_count,
                'by_type': type_counts,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {str(e)}")
            return {
                'total_notifications': 0,
                'unread_count': 0,
                'recent_count': 0,
                'by_type': {},
                'error': str(e)
            }