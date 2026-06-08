import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from planner.setup import initialize
initialize()

from django.utils import timezone
from planner.models import Board, Task, Team, User
from project_board_base import ProjectBoardBase

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
VALID_TASK_STATUSES = {Task.OPEN, Task.IN_PROGRESS, Task.COMPLETE}


class ProjectBoardImpl(ProjectBoardBase):

    def create_board(self, request: str) -> str:
        """
        Create a new board for a team. Board name must be unique per team.
        Input:  {"name": ..., "description": ..., "team_id": ..., "creation_time": ...}
        Output: {"id": "<board_id>"}
        """
        data = json.loads(request)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        team_id = data.get('team_id')
        creation_time = data.get('creation_time')

        if not name:
            raise ValueError("Board name is required")
        if len(name) > 64:
            raise ValueError("Board name can be max 64 characters")
        if len(description) > 128:
            raise ValueError("Description can be max 128 characters")

        team = self._get_team(team_id)

        if Board.objects.filter(name=name, team=team).exists():
            raise ValueError(f"Board with name '{name}' already exists for this team")

        kwargs = dict(name=name, description=description, team=team)
        if creation_time:
            kwargs['creation_time'] = self._parse_dt(creation_time)

        board = Board.objects.create(**kwargs)
        return json.dumps({"id": str(board.id)})

    def close_board(self, request: str) -> str:
        """
        Close a board. All tasks must be COMPLETE before closing.
        Input:  {"id": "<board_id>"}
        Output: {}
        """
        data = json.loads(request)
        board = self._get_board(data.get('id'))

        if board.status == Board.CLOSED:
            raise ValueError("Board is already closed")

        incomplete = board.tasks.exclude(status=Task.COMPLETE).count()
        if incomplete > 0:
            raise ValueError(
                f"Cannot close board: {incomplete} task(s) are not yet COMPLETE"
            )

        board.status = Board.CLOSED
        board.end_time = timezone.now()
        board.save(update_fields=['status', 'end_time'])
        return json.dumps({})

    def add_task(self, request: str) -> str:
        """
        Add a task to an OPEN board.

        Note: the base docstring omits board_id. This implementation requires it.
        Input:  {"title": ..., "description": ..., "user_id": ..., "board_id": ...,
                 "creation_time": ...}
        Output: {"id": "<task_id>"}
        """
        data = json.loads(request)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        user_id = data.get('user_id')
        board_id = data.get('board_id')
        creation_time = data.get('creation_time')

        if not title:
            raise ValueError("Task title is required")
        if len(title) > 64:
            raise ValueError("Task title can be max 64 characters")
        if len(description) > 128:
            raise ValueError("Description can be max 128 characters")

        board = self._get_board(board_id)
        if board.status == Board.CLOSED:
            raise ValueError("Cannot add tasks to a closed board")

        user = self._get_user(user_id)

        if Task.objects.filter(title=title, board=board).exists():
            raise ValueError(f"Task with title '{title}' already exists on this board")

        kwargs = dict(title=title, description=description, board=board, assigned_to=user)
        if creation_time:
            kwargs['creation_time'] = self._parse_dt(creation_time)

        task = Task.objects.create(**kwargs)
        return json.dumps({"id": str(task.id)})

    def update_task_status(self, request: str):
        """
        Update a task's status.
        Input:  {"id": "<task_id>", "status": "OPEN | IN_PROGRESS | COMPLETE"}
        Output: {}
        """
        data = json.loads(request)
        task_id = data.get('id')
        status = data.get('status', '').strip().upper()

        if status not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_TASK_STATUSES))}"
            )

        task = self._get_task(task_id)
        task.status = status
        task.save(update_fields=['status'])
        return json.dumps({})

    def list_boards(self, request: str) -> str:
        """
        List all OPEN boards for a team.
        Input:  {"id": "<team_id>"}
        Output: [{"id": ..., "name": ...}]
        """
        data = json.loads(request)
        team = self._get_team(data.get('id'))

        boards = Board.objects.filter(team=team, status=Board.OPEN).order_by('creation_time')
        result = [{"id": str(b.id), "name": b.name} for b in boards]
        return json.dumps(result)

    def export_board(self, request: str) -> str:
        """
        Export a board as a formatted txt file in the out/ folder.
        Input:  {"id": "<board_id>"}
        Output: {"out_file": "<filename>"}
        """
        data = json.loads(request)
        board = self._get_board(data.get('id'))
        tasks = list(board.tasks.select_related('assigned_to').order_by('creation_time'))

        content = self._render_board(board, tasks)

        os.makedirs(OUT_DIR, exist_ok=True)
        slug = re.sub(r'[^a-z0-9_]', '_', board.name.lower())
        filename = f"{slug}_{str(board.id)[:8]}.txt"
        filepath = os.path.join(OUT_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return json.dumps({"out_file": filename})

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render_board(self, board: Board, tasks: list) -> str:
        WIDTH = 66

        total = len(tasks)
        complete = sum(1 for t in tasks if t.status == Task.COMPLETE)
        in_progress = sum(1 for t in tasks if t.status == Task.IN_PROGRESS)
        open_count = sum(1 for t in tasks if t.status == Task.OPEN)
        pct = int((complete / total) * 100) if total else 0
        filled = int(pct / 5)
        bar = '█' * filled + '░' * (20 - filled)

        status_icon = {'OPEN': '○', 'CLOSED': '●'}
        task_icon = {Task.OPEN: '○', Task.IN_PROGRESS: '◑', Task.COMPLETE: '●'}

        def row(text='', pad=' '):
            inner = text.ljust(WIDTH - 4)
            return f'║  {inner}  ║'

        def divider(left='╠', mid='═', right='╣'):
            return left + mid * (WIDTH) + right

        lines = [
            '╔' + '═' * WIDTH + '╗',
            row(f"BOARD: {board.name}"),
            row(f"Team: {board.team.name}   Status: {board.status} {status_icon.get(board.status, '')}"),
            row(f"Created: {board.creation_time.strftime('%Y-%m-%d %H:%M')}   " +
                (f"Closed: {board.end_time.strftime('%Y-%m-%d %H:%M')}" if board.end_time else "Closed: —")),
            divider(),
            row('SUMMARY'),
            row(f"Total: {total}   Open: {open_count}   In Progress: {in_progress}   Complete: {complete}"),
            row(f"Progress: [{bar}] {pct}%"),
            divider(),
        ]

        if not tasks:
            lines += [row('TASKS'), row('  No tasks found.'), '╚' + '═' * WIDTH + '╝']
        else:
            lines.append(row('TASKS'))
            lines.append(divider())

            for i, task in enumerate(tasks, 1):
                icon = task_icon.get(task.status, ' ')
                status_label = task.status.replace('_', ' ')
                lines.append(row(f"{icon} [{i:02d}] {task.title}"))
                lines.append(row(f"       Status:   {status_label}"))
                lines.append(row(f"       Assignee: {task.assigned_to.name}"))
                lines.append(row(f"       Created:  {task.creation_time.strftime('%Y-%m-%d %H:%M')}"))
                if task.description:
                    lines.append(row(f"       Note:     {task.description[:50]}"))
                if i < len(tasks):
                    lines.append(divider('╟', '─', '╢'))

            lines.append('╚' + '═' * WIDTH + '╝')

        lines.append('')
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return '\n'.join(lines)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_board(self, board_id):
        try:
            return Board.objects.get(id=board_id)
        except (Board.DoesNotExist, ValueError):
            raise ValueError(f"Board with id '{board_id}' not found")

    def _get_task(self, task_id):
        try:
            return Task.objects.get(id=task_id)
        except (Task.DoesNotExist, ValueError):
            raise ValueError(f"Task with id '{task_id}' not found")

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

    def _parse_dt(self, value: str):
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        raise ValueError(f"Unrecognised datetime format: '{value}'")
