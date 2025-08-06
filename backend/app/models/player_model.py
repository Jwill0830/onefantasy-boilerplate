"""
Player data model and Firestore operations.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from .. import get_db
from ..utils.logger import get_logger
from ..utils.api_integrations import get_fpl_client

logger = get_logger('player_model')

class PlayerModel:
    """Model for player operations and caching."""
    
    def __init__(self):
        self.db = get_db()
        self.fpl_client = get_fpl_client()
        self.collection = 'players'
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
    
    def sync_players_from_fpl(self) -> bool:
        """Sync player data from FPL API to Firestore."""
        try:
            logger.info("Starting player data sync from FPL API")
            
            # Get bootstrap data from FPL
            bootstrap_data = self.fpl_client.get_bootstrap_data()
            if not bootstrap_data:
                logger.error("Failed to fetch bootstrap data from FPL")
                return False
            
            players = bootstrap_data.get('elements', [])
            teams = bootstrap_data.get('teams', [])
            element_types = bootstrap_data.get('element_types', [])
            
            # Create lookup dictionaries
            team_lookup = {team['id']: team for team in teams}
            position_lookup = {pos['id']: pos for pos in element_types}
            
            # Process players
            processed_count = 0
            batch = self.db.batch()
            batch_size = 0
            
            for player in players:
                try:
                    player_doc = self._format_player_data(player, team_lookup, position_lookup)
                    
                    # Add to batch
                    doc_ref = self.db.collection(self.collection).document(str(player['id']))
                    batch.set(doc_ref, player_doc)
                    batch_size += 1
                    
                    # Commit batch every 500 documents
                    if batch_size >= 500:
                        batch.commit()
                        batch = self.db.batch()
                        batch_size = 0
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process player {player.get('id')}: {e}")
                    continue
            
            # Commit remaining documents
            if batch_size > 0:
                batch.commit()
            
            # Update sync metadata
            self._update_sync_metadata(processed_count)
            
            logger.info(f"Successfully synced {processed_count} players")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync players: {e}")
            return False
    
    def get_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player by ID."""
        try:
            doc = self.db.collection(self.collection).document(str(player_id)).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to get player {player_id}: {e}")
            return None
    
    def get_players(self, player_ids: List[int]) -> List[Dict[str, Any]]:
        """Get multiple players by IDs."""
        try:
            players = []
            
            # Firestore has a limit of 10 documents per get() call
            for i in range(0, len(player_ids), 10):
                batch_ids = player_ids[i:i+10]
                doc_refs = [self.db.collection(self.collection).document(str(pid)) for pid in batch_ids]
                docs = self.db.get_all(doc_refs)
                
                for doc in docs:
                    if doc.exists:
                        players.append(doc.to_dict())
            
            return players
            
        except Exception as e:
            logger.error(f"Failed to get players: {e}")
            return []
    
    def search_players(self, query: str = '', position: str = '', team: str = '', 
                      available_only: bool = False, league_id: str = None,
                      limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search players with filters.
        
        Returns:
            Tuple of (players_list, total_count)
        """
        try:
            # Start with base query
            players_ref = self.db.collection(self.collection)
            
            # Apply filters
            if position:
                players_ref = players_ref.where('position_short', '==', position)
            
            if team:
                players_ref = players_ref.where('team_short', '==', team)
            
            # Get all matching documents
            docs = list(players_ref.stream())
            all_players = [doc.to_dict() for doc in docs]
            
            # Apply text search filter
            if query:
                query_lower = query.lower()
                all_players = [
                    player for player in all_players
                    if (query_lower in player.get('name', '').lower() or
                        query_lower in player.get('web_name', '').lower() or
                        query_lower in player.get('team', '').lower())
                ]
            
            # Apply availability filter
            if available_only and league_id:
                drafted_players = self._get_drafted_players(league_id)
                all_players = [
                    player for player in all_players
                    if player.get('id') not in drafted_players
                ]
            
            # Sort by total points (descending)
            all_players.sort(key=lambda p: p.get('total_points', 0), reverse=True)
            
            total_count = len(all_players)
            
            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            paginated_players = all_players[start_idx:end_idx]
            
            return paginated_players, total_count
            
        except Exception as e:
            logger.error(f"Failed to search players: {e}")
            return [], 0
    
    def get_trending_players(self, league_id: str = None, timeframe: str = 'week') -> List[Dict[str, Any]]:
        """
        Get trending players based on adds/drops.
        
        Args:
            league_id: Optional league ID for league-specific trends
            timeframe: 'week' or 'month'
        """
        try:
            # Calculate timeframe
            if timeframe == 'week':
                since_date = datetime.utcnow() - timedelta(days=7)
            else:  # month
                since_date = datetime.utcnow() - timedelta(days=30)
            
            # Query transactions for adds/drops
            transactions_ref = self.db.collection_group('transactions')
            transactions_ref = transactions_ref.where('timestamp', '>=', since_date)
            transactions_ref = transactions_ref.where('type', 'in', ['waiver_claim', 'free_agent_add', 'drop'])
            
            if league_id:
                transactions_ref = transactions_ref.where('league_id', '==', league_id)
            
            # Process transactions to calculate trends
            player_trends = {}
            for doc in transactions_ref.stream():
                transaction = doc.to_dict()
                player_id = transaction.get('player_id')
                
                if not player_id:
                    continue
                
                if player_id not in player_trends:
                    player_trends[player_id] = {'adds': 0, 'drops': 0}
                
                if transaction.get('type') in ['waiver_claim', 'free_agent_add']:
                    player_trends[player_id]['adds'] += 1
                elif transaction.get('type') == 'drop':
                    player_trends[player_id]['drops'] += 1
            
            # Calculate net adds and sort
            trending_data = []
            for player_id, trends in player_trends.items():
                net_adds = trends['adds'] - trends['drops']
                if net_adds > 0:  # Only include players with positive trend
                    trending_data.append({
                        'player_id': int(player_id),
                        'net_adds': net_adds,
                        'total_adds': trends['adds'],
                        'total_drops': trends['drops']
                    })
            
            # Sort by net adds
            trending_data.sort(key=lambda x: x['net_adds'], reverse=True)
            
            # Get player details for top trending players
            top_trending = trending_data[:20]  # Top 20
            player_ids = [item['player_id'] for item in top_trending]
            players = self.get_players(player_ids)
            
            # Merge trend data with player data
            player_map = {p['id']: p for p in players}
            result = []
            
            for trend_item in top_trending:
                player_id = trend_item['player_id']
                if player_id in player_map:
                    player_data = player_map[player_id].copy()
                    player_data['trend_data'] = {
                        'net_adds': trend_item['net_adds'],
                        'total_adds': trend_item['total_adds'],
                        'total_drops': trend_item['total_drops']
                    }
                    result.append(player_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get trending players: {e}")
            return []
    
    def get_player_leaders(self, stat: str = 'total_points', position: str = '', 
                          limit: int = 20) -> List[Dict[str, Any]]:
        """Get league leaders for a specific stat."""
        try:
            # Start with base query
            players_ref = self.db.collection(self.collection)
            
            # Apply position filter
            if position:
                players_ref = players_ref.where('position_short', '==', position)
            
            # Order by stat and limit
            if stat in ['total_points', 'goals_scored', 'assists', 'clean_sheets', 'saves']:
                players_ref = players_ref.order_by(stat, direction='DESCENDING').limit(limit)
            else:
                # For custom stats, get all and sort in memory
                docs = list(players_ref.stream())
                all_players = [doc.to_dict() for doc in docs]
                all_players.sort(key=lambda p: p.get(stat, 0), reverse=True)
                return all_players[:limit]
            
            return [doc.to_dict() for doc in players_ref.stream()]
            
        except Exception as e:
            logger.error(f"Failed to get player leaders for {stat}: {e}")
            return []
    
    def get_available_players(self, league_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get players available for waiver claims or free agent adds."""
        try:
            # Get all drafted players in the league
            drafted_players = self._get_drafted_players(league_id)
            
            # Query all players not drafted
            all_players_ref = self.db.collection(self.collection)
            all_players = [doc.to_dict() for doc in all_players_ref.stream()]
            
            # Filter out drafted players
            available_players = [
                player for player in all_players
                if player.get('id') not in drafted_players
            ]
            
            # Sort by total points
            available_players.sort(key=lambda p: p.get('total_points', 0), reverse=True)
            
            return available_players[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get available players for league {league_id}: {e}")
            return []
    
    def update_player_stats(self, player_id: int, stats_update: Dict[str, Any]) -> bool:
        """Update player statistics."""
        try:
            stats_update['last_updated'] = datetime.utcnow()
            
            doc_ref = self.db.collection(self.collection).document(str(player_id))
            doc_ref.update(stats_update)
            
            logger.info(f"Updated stats for player {player_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update player stats for {player_id}: {e}")
            return False
    
    def _format_player_data(self, player: Dict, team_lookup: Dict, position_lookup: Dict) -> Dict[str, Any]:
        """Format player data for Firestore storage."""
        team_info = team_lookup.get(player['team'], {})
        position_info = position_lookup.get(player['element_type'], {})
        
        return {
            'id': player['id'],
            'name': f"{player['first_name']} {player['second_name']}",
            'web_name': player['web_name'],
            'first_name': player['first_name'],
            'second_name': player['second_name'],
            'position': position_info.get('singular_name', 'Unknown'),
            'position_short': position_info.get('singular_name_short', 'UNK'),
            'team': team_info.get('name', 'Unknown'),
            'team_short': team_info.get('short_name', 'UNK'),
            'team_id': player['team'],
            'total_points': player['total_points'],
            'points_per_game': float(player['points_per_game']),
            'form': float(player['form']),
            'selected_by_percent': float(player['selected_by_percent']),
            'now_cost': player['now_cost'],
            'cost_change_start': player['cost_change_start'],
            'goals_scored': player['goals_scored'],
            'assists': player['assists'],
            'clean_sheets': player['clean_sheets'],
            'goals_conceded': player['goals_conceded'],
            'saves': player['saves'],
            'yellow_cards': player['yellow_cards'],
            'red_cards': player['red_cards'],
            'minutes': player['minutes'],
            'bonus': player['bonus'],
            'bps': player['bps'],
            'influence': float(player['influence']),
            'creativity': float(player['creativity']),
            'threat': float(player['threat']),
            'ict_index': float(player['ict_index']),
            'status': player['status'],
            'news': player['news'],
            'photo_url': f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{player['photo'].replace('.jpg', '.png')}" if player.get('photo') else None,
            'last_updated': datetime.utcnow(),
            'dreamteam_count': player.get('dreamteam_count', 0),
            'value_form': float(player.get('value_form', 0)),
            'value_season': float(player.get('value_season', 0)),
            'transfers_in': player.get('transfers_in', 0),
            'transfers_out': player.get('transfers_out', 0),
            'transfers_in_event': player.get('transfers_in_event', 0),
            'transfers_out_event': player.get('transfers_out_event', 0)
        }
    
    def _get_drafted_players(self, league_id: str) -> set:
        """Get set of all drafted player IDs in a league."""
        try:
            # Query all teams in the league
            teams_ref = self.db.collection('leagues').document(league_id).collection('teams')
            
            drafted_players = set()
            for team_doc in teams_ref.stream():
                team_data = team_doc.to_dict()
                roster = team_data.get('roster', {})
                
                # Add all players from roster
                starters = roster.get('starters', [])
                bench = roster.get('bench', [])
                
                drafted_players.update(starters)
                drafted_players.update(bench)
            
            return drafted_players
            
        except Exception as e:
            logger.error(f"Failed to get drafted players for league {league_id}: {e}")
            return set()
    
    def _update_sync_metadata(self, player_count: int):
        """Update sync metadata."""
        try:
            metadata = {
                'last_sync': datetime.utcnow(),
                'player_count': player_count,
                'sync_version': '1.0'
            }
            
            doc_ref = self.db.collection('metadata').document('player_sync')
            doc_ref.set(metadata)
            
        except Exception as e:
            logger.error(f"Failed to update sync metadata: {e}")
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync."""
        try:
            doc = self.db.collection('metadata').document('player_sync').get()
            if doc.exists:
                return doc.to_dict().get('last_sync')
            return None
        except Exception as e:
            logger.error(f"Failed to get last sync time: {e}")
            return None
    
    def is_sync_needed(self) -> bool:
        """Check if player data sync is needed."""
        last_sync = self.get_last_sync_time()
        if not last_sync:
            return True
        
        return datetime.utcnow() - last_sync > self.cache_duration