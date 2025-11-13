from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from unittest.mock import patch
from api.models import Team, User, PullRequest
from api.services import PullRequestService


class PullRequestServiceTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="backend")

        self.author = User.objects.create(id="author1", username="Author", is_active=True, team=self.team)
        self.reviewer1 = User.objects.create(id="reviewer1", username="Reviewer 1", is_active=True, team=self.team)
        self.reviewer2 = User.objects.create(id="reviewer2", username="Reviewer 2", is_active=True, team=self.team)
        self.reviewer3 = User.objects.create(id="reviewer3", username="Reviewer 3", is_active=True, team=self.team)
        self.inactive_reviewer = User.objects.create(id="inactive1", username="Inactive", is_active=False,
                                                     team=self.team)

    def test_create_pull_request_success(self):
        """Тест успешного создания PR"""
        with patch('random.sample') as mock_sample:
            mock_sample.return_value = [self.reviewer1, self.reviewer2]

            pr = PullRequestService.create_pull_request("pr-1", "Test PR", "author1")

            self.assertEqual(pr.id, "pr-1")
            self.assertEqual(pr.name, "Test PR")
            self.assertEqual(pr.author, self.author)
            self.assertEqual(pr.status, PullRequest.Status.OPEN)
            self.assertEqual(pr.reviewers.count(), 2)
            self.assertIn(self.reviewer1, pr.reviewers.all())
            self.assertIn(self.reviewer2, pr.reviewers.all())

    def test_create_pull_request_duplicate(self):
        """Тест создания дубликата PR"""
        PullRequestService.create_pull_request("pr-1", "Test PR", "author1")

        with self.assertRaises(ValidationError) as context:
            PullRequestService.create_pull_request("pr-1", "Another PR", "author1")

        self.assertEqual(context.exception.code, 'PR_EXISTS')

    def test_create_pull_request_author_not_found(self):
        """Тест создания PR с несуществующим автором"""
        with self.assertRaises(ObjectDoesNotExist):
            PullRequestService.create_pull_request("pr-1", "Test PR", "nonexistent")

    def test_create_pull_request_author_no_team(self):
        """Тест создания PR когда у автора нет команды"""
        author_no_team = User.objects.create(id="no_team", username="No Team", is_active=True)
        # Не назначаем команду - team=None

        with self.assertRaises(ObjectDoesNotExist):
            PullRequestService.create_pull_request("pr-1", "Test PR", "no_team")

    def test_create_pull_request_insufficient_reviewers(self):
        """Тест создания PR когда недостаточно ревьюверов"""
        # Оставляем только одного активного пользователя кроме автора
        self.reviewer2.is_active = False
        self.reviewer2.save()
        self.reviewer3.is_active = False
        self.reviewer3.save()

        pr = PullRequestService.create_pull_request("pr-1", "Test PR", "author1")

        # Должен быть назначен только 1 ревьювер
        self.assertEqual(pr.reviewers.count(), 1)
        self.assertEqual(pr.reviewers.first(), self.reviewer1)

    def test_create_pull_request_no_reviewers(self):
        """Тест создания PR когда нет доступных ревьюверов"""
        # Деактивируем всех кроме автора
        self.reviewer1.is_active = False
        self.reviewer1.save()
        self.reviewer2.is_active = False
        self.reviewer2.save()
        self.reviewer3.is_active = False
        self.reviewer3.save()

        pr = PullRequestService.create_pull_request("pr-1", "Test PR", "author1")

        # Не должно быть назначено ни одного ревьювера
        self.assertEqual(pr.reviewers.count(), 0)

    def test_merge_pull_request_success(self):
        """Тест успешного мержа PR"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)

        merged_pr = PullRequestService.merge_pull_request("pr-1")

        self.assertEqual(merged_pr.status, PullRequest.Status.MERGED)
        self.assertIsNotNone(merged_pr.merged_at)
        self.assertTrue(merged_pr.merged_at <= timezone.now())

    def test_merge_pull_request_idempotent(self):
        """Тест идемпотентности мержа PR"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)

        # Мержим первый раз
        merged_pr1 = PullRequestService.merge_pull_request("pr-1")
        first_merge_time = merged_pr1.merged_at

        # Мержим второй раз
        merged_pr2 = PullRequestService.merge_pull_request("pr-1")

        # Статус должен остаться MERGED, время не должно измениться
        self.assertEqual(merged_pr2.status, PullRequest.Status.MERGED)
        self.assertEqual(merged_pr2.merged_at, first_merge_time)

    def test_merge_pull_request_not_found(self):
        """Тест мержа несуществующего PR"""
        with self.assertRaises(PullRequest.DoesNotExist):
            PullRequestService.merge_pull_request("nonexistent")

    def test_reassign_reviewer_success(self):
        """Тест успешного переназначения ревьювера"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)
        pr.reviewers.add(self.reviewer1, self.reviewer2)

        with patch('random.choice') as mock_choice:
            mock_choice.return_value = self.reviewer3

            updated_pr, new_reviewer = PullRequestService.reassign_reviewer("pr-1", "reviewer1")

            self.assertEqual(new_reviewer, self.reviewer3)
            self.assertNotIn(self.reviewer1, updated_pr.reviewers.all())
            self.assertIn(self.reviewer3, updated_pr.reviewers.all())
            self.assertIn(self.reviewer2, updated_pr.reviewers.all())

    def test_reassign_reviewer_merged_pr(self):
        """Тест переназначения на мерженом PR"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)
        pr.reviewers.add(self.reviewer1)
        pr.status = PullRequest.Status.MERGED
        pr.save()

        with self.assertRaises(ValidationError) as context:
            PullRequestService.reassign_reviewer("pr-1", "reviewer1")

        self.assertEqual(context.exception.code, 'PR_MERGED')

    def test_reassign_reviewer_not_assigned(self):
        """Тест переназначения не назначенного ревьювера"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)
        pr.reviewers.add(self.reviewer1)

        with self.assertRaises(ValidationError) as context:
            PullRequestService.reassign_reviewer("pr-1", "reviewer2")

        self.assertEqual(context.exception.code, 'NOT_ASSIGNED')

    def test_reassign_reviewer_no_candidates(self):
        """Тест когда нет кандидатов для переназначения"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)
        pr.reviewers.add(self.reviewer1, self.reviewer2, self.reviewer3)

        # Все возможные кандидаты уже назначены
        with self.assertRaises(ValidationError) as context:
            PullRequestService.reassign_reviewer("pr-1", "reviewer1")

        self.assertEqual(context.exception.code, 'NO_CANDIDATE')

    def test_reassign_reviewer_reviewer_no_team(self):
        """Тест переназначения когда у ревьювера нет команды вдруг кто-то ручками полазил в базе"""
        reviewer_no_team = User.objects.create(id="no_team", username="No Team", is_active=True)
        # Не назначаем команду - team=None
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)
        pr.reviewers.add(reviewer_no_team)

        with self.assertRaises(ValidationError) as context:
            PullRequestService.reassign_reviewer("pr-1", "no_team")

        self.assertEqual(context.exception.code, 'NO_CANDIDATE')

    def test_reassign_reviewer_pr_not_found(self):
        """Тест переназначения для несуществующего PR"""
        with self.assertRaises(ObjectDoesNotExist):
            PullRequestService.reassign_reviewer("nonexistent", "reviewer1")

    def test_reassign_reviewer_user_not_found(self):
        """Тест переназначения несуществующего пользователя"""
        pr = PullRequest.objects.create(id="pr-1", name="Test PR", author=self.author)

        with self.assertRaises(ObjectDoesNotExist):
            PullRequestService.reassign_reviewer("pr-1", "nonexistent")

    def test_assign_reviewers_method(self):
        """Тест внутреннего метода назначения ревьюверов"""
        reviewers = PullRequestService._assign_reviewers(self.author)

        # Должны быть назначены 2 активных ревьювера (исключая автора)
        self.assertEqual(len(reviewers), 2)
        self.assertNotIn(self.author, reviewers)
        self.assertNotIn(self.inactive_reviewer, reviewers)