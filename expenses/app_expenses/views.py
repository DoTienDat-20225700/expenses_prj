import csv
import threading
import os
import logging
import re
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user
from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.http import require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count, Q
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from decouple import config
from .models import *
from .form import *
from .ml_utils import predict_category, train_model, get_model_path
from .services import (
    generate_due_recurring_transactions,
    toggle_recurring_active_status,
    get_dashboard_summary_metrics,
    get_monthly_trend_chart_data,
    get_expense_vs_income_chart_data,
    get_category_distribution_chart_data,
    get_dashboard_refresh_payload,
    calculate_ai_savings_suggestions,
    sync_savings_goal_status,
    build_recurring_chat_preview,
    build_expense_action_preview,
    create_income_from_chat,
    create_recurring_from_chat,
    manage_expense_from_chat,
    create_expense_from_chat,
)

logger = logging.getLogger(__name__)


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
    # 1. Thống kê User (gộp total và new_users thành 1 query)
    month_ago = timezone.now() - timedelta(days=30)
    user_stats = User.objects.aggregate(
        total_users=Count('id'),
        new_users=Count('id', filter=Q(date_joined__gte=month_ago))
    )
    total_users = user_stats['total_users'] or 0
    new_users = user_stats['new_users'] or 0

    # 2. Thống kê Dòng tiền (Toàn hệ thống - gộp count và total sum)
    expense_stats = Expense.objects.aggregate(
        count=Count('id'),
        total=Sum('amount')
    )
    total_expenses_count = expense_stats['count'] or 0
    total_expenses = expense_stats['total'] or 0
    
    income_stats = Income.objects.aggregate(
        count=Count('id'),
        total=Sum('amount')
    )
    total_income_count = income_stats['count'] or 0
    total_income = income_stats['total'] or 0
    
    # DÒNG TIỀN THỰC = Thu nhập - Chi tiêu
    net_cash_flow = total_income - total_expenses

    # 3. Top Danh mục phổ biến nhất hệ thống (theo số lượng giao dịch)
    top_categories = Expense.objects.values('category__name') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:5]  # Lấy top 5

    context = {
        'total_users': total_users,
        'new_users': new_users,
        'total_expenses_count': total_expenses_count,
        'total_income_count': total_income_count,
        'total_expenses': total_expenses,
        'total_income': total_income,
        'net_cash_flow': net_cash_flow,
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
    """Trang giám sát trạng thái Model AI của từng user (dùng annotate để tránh N+1)"""
    users = User.objects.annotate(expense_count=Count('expense')).order_by('-date_joined')
    ai_stats = []

    for user in users:
        model_path = get_model_path(user)
        has_model = os.path.exists(model_path)
        model_size = 0

        if has_model:
            # Lấy kích thước file (KB)
            model_size = round(os.path.getsize(model_path) / 1024, 2)
            data_count = user.expense_count
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
@require_http_methods(["POST"])
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
@require_http_methods(["POST"])
def delete_announcement(request, pk):
    """Xóa thông báo"""
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.delete()
    messages.success(request, "Đã xóa thông báo.")
    return redirect('ep1:announcement_manager')

@user_passes_test(is_admin)
@require_http_methods(["POST"])
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
        # ⚠️ QUAN TRỌNG: Lấy avatar cũ từ DATABASE trước khi form xử lý
        old_avatar_from_db = Profile.objects.get(pk=profile_obj.pk).avatar
        
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            # Xử lý THAY ĐỔI ảnh mới (upload ảnh mới)
            if 'avatar' in request.FILES:
                # Sử dụng avatar cũ từ database (KHÔNG phải từ form)
                old_avatar = old_avatar_from_db
                
                # Nếu có avatar cũ, xóa nó trên Cloudinary
                if old_avatar:
                    try:
                        import cloudinary.uploader
                        import cloudinary
                        from cloudinary import CloudinaryResource
                        
                        # Kiểm tra xem avatar cũ có phải CloudinaryResource không
                        is_cloudinary = isinstance(old_avatar, CloudinaryResource)
                        avatar_str = str(old_avatar)
                        
                        logger.debug("Old avatar info: %s (CloudinaryResource=%s)", avatar_str, is_cloudinary)
                        
                        # Nếu là CloudinaryResource HOẶC URL chứa cloudinary.com
                        if is_cloudinary or 'cloudinary.com' in avatar_str or 'res.cloudinary.com' in avatar_str:
                            old_public_id = None
                            
                            # Cách 1: Nếu là CloudinaryResource, lấy public_id trực tiếp
                            if is_cloudinary:
                                if hasattr(old_avatar, 'public_id') and old_avatar.public_id:
                                    old_public_id = old_avatar.public_id
                                else:
                                    old_public_id = avatar_str
                            
                            # Cách 2: Parse từ URL đầy đủ nếu có
                            elif 'cloudinary.com' in avatar_str:
                                parts = avatar_str.split('/upload/')
                                if len(parts) > 1:
                                    path_with_version = parts[1]
                                    path_parts = path_with_version.split('/', 1)
                                    if len(path_parts) > 1:
                                        full_path = path_parts[1]
                                        old_public_id = full_path.split('?')[0].rsplit('.', 1)[0]
                            
                            # Xóa ảnh cũ nếu tìm được public_id
                            if old_public_id:
                                result = cloudinary.uploader.destroy(old_public_id)
                                logger.info("Cloudinary old avatar deletion result for %s: %s", old_public_id, result.get('result'))
                            else:
                                logger.warning("Could not determine public_id for old avatar: %s", avatar_str)
                        else:
                            logger.debug("Old avatar is local file: %s", avatar_str)
                            
                    except Exception as e:
                        logger.warning("Error deleting old avatar from Cloudinary: %s", e)
                
                # Save cả 2 form
                u_form.save()
                p_form.save()
                messages.success(request, 'Cập nhật hồ sơ thành công!')
                return redirect('ep1:profile')
            else:
                # Không có thay đổi avatar, chỉ cập nhật thông tin khác
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
    # Get top category
    global_category_data = base_expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    top_category_item = global_category_data.first()
    top_category = top_category_item['category__name'] if top_category_item else '—'

    # Chart data
    category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    daily_data = expenses.annotate(day=TruncDate('date')).values('day').annotate(total=Sum('amount')).order_by('day')

    chart_labels = [item['category__name'] or 'Chưa phân loại' for item in category_data]
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
def ep1_list_refresh_api(request):
    """Return updated list rows, summaries, and chart data for the expenses list page."""
    base_expenses = Expense.objects.filter(user=request.user).select_related('category')
    filtered_expenses = _apply_filters(base_expenses, request.GET)
    expenses = _apply_sorting(filtered_expenses, request.GET)

    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    today = timezone.now().date()
    first_day_this_month = today.replace(day=1)
    from dateutil.relativedelta import relativedelta
    first_day_next_month = (first_day_this_month + relativedelta(months=1))

    this_month_expenses = Expense.objects.filter(
        user=request.user,
        date__gte=first_day_this_month,
        date__lt=first_day_next_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    filtered_total = expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    global_category_data = base_expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    top_category_item = global_category_data.first()
    top_category = (top_category_item['category__name'] or 'Chưa phân loại') if top_category_item else '—'

    category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    daily_data = expenses.annotate(day=TruncDate('date')).values('day').annotate(total=Sum('amount')).order_by('day')

    chart_labels = [item['category__name'] or 'Chưa phân loại' for item in category_data]
    chart_data = [float(item['total']) for item in category_data]
    chart_labels_day = [item['day'].strftime('%d/%m/%Y') for item in daily_data]
    chart_data_day = [float(item['total']) for item in daily_data]

    budget_obj, _ = Budget.objects.get_or_create(user=request.user)
    remaining = budget_obj.total - this_month_expenses

    rows_html = render_to_string(
        'ep1/partials/expense_rows.html',
        {
            'expenses': page_obj,
            'next_url': request.get_full_path(),
        },
        request=request,
    )

    return JsonResponse({
        'success': True,
        'rows_html': rows_html,
        'summary': {
            'this_month_expenses': float(this_month_expenses),
            'total_spent': float(filtered_total),
            'remaining': float(remaining),
            'top_category': top_category,
        },
        'charts': {
            'labels': chart_labels,
            'data': chart_data,
            'labels_day': chart_labels_day,
            'data_day': chart_data_day,
        },
    })

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
                logger.warning("Lỗi chạy background task: %s", e)
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
    base_expenses = Expense.objects.filter(user=request.user).select_related('category')
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
    budget_obj, _ = Budget.objects.get_or_create(user=request.user)

    # Xử lý Budget form (như bên ep1_lists)
    if 'budget_submit' in request.POST:
        b_form = BudgetForm(request.POST, instance=budget_obj)
        if b_form.is_valid():
            b_form.save()
            messages.success(request, 'Cập nhật ngân sách thành công!')
            return redirect('ep1:dashboard')
    else:
        b_form = BudgetForm(instance=budget_obj)

    metrics = get_dashboard_summary_metrics(request.user)
    context = {
        **metrics,
        'b_form': b_form,
    }
    return render(request, 'ep1/dashboard.html', context)


@login_required
def chart_category_data(request):
    """API endpoint for category pie chart data"""
    return JsonResponse(get_category_distribution_chart_data(request.user))


@login_required
def chart_monthly_trend(request):
    """API endpoint for monthly trend chart (last 6 months) using single conditional aggregate"""
    return JsonResponse(get_monthly_trend_chart_data(request.user))


@login_required
def chart_expense_vs_income(request):
    """API endpoint for income vs expense comparison (last 6 months) using conditional aggregates"""
    return JsonResponse(get_expense_vs_income_chart_data(request.user))


@login_required
def dashboard_refresh_api(request):
    """Return updated dashboard summary, lists, and chart data using conditional aggregates."""
    payload = get_dashboard_refresh_payload(request.user, request=request)
    return JsonResponse(payload)


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
    sort_date = request.GET.get('sort_date')
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
    
    
    # Calculate counts for badges with single conditional aggregation
    counts = RecurringExpense.objects.filter(user=request.user).aggregate(
        active=Count('id', filter=Q(end_date__isnull=True) | Q(end_date__gte=today)),
        expired=Count('id', filter=Q(end_date__lt=today)),
    )
    active_count = counts['active'] or 0
    expired_count = counts['expired'] or 0
    
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
        # Validate next param chống open redirect
        next_url = request.POST.get('next') or request.GET.get('next')
        return redirect(_get_safe_redirect_url(request, next_url, 'ep1:recurring_list'))

    # Pass next parameter to template
    next_url = request.GET.get('next', '')
    return render(request, 'ep1/delete_recurring.html', {
        'recurring': recurring,
        'next': next_url
    })


def _get_safe_redirect_url(request, next_param_value, fallback):
    """Validate next URL trước redirect để chống open redirect attack.

    Chỉ cho phép redirect đến URL cùng host (relative path).
    """
    url = next_param_value
    if url and url_has_allowed_host_and_scheme(
        url=url,
        allowed_hosts=request.get_host(),
        require_https=request.is_secure(),
    ):
        return url
    return fallback


@login_required
@require_http_methods(["POST"])
def toggle_recurring_status(request, pk):
    """Bật/tắt trạng thái chi tiêu định kỳ"""
    try:
        is_active, name = toggle_recurring_active_status(pk, request.user)
    except RecurringExpense.DoesNotExist:
        raise Http404("Chi tiêu định kỳ không tồn tại")
    status = "kích hoạt" if is_active else "vô hiệu hóa"
    messages.success(request, f'Đã {status} chi tiêu định kỳ "{name}".')

    # Validate next param chống open redirect
    next_url = request.POST.get('next') or request.GET.get('next')
    return redirect(_get_safe_redirect_url(request, next_url, 'ep1:recurring_list'))


@login_required
@require_http_methods(["POST"])
def generate_recurring_expenses(request):
    """Generate actual expenses/incomes from due recurring templates."""
    generated_count, generated_income_count, _ = generate_due_recurring_transactions(request.user)

    # ── Notify user ────────────────────────────────────────────────────────────
    if generated_count > 0 or generated_income_count > 0:
        messages.success(
            request,
            f'Đã tạo {generated_count} chi tiêu và {generated_income_count} thu nhập từ các mẫu định kỳ.',
        )
    else:
        messages.info(request, 'Không có chi tiêu định kỳ nào đến hạn.')

    return redirect('ep1:recurring_list')


# ============================================
# SAVINGS GOAL MANAGEMENT
# ============================================

@login_required
def savings_goal_list(request):
    """Hiển thị danh sách mục tiêu tiết kiệm"""
    goals = SavingsGoal.objects.filter(user=request.user).order_by('-created_at')

    # Cập nhật trạng thái chỉ khi mục tiêu chuyển từ chưa hoàn thành sang hoàn thành
    for goal in goals:
        sync_savings_goal_status(goal)

    context = {
        'goals': goals,
    }
    return render(request, 'ep1/savings_goal_list.html', context)


@login_required
def add_savings_goal(request):
    """Tạo mục tiêu tiết kiệm mới"""
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Đã tạo mục tiêu "{goal.goal_name}" thành công!')
            return redirect('ep1:savings_goal_detail', pk=goal.pk)
    else:
        form = SavingsGoalForm(user=request.user)

    context = {
        'form': form,
        'title': 'Tạo mục tiêu tiết kiệm mới',
    }
    return render(request, 'ep1/add_savings_goal.html', context)


@login_required
def edit_savings_goal(request, pk):
    """Chỉnh sửa mục tiêu tiết kiệm"""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)

    if request.method == 'POST':
        form = SavingsGoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật mục tiêu "{goal.goal_name}"!')
            return redirect('ep1:savings_goal_detail', pk=goal.pk)
    else:
        form = SavingsGoalForm(instance=goal, user=request.user)

    context = {
        'form': form,
        'goal': goal,
        'title': f'Chỉnh sửa: {goal.goal_name}',
    }
    return render(request, 'ep1/edit_savings_goal.html', context)


@login_required
def delete_savings_goal(request, pk):
    """Xóa mục tiêu tiết kiệm"""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)

    if request.method == 'POST':
        goal_name = goal.goal_name
        goal.delete()
        messages.success(request, f'Đã xóa mục tiêu "{goal_name}"!')
        return redirect('ep1:savings_goal_list')

    context = {
        'goal': goal,
    }
    return render(request, 'ep1/delete_savings_goal.html', context)


