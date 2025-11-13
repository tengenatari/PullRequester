from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from ..services import PullRequestService
from ..serializers import PullRequestSerializer


@api_view(['POST'])
def pullrequest_create(request):
    """POST /pullRequest/create - Создать PR"""
    try:
        pr_id = request.data.get('pull_request_id')
        pr_name = request.data.get('pull_request_name')
        author_id = request.data.get('author_id')

        if not all([pr_id, pr_name, author_id]):
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'pull_request_id, pull_request_name, and author_id are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        pr = PullRequestService.create_pull_request(pr_id, pr_name, author_id)
        serializer = PullRequestSerializer(pr)

        return Response({
            'pr': serializer.data
        }, status=status.HTTP_201_CREATED)

    except ObjectDoesNotExist as e:
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': str(e)
            }
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'error': {
                'code': e.code if hasattr(e, 'code') else 'VALIDATION_ERROR',
                'message': str(e)
            }
        }, status=status.HTTP_409_CONFLICT)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def pullrequest_merge(request):
    """POST /pullRequest/merge - Пометить PR как MERGED"""
    try:
        pr_id = request.data.get('pull_request_id')

        if not pr_id:
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'pull_request_id is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        pr = PullRequestService.merge_pull_request(pr_id)
        serializer = PullRequestSerializer(pr)

        return Response({
            'pr': serializer.data
        })

    except ObjectDoesNotExist:
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'PR not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def pullrequest_reassign(request):
    """POST /pullRequest/reassign - Переназначить ревьювера"""
    try:
        pr_id = request.data.get('pull_request_id')
        old_user_id = request.data.get('old_user_id')

        if not all([pr_id, old_user_id]):
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'pull_request_id and old_user_id are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        pr, new_reviewer = PullRequestService.reassign_reviewer(pr_id, old_user_id)
        serializer = PullRequestSerializer(pr)

        return Response({
            'pr': serializer.data,
            'replaced_by': new_reviewer.id
        })

    except ObjectDoesNotExist:
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'PR or user not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'error': {
                'code': e.code if hasattr(e, 'code') else 'VALIDATION_ERROR',
                'message': str(e)
            }
        }, status=status.HTTP_409_CONFLICT)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)