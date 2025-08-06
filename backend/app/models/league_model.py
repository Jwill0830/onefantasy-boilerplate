"""
League data model and Firestore operations.
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import uuid
import random
import string
from .. import get_db, get_socketio
from ..utils.logger import get_logger

logger = get_logger('league_model')

class LeagueModel:
    """Model for league operations in Firestore."""
    
    def __init__(self):
        self.db = get_db()
        self.socketio = get_socketio()
        self.collection = 'leagues'
    
    def create_league(self, commissioner_id: str, league_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new league.
        
        Args:
            commissioner_id: User ID of the league commissioner
            league_data: League configuration data
            
        Returns:
            Dict with league_id and success status
        """
        try:
            league_id = str(uuid.uuid4())
            invite_code = self._generate_invite_code()
            
            # Default league settings
            default_settings = {
                'league_size': league_data.get('league_size', 10),
                'roster_size': 15,
                'starting_lineup_size': 11,
                'pick_time_seconds': 120,
                'waiver_budget': 100,
                'trade_deadline': None,
                'playoff_teams': 4,
                'playoff_weeks': [37, 38],  # Last 2 gameweeks of Premier League
                'scoring_settings': self._get_default_scoring(),
                'draft_order_type': 'snake',  # snake or linear
                'auto_pick_enabled': True,
                'auto_pick_threshold': 30,  # seconds before auto pick
                'waiver_process_day': 'wednesday',  # day of week to process waivers
                'trade_review_period': 24,  # hours for trade review
                'commissioner_approval_required': False
            }
            
            # Merge with provided data
            settings = {**default_settings, **league_data.get('settings', {})}
            
            # Create league document
            league_doc = {
                'id': league_id,
                'name': league_data.get('name', f'League {league_id[:8]}'),
                'description': league_data.get('description', ''),
                'commissioner_id': commissioner_id,
                'invite_code': invite_code,
                'status': 'created',  # created, drafting, active, completed, cancelled
                'is_public': league_data.get('is_public', False),
                'password': league_data.get('password', ''),  # For private leagues
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'settings': settings,
                'teams_count': 0,
                'max_teams': settings['league_size'],
                'draft_settings': {
                    'scheduled_time': league_data.get('draft_time'),
                    'started_at': None,
                    'completed_at': None,
                    'current_pick': 1,
                    'current_round': 1,
                    'auto_pick_enabled': settings['auto_pick_enabled'],
                    'draft_order': [],
                    'is_mock': league_data.get('is_mock_draft', False)
                },
                'season_info': {
                    'current_gameweek': 1,
                    'total_gameweeks': 38,
                    'regular_season_weeks': 34,
                    'playoff_weeks': [35, 36, 37, 38],
                    'season_start': league_data.get('season_start'),
                    'season_end': league_data.get('season_end')
                },
                'matchup_schedule': [],
                'playoff_bracket': {},
                'waiver_settings': {
                    'budget_per_team': settings['waiver_budget'],
                    'process_day': settings['waiver_process_day'],
                    'process_time': '10:00',  # UTC time
                    'rolling_waivers': True
                }
            }
            
            # Store in Firestore
            doc_ref = self.db.collection(self.collection).document(league_id)
            doc_ref.set(league_doc)
            
            logger.info(f"Created league {league_id} with commissioner {commissioner_id}")
            
            return {
                'success': True,
                'league_id': league_id,
                'invite_code': invite_code,
                'message': 'League created successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to create league: {e}")
            return {'success': False, 'error': 'Failed to create league'}
    
    def get_league(self, league_id: str) -> Optional[Dict[str, Any]]:
        """Get league by ID."""
        try:
            doc_ref = self.db.collection(self.collection).document(league_id)
            doc = doc_ref.get()
            
            if doc.exists:
                league_data = doc.to_dict()
                
                # Enhance with team count and other computed fields
                league_data['teams_count'] = self._get_teams_count(league_id)
                league_data['is_full'] = league_data['teams_count'] >= league_data.get('max_teams', 10)
                
                return league_data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get league {league_id}: {e}")
            return None
    
    def get_league_by_invite_code(self, invite_code: str) -> Optional[Dict[str, Any]]:
        """Get league by invite code."""
        try:
            query = (self.db.collection(self.collection)
                    .where('invite_code', '==', invite_code)
                    .limit(1))
            
            docs = list(query.stream())
            
            if docs:
                league_data = docs[0].to_dict()
                league_id = league_data['id']
                
                # Enhance with team count
                league_data['teams_count'] = self._get_teams_count(league_id)
                league_data['is_full'] = league_data['teams_count'] >= league_data.get('max_teams', 10)
                
                return league_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get league by invite code {invite_code}: {e}")
            return None
    
    def join_league(self, league_id: str, user_id: str, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """Join a league by creating a team."""
        try:
            league = self.get_league(league_id)
            if not league:
                return {'success': False, 'error': 'League not found'}
            
            # Check if league is full
            if league.get('is_full', False):
                return {'success': False, 'error': 'League is full'}
            
            # Check if user already has a team
            if self._user_has_team_in_league(league_id, user_id):
                return {'success': False, 'error': 'You already have a team in this league'}
            
            # Create team
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            team_result = team_model.create_team(league_id, user_id, team_data)
            if not team_result['success']:
                return team_result
            
            # Update league teams count
            self.update_league(league_id, {
                'teams_count': league['teams_count'] + 1,
                'updated_at': datetime.utcnow()
            })
            
            # Emit real-time update
            self.socketio.emit('team_joined_league', {
                'league_id': league_id,
                'team_id': team_result['team_id'],
                'team_name': team_data.get('name', 'New Team'),
                'owner_id': user_id,
                'teams_count': league['teams_count'] + 1
            }, room=f'league_{league_id}')
            
            logger.info(f"User {user_id} joined league {league_id}")
            
            return {
                'success': True,
                'team_id': team_result['team_id'],
                'message': 'Successfully joined league'
            }
            
        except Exception as e:
            logger.error(f"Failed to join league {league_id}: {e}")
            return {'success': False, 'error': 'Failed to join league'}
    
    def update_league(self, league_id: str, update_data: Dict[str, Any]) -> bool:
        """Update league data."""
        try:
            update_data['updated_at'] = datetime.utcnow()
            
            doc_ref = self.db.collection(self.collection).document(league_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated league {league_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update league {league_id}: {e}")
            return False
    
    def get_user_leagues(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all leagues where user is a member or commissioner."""
        try:
            user_leagues = []
            
            # Get leagues where user is commissioner
            commissioner_query = (self.db.collection(self.collection)
                                .where('commissioner_id', '==', user_id))
            
            for doc in commissioner_query.stream():
                league_data = doc.to_dict()
                league_data['user_role'] = 'commissioner'
                league_data['teams_count'] = self._get_teams_count(league_data['id'])
                user_leagues.append(league_data)
            
            # Get leagues where user has a team (not commissioner)
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            user_teams = team_model.get_user_teams(user_id)
            
            commissioner_league_ids = {league['id'] for league in user_leagues}
            
            for team in user_teams:
                league_id = team['league_id']
                
                # Skip if already included as commissioner
                if league_id in commissioner_league_ids:
                    continue
                
                league = self.get_league(league_id)
                if league:
                    league['user_role'] = 'member'
                    league['user_team'] = team
                    user_leagues.append(league)
            
            # Sort by most recently updated
            user_leagues.sort(key=lambda x: x.get('updated_at', datetime.min), reverse=True)
            
            return user_leagues
            
        except Exception as e:
            logger.error(f"Failed to get user leagues for {user_id}: {e}")
            return []
    
    def start_draft(self, league_id: str) -> Dict[str, Any]:
        """Start the draft for a league."""
        try:
            league = self.get_league(league_id)
            if not league:
                return {'success': False, 'error': 'League not found'}
            
            if league['status'] != 'created':
                return {'success': False, 'error': 'League is not in created status'}
            
            # Check minimum teams
            teams_count = league.get('teams_count', 0)
            if teams_count < 2:
                return {'success': False, 'error': 'Need at least 2 teams to start draft'}
            
            # Generate draft order
            draft_order = self._generate_draft_order(league_id)
            if not draft_order:
                return {'success': False, 'error': 'Failed to generate draft order'}
            
            # Create draft using DraftModel
            from ..models.draft_model import DraftModel
            draft_model = DraftModel()
            
            draft_settings = {
                'draft_type': league['settings'].get('draft_order_type', 'snake'),
                'pick_duration': league['settings'].get('pick_time_seconds', 120),
                'rounds': league['settings'].get('roster_size', 15),
                'auto_pick_enabled': league['settings'].get('auto_pick_enabled', True),
                'is_mock': league['draft_settings'].get('is_mock', False)
            }
            
            draft_result = draft_model.create_draft(league_id, draft_settings)
            if not draft_result['success']:
                return draft_result
            
            # Update league status
            update_data = {
                'status': 'drafting',
                'draft_settings.started_at': datetime.utcnow(),
                'draft_settings.draft_id': draft_result['draft_id'],
                'updated_at': datetime.utcnow()
            }
            
            success = self.update_league(league_id, update_data)
            if not success:
                return {'success': False, 'error': 'Failed to update league status'}
            
            # Emit real-time notification
            self.socketio.emit('draft_starting', {
                'league_id': league_id,
                'draft_id': draft_result['draft_id'],
                'message': 'Draft is starting!'
            }, room=f'league_{league_id}')
            
            logger.info(f"Started draft for league {league_id}")
            
            return {
                'success': True,
                'draft_id': draft_result['draft_id'],
                'message': 'Draft started successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to start draft for league {league_id}: {e}")
            return {'success': False, 'error': 'Failed to start draft'}
    
    def complete_draft(self, league_id: str) -> Dict[str, Any]:
        """Mark draft as completed and transition league to active."""
        try:
            update_data = {
                'status': 'active',
                'draft_settings.completed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            success = self.update_league(league_id, update_data)
            if not success:
                return {'success': False, 'error': 'Failed to update league'}
            
            # Generate initial matchup schedule
            self._generate_matchup_schedule(league_id)
            
            # Emit notification
            self.socketio.emit('draft_completed', {
                'league_id': league_id,
                'message': 'Draft completed! League is now active.'
            }, room=f'league_{league_id}')
            
            logger.info(f"Completed draft for league {league_id}")
            
            return {
                'success': True,
                'message': 'Draft completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to complete draft for league {league_id}: {e}")
            return {'success': False, 'error': 'Failed to complete draft'}
    
    def get_league_standings(self, league_id: str) -> List[Dict[str, Any]]:
        """Get current league standings."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            teams = team_model.get_league_teams(league_id)
            
            # Sort by wins, then points for, then points against
            standings = sorted(teams, key=lambda t: (
                -t.get('wins', 0),
                -t.get('points_for', 0),
                t.get('points_against', 0)
            ))
            
            # Add rank
            for i, team in enumerate(standings):
                team['rank'] = i + 1
            
            return standings
            
        except Exception as e:
            logger.error(f"Failed to get league standings for {league_id}: {e}")
            return []
    
    def delete_league(self, league_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a league (commissioner only)."""
        try:
            league = self.get_league(league_id)
            if not league:
                return {'success': False, 'error': 'League not found'}
            
            # Check if user is commissioner
            if league['commissioner_id'] != user_id:
                return {'success': False, 'error': 'Only commissioner can delete league'}
            
            # Check if league has started
            if league['status'] in ['drafting', 'active']:
                return {'success': False, 'error': 'Cannot delete active league'}
            
            # Delete league document
            doc_ref = self.db.collection(self.collection).document(league_id)
            doc_ref.delete()
            
            # TODO: Clean up subcollections (teams, drafts, trades, etc.)
            # This should be handled by Cloud Functions or a cleanup service
            
            logger.info(f"Deleted league {league_id}")
            
            return {
                'success': True,
                'message': 'League deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete league {league_id}: {e}")
            return {'success': False, 'error': 'Failed to delete league'}
    
    def update_league_settings(self, league_id: str, user_id: str, 
                              new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update league settings (commissioner only)."""
        try:
            league = self.get_league(league_id)
            if not league:
                return {'success': False, 'error': 'League not found'}
            
            # Check if user is commissioner
            if league['commissioner_id'] != user_id:
                return {'success': False, 'error': 'Only commissioner can update settings'}
            
            # Check if league has started (some settings can't be changed)
            if league['status'] in ['drafting', 'active']:
                # Only allow certain settings to be changed after start
                allowed_settings = ['trade_deadline', 'waiver_process_day', 'commissioner_approval_required']
                new_settings = {k: v for k, v in new_settings.items() if k in allowed_settings}
            
            # Merge settings
            current_settings = league.get('settings', {})
            updated_settings = {**current_settings, **new_settings}
            
            # Update league
            success = self.update_league(league_id, {
                'settings': updated_settings
            })
            
            if success:
                return {
                    'success': True,
                    'message': 'League settings updated successfully'
                }
            else:
                return {'success': False, 'error': 'Failed to update settings'}
            
        except Exception as e:
            logger.error(f"Failed to update league settings: {e}")
            return {'success': False, 'error': 'Failed to update settings'}
    
    def _generate_invite_code(self) -> str:
        """Generate a unique invite code."""
        max_attempts = 10
        
        for _ in range(max_attempts):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Check if code already exists
            existing = self.get_league_by_invite_code(code)
            if not existing:
                return code
        
        # Fallback to UUID if can't generate unique code
        return str(uuid.uuid4())[:6].upper()
    
    def _generate_draft_order(self, league_id: str) -> List[str]:
        """Generate draft order for the league."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            teams = team_model.get_league_teams(league_id)
            if not teams:
                return []
            
            # Simple random order for now
            # TODO: Implement other order types (reverse standings, custom)
            team_ids = [team['id'] for team in teams]
            random.shuffle(team_ids)
            
            return team_ids
            
        except Exception as e:
            logger.error(f"Error generating draft order: {e}")
            return []
    
    def _generate_matchup_schedule(self, league_id: str) -> bool:
        """Generate regular season matchup schedule."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            teams = team_model.get_league_teams(league_id)
            team_count = len(teams)
            
            if team_count < 2:
                return False
            
            # Simple round-robin schedule
            # TODO: Implement more sophisticated scheduling
            schedule = []
            weeks = 14  # Regular season weeks
            
            for week in range(1, weeks + 1):
                week_matchups = []
                
                # Simple pairing for this week
                for i in range(0, team_count - 1, 2):
                    if i + 1 < team_count:
                        matchup = {
                            'week': week,
                            'team1_id': teams[i]['id'],
                            'team2_id': teams[i + 1]['id'],
                            'team1_score': 0,
                            'team2_score': 0,
                            'status': 'scheduled'  # scheduled, active, completed
                        }
                        week_matchups.append(matchup)
                
                # Rotate teams for next week (except first team)
                if len(teams) > 2:
                    teams = [teams[0]] + [teams[-1]] + teams[1:-1]
                
                schedule.extend(week_matchups)
            
            # Store schedule
            self.update_league(league_id, {
                'matchup_schedule': schedule
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating matchup schedule: {e}")
            return False
    
    def _get_teams_count(self, league_id: str) -> int:
        """Get count of teams in league."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            teams = team_model.get_league_teams(league_id)
            return len(teams)
        except Exception as e:
            logger.error(f"Error getting teams count: {e}")
            return 0
    
    def _user_has_team_in_league(self, league_id: str, user_id: str) -> bool:
        """Check if user already has a team in the league."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel()
            
            user_teams = team_model.get_user_teams(user_id)
            return any(team['league_id'] == league_id for team in user_teams)
            
        except Exception as e:
            logger.error(f"Error checking user team in league: {e}")
            return False
    
    def _get_default_scoring(self) -> Dict[str, Any]:
        """Get default FPL-style scoring settings."""
        return {
            'goals_scored': {
                'GK': 6,   # Goalkeeper
                'DEF': 6,  # Defender
                'MID': 5,  # Midfielder
                'FWD': 4   # Forward
            },
            'assists': 3,
            'clean_sheets': {
                'GK': 4,
                'DEF': 4,
                'MID': 1,
                'FWD': 0
            },
            'saves': {
                'points_per_save': 1,
                'saves_required': 3  # 1 point per 3 saves
            },
            'penalty_saves': 5,
            'penalty_misses': -2,
            'yellow_cards': -1,
            'red_cards': -3,
            'own_goals': -2,
            'goals_conceded': {
                'GK': -1,   # per 2 goals conceded
                'DEF': -1,  # per 2 goals conceded
                'MID': 0,
                'FWD': 0
            },
            'bonus_points': 1,  # Bonus points system (1-3 points)
            'minutes_played': {
                '60_plus': 2,      # Played 60+ minutes
                '1_to_59': 1,      # Played 1-59 minutes
                '0': 0             # Didn't play
            }
        }