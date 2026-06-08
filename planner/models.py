import uuid
from django.db import models
from django.utils import timezone


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128)
    creation_time = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'planner'
        db_table = 'users'

    def __str__(self):
        return self.name


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=128, blank=True, default='')
    admin = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='administered_teams'
    )
    members = models.ManyToManyField(
        User, through='TeamMembership', related_name='teams', blank=True
    )
    creation_time = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'planner'
        db_table = 'teams'

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'planner'
        db_table = 'team_memberships'
        unique_together = ('team', 'user')


class Board(models.Model):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    STATUS_CHOICES = [(OPEN, 'Open'), (CLOSED, 'Closed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=128, blank=True, default='')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='boards')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OPEN)
    creation_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'planner'
        db_table = 'boards'
        unique_together = ('name', 'team')

    def __str__(self):
        return self.name


class Task(models.Model):
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETE = 'COMPLETE'
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETE, 'Complete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=64)
    description = models.CharField(max_length=128, blank=True, default='')
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tasks')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=OPEN)
    creation_time = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'planner'
        db_table = 'tasks'
        unique_together = ('title', 'board')

    def __str__(self):
        return self.title
