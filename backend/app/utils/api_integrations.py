"""
External API integration utilities for the OneFantasy application.
"""
import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger('api_integrations')

class FPLAPIClient:
    """Client for Fantasy Premier League API."""
    
    def __init__(self):
        self.base_url = 'https://fantasy.premierleague.com/api'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OneFantasy/1.0'
        })
        self._cache = {}
        self._cache_timeout = 3600  # 1 hour
    
    def _get_cached_or_fetch(self, key: str, url: str, params: Dict = None) -> Optional[Dict]:
        """Get data from cache or fetch from API."""
        now = time.time()
        
        # Check cache
        if key in self._cache:
            cached_data, timestamp = self._cache[key]
            if now - timestamp < self._cache_timeout:
                logger.debug(f"Returning cached data for {key}")
                return cached_data
        
        # Fetch from API
        try:
            logger.info(f"Fetching data from FPL API: {url}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._cache[key] = (data, now)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            return None
    
    def get_bootstrap_data(self) -> Optional[Dict]:
        """Get bootstrap static data including players, teams, and game settings."""
        url = f"{self.base_url}/bootstrap-static/"
        return self._get_cached_or_fetch('bootstrap', url)
    
    def get_player_data(self, player_id: int) -> Optional[Dict]:
        """Get detailed data for a specific player."""
        url = f"{self.base_url}/element-summary/{player_id}/"
        return self._get_cached_or_fetch(f'player_{player_id}', url)
    
    def get_fixtures(self, gameweek: Optional[int] = None) -> Optional[List[Dict]]:
        """Get fixture data, optionally filtered by gameweek."""
        url = f"{self.base_url}/fixtures/"
        params = {'event': gameweek} if gameweek else None
        
        cache_key = f'fixtures_{gameweek}' if gameweek else 'fixtures_all'
        return self._get_cached_or_fetch(cache_key, url, params)
    
    def get_current_gameweek(self) -> Optional[int]:
        """Get the current gameweek number."""
        bootstrap = self.get_bootstrap_data()
        if not bootstrap:
            return None
        
        events = bootstrap.get('events', [])
        for event in events:
            if event.get('is_current'):
                return event.get('id')
        
        return None
    
    def get_teams(self) -> Optional[List[Dict]]:
        """Get Premier League teams data."""
        bootstrap = self.get_bootstrap_data()
        if bootstrap:
            return bootstrap.get('teams', [])
        return None
    
    def get_players(self) -> Optional[List[Dict]]:
        """Get all players data."""
        bootstrap = self.get_bootstrap_data()
        if bootstrap:
            return bootstrap.get('elements', [])
        return None
    
    def get_player_types(self) -> Optional[List[Dict]]:
        """Get player position types."""
        bootstrap = self.get_bootstrap_data()
        if bootstrap:
            return bootstrap.get('element_types', [])
        return None
    
    def get_gameweek_live_data(self, gameweek: int) -> Optional[Dict]:
        """Get live data for a specific gameweek."""
        url = f"{self.base_url}/event/{gameweek}/live/"
        return self._get_cached_or_fetch(f'live_{gameweek}', url)
    
    def search_players(self, query: str, position: Optional[str] = None, 
                      team: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """
        Search players by name, position, or team.
        
        Args:
            query: Search query for player name
            position: Filter by position (GK, DEF, MID, FWD)
            team: Filter by team ID
            limit: Maximum results to return
            
        Returns:
            List of matching players
        """
        players = self.get_players()
        if not players:
            return []
        
        # Position mapping
        position_map = {'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
        position_id = position_map.get(position) if position else None
        
        results = []
        query_lower = query.lower() if query else ''
        
        for player in players:
            # Name filter
            if query and query_lower not in (player.get('web_name', '') + ' ' + 
                                           player.get('first_name', '') + ' ' + 
                                           player.get('second_name', '')).lower():
                continue
            
            # Position filter
            if position_id and player.get('element_type') != position_id:
                continue
            
            # Team filter
            if team and player.get('team') != team:
                continue
            
            results.append(player)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_player_stats(self, player_id: int) -> Dict[str, Any]:
        """
        Get comprehensive stats for a player.
        
        Returns:
            Dict with player stats including form, points, etc.
        """
        player_data = self.get_player_data(player_id)
        bootstrap = self.get_bootstrap_data()
        
        if not bootstrap:
            return {}
        
        # Find player in bootstrap data
        players = bootstrap.get('elements', [])
        player_info = next((p for p in players if p['id'] == player_id), None)
        
        if not player_info:
            return {}
        
        # Get team info
        teams = bootstrap.get('teams', [])
        team_info = next((t for t in teams if t['id'] == player_info['team']), None)
        
        # Get position info
        element_types = bootstrap.get('element_types', [])
        position_info = next((et for et in element_types if et['id'] == player_info['element_type']), None)
        
        stats = {
            'id': player_info['id'],
            'name': f"{player_info['first_name']} {player_info['second_name']}",
            'web_name': player_info['web_name'],
            'position': position_info['singular_name'] if position_info else 'Unknown',
            'position_short': position_info['singular_name_short'] if position_info else 'UNK',
            'team': team_info['name'] if team_info else 'Unknown',
            'team_short': team_info['short_name'] if team_info else 'UNK',
            'total_points': player_info['total_points'],
            'points_per_game': player_info['points_per_game'],
            'form': player_info['form'],
            'selected_by_percent': player_info['selected_by_percent'],
            'now_cost': player_info['now_cost'],
            'cost_change_start': player_info['cost_change_start'],
            'goals_scored': player_info['goals_scored'],
            'assists': player_info['assists'],
            'clean_sheets': player_info['clean_sheets'],
            'goals_conceded': player_info['goals_conceded'],
            'saves': player_info['saves'],
            'yellow_cards': player_info['yellow_cards'],
            'red_cards': player_info['red_cards'],
            'minutes': player_info['minutes'],
            'bonus': player_info['bonus'],
            'bps': player_info['bps'],
            'influence': player_info['influence'],
            'creativity': player_info['creativity'],
            'threat': player_info['threat'],
            'ict_index': player_info['ict_index'],
            'status': player_info['status'],
            'news': player_info['news'],
            'photo': f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{player_info['photo'].replace('.jpg', '.png')}" if player_info.get('photo') else None
        }
        
        # Add detailed fixture and history data if available
        if player_data:
            stats.update({
                'fixtures': player_data.get('fixtures', []),
                'history': player_data.get('history', []),
                'history_past': player_data.get('history_past', [])
            })
        
        return stats

class NewsAPIClient:
    """Client for fetching football news."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = 'https://newsapi.org/v2'
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                'X-API-Key': api_key
            })
    
    def get_premier_league_news(self, limit: int = 10) -> List[Dict]:
        """Get latest Premier League news."""
        if not self.api_key:
            logger.warning("News API key not configured")
            return []
        
        try:
            url = f"{self.base_url}/everything"
            params = {
                'q': 'Premier League OR EPL OR English Premier League',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('articles', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch news: {e}")
            return []
    
    def get_player_news(self, player_name: str, limit: int = 5) -> List[Dict]:
        """Get news about a specific player."""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/everything"
            params = {
                'q': f'"{player_name}" AND (Premier League OR EPL)',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('articles', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch player news for {player_name}: {e}")
            return []

# Global instances
fpl_client = FPLAPIClient()
news_client = NewsAPIClient()

def get_fpl_client() -> FPLAPIClient:
    """Get the FPL API client instance."""
    return fpl_client

def get_news_client() -> NewsAPIClient:
    """Get the News API client instance."""
    return news_client