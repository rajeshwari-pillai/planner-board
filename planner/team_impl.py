import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from planner.setup import initialize
initialize()

from planner.models import User, Team, TeamMembership
from team_base import TeamBase

MAX_TEAM_MEMBERS = 50


class TeamImpl(TeamBase):

    def create_team(self, request: str) -> str:
        """
        Create a new team.
        Input:  {"name": "<team_name>", "description": "<description>", "admin": "<user_id>"}
        Output: {"id": "<team_id>"}
        """
        data = json.loads(request)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        admin_id = data.get('admin')

        if not name:
            raise ValueError("Team name is required")
        if len(name) > 64:
            raise ValueError("Team name can be max 64 characters")
        if len(description) > 128:
            raise ValueError("Description can be max 128 characters")
        if Team.objects.filter(name=name).exists():
            raise ValueError(f"Team with name '{name}' already exists")

        admin = self._get_user(admin_id)
        team = Team.objects.create(name=name, description=description, admin=admin)
        return json.dumps({"id": str(team.id)})

    def list_teams(self) -> str:
        """
        List all teams.
        Output: [{"name": ..., "description": ..., "creation_time": ..., "admin": "<user_id>"}]
        """
        teams = Team.objects.all().select_related('admin').order_by('creation_time')
        result = [
            {
                "name": t.name,
                "description": t.description,
                "creation_time": t.creation_time.isoformat(),
                "admin": str(t.admin_id),
            }
            for t in teams
        ]
        return json.dumps(result)

    def describe_team(self, request: str) -> str:
        """
        Describe a team by id.
        Input:  {"id": "<team_id>"}
        Output: {"name": ..., "description": ..., "creation_time": ..., "admin": "<user_id>"}
        """
        data = json.loads(request)
        team = self._get_team(data.get('id'))
        return json.dumps({
            "name": team.name,
            "description": team.description,
            "creation_time": team.creation_time.isoformat(),
            "admin": str(team.admin_id),
        })

    def update_team(self, request: str) -> str:
        """
        Update team name, description, or admin.
        Input:  {"id": "<team_id>", "team": {"name": ..., "description": ..., "admin": "<user_id>"}}
        Output: {}
        """
        data = json.loads(request)
        team = self._get_team(data.get('id'))
        team_data = data.get('team', {})

        name = team_data.get('name', '').strip()
        description = team_data.get('description', '').strip()
        admin_id = team_data.get('admin')

        if name:
            if len(name) > 64:
                raise ValueError("Team name can be max 64 characters")
            if Team.objects.filter(name=name).exclude(id=team.id).exists():
                raise ValueError(f"Team with name '{name}' already exists")
            team.name = name

        if description:
            if len(description) > 128:
                raise ValueError("Description can be max 128 characters")
            team.description = description

        if admin_id:
            team.admin = self._get_user(admin_id)

        team.save()
        return json.dumps({})

    def add_users_to_team(self, request: str):
        """
        Add users to a team. Total members cannot exceed 50.
        Input:  {"id": "<team_id>", "users": ["<user_id>", ...]}
        Output: {}
        """
        data = json.loads(request)
        team = self._get_team(data.get('id'))
        user_ids = data.get('users', [])

        current_count = TeamMembership.objects.filter(team=team).count()
        new_users = [uid for uid in user_ids
                     if not TeamMembership.objects.filter(team=team, user_id=uid).exists()]

        if current_count + len(new_users) > MAX_TEAM_MEMBERS:
            raise ValueError(
                f"Adding these users would exceed the maximum team size of {MAX_TEAM_MEMBERS}"
            )

        for uid in new_users:
            user = self._get_user(uid)
            TeamMembership.objects.create(team=team, user=user)

        return json.dumps({})

    def remove_users_from_team(self, request: str):
        """
        Remove users from a team.
        Input:  {"id": "<team_id>", "users": ["<user_id>", ...]}
        Output: {}
        """
        data = json.loads(request)
        team = self._get_team(data.get('id'))
        user_ids = data.get('users', [])

        TeamMembership.objects.filter(team=team, user_id__in=user_ids).delete()
        return json.dumps({})

    def list_team_users(self, request: str):
        """
        List all users in a team.
        Input:  {"id": "<team_id>"}
        Output: [{"id": ..., "name": ..., "display_name": ...}]
        """
        data = json.loads(request)
        team = self._get_team(data.get('id'))

        memberships = (
            TeamMembership.objects
            .filter(team=team)
            .select_related('user')
            .order_by('joined_at')
        )
        result = [
            {
                "id": str(m.user.id),
                "name": m.user.name,
                "display_name": m.user.display_name,
            }
            for m in memberships
        ]
        return json.dumps(result)

    def _get_team(self, team_id):
        try:
            return Team.objects.get(id=team_id)
        except (Team.DoesNotExist, ValueError):
            raise ValueError(f"Team with id '{team_id}' not found")

    def _get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            raise ValueError(f"User with id '{user_id}' not found")
