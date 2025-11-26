from django.urls import path
from . import views

app_name = 'transfer_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('requests/bulk/', views.bulk_action, name='bulk_action'),
    path('request/create/', views.create_request, name='create_request'),
    path('request/<int:request_id>/', views.view_request, name='view_request'),
    path('request/<int:request_id>/approve/', views.approve_request, name='approve_request'),
    path('request/<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('request/<int:request_id>/confirm/', views.confirm_request, name='confirm_request'),
    path('request/<int:request_id>/cancel/', views.cancel_request, name='cancel_request'),
    path('my/requests/', views.my_requests_full, name='my_requests_full'),
    path('my/approved/', views.approved_by_me_full, name='approved_by_me_full'),
    path('my/confirmed/', views.confirmed_by_me_full, name='confirmed_by_me_full'),
]
