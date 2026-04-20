from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/record-death/', views.record_death, name='record_death'),
    path('api/delete-record/<int:record_id>/', views.delete_record, name='delete_record'),
    path('api/push/subscribe/', views.push_subscribe, name='push_subscribe'),
    path('api/push/unsubscribe/', views.push_unsubscribe, name='push_unsubscribe'),
    path('api/push/vapid-key/', views.push_vapid_key, name='push_vapid_key'),
    path('api/push/test/', views.push_test, name='push_test'),
    path('api/push/status/', views.push_status, name='push_status'),
]
