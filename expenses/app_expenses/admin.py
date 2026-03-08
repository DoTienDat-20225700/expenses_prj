from django.contrib import admin
from .models import Category, Expense, SavingsGoal

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    list_filter = ('user',)
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'description', 'category', 'date', 'user')
    list_filter = ('category', 'date', 'user')
    search_fields = ('description', 'category__name')
    date_hierarchy = 'date'

@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ('goal_name', 'user', 'target_amount', 'current_amount', 'progress_percentage', 'target_date', 'is_completed', 'is_active')
    list_filter = ('is_completed', 'is_active', 'user', 'target_date')
    search_fields = ('goal_name', 'user__username', 'notes')
    date_hierarchy = 'target_date'
    readonly_fields = ('created_at', 'updated_at', 'progress_percentage')
    filter_horizontal = ('categories_to_reduce',)
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('user', 'goal_name', 'notes')
        }),
        ('Tài chính', {
            'fields': ('target_amount', 'current_amount')
        }),
        ('Thời gian', {
            'fields': ('start_date', 'target_date', 'created_at', 'updated_at')
        }),
        ('Cài đặt', {
            'fields': ('is_completed', 'is_active', 'categories_to_reduce')
        }),
    )
    
    def progress_percentage(self, obj):
        """Hiển thị phần trăm tiến độ"""
        return f"{obj.progress_percentage():.1f}%"
    progress_percentage.short_description = 'Tiến độ'