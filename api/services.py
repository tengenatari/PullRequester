import random
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from .models import Team, User, PullRequest
from django.db.models import Count
from django.db import models
class TeamService:
    """
    Сервис для управления командами и пользователями
    """

    @classmethod
    @transaction.atomic
    def create_team_with_members(cls, team_name: str, members_data: list) -> Team:
        """
        Создает команду с пользователями
        """
        # Проверяем, существует ли команда
        team = Team.objects.filter(name=team_name)
        if team.exists() and len(members_data) == 0:
            raise ValidationError('team_name already exists', code='TEAM_EXISTS')

        elif not team.exists():
            team = Team.objects.create(name=team_name)
        else:
            team = team.first()
        # Создаем/обновляем пользователей и добавляем их в команду
        for member_data in members_data:
            cls._create_or_update_user(team, member_data)

        return team

    @classmethod
    def _create_or_update_user(cls, team: Team, member_data: dict) -> User:
        user_id = member_data['user_id']
        username = member_data['username']
        is_active = member_data['is_active']

        # Ищем существующего пользователя
        try:
            user = User.objects.get(id=user_id)
            # Обновляем данные пользователя
            user.username = username
            user.is_active = is_active
            user.team = team  # Устанавливаем команду
            user.save()
        except User.DoesNotExist:
            # Создаем нового пользователя
            user = User.objects.create(
                id=user_id,
                username=username,
                team=team,  # Устанавливаем команду
                is_active=is_active
            )

        return user

    @classmethod
    def get_team_with_members(cls, team_name: str) -> Team:
        try:
            team = Team.objects.prefetch_related('members').get(name=team_name)
            return team
        except Team.DoesNotExist:
            raise Team.DoesNotExist(f"Team '{team_name}' not found")

    @classmethod
    @transaction.atomic
    def bulk_deactivate_team_members(cls, team_name: str, user_ids: list = None):
        """
        Массовая деактивация пользователей команды с безопасной переназначаемостью открытых PR
        """
        try:
            team = Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            raise ObjectDoesNotExist(f"Team '{team_name}' not found")

        # Определяем пользователей для деактивации
        if user_ids:
            users_to_deactivate = User.objects.filter(team=team, id__in=user_ids)
        else:
            users_to_deactivate = User.objects.filter(team=team)

        users_to_deactivate = list(users_to_deactivate)

        if not users_to_deactivate:
            return

        # Получаем все открытые PR где эти пользователи являются ревьюверами
        open_prs = PullRequest.objects.filter(
            status='OPEN',
            reviewers__in=users_to_deactivate
        ).distinct().prefetch_related('reviewers')

        # Безопасная переназначаемость ревьюверов
        cls._safely_reassign_reviewers(open_prs, users_to_deactivate, team)

        # Деактивируем пользователей
        User.objects.filter(
            id__in=[user.id for user in users_to_deactivate]
        ).update(is_active=False)

    @classmethod
    def _safely_reassign_reviewers(cls, open_prs: list, users_to_deactivate: list, team: Team):
        """
        Безопасная переназначаемость ревьюверов в открытых PR
        """
        # Получаем активных пользователей команды (кроме тех, кого деактивируем)
        active_users = User.objects.filter(
            team=team,
            is_active=True
        ).exclude(id__in=[user.id for user in users_to_deactivate])

        for pr in open_prs:
            # Получаем текущих ревьюверов которые будут деактивированы
            deactivating_reviewers = [
                user for user in users_to_deactivate
                if pr.reviewers.filter(id=user.id).exists()
            ]

            if not deactivating_reviewers:
                continue

            # Доступные кандидаты для замены
            available_candidates = active_users.exclude(
                id=pr.author.id
            ).exclude(
                id__in=list(pr.reviewers.values_list('id', flat=True))
            )

            # Для каждого деактивируемого ревьювера ищем замену
            for old_reviewer in deactivating_reviewers:
                if available_candidates.exists():
                    # Выбираем случайного кандидата
                    new_reviewer = random.choice(list(available_candidates))

                    # Переназначаем
                    pr.reviewers.remove(old_reviewer)
                    pr.reviewers.add(new_reviewer)

                    # Убираем нового ревьювера из доступных кандидатов для этого PR
                    available_candidates = available_candidates.exclude(id=new_reviewer.id)

