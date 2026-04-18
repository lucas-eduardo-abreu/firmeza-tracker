from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/record-death/', views.record_death, name='record_death'),
    path('api/delete-record/<int:record_id>/', views.delete_record, name='delete_record'),
]
