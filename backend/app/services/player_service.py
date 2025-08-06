"""
Player service for managing player data, search, trending, and statistics.
Handles API integrations and caching for player information.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from collections import defaultdict
import json

from ..models.player_model import PlayerModel
from ..utils.api_integrations import FPLAPIClient

logger = logging.getLogger(__name__)

class PlayerService:
    def __init__(self, db):
        """Initialize player service with database client."""
        self.db = db
        self.player_model = PlayerModel(db)
        self.fpl_client = FPLAPIClient()
        
        # Cache for player data
        self._player_cache = {}
        self._cache_expiry = None
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour

    async def refresh_player_data(self) -> Dict[str, Any]:
        """
        Refresh player data from FPL API and update database.
        
        Returns:
            Update summary
        """
        try:
            logger.info("Starting player data refresh")
            
            # Get latest data from FPL API
            bootstrap_data = await self.fpl_client.get_bootstrap_static()
            
            if not bootstrap_data or 'elements' not in bootstrap_data:
                raise ValueError("Failed to fetch player data from FPL API")
            
            players = bootstrap_data['elements']
            teams = bootstrap_data.get('teams', [])
            positions = bootstrap_data.get('element_types', [])
            
            # Create lookup dictionaries
            team_lookup = {team['id']: team for team in teams}
            position_lookup = {pos['id']: pos for pos in positions}
            
            updated_players = []
            new_players = []
            
            for player_data in players:
                # Transform player data
                player = self._transform_fpl_player(player_data, team_lookup, position_lookup)
                
                # Check if player exists
                existing_player = self.player_model.get_player_by_fpl_id(player['fpl_id'])
                
                if existing_player:
                    # Update existing player
                    self.player_model.update_player(existing_player['id'], player)
                    updated_players.append(player['fpl_id'])
                else:
                    # Create new player
                    self.player_model.create_player(player)
                    new_players.append(player['fpl_id'])
            
            # Update cache
            self._update_player_cache(players, team_lookup, position_lookup)
            
            summary = {
                'total_players': len(players),
                'updated_players': len(updated_players),
                'new_players': len(new_players),
                'last_updated': datetime.utcnow()
            }
            
            # Store refresh summary
            self.db.collection('system').document('player_refresh').set(summary)
            
            logger.info(f"Player data refresh completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error refreshing player data: {str(e)}")
            raise

    def _transform_fpl_player(self, player_data: Dict, team_lookup: Dict, 
                            position_lookup: Dict) -> Dict[str, Any]:
        """
        Transform FPL API player data to our format.
        
        Args:
            player_data: Raw player data from FPL API
            team_lookup: Team ID to team data mapping
            position_lookup: Position ID to position data mapping
            
        Returns:
            Transformed player data
        """
        try:
            team_data = team_lookup.get(player_data['team'], {})
            position_data = position_lookup.get(player_data['element_type'], {})
            
            return {
                'fpl_id': player_data['id'],
                'web_name': player_data['web_name'],
                'first_name': player_data['first_name'],
                'second_name': player_data['second_name'],
                'full_name': f"{player_data['first_name']} {player_data['second_name']}",
                'position': position_data.get('singular_name_short', 'Unknown'),
                'position_id': player_data['element_type'],
                'team': team_data.get('short_name', 'Unknown'),
                'team_id': player_data['team'],
                'team_code': team_data.get('code', 0),
                'now_cost': player_data['now_cost'],
                'cost_change_start': player_data['cost_change_start'],
                'cost_change_event': player_data['cost_change_event'],
                'cost_change_start_fall': player_data['cost_change_start_fall'],
                'cost_change_event_fall': player_data['cost_change_event_fall'],
                'in_dreamteam': player_data['in_dreamteam'],
                'dreamteam_count': player_data['dreamteam_count'],
                'selected_by_percent': float(player_data['selected_by_percent']),
                'form': float(player_data['form']),
                'transfers_out': player_data['transfers_out'],
                'transfers_in': player_data['transfers_in'],
                'transfers_out_event': player_data['transfers_out_event'],
                'transfers_in_event': player_data['transfers_in_event'],
                'loans_in': player_data['loans_in'],
                'loans_out': player_data['loans_out'],
                'loaned_in': player_data['loaned_in'],
                'loaned_out': player_data['loaned_out'],
                'total_points': player_data['total_points'],
                'event_points': player_data['event_points'],
                'points_per_game': float(player_data['points_per_game']),
                'ep_this': float(player_data['ep_this']) if player_data['ep_this'] else 0.0,
                'ep_next': float(player_data['ep_next']) if player_data['ep_next'] else 0.0,
                'special': player_data['special'],
                'minutes': player_data['minutes'],
                'goals_scored': player_data['goals_scored'],
                'assists': player_data['assists'],
                'clean_sheets': player_data['clean_sheets'],
                'goals_conceded': player_data['goals_conceded'],
                'own_goals': player_data['own_goals'],
                'penalties_saved': player_data['penalties_saved'],
                'penalties_missed': player_data['penalties_missed'],
                'yellow_cards': player_data['yellow_cards'],
                'red_cards': player_data['red_cards'],
                'saves': player_data['saves'],
                'bonus': player_data['bonus'],
                'bps': player_data['bps'],
                'influence': float(player_data['influence']),
                'creativity': float(player_data['creativity']),
                'threat': float(player_data['threat']),
                'ict_index': float(player_data['ict_index']),
                'starts': player_data['starts'],
                'expected_goals': float(player_data['expected_goals']),
                'expected_assists': float(player_data['expected_assists']),
                'expected_goal_involvements': float(player_data['expected_goal_involvements']),
                'expected_goals_conceded': float(player_data['expected_goals_conceded']),
                'influence_rank': player_data['influence_rank'],
                'influence_rank_type': player_data['influence_rank_type'],
                'creativity_rank': player_data['creativity_rank'],
                'creativity_rank_type': player_data['creativity_rank_type'],
                'threat_rank': player_data['threat_rank'],
                'threat_rank_type': player_data['threat_rank_type'],
                'ict_index_rank': player_data['ict_index_rank'],
                'ict_index_rank_type': player_data['ict_index_rank_type'],
                'corners_and_indirect_freekicks_order': player_data['corners_and_indirect_freekicks_order'],
                'corners_and_indirect_freekicks_text': player_data['corners_and_indirect_freekicks_text'],
                'direct_freekicks_order': player_data['direct_freekicks_order'],
                'direct_freekicks_text': player_data['direct_freekicks_text'],
                'penalties_order': player_data['penalties_order'],
                'penalties_text': player_data['penalties_text'],
                'now_cost_rank': player_data['now_cost_rank'],
                'now_cost_rank_type': player_data['now_cost_rank_type'],
                'form_rank': player_data['form_rank'],
                'form_rank_type': player_data['form_rank_type'],
                'points_per_game_rank': player_data['points_per_game_rank'],
                'points_per_game_rank_type': player_data['points_per_game_rank_type'],
                'selected_rank': player_data['selected_rank'],
                'selected_rank_type': player_data['selected_rank_type'],
                'photo': player_data['photo'],
                'status': player_data['status'],
                'news': player_data['news'],
                'news_added': player_data['news_added'],
                'chance_of_playing_this_round': player_data['chance_of_playing_this_round'],
                'chance_of_playing_next_round': player_data['chance_of_playing_next_round'],
                'value_form': float(player_data['value_form']),
                'value_season': float(player_data['value_season']),
                'updated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error transforming player data: {str(e)}")
            raise

    def _update_player_cache(self, players: List[Dict], team_lookup: Dict, 
                           position_lookup: Dict) -> None:
        """Update in-memory player cache."""
        try:
            self._player_cache = {}
            
            for player_data in players:
                player = self._transform_fpl_player(player_data, team_lookup, position_lookup)
                self._player_cache[player['fpl_id']] = player
            
            self._cache_expiry = datetime.utcnow() + self._cache_duration
            logger.info(f"Updated player cache with {len(players)} players")
            
        except Exception as e:
            logger.error(f"Error updating player cache: {str(e)}")

    async def search_players(self, query: str, filters: Dict[str, Any] = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for players with optional filters.
        
        Args:
            query: Search query (name, team, etc.)
            filters: Additional filters (position, team, price range, etc.)
            limit: Maximum results to return
            
        Returns:
            List of matching players
        """
        try:
            # Ensure we have fresh player data
            await self._ensure_fresh_cache()
            
            results = []
            filters = filters or {}
            
            # Convert query to lowercase for case-insensitive search
            query_lower = query.lower() if query else ""
            
            for player in self._player_cache.values():
                # Text search
                if query_lower:
                    searchable_text = " ".join([
                        player.get('web_name', '').lower(),
                        player.get('full_name', '').lower(),
                        player.get('team', '').lower()
                    ])
                    
                    if query_lower not in searchable_text:
                        continue
                
                # Apply filters
                if not self._player_matches_filters(player, filters):
                    continue
                
                results.append(player)
            
            # Sort results by relevance
            results = self._sort_search_results(results, query)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching players: {str(e)}")
            return []

    def _player_matches_filters(self, player: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if player matches the provided filters."""
        try:
            # Position filter
            if 'position' in filters:
                positions = filters['position']
                if isinstance(positions, str):
                    positions = [positions]
                if player.get('position') not in positions:
                    return False
            
            # Team filter
            if 'team' in filters:
                teams = filters['team']
                if isinstance(teams, str):
                    teams = [teams]
                if player.get('team') not in teams:
                    return False
            
            # Price range filter
            if 'min_price' in filters:
                if player.get('now_cost', 0) < filters['min_price']:
                    return False
            
            if 'max_price' in filters:
                if player.get('now_cost', 0) > filters['max_price']:
                    return False
            
            # Points range filter
            if 'min_points' in filters:
                if player.get('total_points', 0) < filters['min_points']:
                    return False
            
            if 'max_points' in filters:
                if player.get('total_points', 0) > filters['max_points']:
                    return False
            
            # Form filter
            if 'min_form' in filters:
                if player.get('form', 0) < filters['min_form']:
                    return False
            
            # Availability filter
            if 'available_only' in filters and filters['available_only']:
                if player.get('status') != 'a':  # 'a' = available
                    return False
            
            # News filter (filter out injured players)
            if 'exclude_injured' in filters and filters['exclude_injured']:
                if player.get('chance_of_playing_this_round', 100) < 75:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            return True

    def _sort_search_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Sort search results by relevance."""
        try:
            if not query:
                # No search query, sort by total points
                return sorted(results, key=lambda x: x.get('total_points', 0), reverse=True)
            
            query_lower = query.lower()
            
            def relevance_score(player):
                score = 0
                web_name = player.get('web_name', '').lower()
                full_name = player.get('full_name', '').lower()
                
                # Exact web name match gets highest score
                if web_name == query_lower:
                    score += 100
                # Web name starts with query
                elif web_name.startswith(query_lower):
                    score += 50
                # Web name contains query
                elif query_lower in web_name:
                    score += 25
                
                # Full name matches
                if full_name == query_lower:
                    score += 80
                elif full_name.startswith(query_lower):
                    score += 40
                elif query_lower in full_name:
                    score += 20
                
                # Boost score based on player performance
                score += player.get('total_points', 0) * 0.1
                score += player.get('selected_by_percent', 0) * 0.5
                
                return score
            
            return sorted(results, key=relevance_score, reverse=True)
            
        except Exception as e:
            logger.error(f"Error sorting search results: {str(e)}")
            return results

    async def get_trending_players(self, timeframe: str = 'week', 
                                 metric: str = 'transfers_in') -> List[Dict[str, Any]]:
        """
        Get trending players based on various metrics.
        
        Args:
            timeframe: Time period ('week', 'gameweek', 'month')
            metric: Trending metric ('transfers_in', 'form', 'points', 'ownership')
            
        Returns:
            List of trending players
        """
        try:
            await self._ensure_fresh_cache()
            
            players = list(self._player_cache.values())
            
            # Sort by the specified metric
            if metric == 'transfers_in':
                players.sort(key=lambda x: x.get('transfers_in_event', 0), reverse=True)
            elif metric == 'transfers_out':
                players.sort(key=lambda x: x.get('transfers_out_event', 0), reverse=True)
            elif metric == 'form':
                players.sort(key=lambda x: x.get('form', 0), reverse=True)
            elif metric == 'points':
                players.sort(key=lambda x: x.get('event_points', 0), reverse=True)
            elif metric == 'ownership':
                players.sort(key=lambda x: x.get('selected_by_percent', 0), reverse=True)
            elif metric == 'price_rise':
                players.sort(key=lambda x: x.get('cost_change_event', 0), reverse=True)
            elif metric == 'price_fall':
                players.sort(key=lambda x: x.get('cost_change_event_fall', 0), reverse=True)
            else:
                # Default to total points
                players.sort(key=lambda x: x.get('total_points', 0), reverse=True)
            
            # Add trending stats
            trending_players = []
            for i, player in enumerate(players[:50]):  # Top 50
                trending_data = {
                    **player,
                    'trending_rank': i + 1,
                    'trending_metric': metric,
                    'trending_value': player.get(f'{metric}_event' if 'event' not in metric else metric, 0)
                }
                trending_players.append(trending_data)
            
            return trending_players
            
        except Exception as e:
            logger.error(f"Error getting trending players: {str(e)}")
            return []

    async def get_player_leaders(self, stat: str, position: str = None, 
                               timeframe: str = 'season') -> List[Dict[str, Any]]:
        """
        Get players leading in specific statistics.
        
        Args:
            stat: Statistic to rank by (goals, assists, points, etc.)
            position: Filter by position (optional)
            timeframe: Time period for stats
            
        Returns:
            List of leading players
        """
        try:
            await self._ensure_fresh_cache()
            
            players = list(self._player_cache.values())
            
            # Filter by position if specified
            if position:
                players = [p for p in players if p.get('position') == position]
            
            # Sort by the specified statistic
            stat_mapping = {
                'goals': 'goals_scored',
                'assists': 'assists',
                'points': 'total_points',
                'clean_sheets': 'clean_sheets',
                'saves': 'saves',
                'bonus': 'bonus',
                'minutes': 'minutes',
                'form': 'form',
                'points_per_game': 'points_per_game',
                'influence': 'influence',
                'creativity': 'creativity',
                'threat': 'threat',
                'ict_index': 'ict_index',
                'expected_goals': 'expected_goals',
                'expected_assists': 'expected_assists',
                'value_season': 'value_season'
            }
            
            sort_key = stat_mapping.get(stat, stat)
            players.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
            
            # Add leader stats
            leaders = []
            for i, player in enumerate(players[:25]):  # Top 25
                leader_data = {
                    **player,
                    'rank': i + 1,
                    'stat_name': stat,
                    'stat_value': player.get(sort_key, 0),
                    'position_rank': None  # Will be calculated if needed
                }
                leaders.append(leader_data)
            
            return leaders
            
        except Exception as e:
            logger.error(f"Error getting player leaders: {str(e)}")
            return []

    async def get_player_details(self, player_fpl_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific player.
        
        Args:
            player_fpl_id: FPL ID of the player
            
        Returns:
            Detailed player information
        """
        try:
            await self._ensure_fresh_cache()
            
            # Get basic player data from cache
            player = self._player_cache.get(player_fpl_id)
            if not player:
                return None
            
            # Get additional details from FPL API
            player_history = await self.fpl_client.get_player_summary(player_fpl_id)
            
            # Combine data
            detailed_player = {
                **player,
                'history': player_history.get('history', []) if player_history else [],
                'fixtures': player_history.get('fixtures', []) if player_history else [],
                'history_past': player_history.get('history_past', []) if player_history else []
            }
            
            # Calculate additional metrics
            detailed_player.update(self._calculate_player_metrics(detailed_player))
            
            return detailed_player
            
        except Exception as e:
            logger.error(f"Error getting player details: {str(e)}")
            return None

    def _calculate_player_metrics(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional metrics for a player."""
        try:
            metrics = {}
            
            # Calculate recent form (last 5 games)
            history = player.get('history', [])
            if history:
                recent_games = history[-5:]
                recent_points = [game.get('total_points', 0) for game in recent_games]
                metrics['recent_form'] = sum(recent_points) / len(recent_points) if recent_points else 0
                metrics['recent_games_played'] = len([g for g in recent_games if g.get('minutes', 0) > 0])
            
            # Calculate consistency (standard deviation of points)
            if history:
                points_list = [game.get('total_points', 0) for game in history]
                if len(points_list) > 1:
                    mean_points = sum(points_list) / len(points_list)
                    variance = sum((x - mean_points) ** 2 for x in points_list) / len(points_list)
                    metrics['consistency_score'] = mean_points / (variance ** 0.5) if variance > 0 else mean_points
                else:
                    metrics['consistency_score'] = 0
            
            # Calculate value metrics
            total_points = player.get('total_points', 0)
            cost = player.get('now_cost', 1)
            metrics['points_per_million'] = (total_points / cost) * 10 if cost > 0 else 0
            
            # Calculate fixture difficulty
            fixtures = player.get('fixtures', [])
            if fixtures:
                upcoming_fixtures = fixtures[:5]  # Next 5 fixtures
                difficulties = [f.get('difficulty', 3) for f in upcoming_fixtures]
                metrics['avg_fixture_difficulty'] = sum(difficulties) / len(difficulties) if difficulties else 3
                metrics['upcoming_fixtures_count'] = len(upcoming_fixtures)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating player metrics: {str(e)}")
            return {}

    async def get_player_comparison(self, player_ids: List[int]) -> Dict[str, Any]:
        """
        Compare multiple players side by side.
        
        Args:
            player_ids: List of player FPL IDs to compare
            
        Returns:
            Comparison data
        """
        try:
            await self._ensure_fresh_cache()
            
            players = []
            for player_id in player_ids:
                player = self._player_cache.get(player_id)
                if player:
                    players.append(player)
            
            if not players:
                return {}
            
            # Define comparison metrics
            metrics = [
                'total_points', 'points_per_game', 'now_cost', 'form',
                'goals_scored', 'assists', 'clean_sheets', 'minutes',
                'selected_by_percent', 'transfers_in_event', 'ict_index'
            ]
            
            comparison = {
                'players': players,
                'metrics': {},
                'best_in_metric': {},
                'comparison_date': datetime.utcnow()
            }
            
            # Calculate comparisons for each metric
            for metric in metrics:
                values = [p.get(metric, 0) for p in players]
                comparison['metrics'][metric] = values
                
                # Find best player for this metric
                if values:
                    max_value = max(values)
                    best_index = values.index(max_value)
                    comparison['best_in_metric'][metric] = {
                        'player_id': players[best_index]['fpl_id'],
                        'player_name': players[best_index]['web_name'],
                        'value': max_value
                    }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing players: {str(e)}")
            return {}

    async def track_player(self, user_id: str, player_fpl_id: int) -> bool:
        """
        Add a player to user's tracking list.
        
        Args:
            user_id: User identifier
            player_fpl_id: Player FPL ID to track
            
        Returns:
            Success status
        """
        try:
            player = self._player_cache.get(player_fpl_id)
            if not player:
                return False
            
            tracking_data = {
                'player_fpl_id': player_fpl_id,
                'player_name': player['web_name'],
                'player_position': player['position'],
                'player_team': player['team'],
                'tracked_at': datetime.utcnow(),
                'tracking_notes': ''
            }
            
            # Add to user's tracked players
            doc_ref = self.db.collection('users').document(user_id)\
                        .collection('tracked_players').document(str(player_fpl_id))
            doc_ref.set(tracking_data)
            
            logger.info(f"User {user_id} started tracking player {player['web_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking player: {str(e)}")
            return False

    def untrack_player(self, user_id: str, player_fpl_id: int) -> bool:
        """
        Remove a player from user's tracking list.
        
        Args:
            user_id: User identifier
            player_fpl_id: Player FPL ID to untrack
            
        Returns:
            Success status
        """
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                        .collection('tracked_players').document(str(player_fpl_id))
            doc_ref.delete()
            
            logger.info(f"User {user_id} stopped tracking player {player_fpl_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error untracking player: {str(e)}")
            return False

    def get_tracked_players(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user's tracked players with current data.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of tracked players with current stats
        """
        try:
            docs = self.db.collection('users').document(user_id)\
                     .collection('tracked_players').stream()
            
            tracked_players = []
            
            for doc in docs:
                tracking_data = doc.to_dict()
                player_fpl_id = tracking_data['player_fpl_id']
                
                # Get current player data
                current_player = self._player_cache.get(player_fpl_id)
                if current_player:
                    tracked_player = {
                        **tracking_data,
                        'current_data': current_player,
                        'price_change_since_tracking': current_player.get('now_cost', 0) - tracking_data.get('initial_price', 0)
                    }
                    tracked_players.append(tracked_player)
            
            logger.info(f"Retrieved {len(tracked_players)} tracked players for user {user_id}")
            return tracked_players
            
        except Exception as e:
            logger.error(f"Error getting tracked players: {str(e)}")
            return []

    async def get_position_analysis(self, position: str) -> Dict[str, Any]:
        """
        Get analysis for all players in a specific position.
        
        Args:
            position: Position to analyze (GKP, DEF, MID, FWD)
            
        Returns:
            Position analysis data
        """
        try:
            await self._ensure_fresh_cache()
            
            position_players = [p for p in self._player_cache.values() 
                              if p.get('position') == position]
            
            if not position_players:
                return {}
            
            # Calculate position statistics
            total_players = len(position_players)
            total_points = sum(p.get('total_points', 0) for p in position_players)
            avg_points = total_points / total_players
            avg_cost = sum(p.get('now_cost', 0) for p in position_players) / total_players
            
            # Find top performers
            top_points = sorted(position_players, key=lambda x: x.get('total_points', 0), reverse=True)[:10]
            top_value = sorted(position_players, key=lambda x: x.get('value_season', 0), reverse=True)[:10]
            top_form = sorted(position_players, key=lambda x: x.get('form', 0), reverse=True)[:10]
            
            # Price distribution
            price_ranges = {
                'budget': [p for p in position_players if p.get('now_cost', 0) < 60],
                'mid_range': [p for p in position_players if 60 <= p.get('now_cost', 0) < 80],
                'premium': [p for p in position_players if p.get('now_cost', 0) >= 80]
            }
            
            analysis = {
                'position': position,
                'total_players': total_players,
                'avg_points': round(avg_points, 2),
                'avg_cost': round(avg_cost / 10, 1),  # Convert to millions
                'top_points': top_points,
                'top_value': top_value,
                'top_form': top_form,
                'price_distribution': {
                    'budget': len(price_ranges['budget']),
                    'mid_range': len(price_ranges['mid_range']),
                    'premium': len(price_ranges['premium'])
                },
                'analysis_date': datetime.utcnow()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting position analysis: {str(e)}")
            return {}

    async def _ensure_fresh_cache(self) -> None:
        """Ensure player cache is fresh, refresh if needed."""
        try:
            if (not self._player_cache or 
                not self._cache_expiry or 
                datetime.utcnow() > self._cache_expiry):
                
                logger.info("Player cache expired, refreshing...")
                await self.refresh_player_data()
            
        except Exception as e:
            logger.error(f"Error ensuring fresh cache: {str(e)}")

    def get_cache_status(self) -> Dict[str, Any]:
        """Get current cache status information."""
        return {
            'cached_players': len(self._player_cache),
            'cache_expiry': self._cache_expiry,
            'cache_expired': datetime.utcnow() > self._cache_expiry if self._cache_expiry else True,
            'last_refresh': self._cache_expiry - self._cache_duration if self._cache_expiry else None
        }