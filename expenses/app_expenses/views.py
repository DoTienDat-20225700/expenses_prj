import csv
import threading
import os
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user
from django.contrib.auth.decorators import user_passes_test, login_required
from django.core.paginator import Paginator
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count, Q
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from .models import *
from .form import *
from .ml_utils import predict_category, train_model, get_model_path


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  
            return redirect('ep1:dashboard')  # Redirect to dashboard
    else:
        form = RegisterForm()
    return render(request, 'ep1/register.html', {'form': form})

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin)
def admin_dashboard(request):
    # 1. Thống kê User
    total_users = User.objects.count()

    # User mới trong 30 ngày qua
    month_ago = timezone.now() - timedelta(days=30)
    new_users = User.objects.filter(date_joined__gte=month_ago).count()

    # 2. Thống kê Dòng tiền (Toàn hệ thống)
    total_expenses_count = Expense.objects.count()
    total_money = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    # 3. Top Danh mục phổ biến nhất hệ thống (theo số lượng giao dịch)
    # Lấy tên danh mục và đếm số lần xuất hiện
    top_categories = Expense.objects.values('category__name') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:5]  # Lấy top 5

    context = {
        'total_users': total_users,
        'new_users': new_users,
        'total_expenses_count': total_expenses_count,
        'total_money': total_money,
        'top_categories': top_categories
    }
    return render(request, 'ep1/admin/dashboard.html', context)

@user_passes_test(is_admin)
def user_management(request):
    """Hiển thị danh sách người dùng cho Admin"""
    # Lấy tất cả user, sắp xếp người mới nhất lên đầu
    users = User.objects.all().order_by('-date_joined')
    
    context = {
        'users': users
    }
    return render(request, 'ep1/admin/user_list.html', context)

