from rest_framework import serializers
from .models import Team, User, PullRequest


class TeamMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='id')
    username = serializers.CharField()
    is_active = serializers.BooleanField()

    class Meta:
        model = User
        fields = ['user_id', 'username', 'is_active']


class TeamSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='name')
    members = TeamMemberSerializer(many=True, source='members.all')

    class Meta:
        model = Team
        fields = ['team_name', 'members']


class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='id')
    username = serializers.CharField()
    team_name = serializers.CharField(source='team.name')
    is_active = serializers.BooleanField()

    class Meta:
        model = User
        fields = ['user_id', 'username', 'team_name', 'is_active']


class PullRequestSerializer(serializers.ModelSerializer):
    pull_request_id = serializers.CharField(source='id')
    pull_request_name = serializers.CharField(source='name')
    author_id = serializers.CharField(source='author.id')
    status = serializers.CharField()
    assigned_reviewers = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', format='%Y-%m-%dT%H:%M:%SZ')
    mergedAt = serializers.DateTimeField(source='merged_at', format='%Y-%m-%dT%H:%M:%SZ', allow_null=True)

    class Meta:
        model = PullRequest
        fields = [
            'pull_request_id', 'pull_request_name', 'author_id',
            'status', 'assigned_reviewers', 'createdAt', 'mergedAt'
        ]
    @staticmethod
    def get_assigned_reviewers(obj):
        return [reviewer.id for reviewer in obj.reviewers.all()]


class PullRequestShortSerializer(serializers.ModelSerializer):
    pull_request_id = serializers.CharField(source='id')
    pull_request_name = serializers.CharField(source='name')
    author_id = serializers.CharField(source='author.id')
    status = serializers.CharField()

    class Meta:
        model = PullRequest
        fields = ['pull_request_id', 'pull_request_name', 'author_id', 'status']

class UserReviewStatsSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    prs_reviewed = serializers.IntegerField()
    open_prs_reviewed = serializers.IntegerField()
    merged_prs_reviewed = serializers.IntegerField()


class PRReviewerStatsSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField()
    team_name = serializers.CharField(source='author.team.name')
    reviewers_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    merged_at = serializers.DateTimeField(allow_null=True)


class StatsSerializer(serializers.Serializer):
    user_review_stats = UserReviewStatsSerializer(many=True)
    pr_reviewer_stats = PRReviewerStatsSerializer(many=True)