@login_required
def savings_goal_detail(request, pk):
    """Chi tiết mục tiêu với gợi ý AI"""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)

    sync_savings_goal_status(goal)

    ai_suggestions = calculate_ai_savings_suggestions(request.user, goal)

    context = {
        'goal': goal,
        'ai_suggestions': ai_suggestions,
    }
    return render(request, 'ep1/savings_goal_detail.html', context)


@login_required
def update_savings_progress(request, pk):
    """Cập nhật tiến độ tiết kiệm"""
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)

    if request.method == 'POST':
        form = UpdateSavingsProgressForm(request.POST, instance=goal)
        if form.is_valid():
            updated_goal = form.save(commit=False)

            # Kiểm tra và cập nhật trạng thái hoàn thành
            if updated_goal.check_completion():
                messages.success(request, f'🎉 Chúc mừng! Bạn đã hoàn thành mục tiêu "{goal.goal_name}"!')
            else:
                messages.success(request, f'Đã cập nhật tiến độ cho "{goal.goal_name}"!')

            updated_goal.save()
            return redirect('ep1:savings_goal_detail', pk=goal.pk)
    else:
        form = UpdateSavingsProgressForm(instance=goal)

    context = {
        'form': form,
        'goal': goal,
    }
    return render(request, 'ep1/update_savings_progress.html', context)


