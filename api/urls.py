from django.urls import path
from .views import team_views, user_views, health_views, pull_request_views, statistic_view

app_name = 'api'

urlpatterns = [
    path('team/add', team_views.team_add, name='team-add'),
    path('team/get', team_views.team_get, name='team-get'),
    path('users/setIsActive', user_views.user_set_active, name='user-set-active'),
    path('users/getReview', user_views.users_get_review, name='user-get-review'),
    path('pullRequest/create', pull_request_views.pullrequest_create, name='pr-create'),
    path('pullRequest/merge', pull_request_views.pullrequest_merge, name='pr-merge'),
    path('pullRequest/reassign', pull_request_views.pullrequest_reassign, name='pr-reassign'),
    path('health', health_views.health_check, name='health-check'),
    path('statistic', statistic_view.stats_overview, name='statistic-view'),
    path('team/bulkDeactivate', team_views.team_bulk_deactivate, name='team-bulk-deactivate'),
]