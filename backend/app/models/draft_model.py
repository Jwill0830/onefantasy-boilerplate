"""
Draft model for handling draft operations and data.
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import uuid
from .. import get_db, get_socketio
from ..utils.logger import get_logger

logger = get_logger('draft_model')

class DraftModel:
    """Model for managing draft data and operations."""
    
    def __init__(self):
        self.db = get_db()
        self.socketio = get_socketio()
    
    def create_draft(self, league_id: str, draft_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new draft for a league.
        
        Args:
            league_id: League ID
            draft_settings: Draft configuration settings
            
        Returns:
            Dict with draft_id and success status
        """
        try:
            draft_id = str(uuid.uuid4())
            
            # Default draft settings
            default_settings = {
                'draft_type': 'snake',  # snake, linear, auction
                'pick_duration': 90,  # seconds per pick
                'rounds': 15,
                'auto_pick_enabled': True,
                'auto_pick_threshold': 30,  # seconds before auto-pick
                'draft_order_type': 'random',  # random, custom, reverse_standings
                'scheduled_start': None,
                'status': 'scheduled',  # scheduled, active, paused, completed, cancelled
                'is_mock': False
            }
            
            # Merge with provided settings
            final_settings = {**default_settings, **draft_settings}
            
            # Create draft document
            draft_data = {
                'id': draft_id,
                'league_id': league_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'started_at': None,
                'completed_at': None,
                'current_pick': 1,
                'current_team_id': None,
                'pick_deadline': None,
                'total_picks': 0,
                'draft_order': [],
                'settings': final_settings,
                'auto_pick_queue': {},  # team_id -> [player_ids]
                'commissioner_notes': ''
            }
            
            # Calculate total picks and draft order
            teams = self._get_league_teams(league_id)
            if not teams:
                return {'success': False, 'error': 'No teams found in league'}
            
            draft_data['total_picks'] = len(teams) * final_settings['rounds']
            draft_data['draft_order'] = self._generate_draft_order(teams, final_settings)
            
            if draft_data['draft_order']:
                draft_data['current_team_id'] = draft_data['draft_order'][0]['team_id']
            
            # Store in Firestore
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc_ref.set(draft_data)
            
            logger.info(f"Draft {draft_id} created for league {league_id}")
            
            return {
                'success': True,
                'draft_id': draft_id,
                'message': 'Draft created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating draft for league {league_id}: {e}")
            return {'success': False, 'error': 'Failed to create draft'}
    
    def start_draft(self, league_id: str, draft_id: str) -> Dict[str, Any]:
        """
        Start a scheduled draft.
        
        Args:
            league_id: League ID
            draft_id: Draft ID
            
        Returns:
            Dict with success status
        """
        try:
            draft = self.get_draft(league_id, draft_id)
            if not draft:
                return {'success': False, 'error': 'Draft not found'}
            
            if draft['settings']['status'] != 'scheduled':
                return {'success': False, 'error': 'Draft is not in scheduled status'}
            
            # Update draft status
            current_time = datetime.utcnow()
            pick_duration = draft['settings']['pick_duration']
            
            updates = {
                'settings.status': 'active',
                'started_at': current_time,
                'updated_at': current_time,
                'pick_deadline': current_time + timedelta(seconds=pick_duration)
            }
            
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc_ref.update(updates)
            
            # Notify all participants
            self.socketio.emit('draft_started', {
                'league_id': league_id,
                'draft_id': draft_id,
                'current_team_id': draft['current_team_id'],
                'pick_deadline': (current_time + timedelta(seconds=pick_duration)).isoformat()
            }, room=f'league_{league_id}')
            
            logger.info(f"Draft {draft_id} started for league {league_id}")
            
            return {
                'success': True,
                'message': 'Draft started successfully'
            }
            
        except Exception as e:
            logger.error(f"Error starting draft {draft_id}: {e}")
            return {'success': False, 'error': 'Failed to start draft'}
    
    def make_pick(self, league_id: str, draft_id: str, team_id: str, 
                  player_id: int, is_auto_pick: bool = False) -> Dict[str, Any]:
        """
        Make a draft pick.
        
        Args:
            league_id: League ID
            draft_id: Draft ID
            team_id: Team making the pick
            player_id: Player being drafted
            is_auto_pick: Whether this is an automatic pick
            
        Returns:
            Dict with success status
        """
        try:
            draft = self.get_draft(league_id, draft_id)
            if not draft:
                return {'success': False, 'error': 'Draft not found'}
            
            # Validate pick
            validation = self._validate_pick(draft, team_id, player_id)
            if not validation['valid']:
                return {'success': False, 'error': validation['error']}
            
            # Create pick record
            pick_id = str(uuid.uuid4())
            pick_data = {
                'id': pick_id,
                'draft_id': draft_id,
                'league_id': league_id,
                'pick_number': draft['current_pick'],
                'round': ((draft['current_pick'] - 1) // len(draft['draft_order'])) + 1,
                'team_id': team_id,
                'player_id': player_id,
                'picked_at': datetime.utcnow(),
                'is_auto_pick': is_auto_pick,
                'time_taken': self._calculate_pick_time(draft),
                'notes': ''
            }
            
            # Store pick
            pick_ref = (self.db.collection('leagues').document(league_id)
                       .collection('drafts').document(draft_id)
                       .collection('picks').document(pick_id))
            pick_ref.set(pick_data)
            
            # Update player as drafted
            self._mark_player_drafted(league_id, player_id, team_id, pick_data)
            
            # Add player to team roster
            self._add_player_to_team(league_id, team_id, player_id)
            
            # Update draft state
            next_pick_info = self._advance_to_next_pick(league_id, draft_id, draft)
            
            # Broadcast pick
            self.socketio.emit('pick_made', {
                'league_id': league_id,
                'draft_id': draft_id,
                'pick': pick_data,
                'next_team_id': next_pick_info.get('next_team_id'),
                'next_pick_deadline': next_pick_info.get('next_pick_deadline'),
                'is_draft_complete': next_pick_info.get('is_complete', False)
            }, room=f'league_{league_id}')
            
            logger.info(f"Pick made: Player {player_id} to team {team_id} in draft {draft_id}")
            
            return {
                'success': True,
                'pick_id': pick_id,
                'message': 'Pick made successfully'
            }
            
        except Exception as e:
            logger.error(f"Error making pick in draft {draft_id}: {e}")
            return {'success': False, 'error': 'Failed to make pick'}
    
    def set_auto_pick_queue(self, league_id: str, draft_id: str, team_id: str, 
                           player_ids: List[int]) -> Dict[str, Any]:
        """
        Set auto-pick queue for a team.
        
        Args:
            league_id: League ID
            draft_id: Draft ID
            team_id: Team ID
            player_ids: Ordered list of player IDs for auto-pick
            
        Returns:
            Dict with success status
        """
        try:
            draft = self.get_draft(league_id, draft_id)
            if not draft:
                return {'success': False, 'error': 'Draft not found'}
            
            # Update auto-pick queue
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc_ref.update({
                f'auto_pick_queue.{team_id}': player_ids,
                'updated_at': datetime.utcnow()
            })
            
            logger.info(f"Auto-pick queue set for team {team_id} in draft {draft_id}")
            
            return {
                'success': True,
                'message': 'Auto-pick queue updated'
            }
            
        except Exception as e:
            logger.error(f"Error setting auto-pick queue: {e}")
            return {'success': False, 'error': 'Failed to set auto-pick queue'}
    
    def pause_draft(self, league_id: str, draft_id: str) -> Dict[str, Any]:
        """Pause an active draft."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc_ref.update({
                'settings.status': 'paused',
                'paused_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            self.socketio.emit('draft_paused', {
                'league_id': league_id,
                'draft_id': draft_id
            }, room=f'league_{league_id}')
            
            return {'success': True, 'message': 'Draft paused'}
            
        except Exception as e:
            logger.error(f"Error pausing draft {draft_id}: {e}")
            return {'success': False, 'error': 'Failed to pause draft'}
    
    def resume_draft(self, league_id: str, draft_id: str) -> Dict[str, Any]:
        """Resume a paused draft."""
        try:
            draft = self.get_draft(league_id, draft_id)
            if not draft:
                return {'success': False, 'error': 'Draft not found'}
            
            if draft['settings']['status'] != 'paused':
                return {'success': False, 'error': 'Draft is not paused'}
            
            # Resume with new pick deadline
            current_time = datetime.utcnow()
            pick_duration = draft['settings']['pick_duration']
            
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc_ref.update({
                'settings.status': 'active',
                'pick_deadline': current_time + timedelta(seconds=pick_duration),
                'updated_at': current_time
            })
            
            self.socketio.emit('draft_resumed', {
                'league_id': league_id,
                'draft_id': draft_id,
                'pick_deadline': (current_time + timedelta(seconds=pick_duration)).isoformat()
            }, room=f'league_{league_id}')
            
            return {'success': True, 'message': 'Draft resumed'}
            
        except Exception as e:
            logger.error(f"Error resuming draft {draft_id}: {e}")
            return {'success': False, 'error': 'Failed to resume draft'}
    
    def get_draft(self, league_id: str, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get draft data by ID."""
        try:
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting draft {draft_id}: {e}")
            return None
    
    def get_draft_picks(self, league_id: str, draft_id: str) -> List[Dict[str, Any]]:
        """Get all picks for a draft."""
        try:
            picks_ref = (self.db.collection('leagues').document(league_id)
                        .collection('drafts').document(draft_id)
                        .collection('picks').order_by('pick_number'))
            
            picks = []
            for doc in picks_ref.stream():
                pick_data = doc.to_dict()
                
                # Enhance with player info
                player_info = self._get_player_info(pick_data['player_id'])
                pick_data['player_info'] = player_info
                
                picks.append(pick_data)
            
            return picks
            
        except Exception as e:
            logger.error(f"Error getting draft picks: {e}")
            return []
    
    def get_available_players(self, league_id: str, draft_id: str = None, 
                             position: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get players available for drafting."""
        try:
            from ..models.player_model import PlayerModel
            player_model = PlayerModel()
            
            # Get all players
            all_players = player_model.get_all_players(limit=limit * 2)  # Get more to filter
            
            # Get drafted players
            drafted_players = set()
            if draft_id:
                picks = self.get_draft_picks(league_id, draft_id)
                drafted_players = {pick['player_id'] for pick in picks}
            else:
                # Get from team rosters
                drafted_players = player_model._get_drafted_players(league_id)
            
            # Filter available players
            available_players = []
            for player in all_players:
                if player['id'] not in drafted_players:
                    if position and player.get('element_type') != position:
                        continue
                    available_players.append(player)
            
            # Sort by total points or other relevant metric
            available_players.sort(key=lambda p: p.get('total_points', 0), reverse=True)
            
            return available_players[:limit]
            
        except Exception as e:
            logger.error(f"Error getting available players: {e}")
            return []
    
    def check_auto_pick(self, league_id: str, draft_id: str) -> Dict[str, Any]:
        """Check if auto-pick should be triggered."""
        try:
            draft = self.get_draft(league_id, draft_id)
            if not draft:
                return {'should_auto_pick': False}
            
            if draft['settings']['status'] != 'active':
                return {'should_auto_pick': False}
            
            if not draft['settings']['auto_pick_enabled']:
                return {'should_auto_pick': False}
            
            # Check if pick deadline has passed
            current_time = datetime.utcnow()
            pick_deadline = draft.get('pick_deadline')
            
            if not pick_deadline or current_time < pick_deadline:
                return {'should_auto_pick': False}
            
            # Auto-pick for current team
            current_team_id = draft['current_team_id']
            auto_pick_result = self._execute_auto_pick(league_id, draft_id, draft, current_team_id)
            
            return {
                'should_auto_pick': True,
                'auto_pick_result': auto_pick_result
            }
            
        except Exception as e:
            logger.error(f"Error checking auto-pick: {e}")
            return {'should_auto_pick': False, 'error': str(e)}
    
    def _generate_draft_order(self, teams: List[Dict[str, Any]], 
                             settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate draft order based on settings."""
        try:
            import random
            
            order_type = settings.get('draft_order_type', 'random')
            rounds = settings.get('rounds', 15)
            draft_type = settings.get('draft_type', 'snake')
            
            # Create base order
            if order_type == 'random':
                team_order = teams.copy()
                random.shuffle(team_order)
            elif order_type == 'reverse_standings':
                # Sort by standings (worst first)
                team_order = sorted(teams, key=lambda t: t.get('wins', 0))
            else:  # custom - use provided order or default
                team_order = teams.copy()
            
            # Generate full draft order
            draft_order = []
            pick_number = 1
            
            for round_num in range(1, rounds + 1):
                round_teams = team_order.copy()
                
                # Reverse order for snake draft on even rounds
                if draft_type == 'snake' and round_num % 2 == 0:
                    round_teams.reverse()
                
                for team in round_teams:
                    draft_order.append({
                        'pick_number': pick_number,
                        'round': round_num,
                        'team_id': team['id'],
                        'team_name': team.get('name', f"Team {team['id']}")
                    })
                    pick_number += 1
            
            return draft_order
            
        except Exception as e:
            logger.error(f"Error generating draft order: {e}")
            return []
    
    def _validate_pick(self, draft: Dict[str, Any], team_id: str, 
                      player_id: int) -> Dict[str, Any]:
        """Validate a draft pick."""
        try:
            # Check draft status
            if draft['settings']['status'] != 'active':
                return {'valid': False, 'error': 'Draft is not active'}
            
            # Check if it's the team's turn
            if draft['current_team_id'] != team_id:
                return {'valid': False, 'error': 'Not your turn to pick'}
            
            # Check if player is available
            drafted_players = self._get_drafted_players_in_draft(
                draft['league_id'], draft['id']
            )
            if player_id in drafted_players:
                return {'valid': False, 'error': 'Player already drafted'}
            
            # Check if player exists
            player_info = self._get_player_info(player_id)
            if not player_info:
                return {'valid': False, 'error': 'Player not found'}
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating pick: {e}")
            return {'valid': False, 'error': 'Validation failed'}
    
    def _advance_to_next_pick(self, league_id: str, draft_id: str, 
                             draft: Dict[str, Any]) -> Dict[str, Any]:
        """Advance draft to next pick."""
        try:
            current_pick = draft['current_pick']
            total_picks = draft['total_picks']
            
            # Check if draft is complete
            if current_pick >= total_picks:
                # Complete the draft
                doc_ref = (self.db.collection('leagues').document(league_id)
                          .collection('drafts').document(draft_id))
                doc_ref.update({
                    'settings.status': 'completed',
                    'completed_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                
                return {'is_complete': True}
            
            # Move to next pick
            next_pick = current_pick + 1
            next_team_pick = None
            
            # Find next team
            for pick_info in draft['draft_order']:
                if pick_info['pick_number'] == next_pick:
                    next_team_pick = pick_info
                    break
            
            if not next_team_pick:
                return {'is_complete': True}
            
            # Calculate new deadline
            current_time = datetime.utcnow()
            pick_duration = draft['settings']['pick_duration']
            next_deadline = current_time + timedelta(seconds=pick_duration)
            
            # Update draft
            doc_ref = (self.db.collection('leagues').document(league_id)
                      .collection('drafts').document(draft_id))
            doc_ref.update({
                'current_pick': next_pick,
                'current_team_id': next_team_pick['team_id'],
                'pick_deadline': next_deadline,
                'updated_at': current_time
            })
            
            return {
                'is_complete': False,
                'next_team_id': next_team_pick['team_id'],
                'next_pick_deadline': next_deadline.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error advancing to next pick: {e}")
            return {'is_complete': True}
    
    def _execute_auto_pick(self, league_id: str, draft_id: str, draft: Dict[str, Any], 
                          team_id: str) -> Dict[str, Any]:
        """Execute auto-pick for a team."""
        try:
            # Check auto-pick queue first
            auto_queue = draft.get('auto_pick_queue', {}).get(team_id, [])
            
            # Get available players
            available_players = self.get_available_players(league_id, draft_id, limit=50)
            
            selected_player_id = None
            
            # Try queue first
            for player_id in auto_queue:
                if any(p['id'] == player_id for p in available_players):
                    selected_player_id = player_id
                    break
            
            # Fall back to best available
            if not selected_player_id and available_players:
                selected_player_id = available_players[0]['id']
            
            if not selected_player_id:
                return {'success': False, 'error': 'No players available for auto-pick'}
            
            # Make the pick
            return self.make_pick(league_id, draft_id, team_id, selected_player_id, is_auto_pick=True)
            
        except Exception as e:
            logger.error(f"Error executing auto-pick: {e}")
            return {'success': False, 'error': 'Auto-pick failed'}
    
    def _get_league_teams(self, league_id: str) -> List[Dict[str, Any]]:
        """Get teams in the league."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            return team_model.get_league_teams(league_id)
        except Exception as e:
            logger.error(f"Error getting league teams: {e}")
            return []
    
    def _get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player information."""
        try:
            from ..models.player_model import PlayerModel
            player_model = PlayerModel()
            return player_model.get_player(player_id)
        except Exception as e:
            logger.error(f"Error getting player info: {e}")
            return None
    
    def _mark_player_drafted(self, league_id: str, player_id: int, team_id: str, 
                           pick_data: Dict[str, Any]) -> None:
        """Mark player as drafted."""
        try:
            from ..models.player_model import PlayerModel
            player_model = PlayerModel()
            
            player_model.update_player_draft_status(player_id, {
                'league_id': league_id,
                'team_id': team_id,
                'pick_number': pick_data['pick_number'],
                'round': pick_data['round'],
                'drafted_at': pick_data['picked_at']
            })
        except Exception as e:
            logger.error(f"Error marking player as drafted: {e}")
    
    def _add_player_to_team(self, league_id: str, team_id: str, player_id: int) -> None:
        """Add drafted player to team roster."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            # Add to bench by default
            team_model.add_player_to_roster(league_id, team_id, player_id, 'bench')
        except Exception as e:
            logger.error(f"Error adding player to team: {e}")
    
    def _get_drafted_players_in_draft(self, league_id: str, draft_id: str) -> set:
        """Get set of player IDs already drafted in this draft."""
        try:
            picks = self.get_draft_picks(league_id, draft_id)
            return {pick['player_id'] for pick in picks}
        except Exception as e:
            logger.error(f"Error getting drafted players: {e}")
            return set()
    
    def _calculate_pick_time(self, draft: Dict[str, Any]) -> int:
        """Calculate how long the pick took in seconds."""
        try:
            pick_deadline = draft.get('pick_deadline')
            if not pick_deadline:
                return 0
            
            current_time = datetime.utcnow()
            pick_duration = draft['settings']['pick_duration']
            
            # Calculate time remaining when pick was made
            time_remaining = (pick_deadline - current_time).total_seconds()
            time_taken = pick_duration - max(0, time_remaining)
            
            return int(time_taken)
        except Exception as e:
            logger.error(f"Error calculating pick time: {e}")
            return 0