def get_ai_savings_suggestions(user, goal):
    """Alias for backwards compatibility delegating to savings_service."""
    return calculate_ai_savings_suggestions(user, goal)


# ======================== CHATBOT / VOICE ASSISTANT ========================

@login_required
def chat_assistant(request):
    """
    Trang giao diện Trợ lý ảo (Chat + Voice input)
    """
    # Lấy các category của user để hiển thị
    categories = Category.objects.filter(user=request.user)
    
    # Lấy 10 chi tiêu gần nhất để hiển thị context (với select_related để tránh N+1)
    recent_expenses = Expense.objects.filter(user=request.user).select_related('category').order_by('-date', '-id')[:10]
    
    context = {
        'categories': categories,
        'recent_expenses': recent_expenses,
    }
    
    return render(request, 'ep1/chat_assistant.html', context)


def _recurring_chat_preview(text, structured, user, intent):
    return build_recurring_chat_preview(text, structured, user, intent)


def _chat_expense_action_preview(text, user, intent):
    return build_expense_action_preview(text, user, intent)


@login_required
def parse_expense_api(request):
    """
    API endpoint để parse natural language input (hỗ trợ nhiều intent)
    POST: { "text": "Vừa ăn sáng hết 50k" hoặc "Tổng chi tiêu hôm nay?" }
    Returns: { "intent": "...", "response": {...} hoặc null nếu là CREATE_EXPENSE }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    import json
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    
    if not text:
        return JsonResponse({'success': False, 'error': 'Vui lòng nhập nội dung'}, status=400)

    now = timezone.now().timestamp()
    rate_limit = config('CHAT_RATE_LIMIT', default='10', cast=int)
    rate_window = config('CHAT_RATE_WINDOW_SECONDS', default='60', cast=int)
    request_times = [
        timestamp for timestamp in request.session.get('chat_request_times', [])
        if now - timestamp < rate_window
    ]
    if len(request_times) >= rate_limit:
        retry_after = max(1, int(rate_window - (now - request_times[0])))
        response = JsonResponse({
            'success': False,
            'error': f'Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau {retry_after} giây.',
            'retry_after': retry_after,
        }, status=429)
        response['Retry-After'] = str(retry_after)
        return response
    request_times.append(now)
    request.session['chat_request_times'] = request_times
    
    try:
        # Phân tích intent
        from app_expenses.utils.chat_intent import process_chat_input
        chat_history = request.session.get('chat_history', [])
        result = process_chat_input(text, request.user, history=chat_history)
        chat_history.append(text)
        request.session['chat_history'] = chat_history[-6:]
        logger.info(
            'Chat classified: user_id=%s intent=%s confidence=%.2f',
            request.user.id,
            result['intent'],
            result['confidence'],
        )
        
        intent = result['intent']
        confidence = result['confidence']

        if intent in {'EDIT_EXPENSE', 'DELETE_EXPENSE'}:
            preview = _chat_expense_action_preview(text, request.user, intent)
            if not preview:
                return JsonResponse({
                    'success': False,
                    'intent': intent,
                    'error': 'Không tìm thấy khoản chi phù hợp để xử lý.',
                }, status=404)
            return JsonResponse({
                'success': True,
                'intent': intent,
                'confidence': confidence,
                'requires_confirmation': True,
                'expense_action_preview': preview,
                'gemini_warning': result.get('gemini_error'),
            })

        if intent in {'CREATE_RECURRING_EXPENSE', 'CREATE_RECURRING_INCOME'}:
            preview = _recurring_chat_preview(
                text, result.get('structured', {}), request.user, intent
            )
            if not preview:
                return JsonResponse({
                    'success': False,
                    'intent': intent,
                    'error': 'Không tìm thấy số tiền cho giao dịch định kỳ.',
                }, status=400)
            return JsonResponse({
                'success': True,
                'intent': intent,
                'confidence': confidence,
                'requires_confirmation': True,
                'recurring_preview': preview,
                'gemini_warning': result.get('gemini_error'),
            })

        if intent == 'CREATE_INCOME':
            response = result['response']
            if response.get('type') == 'error':
                return JsonResponse({
                    'success': False,
                    'intent': intent,
                    'confidence': confidence,
                    'error': response['message'],
                }, status=400)
            return JsonResponse({
                'success': True,
                'intent': intent,
                'confidence': confidence,
                'is_query': False,
                'requires_confirmation': True,
                'income_preview': {
                    'amount': response['amount'],
                    'description': response['description'],
                    'source_name': response['source_name'],
                    'date': response['date'],
                },
                'gemini_warning': result.get('gemini_error'),
            })
        
        # Nếu là query intent hoặc OUT_OF_SCOPE, trả về response luôn
        if result['response'] is not None:
            return JsonResponse({
                'success': True,
                'intent': intent,
                'confidence': confidence,
                'response': result['response'],
                'is_query': True,
                'gemini_warning': result.get('gemini_error'),
            })
        
        # Nếu là CREATE_EXPENSE, parse như cũ
        from app_expenses.utils.nlp_parser import parse_expense_text
        expense_result = parse_expense_text(text, request.user)
        
        if not expense_result['success']:
            return JsonResponse(expense_result, status=400)
        
        # Convert date object to string để serialize
        if isinstance(expense_result.get('date'), str):
            # Already string
            date_str = expense_result['date']
        else:
            # Convert date object to ISO string
            date_str = expense_result['date'].isoformat()
        expense_result['date'] = date_str
        
        # Lấy thông tin category nếu có
        if expense_result.get('category_id'):
            try:
                category = Category.objects.get(id=expense_result['category_id'], user=request.user)
                expense_result['category_name'] = category.name
            except Category.DoesNotExist:
                expense_result['category_name'] = None
        else:
            expense_result['category_name'] = None
        
        # Thêm intent info
        expense_result['intent'] = intent
        expense_result['confidence'] = confidence
        expense_result['is_query'] = False  # Flag để frontend biết đây là expense
        expense_result['gemini_warning'] = result.get('gemini_error')
        
        return JsonResponse(expense_result)
        
    except Exception:
        logger.exception('Chat processing failed: user_id=%s', request.user.id)
        return JsonResponse({
            'success': False,
            'error': 'Đã xảy ra lỗi trong quá trình xử lý tin nhắn. Vui lòng thử lại sau.'
        }, status=500)


@login_required
def save_income_from_chat_api(request):
    """Lưu thu nhập sau khi người dùng xác nhận preview từ chatbot."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'Dữ liệu thu nhập không hợp lệ'}, status=400)

    success, payload, status_code = create_income_from_chat(request.user, data)
    return JsonResponse(payload, status=status_code)


