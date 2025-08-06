"""
Scheduling service for managing timers, events, and automated tasks.
Handles draft timers, waiver deadlines, matchup scheduling, and periodic tasks.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import logging
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class EventType(Enum):
    DRAFT_START = "draft_start"
    DRAFT_PICK_TIMER = "draft_pick_timer"
    WAIVER_DEADLINE = "waiver_deadline"
    MATCHUP_START = "matchup_start"
    MATCHUP_END = "matchup_end"
    TRADE_DEADLINE = "trade_deadline"
    SEASON_START = "season_start"
    SEASON_END = "season_end"
    WEEKLY_SCORING = "weekly_scoring"
    PLAYER_DATA_REFRESH = "player_data_refresh"

@dataclass
class ScheduledEvent:
    id: str
    event_type: EventType
    scheduled_time: datetime
    league_id: Optional[str]
    data: Dict[str, Any]
    recurring: bool = False
    interval: Optional[timedelta] = None
    active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class SchedulingService:
    def __init__(self, db, socketio=None):
        """Initialize scheduling service with database and socketio clients."""
        self.db = db
        self.socketio = socketio
        
        # Active tasks and timers
        self.active_tasks = {}
        self.event_handlers = {}
        
        # Register default event handlers
        self._register_default_handlers()
        
        # Task loop
        self._scheduler_task = None
        self._running = False

    def start_scheduler(self) -> None:
        """Start the main scheduler loop."""
        if not self._running:
            self._running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("Scheduling service started")

    def stop_scheduler(self) -> None:
        """Stop the scheduler and cancel all active tasks."""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
        
        # Cancel all active tasks
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()
        
        self.active_tasks.clear()
        logger.info("Scheduling service stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for due events."""
        try:
            while self._running:
                await self._process_scheduled_events()
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Error in scheduler loop: {str(e)}")

    async def _process_scheduled_events(self) -> None:
        """Process all due scheduled events."""
        try:
            current_time = datetime.utcnow()
            
            # Get due events from database
            due_events = self._get_due_events(current_time)
            
            for event_data in due_events:
                try:
                    event = ScheduledEvent(**event_data)
                    await self._execute_event(event)
                    
                    # Handle recurring events
                    if event.recurring and event.interval:
                        next_time = event.scheduled_time + event.interval
                        await self.schedule_event(
                            event.event_type,
                            next_time,
                            event.data,
                            event.league_id,
                            recurring=True,
                            interval=event.interval
                        )
                    
                    # Mark event as completed
                    self._mark_event_completed(event.id)
                    
                except Exception as e:
                    logger.error(f"Error executing event {event_data.get('id')}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error processing scheduled events: {str(e)}")

    def _get_due_events(self, current_time: datetime) -> List[Dict[str, Any]]:
        """Get all events that are due to be executed."""
        try:
            docs = self.db.collection('scheduled_events')\
                     .where('scheduled_time', '<=', current_time)\
                     .where('active', '==', True)\
                     .stream()
            
            events = []
            for doc in docs:
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting due events: {str(e)}")
            return []

    async def _execute_event(self, event: ScheduledEvent) -> None:
        """Execute a scheduled event."""
        try:
            handler = self.event_handlers.get(event.event_type)
            
            if handler:
                await handler(event)
                logger.info(f"Executed event {event.id} of type {event.event_type.value}")
            else:
                logger.warning(f"No handler found for event type {event.event_type.value}")
                
        except Exception as e:
            logger.error(f"Error executing event {event.id}: {str(e)}")

    def _mark_event_completed(self, event_id: str) -> None:
        """Mark an event as completed."""
        try:
            self.db.collection('scheduled_events').document(event_id)\
                   .update({'active': False, 'completed_at': datetime.utcnow()})
        except Exception as e:
            logger.error(f"Error marking event {event_id} as completed: {str(e)}")

    def _register_default_handlers(self) -> None:
        """Register default event handlers."""
        self.event_handlers = {
            EventType.DRAFT_START: self._handle_draft_start,
            EventType.DRAFT_PICK_TIMER: self._handle_draft_pick_timer,
            EventType.WAIVER_DEADLINE: self._handle_waiver_deadline,
            EventType.MATCHUP_START: self._handle_matchup_start,
            EventType.MATCHUP_END: self._handle_matchup_end,
            EventType.TRADE_DEADLINE: self._handle_trade_deadline,
            EventType.WEEKLY_SCORING: self._handle_weekly_scoring,
            EventType.PLAYER_DATA_REFRESH: self._handle_player_data_refresh,
        }

    async def _handle_draft_start(self, event: ScheduledEvent) -> None:
        """Handle draft start event."""
        try:
            draft_id = event.data.get('draft_id')
            league_id = event.league_id
            
            if not draft_id or not league_id:
                logger.error("Missing draft_id or league_id in draft start event")
                return
            
            # Import here to avoid circular imports
            from ..services.draft_service import DraftService
            draft_service = DraftService(self.db, self.socketio)
            
            # Start the draft
            await draft_service.start_draft(draft_id, event.data.get('commissioner_id'))
            
            # Emit draft started notification
            if self.socketio:
                self.socketio.emit('draft_starting_soon', {
                    'draft_id': draft_id,
                    'league_id': league_id,
                    'message': 'Draft is starting now!'
                }, room=f"league_{league_id}")
            
            logger.info(f"Auto-started draft {draft_id}")
            
        except Exception as e:
            logger.error(f"Error handling draft start: {str(e)}")

    async def _handle_draft_pick_timer(self, event: ScheduledEvent) -> None:
        """Handle draft pick timer expiry."""
        try:
            draft_id = event.data.get('draft_id')
            
            if not draft_id:
                logger.error("Missing draft_id in draft pick timer event")
                return
            
            from ..services.draft_service import DraftService
            draft_service = DraftService(self.db, self.socketio)
            
            # Execute auto-pick
            await draft_service._auto_pick(draft_id)
            
        except Exception as e:
            logger.error(f"Error handling draft pick timer: {str(e)}")

    async def _handle_waiver_deadline(self, event: ScheduledEvent) -> None:
        """Handle waiver wire deadline."""
        try:
            league_id = event.league_id
            
            if not league_id:
                logger.error("Missing league_id in waiver deadline event")
                return
            
            from ..services.waiver_service import WaiverService
            waiver_service = WaiverService(self.db, self.socketio)
            
            # Process all waiver claims
            await waiver_service.process_waiver_claims(league_id)
            
            # Schedule next waiver deadline
            next_deadline = datetime.utcnow() + timedelta(days=7)  # Weekly waivers
            await self.schedule_event(
                EventType.WAIVER_DEADLINE,
                next_deadline,
                {'league_id': league_id},
                league_id
            )
            
            logger.info(f"Processed waiver deadline for league {league_id}")
            
        except Exception as e:
            logger.error(f"Error handling waiver deadline: {str(e)}")

    async def _handle_matchup_start(self, event: ScheduledEvent) -> None:
        """Handle matchup start event."""
        try:
            league_id = event.league_id
            gameweek = event.data.get('gameweek')
            
            if not league_id or not gameweek:
                logger.error("Missing league_id or gameweek in matchup start event")
                return
            
            # Emit matchup started notification
            if self.socketio:
                self.socketio.emit('matchup_started', {
                    'league_id': league_id,
                    'gameweek': gameweek,
                    'message': f'Gameweek {gameweek} has started!'
                }, room=f"league_{league_id}")
            
            # Lock lineups
            await self._lock_lineups(league_id, gameweek)
            
            logger.info(f"Started matchup for league {league_id}, GW{gameweek}")
            
        except Exception as e:
            logger.error(f"Error handling matchup start: {str(e)}")

    async def _handle_matchup_end(self, event: ScheduledEvent) -> None:
        """Handle matchup end event."""
        try:
            league_id = event.league_id
            gameweek = event.data.get('gameweek')
            
            if not league_id or not gameweek:
                logger.error("Missing league_id or gameweek in matchup end event")
                return
            
            from ..services.scoring_service import ScoringService
            scoring_service = ScoringService(self.db, self.socketio)
            
            # Calculate final scores
            await scoring_service.calculate_gameweek_scores(league_id, gameweek)
            
            # Emit matchup completed notification
            if self.socketio:
                self.socketio.emit('matchup_completed', {
                    'league_id': league_id,
                    'gameweek': gameweek,
                    'message': f'Gameweek {gameweek} scoring completed!'
                }, room=f"league_{league_id}")
            
            # Unlock lineups for next gameweek
            await self._unlock_lineups(league_id, gameweek + 1)
            
            logger.info(f"Completed matchup for league {league_id}, GW{gameweek}")
            
        except Exception as e:
            logger.error(f"Error handling matchup end: {str(e)}")

    async def _handle_trade_deadline(self, event: ScheduledEvent) -> None:
        """Handle trade deadline."""
        try:
            league_id = event.league_id
            
            if not league_id:
                logger.error("Missing league_id in trade deadline event")
                return
            
            # Cancel all pending trades
            from ..services.trade_service import TradeService
            trade_service = TradeService(self.db, self.socketio)
            
            pending_trades = trade_service.get_league_trades(league_id, status='proposed')
            
            for trade in pending_trades:
                trade_service.cancel_trade(trade['id'], 'system')
            
            # Emit trade deadline notification
            if self.socketio:
                self.socketio.emit('trade_deadline_passed', {
                    'league_id': league_id,
                    'message': 'Trade deadline has passed. No more trades allowed.'
                }, room=f"league_{league_id}")
            
            logger.info(f"Trade deadline passed for league {league_id}")
            
        except Exception as e:
            logger.error(f"Error handling trade deadline: {str(e)}")

    async def _handle_weekly_scoring(self, event: ScheduledEvent) -> None:
        """Handle weekly scoring update."""
        try:
            league_id = event.league_id
            gameweek = event.data.get('gameweek')
            
            if not league_id or not gameweek:
                logger.error("Missing league_id or gameweek in weekly scoring event")
                return
            
            from ..services.scoring_service import ScoringService
            scoring_service = ScoringService(self.db, self.socketio)
            
            # Update live scores
            await scoring_service.update_live_scores(league_id)
            
            logger.info(f"Updated weekly scoring for league {league_id}, GW{gameweek}")
            
        except Exception as e:
            logger.error(f"Error handling weekly scoring: {str(e)}")

    async def _handle_player_data_refresh(self, event: ScheduledEvent) -> None:
        """Handle player data refresh."""
        try:
            from ..services.player_service import PlayerService
            player_service = PlayerService(self.db)
            
            # Refresh player data from FPL API
            await player_service.refresh_player_data()
            
            logger.info("Completed scheduled player data refresh")
            
        except Exception as e:
            logger.error(f"Error handling player data refresh: {str(e)}")

    async def _lock_lineups(self, league_id: str, gameweek: int) -> None:
        """Lock all team lineups for a gameweek."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel(self.db)
            
            teams = team_model.get_league_teams(league_id)
            
            for team in teams:
                team_model.lock_lineup(team['id'], gameweek)
            
            logger.info(f"Locked lineups for league {league_id}, GW{gameweek}")
            
        except Exception as e:
            logger.error(f"Error locking lineups: {str(e)}")

    async def _unlock_lineups(self, league_id: str, gameweek: int) -> None:
        """Unlock team lineups for the next gameweek."""
        try:
            from ..models.team_model import TeamModel
            team_model = TeamModel(self.db)
            
            teams = team_model.get_league_teams(league_id)
            
            for team in teams:
                team_model.unlock_lineup(team['id'], gameweek)
            
            logger.info(f"Unlocked lineups for league {league_id}, GW{gameweek}")
            
        except Exception as e:
            logger.error(f"Error unlocking lineups: {str(e)}")

    async def schedule_event(self, event_type: EventType, scheduled_time: datetime,
                           data: Dict[str, Any], league_id: str = None,
                           recurring: bool = False, interval: timedelta = None) -> str:
        """
        Schedule a new event.
        
        Args:
            event_type: Type of event to schedule
            scheduled_time: When to execute the event
            data: Event data
            league_id: Associated league (optional)
            recurring: Whether event should repeat
            interval: Repeat interval for recurring events
            
        Returns:
            Event ID
        """
        try:
            event_data = {
                'event_type': event_type.value,
                'scheduled_time': scheduled_time,
                'league_id': league_id,
                'data': data,
                'recurring': recurring,
                'interval_seconds': interval.total_seconds() if interval else None,
                'active': True,
                'created_at': datetime.utcnow()
            }
            
            doc_ref = self.db.collection('scheduled_events').document()
            doc_ref.set(event_data)
            
            event_id = doc_ref.id
            logger.info(f"Scheduled {event_type.value} event for {scheduled_time}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error scheduling event: {str(e)}")
            raise

    def cancel_event(self, event_id: str) -> bool:
        """
        Cancel a scheduled event.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Success status
        """
        try:
            self.db.collection('scheduled_events').document(event_id)\
                   .update({'active': False, 'cancelled_at': datetime.utcnow()})
            
            logger.info(f"Cancelled event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling event {event_id}: {str(e)}")
            return False

    def reschedule_event(self, event_id: str, new_time: datetime) -> bool:
        """
        Reschedule an existing event.
        
        Args:
            event_id: Event identifier
            new_time: New scheduled time
            
        Returns:
            Success status
        """
        try:
            self.db.collection('scheduled_events').document(event_id)\
                   .update({'scheduled_time': new_time, 'updated_at': datetime.utcnow()})
            
            logger.info(f"Rescheduled event {event_id} to {new_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error rescheduling event {event_id}: {str(e)}")
            return False

    async def schedule_draft_reminder(self, draft_id: str, league_id: str, 
                                    draft_time: datetime, hours_before: int = 24) -> str:
        """
        Schedule a draft reminder notification.
        
        Args:
            draft_id: Draft identifier
            league_id: League identifier
            draft_time: Scheduled draft time
            hours_before: Hours before draft to send reminder
            
        Returns:
            Event ID
        """
        try:
            reminder_time = draft_time - timedelta(hours=hours_before)
            
            event_data = {
                'draft_id': draft_id,
                'draft_time': draft_time.isoformat(),
                'reminder_type': f"{hours_before}h_before"
            }
            
            return await self.schedule_event(
                EventType.DRAFT_START,
                reminder_time,
                event_data,
                league_id
            )
            
        except Exception as e:
            logger.error(f"Error scheduling draft reminder: {str(e)}")
            raise

    async def schedule_weekly_tasks(self, league_id: str) -> List[str]:
        """
        Schedule recurring weekly tasks for a league.
        
        Args:
            league_id: League identifier
            
        Returns:
            List of scheduled event IDs
        """
        try:
            event_ids = []
            
            # Schedule waiver deadline (every Wednesday at 2 AM)
            next_wednesday = self._get_next_weekday(2, hour=2)  # Wednesday = 2
            waiver_event_id = await self.schedule_event(
                EventType.WAIVER_DEADLINE,
                next_wednesday,
                {'league_id': league_id},
                league_id,
                recurring=True,
                interval=timedelta(days=7)
            )
            event_ids.append(waiver_event_id)
            
            # Schedule weekly scoring updates (every day during gameweeks)
            daily_scoring_id = await self.schedule_event(
                EventType.WEEKLY_SCORING,
                datetime.utcnow() + timedelta(hours=1),
                {'league_id': league_id, 'gameweek': 1},
                league_id,
                recurring=True,
                interval=timedelta(hours=6)  # Every 6 hours
            )
            event_ids.append(daily_scoring_id)
            
            logger.info(f"Scheduled weekly tasks for league {league_id}")
            return event_ids
            
        except Exception as e:
            logger.error(f"Error scheduling weekly tasks: {str(e)}")
            return []

    def _get_next_weekday(self, weekday: int, hour: int = 0, minute: int = 0) -> datetime:
        """
        Get the next occurrence of a specific weekday.
        
        Args:
            weekday: Day of week (0=Monday, 6=Sunday)
            hour: Hour of day
            minute: Minute of hour
            
        Returns:
            Next occurrence datetime
        """
        today = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = weekday - today.weekday()
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
            
        return today + timedelta(days=days_ahead)

    async def schedule_season_events(self, league_id: str, season_start: datetime,
                                   season_end: datetime) -> List[str]:
        """
        Schedule season-long events for a league.
        
        Args:
            league_id: League identifier
            season_start: Season start date
            season_end: Season end date
            
        Returns:
            List of scheduled event IDs
        """
        try:
            event_ids = []
            
            # Schedule season start
            season_start_id = await self.schedule_event(
                EventType.SEASON_START,
                season_start,
                {'league_id': league_id},
                league_id
            )
            event_ids.append(season_start_id)
            
            # Schedule season end
            season_end_id = await self.schedule_event(
                EventType.SEASON_END,
                season_end,
                {'league_id': league_id},
                league_id
            )
            event_ids.append(season_end_id)
            
            # Schedule trade deadline (e.g., 6 weeks before season end)
            trade_deadline = season_end - timedelta(weeks=6)
            trade_deadline_id = await self.schedule_event(
                EventType.TRADE_DEADLINE,
                trade_deadline,
                {'league_id': league_id},
                league_id
            )
            event_ids.append(trade_deadline_id)
            
            logger.info(f"Scheduled season events for league {league_id}")
            return event_ids
            
        except Exception as e:
            logger.error(f"Error scheduling season events: {str(e)}")
            return []

    def get_league_scheduled_events(self, league_id: str, 
                                  active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all scheduled events for a league.
        
        Args:
            league_id: League identifier
            active_only: Only return active events
            
        Returns:
            List of scheduled events
        """
        try:
            query = self.db.collection('scheduled_events')\
                      .where('league_id', '==', league_id)
            
            if active_only:
                query = query.where('active', '==', True)
            
            docs = query.order_by('scheduled_time').stream()
            
            events = []
            for doc in docs:
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            logger.info(f"Retrieved {len(events)} scheduled events for league {league_id}")
            return events
            
        except Exception as e:
            logger.error(f"Error getting league scheduled events: {str(e)}")
            return []

    async def create_timer(self, duration: timedelta, callback: Callable,
                         callback_args: tuple = (), timer_id: str = None) -> str:
        """
        Create a one-time timer.
        
        Args:
            duration: Timer duration
            callback: Function to call when timer expires
            callback_args: Arguments for callback function
            timer_id: Optional timer identifier
            
        Returns:
            Timer ID
        """
        try:
            if timer_id is None:
                timer_id = f"timer_{datetime.utcnow().timestamp()}"
            
            async def timer_task():
                await asyncio.sleep(duration.total_seconds())
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*callback_args)
                    else:
                        callback(*callback_args)
                except Exception as e:
                    logger.error(f"Error executing timer callback: {str(e)}")
                finally:
                    # Remove from active tasks
                    if timer_id in self.active_tasks:
                        del self.active_tasks[timer_id]
            
            # Create and store the task
            task = asyncio.create_task(timer_task())
            self.active_tasks[timer_id] = task
            
            logger.info(f"Created timer {timer_id} for {duration}")
            return timer_id
            
        except Exception as e:
            logger.error(f"Error creating timer: {str(e)}")
            raise

    def cancel_timer(self, timer_id: str) -> bool:
        """
        Cancel an active timer.
        
        Args:
            timer_id: Timer identifier
            
        Returns:
            Success status
        """
        try:
            if timer_id in self.active_tasks:
                task = self.active_tasks[timer_id]
                if not task.done():
                    task.cancel()
                del self.active_tasks[timer_id]
                logger.info(f"Cancelled timer {timer_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling timer {timer_id}: {str(e)}")
            return False

    def get_active_timers(self) -> List[str]:
        """Get list of active timer IDs."""
        return list(self.active_tasks.keys())

    async def cleanup_completed_events(self, days_old: int = 30) -> int:
        """
        Clean up old completed events.
        
        Args:
            days_old: Remove events older than this many days
            
        Returns:
            Number of events cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            old_events = self.db.collection('scheduled_events')\
                           .where('active', '==', False)\
                           .where('completed_at', '<', cutoff_date)\
                           .stream()
            
            deleted_count = 0
            batch = self.db.batch()
            
            for doc in old_events:
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Commit in batches of 500
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining deletions
            if deleted_count % 500 != 0:
                batch.commit()
            
            logger.info(f"Cleaned up {deleted_count} old events")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up completed events: {str(e)}")
            return 0

    def register_event_handler(self, event_type: EventType, handler: Callable) -> None:
        """
        Register a custom event handler.
        
        Args:
            event_type: Type of event
            handler: Handler function (async)
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type.value}")

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            'running': self._running,
            'active_tasks': len(self.active_tasks),
            'registered_handlers': len(self.event_handlers),
            'task_ids': list(self.active_tasks.keys())
        }