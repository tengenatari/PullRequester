from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist

from PullRequester.api.services import UserService
from PullRequester.api.serializers import UserSerializer, PullRequestShortSerializer


@api_view(['POST'])
def user_set_active(request):
    """POST /users/setIsActive - Установить флаг активности пользователя"""
    try:
        user_id = request.data.get('user_id')
        is_active = request.data.get('is_active')

        if user_id is None or is_active is None:
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'user_id and is_active are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        user = UserService.set_user_active_status(user_id, is_active)
        serializer = UserSerializer(user)

        return Response({
            'user': serializer.data
        })

    except ObjectDoesNotExist:
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'User not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def users_get_review(request):
    """GET /users/getReview - Получить PR'ы, где пользователь назначен ревьювером"""
    try:
        user_id = request.query_params.get('user_id')

        if not user_id:
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'user_id parameter is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        assigned_prs = UserService.get_user_review_assignments(user_id)
        serializer = PullRequestShortSerializer(assigned_prs, many=True)

        return Response({
            'user_id': user_id,
            'pull_requests': serializer.data
        })

    except ObjectDoesNotExist:
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'User not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)