import random

from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone

from .models import Team, User, PullRequest



class TeamService:
    """
    Сервис для управления командами и пользователями
    """

    @classmethod
    @transaction.atomic
    def create_team_with_members(cls, team_name: str, members_data: list) -> Team:
        """
        Создает команду с пользователями

        Args:
            team_name: Название команды
            members_data: Список данных пользователей

        Returns:
            Team: Созданная команда

        Raises:
            ValidationError: Если команда уже существует
        """
        # Проверяем, существует ли команда
        team = Team.objects.filter(name=team_name)
        if team.exists() and len(members_data) > 0:
            raise ValidationError({
                'error': {
                    'code': 'TEAM_EXISTS',
                    'message': 'team_name already exists'
                }
            })
        elif not team.exists():
            team = Team.objects.create(name=team_name)


        for member_data in members_data:
            cls._create_or_update_user(team, member_data)

        return team

    @classmethod
    def _create_or_update_user(cls, team: Team, member_data: dict) -> User:
        """
        Создает или обновляет пользователя и добавляет его в команду

        Args:
            team: Команда
            member_data: Данные пользователя

        Returns:
            User: Созданный/обновленный пользователь
        """
        user_id = member_data['user_id']
        username = member_data['username']
        is_active = member_data['is_active']

        # Ищем существующего пользователя
        try:
            user = User.objects.get(id=user_id)
            # Обновляем данные пользователя
            user.username = username
            user.is_active = is_active
            user.save()
        except User.DoesNotExist:
            # Создаем нового пользователя
            user = User.objects.create(
                id=user_id,
                username=username,
                is_active=is_active
            )

        # Добавляем пользователя в команду
        user.teams.add(team)

        return user

    @classmethod
    def get_team_with_members(cls, team_name: str) -> Team:
        """
        Получает команду с ее участниками

        Args:
            team_name: Название команды

        Returns:
            Team: Команда с загруженными участниками

        Raises:
            Team.DoesNotExist: Если команда не найдена
        """
        try:
            team = Team.objects.prefetch_related('members').get(name=team_name)
            return team
        except Team.DoesNotExist:
            raise Team.DoesNotExist(f"Team '{team_name}' not found")




class UserService:
    """
    Сервис для управления пользователями
    """

    @classmethod
    def set_user_active_status(cls, user_id: str, is_active: bool) -> User:
        """
        Устанавливает флаг активности пользователя

        Args:
            user_id: ID пользователя
            is_active: Статус активности

        Returns:
            User: Обновленный пользователь

        Raises:
            User.DoesNotExist: Если пользователь не найден
        """
        try:
            user = User.objects.get(id=user_id)
            user.is_active = is_active
            user.save()
            return user
        except User.DoesNotExist:
            raise User.DoesNotExist(f"User '{user_id}' not found")

    @classmethod
    def get_user_review_assignments(cls, user_id: str) -> list:
        """
        Получает PR'ы, где пользователь назначен ревьювером

        Args:
            user_id: ID пользователя

        Returns:
            list: Список PR'ов

        Raises:
            User.DoesNotExist: Если пользователь не найден
        """
        try:
            user = User.objects.get(id=user_id)
            assigned_prs = PullRequest.objects.filter(reviewers=user)
            return list(assigned_prs)
        except User.DoesNotExist:
            raise User.DoesNotExist(f"User '{user_id}' not found")


