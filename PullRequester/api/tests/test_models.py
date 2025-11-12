from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from PullRequester.api.models import Team, User, PullRequest


class TeamModelTest(TestCase):
    def test_create_team(self):
        """Тест создания команды"""
        team = Team.objects.create(name="backend")
        self.assertEqual(team.name, "backend")
        self.assertEqual(str(team), "backend")

    def test_team_unique_name(self):
        """Тест уникальности имени команды"""
        Team.objects.create(name="backend")
        with self.assertRaises(Exception):
            Team.objects.create(name="backend")


class UserModelTest(TestCase):
    def setUp(self):
        self.team1 = Team.objects.create(name="backend")
        self.team2 = Team.objects.create(name="frontend")
        self.user = User.objects.create(
            id="user1",
            username="John Doe",
            is_active=True
        )

    def test_create_user(self):
        """Тест создания пользователя"""
        self.assertEqual(self.user.id, "user1")
        self.assertEqual(self.user.username, "John Doe")
        self.assertTrue(self.user.is_active)
        self.assertEqual(str(self.user), "John Doe (user1)")

    def test_user_teams_relationship(self):
        """Тест связи пользователя с командами"""
        self.user.teams.add(self.team1, self.team2)
        self.assertEqual(self.user.teams.count(), 2)
        self.assertIn(self.team1, self.user.teams.all())
        self.assertIn(self.team2, self.user.teams.all())


class PullRequestModelTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="backend")
        self.author = User.objects.create(id="author1", username="Author")
        self.reviewer1 = User.objects.create(id="reviewer1", username="Reviewer 1")
        self.reviewer2 = User.objects.create(id="reviewer2", username="Reviewer 2")

        self.author.teams.add(self.team)
        self.reviewer1.teams.add(self.team)
        self.reviewer2.teams.add(self.team)

    def test_create_pull_request(self):
        """Тест создания PR"""
        pr = PullRequest.objects.create(
            id="pr-1",
            name="Test PR",
            author=self.author
        )
        pr.reviewers.add(self.reviewer1, self.reviewer2)

        self.assertEqual(pr.id, "pr-1")
        self.assertEqual(pr.name, "Test PR")
        self.assertEqual(pr.author, self.author)
        self.assertEqual(pr.status, PullRequest.Status.OPEN)
        self.assertEqual(pr.reviewers.count(), 2)
        self.assertIn(self.reviewer1, pr.reviewers.all())
        self.assertIn(self.reviewer2, pr.reviewers.all())

    def test_pr_merge(self):
        """Тест мержа PR"""
        pr = PullRequest.objects.create(
            id="pr-1",
            name="Test PR",
            author=self.author
        )

        pr.status = PullRequest.Status.MERGED
        pr.save()

        self.assertEqual(pr.status, PullRequest.Status.MERGED)
        self.assertIsNotNone(pr.merged_at)
        self.assertTrue(pr.merged_at <= timezone.now())

    def test_pr_merge_sets_merged_at(self):
        """Тест что мерж автоматически устанавливает merged_at"""
        pr = PullRequest.objects.create(
            id="pr-1",
            name="Test PR",
            author=self.author
        )

        self.assertIsNone(pr.merged_at)

        pr.status = PullRequest.Status.MERGED
        pr.save()

        pr.refresh_from_db()
        self.assertIsNotNone(pr.merged_at)

    def test_pr_string_representation(self):
        """Тест строкового представления PR"""
        pr = PullRequest.objects.create(
            id="pr-1",
            name="Test PR",
            author=self.author
        )
        self.assertEqual(str(pr), "Test PR (pr-1)")