class UserService:
    """
    Сервис для управления пользователями
    """

    @classmethod
    def set_user_active_status(cls, user_id: str, is_active: bool) -> User:
        try:
            user = User.objects.get(id=user_id)
            user.is_active = is_active
            user.save()
            return user
        except User.DoesNotExist:
            raise User.DoesNotExist(f"User '{user_id}' not found")

    @classmethod
    def get_user_review_assignments(cls, user_id: str) -> list:
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
        # Проверяем, существует ли PR
        if PullRequest.objects.filter(id=pr_id).exists():
            raise ValidationError('PR id already exists', code='PR_EXISTS')

        # Получаем автора
        try:
            author = User.objects.get(id=author_id)
        except User.DoesNotExist:
            raise ObjectDoesNotExist(f"Author '{author_id}' not found")

        # Проверяем, что у автора есть команда
        if not author.team:
            raise ObjectDoesNotExist(f"Author '{author_id}' has no team")

        # Создаем PR
        pr = PullRequest.objects.create(
            id=pr_id,
            name=pr_name,
            author=author
        )

        # Назначаем ревьюверов
        reviewers = cls._assign_reviewers(author)
        pr.reviewers.set(reviewers)

        return pr

    @classmethod
    def _assign_reviewers(cls, author: User) -> list:
        # Получаем активных пользователей из команды автора, исключая самого автора
        available_reviewers = User.objects.filter(
            team=author.team,
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
        try:
            pr = PullRequest.objects.get(id=pr_id)
            old_reviewer = User.objects.get(id=old_user_id)
        except PullRequest.DoesNotExist:
            raise ObjectDoesNotExist(f"PR '{pr_id}' not found")
        except User.DoesNotExist:
            raise ObjectDoesNotExist(f"User '{old_user_id}' not found")

        # Проверяем доменные правила
        if pr.status == PullRequest.Status.MERGED:
            raise ValidationError('cannot reassign on merged PR', code='PR_MERGED')

        if not pr.reviewers.filter(id=old_user_id).exists():
            raise ValidationError('reviewer is not assigned to this PR', code='NOT_ASSIGNED')


        # Ищем доступных кандидатов из той же команды
        available_candidates = User.objects.filter(
            team=old_reviewer.team,
            is_active=True
        ).exclude(id=pr.author.id).exclude(id=old_user_id)

        # Исключаем уже назначенных ревьюверов
        current_reviewer_ids = list(pr.reviewers.values_list('id', flat=True))
        available_candidates = available_candidates.exclude(id__in=current_reviewer_ids)

        if not available_candidates.exists():
            raise ValidationError('no active replacement candidate in team', code='NO_CANDIDATE')

        # Выбираем случайного кандидата
        new_reviewer = random.choice(list(available_candidates))

        # Обновляем ревьюверов
        pr.reviewers.remove(old_reviewer)
        pr.reviewers.add(new_reviewer)

        return pr, new_reviewer


class StatsService:
    """
    Сервис для сбора статистики
    """

    @classmethod
    def get_review_stats(cls):
        """
        Returns:
            dict: Статистика по пользователям и PR
        """
        user_review_stats = (
            User.objects
            .filter(assigned_prs__isnull=False)
            .annotate(
                prs_reviewed=Count('assigned_prs'),
                open_prs_reviewed=Count('assigned_prs', filter=models.Q(assigned_prs__status='OPEN')),
                merged_prs_reviewed=Count('assigned_prs', filter=models.Q(assigned_prs__status='MERGED'))
            )
            .values('id', 'username', 'prs_reviewed', 'open_prs_reviewed', 'merged_prs_reviewed')
            .order_by('-prs_reviewed')
        )

        pr_reviewer_stats = (
            PullRequest.objects
            .annotate(
                reviewers_count=Count('reviewers'),
                team_name=models.F('author__team__name')
            )
            .values(
                'id', 'name', 'status', 'team_name',
                'reviewers_count', 'created_at', 'merged_at'
            )
            .order_by('-created_at')
        )

        return {
            'user_review_stats': list(user_review_stats),
            'pr_reviewer_stats': list(pr_reviewer_stats)
        }