@login_required
def save_recurring_from_chat_api(request):
    """Lưu mẫu chi tiêu hoặc thu nhập định kỳ sau khi người dùng xác nhận."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'Dữ liệu định kỳ không hợp lệ'}, status=400)

    success, payload, status_code = create_recurring_from_chat(request.user, data)
    return JsonResponse(payload, status=status_code)


@login_required
def manage_expense_from_chat_api(request):
    """Edit or delete a user-owned expense after chatbot confirmation."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'Giao dịch không hợp lệ'}, status=400)

    success, payload, status_code = manage_expense_from_chat(request.user, data)
    return JsonResponse(payload, status=status_code)


@login_required
def save_expense_from_chat_api(request):
    """
    API endpoint để lưu expense từ chat input
    POST: {
        "amount": 50000,
        "description": "Ăn sáng",
        "category_id": 1,
        "date": "2024-03-09"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    success, payload, status_code = create_expense_from_chat(request.user, data)
    return JsonResponse(payload, status=status_code)


@login_required
def chat_history_api(request):
    """
    API để lấy lịch sử chat (các expense gần đây)
    GET: /api/chat/history/?limit=10
    """
    try:
        limit = int(request.GET.get('limit', 10))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'limit phải là số nguyên'}, status=400)

    if not 1 <= limit <= 50:
        return JsonResponse({'success': False, 'error': 'limit phải nằm trong khoảng 1 đến 50'}, status=400)
    
    expenses = Expense.objects.filter(user=request.user).select_related('category').order_by('-date', '-id')[:limit]
    
    data = []
    for expense in expenses:
        data.append({
            'id': expense.id,
            'amount': float(expense.amount),
            'description': expense.description,
            'category': expense.category.name if expense.category else None,
            'date': expense.date.isoformat(),
        })
    
    return JsonResponse({'success': True, 'expenses': data})