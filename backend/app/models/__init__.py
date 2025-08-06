"""
Models package initialization.
Import model classes only if they exist to avoid import errors.
"""

# Try to import each model, but don't fail if they don't exist yet
__all__ = []

try:
    from .league_model import LeagueModel
    __all__.append('LeagueModel')
except ImportError:
    pass

try:
    from .team_model import TeamModel
    __all__.append('TeamModel')
except ImportError:
    pass

try:
    from .player_model import PlayerModel
    __all__.append('PlayerModel')
except ImportError:
    pass

try:
    from .draft_model import DraftModel
    __all__.append('DraftModel')
except ImportError:
    pass

try:
    from .trade_model import TradeModel
    __all__.append('TradeModel')
except ImportError:
    pass

try:
    from .chat_model import ChatModel
    __all__.append('ChatModel')
except ImportError:
    pass

# Log which models were successfully imported
import logging
logger = logging.getLogger(__name__)

if __all__:
    logger.info(f"Successfully imported models: {', '.join(__all__)}")
else:
    logger.warning("No model files found - models package is empty")