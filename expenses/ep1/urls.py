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
]