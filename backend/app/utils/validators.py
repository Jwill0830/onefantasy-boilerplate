"""
Input validation utilities for the OneFantasy application.
"""
import re
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from flask import request, jsonify

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_league_name(name: str) -> bool:
    """Validate league name."""
    return (
        isinstance(name, str) and 
        3 <= len(name.strip()) <= 50 and
        re.match(r'^[a-zA-Z0-9\s\-_]+$', name.strip())
    )

def validate_team_name(name: str) -> bool:
    """Validate team name."""
    return (
        isinstance(name, str) and 
        2 <= len(name.strip()) <= 30 and
        re.match(r'^[a-zA-Z0-9\s\-_]+$', name.strip())
    )

def validate_league_size(size: int) -> bool:
    """Validate league size."""
    return isinstance(size, int) and 6 <= size <= 18

def validate_pick_time(seconds: int) -> bool:
    """Validate pick time in seconds."""
    return isinstance(seconds, int) and 30 <= seconds <= 600  # 30 seconds to 10 minutes

def validate_waiver_bid(bid: Union[int, float]) -> bool:
    """Validate waiver bid amount."""
    try:
        bid_amount = float(bid)
        return 0 <= bid_amount <= 100
    except (ValueError, TypeError):
        return False

def validate_player_position(position: str) -> bool:
    """Validate player position."""
    valid_positions = ['GK', 'DEF', 'MID', 'FWD']
    return position in valid_positions

def validate_draft_pick(pick_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate draft pick data.
    
    Returns:
        Dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if not isinstance(pick_data.get('player_id'), int):
        errors.append('player_id must be an integer')
    
    if not isinstance(pick_data.get('team_id'), str) or not pick_data['team_id'].strip():
        errors.append('team_id must be a non-empty string')
    
    if not isinstance(pick_data.get('pick_number'), int) or pick_data['pick_number'] < 1:
        errors.append('pick_number must be a positive integer')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_trade_proposal(trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate trade proposal data.
    
    Returns:
        Dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    # Check required fields
    required_fields = ['from_team_id', 'to_team_id', 'from_players', 'to_players']
    for field in required_fields:
        if field not in trade_data:
            errors.append(f'{field} is required')
    
    # Validate team IDs
    if not isinstance(trade_data.get('from_team_id'), str):
        errors.append('from_team_id must be a string')
    
    if not isinstance(trade_data.get('to_team_id'), str):
        errors.append('to_team_id must be a string')
    
    # Validate player lists
    for field in ['from_players', 'to_players']:
        players = trade_data.get(field, [])
        if not isinstance(players, list):
            errors.append(f'{field} must be a list')
        elif not players:
            errors.append(f'{field} cannot be empty')
        elif not all(isinstance(p, int) for p in players):
            errors.append(f'All items in {field} must be integers')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_lineup(lineup_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate lineup data.
    
    Returns:
        Dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if not isinstance(lineup_data.get('starters'), list):
        errors.append('starters must be a list')
    
    if not isinstance(lineup_data.get('bench'), list):
        errors.append('bench must be a list')
    
    starters = lineup_data.get('starters', [])
    bench = lineup_data.get('bench', [])
    
    # Check for valid player IDs
    all_players = starters + bench
    if not all(isinstance(p, int) for p in all_players):
        errors.append('All player IDs must be integers')
    
    # Check for duplicates
    if len(all_players) != len(set(all_players)):
        errors.append('Duplicate players found in lineup')
    
    # Check lineup size (11 starters + bench)
    if len(starters) != 11:
        errors.append('Must have exactly 11 starters')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_json_request(required_fields: List[str] = None, optional_fields: List[str] = None):
    """
    Decorator to validate JSON request data.
    
    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            errors = []
            
            # Check required fields
            if required_fields:
                for field in required_fields:
                    if field not in data:
                        errors.append(f'{field} is required')
            
            # Check for unexpected fields
            allowed_fields = set((required_fields or []) + (optional_fields or []))
            if allowed_fields:
                unexpected = set(data.keys()) - allowed_fields
                if unexpected:
                    errors.append(f'Unexpected fields: {", ".join(unexpected)}')
            
            if errors:
                return jsonify({'error': 'Validation failed', 'details': errors}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_string(value: str, max_length: int = None) -> str:
    """
    Sanitize string input by trimming whitespace and limiting length.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    
    sanitized = value.strip()
    
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def validate_pagination_params(page: Any, per_page: Any) -> Dict[str, Union[int, List[str]]]:
    """
    Validate pagination parameters.
    
    Returns:
        Dict with validated params or errors
    """
    errors = []
    
    try:
        page = int(page) if page else 1
        if page < 1:
            errors.append('page must be >= 1')
    except (ValueError, TypeError):
        errors.append('page must be an integer')
        page = 1
    
    try:
        per_page = int(per_page) if per_page else 20
        if per_page < 1 or per_page > 100:
            errors.append('per_page must be between 1 and 100')
    except (ValueError, TypeError):
        errors.append('per_page must be an integer')
        per_page = 20
    
    return {
        'page': page,
        'per_page': per_page,
        'errors': errors
    }