from django.apps import AppConfig

class AppExpensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_expenses'
    label = 'ep1' 
    verbose_name = "Quản lý chi tiêu"  