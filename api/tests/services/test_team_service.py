from django.test import TestCase
from django.core.exceptions import ValidationError
from api.models import Team, User
from api.services import TeamService


class TeamServiceTest(TestCase):
    def setUp(self):
        self.team_name = "backend"
        self.members_data = [
            {"user_id": "u1", "username": "Alice", "is_active": True},
            {"user_id": "u2", "username": "Bob", "is_active": True},
            {"user_id": "u3", "username": "Charlie", "is_active": False},
        ]

    def test_create_team_with_members_success(self):
        """Тест успешного создания команды с пользователями"""
        team = TeamService.create_team_with_members(self.team_name, self.members_data)

        self.assertEqual(team.name, self.team_name)
        self.assertEqual(team.members.count(), 3)

        # Проверяем созданных пользователей
        user1 = User.objects.get(id="u1")
        self.assertEqual(user1.username, "Alice")
        self.assertTrue(user1.is_active)
        self.assertEqual(user1.team, team)  # Проверяем что пользователь в команде

    def test_create_team_duplicate(self):
        """Тест создания дубликата команды"""
        TeamService.create_team_with_members(self.team_name, self.members_data)

        with self.assertRaises(ValidationError) as context:
            TeamService.create_team_with_members(self.team_name, [])

        self.assertEqual(context.exception.code, 'TEAM_EXISTS')
        self.assertEqual(str(context.exception), "['team_name already exists']")


    def test_create_team_empty_members(self):
        """Тест создания команды без пользователей"""
        team = TeamService.create_team_with_members("empty_team", [])

        self.assertEqual(team.name, "empty_team")
        self.assertEqual(team.members.count(), 0)

    def test_get_team_with_members_success(self):
        """Тест успешного получения команды с пользователями"""
        TeamService.create_team_with_members(self.team_name, self.members_data)

        team = TeamService.get_team_with_members(self.team_name)

        self.assertEqual(team.name, self.team_name)
        self.assertEqual(team.members.count(), 3)

    def test_get_team_with_members_not_found(self):
        """Тест получения несуществующей команды"""
        with self.assertRaises(Team.DoesNotExist):
            TeamService.get_team_with_members("nonexistent")

    def test_create_or_update_user_new_user(self):
        """Тест создания нового пользователя"""
        team = Team.objects.create(name="test_team")
        member_data = {"user_id": "new_user", "username": "New User", "is_active": True}

        user = TeamService._create_or_update_user(team, member_data)

        self.assertEqual(user.id, "new_user")
        self.assertEqual(user.username, "New User")
        self.assertTrue(user.is_active)
        self.assertEqual(user.team, team)  # Проверяем связь с командой

    def test_create_or_update_user_existing_user(self):
        """Тест обновления существующего пользователя"""
        team = Team.objects.create(name="test_team")
        User.objects.create(id="existing", username="Old Name", is_active=False)

        member_data = {"user_id": "existing", "username": "New Name", "is_active": True}
        user = TeamService._create_or_update_user(team, member_data)

        self.assertEqual(user.username, "New Name")
        self.assertTrue(user.is_active)
        self.assertEqual(user.team, team)  # Проверяем что пользователь теперь в команде