@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Xóa vĩnh viễn tài khoản User và toàn bộ dữ liệu liên quan"""
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        
        # Bảo vệ: Không cho phép Admin tự xóa chính mình
        if user == request.user:
            messages.error(request, "Bạn không thể tự xóa tài khoản của chính mình!")
            return redirect('ep1:user_management')
            
        username = user.username
        # Lệnh này sẽ tự động xóa sạch Profile, Expense, Budget... nhờ on_delete=models.CASCADE
        user.delete() 
        
        messages.success(request, f"Đã xóa vĩnh viễn user '{username}' và toàn bộ dữ liệu của họ.")
        
    return redirect('ep1:user_management')

@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """Khóa hoặc Mở khóa tài khoản User"""
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        
        # Không cho phép tự khóa chính mình (Admin)
        if user == request.user:
            messages.error(request, "Bạn không thể tự khóa tài khoản của chính mình!")
            return redirect('ep1:user_management')

        # Đảo ngược trạng thái: Đang mở -> Khóa, Đang khóa -> Mở
        user.is_active = not user.is_active
        user.save()
        
        status_msg = "đã được mở khóa" if user.is_active else "đã bị khóa"
        messages.success(request, f"Tài khoản {user.username} {status_msg}.")
        
    return redirect('ep1:user_management')

@user_passes_test(is_admin)
def ai_monitor(request):
    """Trang giám sát trạng thái Model AI của từng user"""
    users = User.objects.all().order_by('-date_joined')
    ai_stats = []

    for user in users:
        model_path = get_model_path(user)
        has_model = os.path.exists(model_path)
        model_size = 0
        last_modified = None

        if has_model:
            # Lấy kích thước file (KB)
            model_size = round(os.path.getsize(model_path) / 1024, 2)
            # Lấy số lượng dữ liệu đã học (Số bản ghi chi tiêu)
            data_count = Expense.objects.filter(user=user).count()
        else:
            data_count = 0

        ai_stats.append({
            'user': user,
            'has_model': has_model,
            'model_size': model_size,
            'data_count': data_count
        })

    context = {
        'ai_stats': ai_stats
    }
    return render(request, 'ep1/admin/ai_monitor.html', context)

@user_passes_test(is_admin)
def force_retrain_ai(request, user_id):
    """Admin ép buộc huấn luyện lại AI cho 1 user"""
    user = get_object_or_404(User, pk=user_id)

    # Gọi hàm train từ ml_utils
    model = train_model(user)

    if model:
        messages.success(request, f"Đã huấn luyện lại thành công AI cho user: {user.username}")
    else:
        messages.warning(request, f"Không thể huấn luyện. User {user.username} chưa đủ dữ liệu (cần ít nhất 3 chi tiêu).")

    return redirect('ep1:ai_monitor')

# ... import Announcement từ models nếu chưa có (thường là import * rồi nên ok) ...

@user_passes_test(is_admin)
def announcement_manager(request):
    """Trang quản lý thông báo của Admin"""
    if request.method == 'POST':
        # Xử lý tạo thông báo mới
        title = request.POST.get('title')
        content = request.POST.get('content')
        priority = request.POST.get('priority')
        
        if title and content:
            Announcement.objects.create(title=title, content=content, priority=priority)
            messages.success(request, "Đã đăng thông báo mới!")
        return redirect('ep1:announcement_manager')

    announcements = Announcement.objects.all()
    return render(request, 'ep1/admin/announcement_manager.html', {'announcements': announcements})

@user_passes_test(is_admin)
def delete_announcement(request, pk):
    """Xóa thông báo"""
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.delete()
    messages.success(request, "Đã xóa thông báo.")
    return redirect('ep1:announcement_manager')

@user_passes_test(is_admin)
def toggle_announcement(request, pk):
    """Ẩn/Hiện thông báo"""
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_active = not announcement.is_active
    announcement.save()
    return redirect('ep1:announcement_manager')

def create_default_categories(user):
    default_categories = [
        "Ăn uống",
        "Đi lại",
        "Nhà cửa",
        "Hóa đơn",
        "Mua sắm",
        "Giải trí",
        "Y tế",
        "Giáo dục",
        "Tiết kiệm",
        "Quà tặng"
    ]
    for cat_name in default_categories:
        Category.objects.get_or_create(name=cat_name, user=user)

@login_required
def profile(request):
    profile_obj, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST,  instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Cập nhật hồ sơ thành công!')
            return redirect('ep1:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'ep1/profile.html', {
        'u_form': u_form,
        'p_form': p_form
    })

def _apply_filters(queryset, params):
    """Áp dụng các bộ lọc cho queryset chi tiêu."""
    category_id = params.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    date_from = params.get('date_from')
    date_to = params.get('date_to')
    if date_from and date_to:
        queryset = queryset.filter(date__range=[date_from, date_to])
    elif date_from:
        queryset = queryset.filter(date__gte=date_from)
    elif date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    return queryset

def _apply_sorting(queryset, params):
    """Áp dụng sắp xếp cho queryset chi tiêu."""
    sort_amount = params.get('sort_amount')
    sort_date = params.get('sort_date')
    date_from = params.get('date_from')
    date_to = params.get('date_to')
    
    order_fields = []
    if sort_amount == 'asc':
        order_fields.append('amount')
    elif sort_amount == 'desc':
        order_fields.append('-amount')

    if sort_date == 'asc':
        order_fields.append('date')
    elif sort_date == 'desc':
        order_fields.append('-date')
    elif date_from or date_to:
        # Nếu đang lọc theo ngày nhưng chưa chọn sắp xếp ngày, mặc định sắp xếp tăng dần
        order_fields.append('date')

    return queryset.order_by(*order_fields) if order_fields else queryset.order_by('-date')

@login_required
def ep1_lists(request):
    # Get base expenses with optimized query
    base_expenses = Expense.objects.filter(user=request.user).select_related('category')
    # Apply filters and sorting
    filtered_expenses = _apply_filters(base_expenses, request.GET)
    expenses = _apply_sorting(filtered_expenses, request.GET)

    # Pagination
    paginator = Paginator(expenses, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Calculate monthly expenses
    today = timezone.now().date()
    first_day_this_month = today.replace(day=1)
    from dateutil.relativedelta import relativedelta
    first_day_next_month = (first_day_this_month + relativedelta(months=1))

    this_month_expenses = Expense.objects.filter(
        user=request.user, 
        date__gte=first_day_this_month,
        date__lt=first_day_next_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate totals
    filtered_total = expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    global_total = base_expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    # Get top category
    global_category_data = base_expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    top_category_item = global_category_data.first()
    top_category = top_category_item['category__name'] if top_category_item else '—'

    # Chart data
    category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    daily_data = expenses.annotate(day=TruncDate('date')).values('day').annotate(total=Sum('amount')).order_by('day')

    chart_labels = [item['category__name'] for item in category_data]
    chart_data = [float(item['total']) for item in category_data]
    chart_labels_day = [item['day'].strftime('%d/%m/%Y') for item in daily_data]
    chart_data_day = [float(item['total']) for item in daily_data]

    # Xử lý Budget form
    budget_obj, _ = Budget.objects.get_or_create(user=request.user)
    if request.method == 'POST' and 'budget_submit' in request.POST:
        b_form = BudgetForm(request.POST, instance=budget_obj)
        if b_form.is_valid():
            b_form.save()
            messages.success(request, 'Cập nhật ngân sách thành công!')
            return redirect('ep1:ep1_lists')
    else:
        b_form = BudgetForm(instance=budget_obj)

    # Lấy các thông báo đang Active (Mới nhất lên đầu)
    active_announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')

    context = {
        'expenses': page_obj, 
        'page_obj': page_obj,
        
        'total_spent': filtered_total,
        'this_month_expenses': this_month_expenses,
        'remaining': budget_obj.total - this_month_expenses,
        'top_category': top_category,

        'b_form': b_form,
        'budget_obj': budget_obj,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'chart_labels_day': chart_labels_day,
        'chart_data_day': chart_data_day,
        'categories': Category.objects.filter(user=request.user),
        'selected_category': int(request.GET.get('category')) if request.GET.get('category') else None,
        'sort_amount': request.GET.get('sort_amount'),
        'sort_date': request.GET.get('sort_date'),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
    }
    return render(request, 'ep1/ep1_lists.html', context)

@login_required
def add_ep1(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user 
            
            try:
                budget = Budget.objects.get(user=request.user)
                current_total = Expense.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
                new_total = current_total + expense.amount
                
                if new_total > budget.total:
                    over_amount = new_total - budget.total
                    messages.warning(
                        request, 
                        f'⚠️ Cảnh báo: Bạn đã vượt quá ngân sách {over_amount:,.0f} ₫!'
                    )
                else:
                    messages.success(request, 'Thêm chi tiêu thành công!')
                    
            except Budget.DoesNotExist:
                pass

            expense.save()
            try:
                thread = threading.Thread(target=train_model, args=(request.user,))
                thread.start()
            except Exception as e:
                print(f"Lỗi chạy background task: {e}")
            # -----------------------------------------------------

            return redirect('ep1:ep1_lists')
    else:
        form = ExpenseForm(user=request.user)
        
    return render(request, 'ep1/add_ep1.html', {'form': form})

@login_required
def edit_ep1(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    next_url = request.GET.get('next')
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            if next_url:
                return redirect(f"{next_url}#list-section")
            return redirect('ep1:ep1_lists')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    
    return render(request, 'ep1/edit_ep1.html', {'form': form})

@login_required
def delete_ep1(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    next_url = request.GET.get('next')
    if request.method == 'POST':
        expense.delete()
        if next_url:
            return redirect(f"{next_url}#list-section")
        return redirect('ep1:ep1_lists')
    
    return render(request, 'ep1/delete_ep1.html', {'expense': expense})

@login_required
def export_expenses_csv(request):
    base_expenses = Expense.objects.filter(user=request.user)
    filtered_expenses = _apply_filters(base_expenses, request.GET)
    expenses = _apply_sorting(filtered_expenses, request.GET)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bao_cao_chi_tieu.csv"'
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response)
    writer.writerow(['Ngày', 'Danh mục', 'Số tiền (VNĐ)', 'Mô tả'])

    for expense in expenses:
        writer.writerow([
            expense.date.strftime('%d/%m/%Y'),
            expense.category.name if expense.category else 'Khác',
            int(expense.amount), 
            expense.description
        ])

    return response

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'ep1/category_list.html', {'categories': categories})

@login_required
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, 'Thêm danh mục thành công!')
            return redirect('ep1:category_list')
    else:
        form = CategoryForm()
    return render(request, 'ep1/add_category.html', {'form': form, 'title': 'Thêm danh mục'})

@login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật danh mục thành công!')
            return redirect('ep1:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'ep1/add_category.html', {'form': form, 'title': 'Sửa danh mục'})

@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if category.expense_set.exists():
        messages.error(request, 'Không thể xóa danh mục đang có dữ liệu chi tiêu!')
        return redirect('ep1:category_list')
        
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Đã xóa danh mục.')
        return redirect('ep1:category_list')
        
    return render(request, 'ep1/delete_ep1.html', {
        'expense': category, 
        'title': 'Xóa danh mục' 
    }) 

@login_required
def predict_category_api(request):
    description = request.GET.get('description', '').strip()
    
    if not description:
        return JsonResponse({'category_id': None})
    
    cat_id = predict_category(description, request.user)
    
    return JsonResponse({'category_id': cat_id})


# ============================================
# DASHBOARD & CHARTS
# ============================================

@login_required
def dashboard(request):
    """Dashboard with charts and statistics"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    user = request.user
    today = timezone.now().date()
    
    # Tháng hiện tại
    first_day_this_month = today.replace(day=1)
    first_day_next_month = (first_day_this_month + relativedelta(months=1))
    
    # Tháng trước
    first_day_last_month = (first_day_this_month - relativedelta(months=1))
    
    # Tổng chi tiêu
    total_expenses = Expense.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Chi tiêu tháng này
    this_month_expenses = Expense.objects.filter(
        user=user, 
        date__gte=first_day_this_month,
        date__lt=first_day_next_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Chi tiêu tháng trước
    last_month_expenses = Expense.objects.filter(
        user=user,
        date__gte=first_day_last_month,
        date__lt=first_day_this_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Tổng thu nhập
    total_income = Income.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Thu nhập tháng này
    this_month_income = Income.objects.filter(
        user=user,
        date__gte=first_day_this_month,
        date__lt=first_day_next_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Số dư
    balance = total_income - total_expenses
    
    # Budget
    budget_obj, _ = Budget.objects.get_or_create(user=user)
    
    # Xử lý Budget form (như bên ep1_lists)
    if 'budget_submit' in request.POST:
        b_form = BudgetForm(request.POST, instance=budget_obj)
        if b_form.is_valid():
            b_form.save()
            messages.success(request, 'Cập nhật ngân sách thành công!')
            return redirect('ep1:dashboard')
    else:
        b_form = BudgetForm(instance=budget_obj)
    
    # Tính toán ngân sách còn lại
    budget_remaining = budget_obj.total - this_month_expenses
    
    # Top 5 danh mục chi tiêu
    top_categories = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]
    
    # Recent transactions with optimized queries
    recent_expenses = Expense.objects.filter(user=user).select_related('category').order_by('-date')[:3]
    recent_income = Income.objects.filter(user=user).select_related('source').order_by('-date')[:3]
    
    # Upcoming recurring expenses
    upcoming_recurring = RecurringExpense.objects.filter(
        user=user,
        is_active=True,
        next_due_date__gte=today
    ).select_related('category').order_by('next_due_date')[:5]
    
    # Lấy các thông báo đang Active
    active_announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')

    # Tính phần trăm ngân sách đã dùng
    if budget_obj.total > 0:
        budget_percentage = (this_month_expenses / budget_obj.total) * 100
    else:
        budget_percentage = 0
    
    context = {
        'total_expenses': total_expenses,
        'this_month_expenses': this_month_expenses,
        'last_month_expenses': last_month_expenses,
        'total_income': total_income,
        'this_month_income': this_month_income,
        'balance': balance,
        'budget': budget_obj,
        'b_form': b_form, # Thêm form vào context
        'budget_remaining': budget_remaining,
        'budget_percentage': budget_percentage, # Thêm phần trăm
        'top_categories': top_categories,
        'recent_expenses': recent_expenses,
        'recent_income': recent_income,
        'upcoming_recurring': upcoming_recurring,
        'active_announcements': active_announcements,
    }
    
    return render(request, 'ep1/dashboard.html', context)


@login_required
def chart_category_data(request):
    """API endpoint for category pie chart data"""
    user = request.user
    
    category_data = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:10]
    
    labels = [item['category__name'] or 'Không xác định' for item in category_data]
    data = [float(item['total']) for item in category_data]
    
    return JsonResponse({
        'labels': labels,
        'data': data
    })


@login_required
def chart_monthly_trend(request):
    """API endpoint for monthly trend chart (last 6 months)"""
    from dateutil.relativedelta import relativedelta
    user = request.user
    today = timezone.now().date()
    
    # Lấy 6 tháng trước
    months_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - relativedelta(months=i))
        month_end = (month_start + relativedelta(months=1))
        
        month_expenses = Expense.objects.filter(
            user=user,
            date__gte=month_start,
            date__lt=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        months_data.append({
            'label': month_start.strftime('%m/%Y'),
            'value': float(month_expenses)
        })
    
    labels = [item['label'] for item in months_data]
    data = [item['value'] for item in months_data]
    
    return JsonResponse({
        'labels': labels,
        'data': data
    })


@login_required
def chart_expense_vs_income(request):
    """API endpoint for income vs expense comparison (last 6 months)"""
    from dateutil.relativedelta import relativedelta
    user = request.user
    today = timezone.now().date()
    
    months_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - relativedelta(months=i))
        month_end = (month_start + relativedelta(months=1))
        
        month_expenses = Expense.objects.filter(
            user=user,
            date__gte=month_start,
            date__lt=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        month_income = Income.objects.filter(
            user=user,
            date__gte=month_start,
            date__lt=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        months_data.append({
            'label': month_start.strftime('%m/%Y'),
            'expenses': float(month_expenses),
            'income': float(month_income)
        })
    
    labels = [item['label'] for item in months_data]
    expense_data = [item['expenses'] for item in months_data]
    income_data = [item['income'] for item in months_data]
    
    return JsonResponse({
        'labels': labels,
        'expenses': expense_data,
        'income': income_data
    })


# ============================================
# INCOME MANAGEMENT
# ============================================

@login_required
def income_list(request):
    """Income list with filters"""
    base_income = Income.objects.filter(user=request.user).select_related('source')
    
    # Filter by source
    source_id = request.GET.get('source')
    if source_id:
        base_income = base_income.filter(source_id=source_id)
    
    # Filter by date
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from and date_to:
        base_income = base_income.filter(date__range=[date_from, date_to])
    elif date_from:
        base_income = base_income.filter(date__gte=date_from)
    elif date_to:
        base_income = base_income.filter(date__lte=date_to)
    
    # Sort
    sort_amount = request.GET.get('sort_amount')
    if sort_amount == 'asc':
        incomes = base_income.order_by('amount')
    elif sort_amount == 'desc':
        incomes = base_income.order_by('-amount')
    else:
        incomes = base_income.order_by('-date')
    
    # Pagination
    paginator = Paginator(incomes, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate total
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Income sources
    sources = IncomeSource.objects.filter(user=request.user)
    
    context = {
        'incomes': page_obj,
        'page_obj': page_obj,
        'total_income': total_income,
        'sources': sources,
        'selected_source': int(source_id) if source_id else None,
        'date_from': date_from,
        'date_to': date_to,
        'sort_amount': sort_amount,
        'sort_date': sort_date,
    }
    
    return render(request, 'ep1/income_list.html', context)


@login_required
def add_income(request):
    """Thêm thu nhập mới"""
    if request.method == 'POST':
        form = IncomeForm(request.POST, user=request.user)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            messages.success(request, 'Thêm thu nhập thành công!')
            return redirect('ep1:income_list')
    else:
        form = IncomeForm(user=request.user)
    
    return render(request, 'ep1/add_income.html', {'form': form})


@login_required
def edit_income(request, pk):
    """Sửa thu nhập"""
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thu nhập thành công!')
            # Redirect to 'next' if provided, otherwise go to income_list
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('ep1:income_list')
    else:
        form = IncomeForm(instance=income, user=request.user)
    
    # Pass next parameter to template
    next_url = request.GET.get('next', '')
    return render(request, 'ep1/edit_income.html', {
        'form': form, 
        'income': income,
        'next': next_url
    })


@login_required
def delete_income(request, pk):
    """Xóa thu nhập"""
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        income.delete()
        messages.success(request, 'Đã xóa thu nhập.')
        # Redirect to 'next' if provided, otherwise go to income_list
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('ep1:income_list')
    
    # Pass next parameter to template
    next_url = request.GET.get('next', '')
    return render(request, 'ep1/delete_income.html', {
        'income': income,
        'next': next_url
    })


@login_required
def income_source_manage(request):
    """Quản lý nguồn thu nhập"""
    if request.method == 'POST':
        form = IncomeSourceForm(request.POST)
        if form.is_valid():
            source = form.save(commit=False)
            source.user = request.user
            source.save()
            messages.success(request, 'Thêm nguồn thu nhập thành công!')
            return redirect('ep1:income_source_manage')
    else:
        form = IncomeSourceForm()
    
    sources = IncomeSource.objects.filter(user=request.user)
    return render(request, 'ep1/income_sources.html', {'sources': sources, 'form': form})


@login_required
def edit_income_source(request, pk):
    """Sửa nguồn thu nhập"""
    source = get_object_or_404(IncomeSource, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IncomeSourceForm(request.POST, instance=source)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật nguồn thu thành công!')
            return redirect('ep1:income_source_manage')
    else:
        form = IncomeSourceForm(instance=source)
    
    return render(request, 'ep1/edit_income_source.html', {'form': form, 'source': source})


@login_required
def delete_income_source(request, pk):
    """Xóa nguồn thu nhập"""
    source = get_object_or_404(IncomeSource, pk=pk, user=request.user)
    if source.income_set.exists():
        messages.error(request, 'Không thể xóa nguồn thu đang có dữ liệu!')
        return redirect('ep1:income_source_manage')
    
    if request.method == 'POST':
        source.delete()
        messages.success(request, 'Đã xóa nguồn thu.')
        return redirect('ep1:income_source_manage')
    
    return render(request, 'ep1/delete_income_source.html', {'source': source})


# ============================================
# RECURRING EXPENSES
# ============================================

@login_required
def recurring_list(request):
    """Danh sách chi tiêu định kỳ"""
    from django.utils import timezone
    
    # Get show_history parameter
    show_history = request.GET.get('show_history', 'false') == 'true'
    today = timezone.now().date()
    
    base_recurrings = RecurringExpense.objects.filter(user=request.user).select_related('category')
    
    # Filter by expired status based on tab
    if show_history:
        # History tab: show only expired items
        base_recurrings = base_recurrings.filter(end_date__lt=today)
    else:
        # Active tab: hide expired items (show only active/future ones)
        base_recurrings = base_recurrings.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        )
    
    # Lọc theo danh mục
    category_id = request.GET.get('category')
    if category_id:
        base_recurrings = base_recurrings.filter(category_id=category_id)
    
    # Lọc theo trạng thái
    status = request.GET.get('status')
    if status == 'active':
        base_recurrings = base_recurrings.filter(is_active=True)
    elif status == 'inactive':
        base_recurrings = base_recurrings.filter(is_active=False)
    
    # Lọc theo tần suất
    frequency = request.GET.get('frequency')
    if frequency:
        base_recurrings = base_recurrings.filter(frequency=frequency)
    
    # Lọc theo ngày đến hạn
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    if due_date_from:
        base_recurrings = base_recurrings.filter(next_due_date__gte=due_date_from)
    if due_date_to:
        base_recurrings = base_recurrings.filter(next_due_date__lte=due_date_to)
    
    # Sắp xếp theo số tiền
    sort_amount = request.GET.get('sort_amount')
    if sort_amount == 'asc':
        recurrings = base_recurrings.order_by('amount')
    elif sort_amount == 'desc':
        recurrings = base_recurrings.order_by('-amount')
    else:
        recurrings = base_recurrings.order_by('-next_due_date')
    
    # Phân trang
    paginator = Paginator(recurrings, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    
    # Calculate counts for badges
    active_count = RecurringExpense.objects.filter(
        user=request.user
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).count()
    
    expired_count = RecurringExpense.objects.filter(
        user=request.user,
        end_date__lt=today
    ).count()
    
    context = {
        'recurrings': page_obj,
        'page_obj': page_obj,
        'today': today,
        'show_history': show_history,
        'active_count': active_count,
        'expired_count': expired_count,
        'categories': Category.objects.filter(user=request.user),
        'selected_category': int(category_id) if category_id else None,
        'selected_status': status,
        'selected_frequency': frequency,
        'sort_amount': sort_amount,
    }
    
    return render(request, 'ep1/recurring_list.html', context)


@login_required
def add_recurring(request):
    """Add new recurring expense"""
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.user = request.user
            
            # Auto-calculate next_due_date based on start_date and frequency
            from datetime import timedelta
            from dateutil.relativedelta import relativedelta
            
            if recurring.frequency == 'daily':
                recurring.next_due_date = recurring.start_date + timedelta(days=1)
            elif recurring.frequency == 'weekly':
                recurring.next_due_date = recurring.start_date + timedelta(weeks=1)
            elif recurring.frequency == 'monthly':
                recurring.next_due_date = recurring.start_date + relativedelta(months=1)
            elif recurring.frequency == 'yearly':
                recurring.next_due_date = recurring.start_date + relativedelta(years=1)
            else:
                recurring.next_due_date = recurring.start_date
            
            recurring.save()
            messages.success(request, 'Thêm chi tiêu định kỳ thành công!')
            return redirect('ep1:recurring_list')
    else:
        form = RecurringExpenseForm(user=request.user)
    
    return render(request, 'ep1/add_recurring.html', {'form': form})


@login_required
def edit_recurring(request, pk):
    """Edit recurring expense with auto-recalculation of next_due_date"""
    recurring = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, instance=recurring, user=request.user)
        if form.is_valid():
            recurring = form.save(commit=False)
            
            # Always recalculate next_due_date based on start_date and frequency
            from datetime import timedelta
            from dateutil.relativedelta import relativedelta
            
            if recurring.frequency == 'daily':
                recurring.next_due_date = recurring.start_date + timedelta(days=1)
            elif recurring.frequency == 'weekly':
                recurring.next_due_date = recurring.start_date + timedelta(weeks=1)
            elif recurring.frequency == 'monthly':
                recurring.next_due_date = recurring.start_date + relativedelta(months=1)
            elif recurring.frequency == 'yearly':
                recurring.next_due_date = recurring.start_date + relativedelta(years=1)
            else:
                recurring.next_due_date = recurring.start_date
            
            recurring.save()
            messages.success(request, 'Cập nhật chi tiêu định kỳ thành công!')
            # Redirect to 'next' if provided
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('ep1:recurring_list')
    else:
        form = RecurringExpenseForm(instance=recurring, user=request.user)
    
    # Pass next parameter to template
    next_url = request.GET.get('next', '')
    return render(request, 'ep1/edit_recurring.html', {
        'form': form,
        'recurring': recurring,
        'next': next_url
    })


@login_required
def delete_recurring(request, pk):
    """Xóa chi tiêu định kỳ"""
    recurring = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    if request.method == 'POST':
        recurring.delete()
        messages.success(request, 'Đã xóa chi tiêu định kỳ.')
        # Redirect to 'next' if provided
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('ep1:recurring_list')
    
    # Pass next parameter to template
    next_url = request.GET.get('next', '')
    return render(request, 'ep1/delete_recurring.html', {
        'recurring': recurring,
        'next': next_url
    })


@login_required
def toggle_recurring_status(request, pk):
    """Bật/tắt trạng thái chi tiêu định kỳ"""
    recurring = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    recurring.is_active = not recurring.is_active
    recurring.save()
    
    status = "kích hoạt" if recurring.is_active else "vô hiệu hóa"
    messages.success(request, f'Đã {status} chi tiêu định kỳ "{recurring.name}".')
    
    # Redirect to 'next' if provided
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('ep1:recurring_list')


@login_required
def generate_recurring_expenses(request):
    """Generate actual expenses from due recurring templates"""
    user = request.user
    today = timezone.now().date()
    
    # Find all active recurring expenses that are due
    due_recurrings = RecurringExpense.objects.filter(
        user=user,
        is_active=True,
        next_due_date__lte=today
    ).select_related('category')
    
    generated_count = 0
    
    # Process each due recurring expense
    for recurring in due_recurrings:
        # Check if expired and deactivate if needed
        if recurring.is_expired():
            recurring.is_active = False
            recurring.save()
            continue
        
        # Create actual expense from template
        Expense.objects.create(
            user=user,
            amount=recurring.amount,
            description=f"[Định kỳ] {recurring.description or recurring.name}",
            category=recurring.category,
            date=recurring.next_due_date
        )
        
        generated_count += 1
        
        # Update next_due_date for next occurrence
        recurring.advance_next_due_date()
        recurring.save()
    
    # Notify user of results
    if generated_count > 0:
        messages.success(request, f'Đã tạo {generated_count} chi tiêu từ các mẫu định kỳ.')
    else:
        messages.info(request, 'Không có chi tiêu định kỳ nào đến hạn.')
    
    return redirect('ep1:recurring_list')