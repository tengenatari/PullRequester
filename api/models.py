from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'teams'


class User(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    username = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.id})"

    class Meta:
        db_table = 'users'


class PullRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        MERGED = 'MERGED', 'Merged'

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_prs')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    reviewers = models.ManyToManyField(User, related_name='assigned_prs', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    merged_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.status == self.Status.MERGED and not self.merged_at:
            self.merged_at = timezone.now()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        db_table = 'pull_requests'