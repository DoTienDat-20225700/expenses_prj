from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from app_expenses.form import UserLoginForm 

app_name = 'ep1' 

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='ep1/login.html', authentication_form=UserLoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='ep1:login'), name='logout'),
    path('register/', views.register, name='register'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    
    # Chart APIs
    path('api/chart/category/', views.chart_category_data, name='chart_category'),
    path('api/chart/monthly/', views.chart_monthly_trend, name='chart_monthly'),
    path('api/chart/income-expense/', views.chart_expense_vs_income, name='chart_income_expense'),
    
    # Expenses
    path('expenses/', views.ep1_lists, name='ep1_lists'),
    path('expenses/add/', views.add_ep1, name='add_ep1'),
    path('expenses/edit/<int:pk>/', views.edit_ep1, name='edit_ep1'),
    path('expenses/delete/<int:pk>/', views.delete_ep1, name='delete_ep1'),
    path('expenses/export/', views.export_expenses_csv, name='export_expenses'),
    path('api/predict-category/', views.predict_category_api, name='predict_category'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    
    # Income Management
    path('income/', views.income_list, name='income_list'),
    path('income/add/', views.add_income, name='add_income'),
    path('income/edit/<int:pk>/', views.edit_income, name='edit_income'),
    path('income/delete/<int:pk>/', views.delete_income, name='delete_income'),
    path('income/sources/', views.income_source_manage, name='income_source_manage'),
    path('income/sources/edit/<int:pk>/', views.edit_income_source, name='edit_income_source'),
    path('income/sources/delete/<int:pk>/', views.delete_income_source, name='delete_income_source'),
    
    # Recurring Expenses
    path('recurring/', views.recurring_list, name='recurring_list'),
    path('recurring/add/', views.add_recurring, name='add_recurring'),
    path('recurring/edit/<int:pk>/', views.edit_recurring, name='edit_recurring'),
    path('recurring/delete/<int:pk>/', views.delete_recurring, name='delete_recurring'),
    path('recurring/toggle/<int:pk>/', views.toggle_recurring_status, name='toggle_recurring'),
    path('recurring/generate/', views.generate_recurring_expenses, name='generate_recurring'),
    
    # Savings Goals
    path('savings-goals/', views.savings_goal_list, name='savings_goal_list'),
    path('savings-goals/add/', views.add_savings_goal, name='add_savings_goal'),
    path('savings-goals/<int:pk>/', views.savings_goal_detail, name='savings_goal_detail'),
    path('savings-goals/<int:pk>/edit/', views.edit_savings_goal, name='edit_savings_goal'),
    path('savings-goals/<int:pk>/delete/', views.delete_savings_goal, name='delete_savings_goal'),
    path('savings-goals/<int:pk>/update-progress/', views.update_savings_progress, name='update_savings_progress'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
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
    # Password reset (quên mật khẩu)
    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='ep1/password_reset_form.html',
             email_template_name='ep1/password_reset_email.html',
             success_url=reverse_lazy('ep1:password_reset_done')
         ),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='ep1/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='ep1/password_reset_confirm.html',
             success_url=reverse_lazy('ep1:password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='ep1/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manager/users/', views.user_management, name='user_management'),
    path('manager/users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('manager/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('manager/ai-monitor/', views.ai_monitor, name='ai_monitor'),
    path('manager/ai-monitor/retrain/<int:user_id>/', views.force_retrain_ai, name='force_retrain_ai'),
    path('manager/announcements/', views.announcement_manager, name='announcement_manager'),
    path('manager/announcements/delete/<int:pk>/', views.delete_announcement, name='delete_announcement'),
    path('manager/announcements/toggle/<int:pk>/', views.toggle_announcement, name='toggle_announcement'),
]

