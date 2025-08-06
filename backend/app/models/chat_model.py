"""
Chat model for handling league chat messages and direct messages.
Manages message storage, retrieval, and real-time updates.
"""

from google.cloud import firestore
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ChatModel:
    def __init__(self, db: firestore.Client):
        """Initialize chat model with Firestore client."""
        self.db = db
        self.collection = 'chats'
        self.dm_collection = 'direct_messages'

    def create_league_message(self, league_id: str, user_id: str, username: str, 
                            message: str, message_type: str = 'general') -> Dict[str, Any]:
        """
        Create a new league chat message.
        
        Args:
            league_id: League identifier
            user_id: User who sent the message
            username: Display name of user
            message: Message content
            message_type: Type of message (general, draft_pick, trade, etc.)
            
        Returns:
            Created message document
        """
        try:
            message_data = {
                'league_id': league_id,
                'user_id': user_id,
                'username': username,
                'message': message,
                'message_type': message_type,
                'timestamp': datetime.utcnow(),
                'edited': False,
                'edited_at': None,
                'reactions': {}  # {emoji: [user_ids]}
            }
            
            # Add to league chat subcollection
            doc_ref = self.db.collection('leagues').document(league_id)\
                        .collection('chat').document()
            doc_ref.set(message_data)
            
            message_data['id'] = doc_ref.id
            logger.info(f"Created league message in {league_id} by {username}")
            return message_data
            
        except Exception as e:
            logger.error(f"Error creating league message: {str(e)}")
            raise

    def get_league_messages(self, league_id: str, limit: int = 50, 
                          last_message_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent league chat messages with pagination.
        
        Args:
            league_id: League identifier
            limit: Maximum number of messages to return
            last_message_id: Last message ID for pagination
            
        Returns:
            List of message documents
        """
        try:
            query = self.db.collection('leagues').document(league_id)\
                      .collection('chat')\
                      .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                      .limit(limit)
            
            if last_message_id:
                last_doc = self.db.collection('leagues').document(league_id)\
                            .collection('chat').document(last_message_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            messages = []
            
            for doc in docs:
                message_data = doc.to_dict()
                message_data['id'] = doc.id
                messages.append(message_data)
                
            # Reverse to show oldest first
            messages.reverse()
            logger.info(f"Retrieved {len(messages)} messages for league {league_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting league messages: {str(e)}")
            raise

    def create_direct_message(self, sender_id: str, sender_username: str,
                            recipient_id: str, message: str) -> Dict[str, Any]:
        """
        Create a direct message between two users.
        
        Args:
            sender_id: User ID of sender
            sender_username: Display name of sender
            recipient_id: User ID of recipient
            message: Message content
            
        Returns:
            Created direct message document
        """
        try:
            # Create conversation ID (consistent ordering)
            conversation_id = '_'.join(sorted([sender_id, recipient_id]))
            
            message_data = {
                'conversation_id': conversation_id,
                'sender_id': sender_id,
                'sender_username': sender_username,
                'recipient_id': recipient_id,
                'message': message,
                'timestamp': datetime.utcnow(),
                'read': False,
                'edited': False,
                'edited_at': None
            }
            
            # Add to direct messages subcollection
            doc_ref = self.db.collection('direct_messages')\
                        .document(conversation_id)\
                        .collection('messages').document()
            doc_ref.set(message_data)
            
            # Update conversation metadata
            conversation_data = {
                'participants': [sender_id, recipient_id],
                'last_message': message,
                'last_message_timestamp': message_data['timestamp'],
                'last_sender': sender_id,
                'updated_at': datetime.utcnow()
            }
            
            self.db.collection('direct_messages')\
                   .document(conversation_id).set(conversation_data, merge=True)
            
            message_data['id'] = doc_ref.id
            logger.info(f"Created DM from {sender_username} to {recipient_id}")
            return message_data
            
        except Exception as e:
            logger.error(f"Error creating direct message: {str(e)}")
            raise

    def get_direct_messages(self, user1_id: str, user2_id: str, 
                          limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get direct messages between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            limit: Maximum number of messages
            
        Returns:
            List of direct messages
        """
        try:
            conversation_id = '_'.join(sorted([user1_id, user2_id]))
            
            docs = self.db.collection('direct_messages')\
                     .document(conversation_id)\
                     .collection('messages')\
                     .order_by('timestamp', direction=firestore.Query.ASCENDING)\
                     .limit(limit).stream()
            
            messages = []
            for doc in docs:
                message_data = doc.to_dict()
                message_data['id'] = doc.id
                messages.append(message_data)
                
            logger.info(f"Retrieved {len(messages)} DMs for conversation {conversation_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting direct messages: {str(e)}")
            raise

    def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation metadata
        """
        try:
            docs = self.db.collection('direct_messages')\
                     .where('participants', 'array_contains', user_id)\
                     .order_by('updated_at', direction=firestore.Query.DESCENDING)\
                     .stream()
            
            conversations = []
            for doc in docs:
                conversation_data = doc.to_dict()
                conversation_data['id'] = doc.id
                conversations.append(conversation_data)
                
            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            raise

    def add_message_reaction(self, league_id: str, message_id: str, 
                           user_id: str, emoji: str) -> bool:
        """
        Add reaction to a league message.
        
        Args:
            league_id: League identifier
            message_id: Message identifier
            user_id: User adding reaction
            emoji: Emoji reaction
            
        Returns:
            Success status
        """
        try:
            message_ref = self.db.collection('leagues').document(league_id)\
                            .collection('chat').document(message_id)
            
            # Use transaction to safely update reactions
            @firestore.transactional
            def update_reactions(transaction):
                doc = message_ref.get(transaction=transaction)
                if not doc.exists:
                    return False
                    
                data = doc.to_dict()
                reactions = data.get('reactions', {})
                
                if emoji not in reactions:
                    reactions[emoji] = []
                    
                if user_id not in reactions[emoji]:
                    reactions[emoji].append(user_id)
                    
                transaction.update(message_ref, {'reactions': reactions})
                return True
            
            transaction = self.db.transaction()
            success = update_reactions(transaction)
            
            if success:
                logger.info(f"Added reaction {emoji} to message {message_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error adding message reaction: {str(e)}")
            return False

    def remove_message_reaction(self, league_id: str, message_id: str, 
                              user_id: str, emoji: str) -> bool:
        """
        Remove reaction from a league message.
        
        Args:
            league_id: League identifier
            message_id: Message identifier
            user_id: User removing reaction
            emoji: Emoji reaction
            
        Returns:
            Success status
        """
        try:
            message_ref = self.db.collection('leagues').document(league_id)\
                            .collection('chat').document(message_id)
            
            @firestore.transactional
            def remove_reaction(transaction):
                doc = message_ref.get(transaction=transaction)
                if not doc.exists:
                    return False
                    
                data = doc.to_dict()
                reactions = data.get('reactions', {})
                
                if emoji in reactions and user_id in reactions[emoji]:
                    reactions[emoji].remove(user_id)
                    
                    # Remove emoji key if no users left
                    if not reactions[emoji]:
                        del reactions[emoji]
                        
                    transaction.update(message_ref, {'reactions': reactions})
                    return True
                return False
            
            transaction = self.db.transaction()
            success = remove_reaction(transaction)
            
            if success:
                logger.info(f"Removed reaction {emoji} from message {message_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error removing message reaction: {str(e)}")
            return False

    def edit_message(self, league_id: str, message_id: str, user_id: str, 
                    new_message: str) -> bool:
        """
        Edit a league chat message.
        
        Args:
            league_id: League identifier
            message_id: Message identifier
            user_id: User editing message (must be original sender)
            new_message: New message content
            
        Returns:
            Success status
        """
        try:
            message_ref = self.db.collection('leagues').document(league_id)\
                            .collection('chat').document(message_id)
            
            doc = message_ref.get()
            if not doc.exists:
                return False
                
            data = doc.to_dict()
            if data.get('user_id') != user_id:
                logger.warning(f"User {user_id} tried to edit message by {data.get('user_id')}")
                return False
            
            message_ref.update({
                'message': new_message,
                'edited': True,
                'edited_at': datetime.utcnow()
            })
            
            logger.info(f"Edited message {message_id} in league {league_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error editing message: {str(e)}")
            return False

    def mark_direct_messages_read(self, conversation_id: str, user_id: str) -> bool:
        """
        Mark all unread direct messages as read for a user.
        
        Args:
            conversation_id: Conversation identifier
            user_id: User marking messages as read
            
        Returns:
            Success status
        """
        try:
            # Get unread messages where user is recipient
            unread_query = self.db.collection('direct_messages')\
                             .document(conversation_id)\
                             .collection('messages')\
                             .where('recipient_id', '==', user_id)\
                             .where('read', '==', False)
            
            batch = self.db.batch()
            count = 0
            
            for doc in unread_query.stream():
                batch.update(doc.reference, {'read': True})
                count += 1
                
            if count > 0:
                batch.commit()
                logger.info(f"Marked {count} messages as read in {conversation_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking messages as read: {str(e)}")
            return False

    def delete_message(self, league_id: str, message_id: str, user_id: str) -> bool:
        """
        Delete a league chat message (soft delete).
        
        Args:
            league_id: League identifier
            message_id: Message identifier
            user_id: User deleting message
            
        Returns:
            Success status
        """
        try:
            message_ref = self.db.collection('leagues').document(league_id)\
                            .collection('chat').document(message_id)
            
            doc = message_ref.get()
            if not doc.exists:
                return False
                
            data = doc.to_dict()
            # Only allow deletion by original sender or commissioner
            # TODO: Add commissioner check when user roles are implemented
            if data.get('user_id') != user_id:
                return False
            
            message_ref.update({
                'message': '[Message deleted]',
                'deleted': True,
                'deleted_at': datetime.utcnow(),
                'deleted_by': user_id
            })
            
            logger.info(f"Deleted message {message_id} in league {league_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            return False