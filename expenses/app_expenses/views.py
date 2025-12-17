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
            return redirect('ep1:ep1_lists')  
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
        p_form = ProfileUpdateForm(request.POST, instance=profile_obj)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Cập nhật hồ sơ thành công!')
            return redirect('ep1:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile_obj)

    return render(request, 'ep1/profile.html', {
        'u_form': u_form,
        'p_form': p_form,
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
    
    order_fields = []
    if sort_amount == 'asc':
        order_fields.append('amount')
    elif sort_amount == 'desc':
        order_fields.append('-amount')

    if sort_date == 'asc':
        order_fields.append('date')
    elif sort_date == 'desc':
        order_fields.append('-date')

    return queryset.order_by(*order_fields) if order_fields else queryset.order_by('-date')

@login_required
def ep1_lists(request):
    # 1. Lấy TOÀN BỘ dữ liệu (Dùng để tính Ngân sách còn lại & Top danh mục)
    base_expenses = Expense.objects.filter(user=request.user)

    # 2. Tạo dữ liệu ĐÃ LỌC (Dùng để hiển thị Bảng, Biểu đồ & tính Tổng chi tiêu theo lọc)
    filtered_expenses = _apply_filters(base_expenses, request.GET)
    expenses = _apply_sorting(filtered_expenses, request.GET)

    # --- PHÂN TRANG ---
    paginator = Paginator(expenses, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- TÍNH TOÁN (XỬ LÝ RIÊNG 2 PHẦN) ---

    # A. Tính số liệu THEO BỘ LỌC (Để hiển thị ở ô "Tổng chi tiêu")
    # Giúp bạn biết: "Tháng này tiêu bao nhiêu?" hoặc "Ăn uống hết bao nhiêu?"
    filtered_total = expenses.aggregate(sum=Sum('amount'))['sum'] or 0

    # B. Tính số liệu TOÀN BỘ (Để tính "Ngân sách còn lại" và "Chi nhiều nhất")
    # Giúp số dư ví không bị sai khi bạn lọc dữ liệu
    global_total = base_expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    
    global_category_data = base_expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    top_category_item = global_category_data.first()
    top_category = top_category_item['category__name'] if top_category_item else '—'

    # --- DỮ LIỆU BIỂU ĐỒ (Dùng dữ liệu đã lọc để biểu đồ khớp với bảng) ---
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
            return redirect('ep1:ep1_lists')
    else:
        b_form = BudgetForm(instance=budget_obj)

    # Lấy các thông báo đang Active (Mới nhất lên đầu)
    active_announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')

    context = {
        'expenses': page_obj, 
        'page_obj': page_obj,
        
        # --- CÁC BIẾN QUAN TRỌNG ĐÃ CHỈNH SỬA ---
        'total_spent': filtered_total,                 # Hiển thị số tiền ĐÃ LỌC
        'remaining': budget_obj.total - global_total,  # Hiển thị ngân sách THỰC TẾ (Toàn bộ)
        'top_category': top_category,                  # Hiển thị Top danh mục TOÀN BỘ
        # ------------------------------------------

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
    if not Category.objects.filter(user=request.user).exists():
        create_default_categories(request.user)

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