from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('statistics/', views.statistics, name='statistics'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('add-workout/', views.add_workout, name='add_workout'),
    path('workout/<int:pk>/', views.workout_detail, name='workout_detail'),
    path('workout/<int:pk>/delete/', views.delete_workout, name='delete_workout'),
    path('workout/<int:pk>/save-template/', views.save_as_template, name='save_as_template'),
    path('api/templates/<int:pk>/', views.api_get_template, name='api_get_template'),
    path('api/templates/<int:pk>/delete/', views.delete_template, name='delete_template'),
    path('api/templates/<int:pk>/rename/', views.rename_template, name='rename_template'),
    path('template/<int:pk>/', views.template_detail, name='template_detail'),
    path('api/ai-recommendation/', views.get_ai_recommendation, name='get_ai_recommendation'),
    path('ai-journal/', views.ai_journal, name='ai_journal'),
    path('ai-strategy/', views.ai_strategy, name='ai_strategy'),
    path('generate-strategy/', views.generate_strategy, name='generate_strategy'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('archive/', views.workout_archive, name='workout_archive'),
    path('api/archive/<int:year>/<int:week>/', views.api_get_workouts_by_week, name='api_archive_week'),
    path('update-dashboard-layout/', views.update_dashboard_layout, name='update_dashboard_layout'),
    path('reset-dashboard-layout/', views.reset_dashboard_layout, name='reset_dashboard_layout'),
    path('dismiss-plateau/', views.dismiss_plateau, name='dismiss_plateau'),
]