class PullRequestService:
    """
    Сервис для управления Pull Request'ами
    """

    @classmethod
    @transaction.atomic
    def create_pull_request(cls, pr_id: str, pr_name: str, author_id: str) -> PullRequest:
        """
        Создает PR и автоматически назначает до 2 ревьюверов из команды автора

        Args:
            pr_id: ID PR
            pr_name: Название PR
            author_id: ID автора

        Returns:
            PullRequest: Созданный PR

        Raises:
            ObjectDoesNotExist: Если автор не найден или у автора нет команды
            ValidationError: Если PR уже существует
        """
        # Проверяем, существует ли PR
        if PullRequest.objects.filter(id=pr_id).exists():
            raise ValidationError({
                'error': {
                    'code': 'PR_EXISTS',
                    'message': 'PR id already exists'
                }
            })

        # Получаем автора
        try:
            author = User.objects.get(id=author_id)
        except User.DoesNotExist:
            raise ObjectDoesNotExist(f"Author '{author_id}' not found")

        # Проверяем, что у автора есть команда
        author_team = author.teams.first()
        if not author_team:
            raise ObjectDoesNotExist(f"Author '{author_id}' has no team")

        # Создаем PR
        pr = PullRequest.objects.create(
            id=pr_id,
            name=pr_name,
            author=author
        )

        # Назначаем ревьюверов
        reviewers = cls._assign_reviewers(author, author_team)
        pr.reviewers.set(reviewers)

        return pr

    @classmethod
    def _assign_reviewers(cls, author: User, author_team) -> list:
        """
        Назначает до 2 активных ревьюверов из команды автора

        Args:
            author: Автор PR
            author_team: Команда автора

        Returns:
            list: Список ревьюверов
        """
        # Получаем активных пользователей из команды автора, исключая самого автора
        available_reviewers = author_team.members.filter(
            is_active=True
        ).exclude(id=author.id)

        # Случайным образом выбираем до 2 ревьюверов
        reviewers_count = min(2, available_reviewers.count())
        if reviewers_count > 0:
            selected_reviewers = random.sample(
                list(available_reviewers),
                reviewers_count
            )
        else:
            selected_reviewers = []

        return selected_reviewers

    @classmethod
    @transaction.atomic
    def merge_pull_request(cls, pr_id: str) -> PullRequest:
        """
        Помечает PR как MERGED

        Args:
            pr_id: ID PR

        Returns:
            PullRequest: Обновленный PR

        Raises:
            PullRequest.DoesNotExist: Если PR не найден
        """
        try:
            pr = PullRequest.objects.get(id=pr_id)

            if pr.status != PullRequest.Status.MERGED:
                pr.status = PullRequest.Status.MERGED
                pr.merged_at = timezone.now()
                pr.save()

            return pr
        except PullRequest.DoesNotExist:
            raise PullRequest.DoesNotExist(f"PR '{pr_id}' not found")

    @classmethod
    @transaction.atomic
    def reassign_reviewer(cls, pr_id: str, old_user_id: str) -> tuple:
        """
        Переназначает конкретного ревьювера на другого из его команды

        Args:
            pr_id: ID PR
            old_user_id: ID старого ревьювера

        Returns:
            tuple: (PullRequest, новый ревьювер)

        Raises:
            ObjectDoesNotExist: Если PR или пользователь не найден
            ValidationError: Если нарушены доменные правила
        """
        try:
            pr = PullRequest.objects.get(id=pr_id)
            old_reviewer = User.objects.get(id=old_user_id)
        except PullRequest.DoesNotExist:
            raise ObjectDoesNotExist(f"PR '{pr_id}' not found")
        except User.DoesNotExist:
            raise ObjectDoesNotExist(f"User '{old_user_id}' not found")

        # Проверяем доменные правила
        if pr.status == PullRequest.Status.MERGED:
            raise ValidationError({
                'error': {
                    'code': 'PR_MERGED',
                    'message': 'cannot reassign on merged PR'
                }
            })

        if not pr.reviewers.filter(id=old_user_id).exists():
            raise ValidationError({
                'error': {
                    'code': 'NOT_ASSIGNED',
                    'message': 'reviewer is not assigned to this PR'
                }
            })

        # Получаем команду старого ревьювера
        reviewer_team = old_reviewer.teams.first()
        if not reviewer_team:
            raise ValidationError({
                'error': {
                    'code': 'NO_CANDIDATE',
                    'message': 'reviewer has no team'
                }
            })

        # Ищем доступных кандидатов
        available_candidates = reviewer_team.members.filter(
            is_active=True
        ).exclude(id=pr.author.id).exclude(id=old_user_id)

        # Исключаем уже назначенных ревьюверов
        current_reviewer_ids = list(pr.reviewers.values_list('id', flat=True))
        available_candidates = available_candidates.exclude(id__in=current_reviewer_ids)

        if not available_candidates.exists():
            raise ValidationError({
                'error': {
                    'code': 'NO_CANDIDATE',
                    'message': 'no active replacement candidate in team'
                }
            })

        new_reviewer = random.choice(list(available_candidates))

        # Обновляем ревьюверов
        pr.reviewers.remove(old_reviewer)
        pr.reviewers.add(new_reviewer)

        return pr, new_reviewer