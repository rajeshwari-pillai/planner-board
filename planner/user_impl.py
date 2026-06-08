import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from planner.setup import initialize
initialize()

from planner.models import User, TeamMembership
from user_base import UserBase


class UserImpl(UserBase):

    def create_user(self, request: str) -> str:
        """
        Create a new user.
        Input:  {"name": "<user_name>", "display_name": "<display_name>"}
        Output: {"id": "<user_id>"}
        """
        data = json.loads(request)
        name = data.get('name', '').strip()
        display_name = data.get('display_name', '').strip()

        if not name:
            raise ValueError("Name is required")
        if len(name) > 64:
            raise ValueError("Name can be max 64 characters")
        if len(display_name) > 64:
            raise ValueError("Display name can be max 64 characters")
        if User.objects.filter(name=name).exists():
            raise ValueError(f"User with name '{name}' already exists")

        user = User.objects.create(name=name, display_name=display_name)
        return json.dumps({"id": str(user.id)})

    def list_users(self) -> str:
        """
        List all users.
        Output: [{"name": ..., "display_name": ..., "creation_time": ...}]
        """
        users = User.objects.all().order_by('creation_time')
        result = [
            {
                "name": u.name,
                "display_name": u.display_name,
                "creation_time": u.creation_time.isoformat(),
            }
            for u in users
        ]
        return json.dumps(result)

    def describe_user(self, request: str) -> str:
        """
        Describe a user by id.
        Input:  {"id": "<user_id>"}
        Output: {"name": ..., "description": ..., "creation_time": ...}
        """
        data = json.loads(request)
        user_id = data.get('id')
        user = self._get_user(user_id)
        return json.dumps({
            "name": user.name,
            "description": user.display_name,
            "creation_time": user.creation_time.isoformat(),
        })

    def update_user(self, request: str) -> str:
        """
        Update a user's display name. Username cannot be changed.
        Input:  {"id": "<user_id>", "user": {"display_name": "<new_display_name>"}}
        Output: {}
        """
        data = json.loads(request)
        user_id = data.get('id')
        user_data = data.get('user', {})

        if 'name' in user_data:
            raise ValueError("User name cannot be updated")

        display_name = user_data.get('display_name', '').strip()
        if len(display_name) > 128:
            raise ValueError("Display name can be max 128 characters")

        user = self._get_user(user_id)
        if display_name:
            user.display_name = display_name
            user.save(update_fields=['display_name'])

        return json.dumps({})

    def get_user_teams(self, request: str) -> str:
        """
        Get all teams a user belongs to.
        Input:  {"id": "<user_id>"}
        Output: [{"name": ..., "description": ..., "creation_time": ...}]
        """
        data = json.loads(request)
        user_id = data.get('id')
        user = self._get_user(user_id)

        memberships = (
            TeamMembership.objects
            .filter(user=user)
            .select_related('team')
            .order_by('team__creation_time')
        )
        result = [
            {
                "name": m.team.name,
                "description": m.team.description,
                "creation_time": m.team.creation_time.isoformat(),
            }
            for m in memberships
        ]
        return json.dumps(result)

    def _get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            raise ValueError(f"User with id '{user_id}' not found")
