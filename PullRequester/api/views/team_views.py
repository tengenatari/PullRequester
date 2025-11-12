from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from PullRequester.api.services import TeamService
from PullRequester.api.serializers import TeamSerializer


@api_view(['POST'])
def team_add(request):
    """POST /team/add - Создать команду с участниками"""
    try:
        team_name = request.data.get('team_name')
        members_data = request.data.get('members', [])

        if not team_name:
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'team_name is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(members_data, list):
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'members must be a list'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        for i, member in enumerate(members_data):
            if not all(key in member for key in ['user_id', 'username', 'is_active']):
                return Response({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'Member at index {i} is missing required fields'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        team = TeamService.create_team_with_members(team_name, members_data)
        serializer = TeamSerializer(team)

        return Response({
            'team': serializer.data
        }, status=status.HTTP_201_CREATED)

    except ValidationError as e:
        return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def team_get(request):
    """GET /team/get - Получить команду с участниками"""
    try:
        team_name = request.query_params.get('team_name')

        if not team_name:
            return Response({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'team_name parameter is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        team = TeamService.get_team_with_members(team_name)
        serializer = TeamSerializer(team)

        return Response(serializer.data)

    except ObjectDoesNotExist:
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Team not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)