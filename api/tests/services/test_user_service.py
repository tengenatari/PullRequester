from django.test import TestCase
from api.models import Team, User, PullRequest
from api.services import UserService


class UserServiceTest(TestCase):
    def setUp(self):
        # Создаем команду
        self.team = Team.objects.create(name="backend")

        self.user1 = User.objects.create(id="u1", username="Alice", is_active=True, team=self.team)
        self.user2 = User.objects.create(id="u2", username="Bob", is_active=True, team=self.team)

        # Создаем PR где user2 - ревьювер
        self.pr = PullRequest.objects.create(
            id="pr-1",
            name="Test PR",
            author=self.user1
        )
        self.pr.reviewers.add(self.user2)

    def test_set_user_active_status_success(self):
        """Тест успешного изменения активности пользователя"""
        user = UserService.set_user_active_status("u1", False)

        self.assertEqual(user.id, "u1")
        self.assertFalse(user.is_active)

        # Проверяем что данные сохранились в БД
        user_from_db = User.objects.get(id="u1")
        self.assertFalse(user_from_db.is_active)

    def test_set_user_active_status_not_found(self):
        """Тест изменения активности несуществующего пользователя"""
        with self.assertRaises(User.DoesNotExist):
            UserService.set_user_active_status("nonexistent", True)

    def test_get_user_review_assignments_success(self):
        """Тест успешного получения PR пользователя как ревьювера"""
        assigned_prs = UserService.get_user_review_assignments("u2")

        self.assertEqual(len(assigned_prs), 1)
        self.assertEqual(assigned_prs[0].id, "pr-1")
        self.assertEqual(assigned_prs[0].author, self.user1)

    def test_get_user_review_assignments_empty(self):
        """Тест получения PR когда пользователь не ревьювер"""
        assigned_prs = UserService.get_user_review_assignments("u1")

        self.assertEqual(len(assigned_prs), 0)

    def test_get_user_review_assignments_not_found(self):
        """Тест получения PR несуществующего пользователя"""
        with self.assertRaises(User.DoesNotExist):
            UserService.get_user_review_assignments("nonexistent")

    def test_get_user_review_assignments_multiple_prs(self):
        """Тест получения нескольких PR пользователя"""
        # Создаем еще один PR с тем же ревьювером
        pr2 = PullRequest.objects.create(
            id="pr-2",
            name="Another PR",
            author=self.user1
        )
        pr2.reviewers.add(self.user2)

        assigned_prs = UserService.get_user_review_assignments("u2")

        self.assertEqual(len(assigned_prs), 2)
        pr_ids = [pr.id for pr in assigned_prs]
        self.assertIn("pr-1", pr_ids)
        self.assertIn("pr-2", pr_ids)