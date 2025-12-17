from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name = 'ep1' 

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='ep1/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='ep1:login'), name='logout'),
    path('register/', views.register, name='register'),
    path('', views.ep1_lists, name='ep1_lists'),
    path('add/', views.add_ep1, name='add_ep1'),
    path('edit/<int:pk>/', views.edit_ep1, name='edit_ep1'),
    path('delete/<int:pk>/', views.delete_ep1, name='delete_ep1'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    path('api/predict-category/', views.predict_category_api, name='predict_category'),
    path('profile/', views.profile, name='profile'),
    path('export/', views.export_expenses_csv, name='export_expenses'),
    path('password_change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='ep1/password_change.html',
             success_url=reverse_lazy('ep1:password_change_done')
         ), 
         name='password_change'),
    path('password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='ep1/password_change_done.html'
         ), 
         name='password_change_done'),
         # --- ADMIN PATH ---
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('export/', views.export_expenses_csv, name='export_expenses'),
    path('manager/users/', views.user_management, name='user_management'),
    path('manager/users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('manager/ai-monitor/', views.ai_monitor, name='ai_monitor'),
    path('manager/ai-monitor/retrain/<int:user_id>/', views.force_retrain_ai, name='force_retrain_ai'),
    path('manager/announcements/', views.announcement_manager, name='announcement_manager'),
    path('manager/announcements/delete/<int:pk>/', views.delete_announcement, name='delete_announcement'),
    path('manager/announcements/toggle/<int:pk>/', views.toggle_announcement, name='toggle_announcement'),
]