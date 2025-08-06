from app import db
from app.utils.logger import log_error

class Team:
    def __init__(self, team_id=None, league_id=None, data=None):
        self.team_id = team_id
        self.league_id = league_id
        self.data = data or {}

    @classmethod
    def create(cls, league_id, data):
        """
        Create a new team in a league.
        :param league_id: str
        :param data: dict containing team details (e.g., {'owner_id': 'user123', 'name': 'Team A'})
        :return: Team instance
        """
        try:
            if not league_id:
                raise ValueError("League ID required")
            ref = db.collection('leagues').document(league_id).collection('teams').document()
            ref.set(data)
            return cls(team_id=ref.id, league_id=league_id, data=data)
        except ValueError as e:
            log_error(f"Validation error creating team: {str(e)}")
            raise
        except Exception as e:
            log_error(f"Error creating team in league {league_id}: {str(e)}", exc_info=True)
            raise

    def get(self):
        """
        Fetch team data by ID.
        """
        try:
            doc = db.collection('leagues').document(self.league_id).collection('teams').document(self.team_id).get()
            if doc.exists:
                self.data = doc.to_dict()
                return self.data
            else:
                raise ValueError("Team not found")
        except Exception as e:
            log_error(f"Error fetching team {self.team_id} in league {self.league_id}: {str(e)}", exc_info=True)
            raise

    def update(self, updates):
        """
        Update team details, e.g., roster, settings.
        :param updates: dict of fields to update
        """
        try:
            db.collection('leagues').document(self.league_id).collection('teams').document(self.team_id).update(updates)
            self.data.update(updates)
        except Exception as e:
            log_error(f"Error updating team {self.team_id}: {str(e)}", exc_info=True)
            raise

    def delete(self):
        """
        Delete the team.
        """
        try:
            db.collection('leagues').document(self.league_id).collection('teams').document(self.team_id).delete()
        except Exception as e:
            log_error(f"Error deleting team {self.team_id}: {str(e)}", exc_info=True)
            raise

    # Add roster management
    def add_player(self, player_id):
        """
        Add a player to the team's roster.
        :param player_id: str
        """
        try:
            roster = self.data.get('roster', [])
            if player_id not in roster:
                roster.append(player_id)
                self.update({'roster': roster})
        except Exception as e:
            log_error(f"Error adding player {player_id} to team {self.team_id}: {str(e)}", exc_info=True)
            raise

    def remove_player(self, player_id):
        """
        Remove a player from the team's roster.
        :param player_id: str
        """
        try:
            roster = self.data.get('roster', [])
            if player_id in roster:
                roster.remove(player_id)
                self.update({'roster': roster})
        except Exception as e:
            log_error(f"Error removing player {player_id} from team {self.team_id}: {str(e)}", exc_info=True)
            raise

    # Get roster
    def get_roster(self):
        return self.data.get('roster', [])