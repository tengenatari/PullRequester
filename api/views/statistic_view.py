from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist

from api.services import StatsService
from api.serializers import StatsSerializer

@api_view(['GET'])
def stats_overview(request):
    """
    GET /stats/overview - Общая статистика системы
    """
    try:
        stats = StatsService.get_review_stats()
        serializer = StatsSerializer(stats)
        return Response(serializer.data)

    except Exception as e:
        return Response({
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Internal server error'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)