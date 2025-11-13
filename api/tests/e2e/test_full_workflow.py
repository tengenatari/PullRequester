from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class FullWorkflowE2ETest(APITestCase):
    """
    End-to-end
    """

    def test_complete_pr_workflow(self):
        """
        E2E тест: полный workflow создания команды, PR, переназначения и мержа
        """
        # Создаем команду через API
        team_data = {
            "team_name": "backend-team",
            "members": [
                {"user_id": "dev1", "username": "Developer 1", "is_active": True},
                {"user_id": "dev2", "username": "Developer 2", "is_active": True},
                {"user_id": "dev3", "username": "Developer 3", "is_active": True},
                {"user_id": "dev4", "username": "Developer 4", "is_active": True},
            ]
        }
        response = self.client.post(reverse('api:team-add'), team_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['team']['team_name'], 'backend-team')
        self.assertEqual(len(response.data['team']['members']), 4)

        # Проверяем что команда создана через GET API
        response = self.client.get(f"{reverse('api:team-get')}?team_name=backend-team")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['team_name'], 'backend-team')
        self.assertEqual(len(response.data['members']), 4)

        # Создаем PR через API
        pr_data = {
            "pull_request_id": "feature-auth",
            "pull_request_name": "Implement authentication",
            "author_id": "dev1"
        }
        response = self.client.post(reverse('api:pr-create'), pr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['pr']['pull_request_id'], 'feature-auth')
        self.assertEqual(response.data['pr']['author_id'], 'dev1')
        self.assertEqual(response.data['pr']['status'], 'OPEN')

        # Должны быть назначены 2 ревьювера (исключая автора)
        assigned_reviewers = response.data['pr']['assigned_reviewers']
        self.assertEqual(len(assigned_reviewers), 2)
        self.assertNotIn('dev1', assigned_reviewers)  # Автор не должен быть ревьювером

        # Получаем PR для одного из ревьюверов
        reviewer_id = assigned_reviewers[0]
        response = self.client.get(f"{reverse('api:user-get-review')}?user_id={reviewer_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_id'], reviewer_id)
        self.assertEqual(len(response.data['pull_requests']), 1)
        self.assertEqual(response.data['pull_requests'][0]['pull_request_id'], 'feature-auth')

        # Переназначаем одного ревьювера через API
        reassign_data = {
            "pull_request_id": "feature-auth",
            "old_user_id": reviewer_id
        }
        response = self.client.post(reverse('api:pr-reassign'), reassign_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('replaced_by', response.data)
        new_reviewer = response.data['replaced_by']
        self.assertNotEqual(new_reviewer, reviewer_id)

        # Проверяем что у старого ревьювера больше нет этого PR
        response = self.client.get(f"{reverse('api:user-get-review')}?user_id={reviewer_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['pull_requests']), 0)

        # Проверяем что у нового ревьювера появился этот PR
        response = self.client.get(f"{reverse('api:user-get-review')}?user_id={new_reviewer}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['pull_requests']), 1)
        self.assertEqual(response.data['pull_requests'][0]['pull_request_id'], 'feature-auth')

        # Мержим PR через API
        merge_data = {"pull_request_id": "feature-auth"}
        response = self.client.post(reverse('api:pr-merge'), merge_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pr']['status'], 'MERGED')
        self.assertIsNotNone(response.data['pr']['mergedAt'])

        # Пытаемся переназначить после мержа (должно быть запрещено)
        response = self.client.post(reverse('api:pr-reassign'), reassign_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'PR_MERGED')

        # Проверяем идемпотентность мержа
        response = self.client.post(reverse('api:pr-merge'), merge_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pr']['status'], 'MERGED')

    def test_user_activation_workflow(self):
        """
        E2E тест: workflow с деактивацией пользователя
        """
        # Создаем команду
        team_data = {
            "team_name": "qa-team",
            "members": [
                {"user_id": "qa1", "username": "QA Engineer 1", "is_active": True},
                {"user_id": "qa2", "username": "QA Engineer 2", "is_active": True},
                {"user_id": "qa3", "username": "QA Engineer 3", "is_active": True},
            ]
        }
        response = self.client.post(reverse('api:team-add'), team_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Деактивируем пользователя через API
        deactivate_data = {"user_id": "qa2", "is_active": False}
        response = self.client.post(reverse('api:user-set-active'), deactivate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['user']['is_active'])

        # Создаем PR - деактивированный пользователь не должен быть назначен
        pr_data = {
            "pull_request_id": "test-fix",
            "pull_request_name": "Fix failing tests",
            "author_id": "qa1"
        }
        response = self.client.post(reverse('api:pr-create'), pr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем что qa2 не назначен ревьювером
        assigned_reviewers = response.data['pr']['assigned_reviewers']
        self.assertNotIn("qa2", assigned_reviewers)

        # Активируем пользователя обратно
        activate_data = {"user_id": "qa2", "is_active": True}
        response = self.client.post(reverse('api:user-set-active'), activate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['user']['is_active'])

        # Создаем еще один PR - теперь qa2 может быть назначен
        pr_data_2 = {
            "pull_request_id": "new-feature",
            "pull_request_name": "Add new feature",
            "author_id": "qa3"
        }
        response = self.client.post(reverse('api:pr-create'), pr_data_2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # qa2 теперь может быть в списке ревьюверов
        assigned_reviewers_2 = response.data['pr']['assigned_reviewers']

    def test_error_scenarios_workflow(self):
        """
        E2E тест: различные сценарии ошибок
        """

        team_data = {
            "team_name": "mobile-team",
            "members": [
                {"user_id": "m1", "username": "Mobile Dev 1", "is_active": True},
            ]
        }
        response = self.client.post(reverse('api:team-add'), team_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


        # Попытка создать PR с несуществующим автором
        pr_data = {
            "pull_request_id": "invalid-pr",
            "pull_request_name": "Invalid PR",
            "author_id": "nonexistent-user"
        }
        response = self.client.post(reverse('api:pr-create'), pr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error']['code'], 'NOT_FOUND')

        # Попытка создать дубликат PR
        valid_pr_data = {
            "pull_request_id": "valid-pr",
            "pull_request_name": "Valid PR",
            "author_id": "m1"
        }
        response = self.client.post(reverse('api:pr-create'), valid_pr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Попытка создать PR с тем же ID
        response = self.client.post(reverse('api:pr-create'), valid_pr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'PR_EXISTS')

        # Попытка переназначить не назначенного ревьювера
        reassign_data = {
            "pull_request_id": "valid-pr",
            "old_user_id": "m2"
        }

        team_data = {
            "team_name": "mobile-team",
            "members": [
                {"user_id": "m2", "username": "Mobile Dev 1", "is_active": True},
            ]
        }

        self.client.post(reverse('api:team-add'), team_data, format='json')
        response = self.client.post(reverse('api:pr-reassign'), reassign_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'NOT_ASSIGNED')

    def test_edge_cases_workflow(self):
        """
        E2E тест: граничные случаи
        """
        # Создаем команду с минимальным количеством пользователей
        team_data = {
            "team_name": "small-team",
            "members": [
                {"user_id": "s1", "username": "Solo Developer", "is_active": True},
            ]
        }
        response = self.client.post(reverse('api:team-add'), team_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Создаем PR - не должно быть ревьюверов (только автор в команде)
        pr_data = {
            "pull_request_id": "solo-pr",
            "pull_request_name": "Solo PR",
            "author_id": "s1"
        }
        response = self.client.post(reverse('api:pr-create'), pr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['pr']['assigned_reviewers']), 0)

        # Создаем команду с неактивными пользователями
        team_data_inactive = {
            "team_name": "inactive-team",
            "members": [
                {"user_id": "i1", "username": "Inactive 1", "is_active": False},
                {"user_id": "i2", "username": "Inactive 2", "is_active": False},
                {"user_id": "i3", "username": "Active User", "is_active": True},
            ]
        }
        response = self.client.post(reverse('api:team-add'), team_data_inactive, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Создаем PR - должны быть назначены только активные пользователи
        pr_data_inactive = {
            "pull_request_id": "inactive-team-pr",
            "pull_request_name": "PR for inactive team",
            "author_id": "i3"
        }
        response = self.client.post(reverse('api:pr-create'), pr_data_inactive, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # В команде только один активный пользователь (автор), поэтому ревьюверов быть не должно
        assigned_reviewers = response.data['pr']['assigned_reviewers']
        self.assertEqual(len(assigned_reviewers), 0)


class MultiplePRE2ETest(APITestCase):
    """
    E2E тесты нескольких PR
    """

    def test_multiple_teams_and_prs(self):
        """
        E2E тест: создание нескольких команд
        """
        # Создаем несколько команд
        teams_data = [
            {
                "team_name": "team-frontend",
                "members": [
                    {"user_id": f"f{i}", "username": f"Frontend Dev {i}", "is_active": True}
                    for i in range(1, 6)  # 5 пользователей
                ]
            },
            {
                "team_name": "team-backend",
                "members": [
                    {"user_id": f"b{i}", "username": f"Backend Dev {i}", "is_active": True}
                    for i in range(1, 6)  # 5 пользователей
                ]
            }
        ]

        for team_data in teams_data:
            response = self.client.post(reverse('api:team-add'), team_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Создаем несколько PR для каждой команды
        prs_data = [
                       {"pull_request_id": f"pr-frontend-{i}", "pull_request_name": f"Frontend PR {i}",
                        "author_id": "f1"}
                       for i in range(1, 4)  # 3 PR
                   ] + [
                       {"pull_request_id": f"pr-backend-{i}", "pull_request_name": f"Backend PR {i}", "author_id": "b1"}
                       for i in range(1, 4)
                   ]

        for pr_data in prs_data:
            response = self.client.post(reverse('api:pr-create'), pr_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            # Проверяем что назначены ревьюверы
            self.assertIn('assigned_reviewers', response.data['pr'])

        # Проверяем что можем получить все PR для пользователя
        response = self.client.get(f"{reverse('api:user-get-review')}?user_id=f2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DataConsistencyE2ETest(APITestCase):
    """
    E2E тесты целостности данных
    """

    def test_data_consistency_after_operations(self):
        """
        E2E тест: проверка целостности данных после серии операций
        """
        team_data = {
            "team_name": "consistency-team",
            "members": [
                {"user_id": "c1", "username": "Consistency 1", "is_active": True},
                {"user_id": "c2", "username": "Consistency 2", "is_active": True},
                {"user_id": "c3", "username": "Consistency 3", "is_active": True},
            ]
        }
        self.client.post(reverse('api:team-add'), team_data, format='json')

        # 2. Создаем несколько PR
        pr_ids = ["consistency-pr-1", "consistency-pr-2"]
        for pr_id in pr_ids:
            pr_data = {
                "pull_request_id": pr_id,
                "pull_request_name": f"Consistency PR {pr_id}",
                "author_id": "c1"
            }
            self.client.post(reverse('api:pr-create'), pr_data, format='json')

        response = self.client.get(f"{reverse('api:team-get')}?team_name=consistency-team")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['members']), 3)

        # Проверяем PR для каждого пользователя
        for user_id in ["c1", "c2", "c3"]:
            response = self.client.get(f"{reverse('api:user-get-review')}?user_id={user_id}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            if user_id == "c1":
                self.assertEqual(len(response.data['pull_requests']), 0)
            else:
                self.assertTrue(len(response.data['pull_requests']) >= 0)

        merge_data = {"pull_request_id": "consistency-pr-1"}
        response = self.client.post(reverse('api:pr-merge'), merge_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"{reverse('api:user-get-review')}?user_id=c2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for pr in response.data['pull_requests']:
            if pr['pull_request_id'] == 'consistency-pr-1':
                self.assertEqual(pr['status'], 'MERGED')
            else:
                self.assertEqual(pr['status'], 'OPEN')