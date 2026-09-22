import csv
import threading
import os
import logging
import re
from django.http import HttpResponse
from django.http import JsonResponse
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
    # 1. Thống kê User
    total_users = User.objects.count()

    # User mới trong 30 ngày qua
    month_ago = timezone.now() - timedelta(days=30)
    new_users = User.objects.filter(date_joined__gte=month_ago).count()

    # 2. Thống kê Dòng tiền (Toàn hệ thống)
    # Tổng số giao dịch chi tiêu
    total_expenses_count = Expense.objects.count()
    
    # Tổng CHI TIÊU toàn hệ thống
    total_expenses = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Tổng THU NHẬP toàn hệ thống
    total_income = Income.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Số giao dịch thu nhập
    total_income_count = Income.objects.count()
    
    # DÒNG TIỀN THỰC = Thu nhập - Chi tiêu
    net_cash_flow = total_income - total_expenses

    # 3. Top Danh mục phổ biến nhất hệ thống (theo số lượng giao dịch)
    # Lấy tên danh mục và đếm số lần xuất hiện
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
                        
                        print(f"🔍 Debug - Avatar từ DB: {avatar_str}")
                        print(f"🔍 Debug - Là CloudinaryResource: {is_cloudinary}")
                        print(f"🔍 Debug - Type: {type(old_avatar)}")
                        
                        # Nếu là CloudinaryResource HOẶC URL chứa cloudinary.com
                        if is_cloudinary or 'cloudinary.com' in avatar_str or 'res.cloudinary.com' in avatar_str:
                            old_public_id = None
                            
                            # Cách 1: Nếu là CloudinaryResource, lấy public_id trực tiếp
                            if is_cloudinary:
                                # CloudinaryResource có thể chứa public_id trực tiếp khi convert sang string
                                if hasattr(old_avatar, 'public_id') and old_avatar.public_id:
                                    old_public_id = old_avatar.public_id
                                else:
                                    # Nếu không có thuộc tính, string representation chính là public_id
                                    old_public_id = avatar_str
                                print(f"✅ CloudinaryResource - public_id: {old_public_id}")
                            
                            # Cách 2: Parse từ URL đầy đủ nếu có
                            elif 'cloudinary.com' in avatar_str:
                                print(f"⚠️ Parse từ URL đầy đủ...")
                                parts = avatar_str.split('/upload/')
                                if len(parts) > 1:
                                    path_with_version = parts[1]
                                    path_parts = path_with_version.split('/', 1)
                                    if len(path_parts) > 1:
                                        full_path = path_parts[1]
                                        old_public_id = full_path.split('?')[0].rsplit('.', 1)[0]
                                        print(f"✅ Parse được public_id từ URL: {old_public_id}")
                            
                            # Xóa ảnh cũ nếu tìm được public_id
                            if old_public_id:
                                result = cloudinary.uploader.destroy(old_public_id)
                                print(f"✅ Đã gọi API xóa - public_id: {old_public_id}")
                                print(f"📊 Kết quả từ Cloudinary: {result}")
                                
                                if result.get('result') == 'ok':
                                    print(f"✅✅✅ ĐÃ XÓA THÀNH CÔNG avatar cũ trên Cloudinary!")
                                elif result.get('result') == 'not found':
                                    print(f"⚠️ Cloudinary không tìm thấy ảnh: {old_public_id}")
                                else:
                                    print(f"⚠️ Kết quả: {result.get('result', 'unknown')}")
                            else:
                                print(f"❌ Không xác định được public_id")
                        else:
                            print(f"ℹ️ Avatar cũ là file local: {avatar_str}")
                            
                    except Exception as e:
                        print(f"❌ Lỗi khi xóa avatar: {e}")
                        import traceback
                        traceback.print_exc()
                
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
    global_total = base_expenses.aggregate(sum=Sum('amount'))['sum'] or 0
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


@login_required
def dashboard_refresh_api(request):
    """Return updated dashboard summary, lists, and chart data."""
    from dateutil.relativedelta import relativedelta

    user = request.user
    today = timezone.now().date()

    first_day_this_month = today.replace(day=1)
    first_day_next_month = (first_day_this_month + relativedelta(months=1))

    total_expenses = Expense.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
    this_month_expenses = Expense.objects.filter(
        user=user,
        date__gte=first_day_this_month,
        date__lt=first_day_next_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_income = Income.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
    this_month_income = Income.objects.filter(
        user=user,
        date__gte=first_day_this_month,
        date__lt=first_day_next_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    balance = total_income - total_expenses

    budget_obj, _ = Budget.objects.get_or_create(user=user)
    budget_remaining = budget_obj.total - this_month_expenses
    budget_percentage = (this_month_expenses / budget_obj.total) * 100 if budget_obj.total > 0 else 0

    top_categories = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    recent_expenses = Expense.objects.filter(user=user).select_related('category').order_by('-date')[:3]
    recent_income = Income.objects.filter(user=user).select_related('source').order_by('-date')[:3]

    category_data = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:10]
    category_labels = [item['category__name'] or 'Không xác định' for item in category_data]
    category_values = [float(item['total']) for item in category_data]

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
            'income': float(month_income),
            'expenses': float(month_expenses),
        })

    income_labels = [item['label'] for item in months_data]
    income_values = [item['income'] for item in months_data]
    expense_values = [item['expenses'] for item in months_data]

    top_categories_html = render_to_string(
        'ep1/partials/dashboard_top_categories.html',
        {'top_categories': top_categories},
        request=request,
    )

    recent_transactions_html = render_to_string(
        'ep1/partials/dashboard_recent_transactions.html',
        {
            'recent_expenses': recent_expenses,
            'recent_income': recent_income,
        },
        request=request,
    )

    return JsonResponse({
        'success': True,
        'summary': {
            'this_month_expenses': float(this_month_expenses),
            'total_expenses': float(total_expenses),
            'this_month_income': float(this_month_income),
            'total_income': float(total_income),
            'balance': float(balance),
            'budget_total': float(budget_obj.total),
            'budget_remaining': float(budget_remaining),
            'budget_percentage': float(budget_percentage),
        },
        'top_categories_html': top_categories_html,
        'recent_transactions_html': recent_transactions_html,
        'charts_category': {
            'labels': category_labels,
            'data': category_values,
        },
        'charts_income_expense': {
            'labels': income_labels,
            'income': income_values,
            'expenses': expense_values,
        },
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
    recurring = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    recurring.is_active = not recurring.is_active
    recurring.save()

    status = "kích hoạt" if recurring.is_active else "vô hiệu hóa"
    messages.success(request, f'Đã {status} chi tiêu định kỳ "{recurring.name}".')

    # Validate next param chống open redirect
    next_url = request.POST.get('next') or request.GET.get('next')
    return redirect(_get_safe_redirect_url(request, next_url, 'ep1:recurring_list'))


@login_required
@require_http_methods(["POST"])
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
    generated_income_count = 0
    
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

    due_incomes = RecurringIncome.objects.filter(
        user=user,
        is_active=True,
        next_due_date__lte=today,
    ).select_related('source')
    for recurring_income in due_incomes:
        if recurring_income.is_expired():
            recurring_income.is_active = False
            recurring_income.save()
            continue

        Income.objects.create(
            user=user,
            source=recurring_income.source,
            amount=recurring_income.amount,
            description=f"[Định kỳ] {recurring_income.description or recurring_income.name}",
            date=recurring_income.next_due_date,
        )
        generated_income_count += 1
        recurring_income.advance_next_due_date()
        recurring_income.save()
    
    # Notify user of results
    if generated_count > 0 or generated_income_count > 0:
        messages.success(request, f'Đã tạo {generated_count} chi tiêu và {generated_income_count} thu nhập từ các mẫu định kỳ.')
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
    
    # Cập nhật trạng thái cho tất cả mục tiêu
    for goal in goals:
        if goal.check_completion():
            goal.save()
    
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
    
    # Cập nhật trạng thái hoàn thành
    if goal.check_completion():
        goal.save()
    
    # Lấy gợi ý AI
    ai_suggestions = get_ai_savings_suggestions(request.user, goal)
    
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
    """
    Logic AI để tạo gợi ý tiết kiệm dựa trên:
    - Chi tiêu hiện tại của user
    - Mục tiêu cần đạt
    - Danh mục đã chọn để cắt giảm
    """
    from datetime import timedelta
    from decimal import Decimal
    
    suggestions = {
        'daily_needed': goal.daily_savings_needed,
        'days_remaining': goal.days_remaining,
        'amount_remaining': goal.amount_remaining,
        'progress_percentage': goal.progress_percentage,
        'is_achievable': True,
        'category_analysis': [],
        'recommendations': [],
        'weekly_plan': {},
        'monthly_plan': {},
    }
    
    # Nếu đã hoàn thành hoặc quá hạn
    if goal.is_completed:
        suggestions['recommendations'].append({
            'type': 'success',
            'message': '🎉 Chúc mừng! Bạn đã hoàn thành mục tiêu này!'
        })
        return suggestions
    
    if goal.is_overdue:
        suggestions['recommendations'].append({
            'type': 'warning',
            'message': '⚠️ Mục tiêu đã quá hạn. Hãy cân nhắc gia hạn hoặc điều chỉnh mục tiêu.'
        })
        suggestions['is_achievable'] = False
        return suggestions
    
    # Phân tích chi tiêu trong 30 ngày gần đây
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    recent_expenses = Expense.objects.filter(
        user=user,
        date__gte=thirty_days_ago
    )
    
    # Tổng chi tiêu 30 ngày
    total_spent_30days = recent_expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    daily_avg_spending = total_spent_30days / 30 if total_spent_30days > 0 else Decimal('0')
    
    # Phân tích từng danh mục được chọn để cắt giảm
    categories_to_reduce = goal.categories_to_reduce.all()
    
    if categories_to_reduce.exists():
        total_reducible = Decimal('0')
        
        for category in categories_to_reduce:
            # Chi tiêu của category này trong 30 ngày
            cat_expenses = recent_expenses.filter(category=category)
            cat_total = cat_expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            cat_daily_avg = cat_total / 30
            
            # Gợi ý cắt giảm 50-70% (có thể điều chỉnh)
            suggested_reduction_pct = 60  # 60%
            suggested_daily_reduction = cat_daily_avg * Decimal(suggested_reduction_pct / 100)
            total_reducible += suggested_daily_reduction
            
            if cat_total > 0:
                suggestions['category_analysis'].append({
                    'category_name': category.name,
                    'total_30days': float(cat_total),
                    'daily_average': float(cat_daily_avg),
                    'suggested_reduction_pct': suggested_reduction_pct,
                    'suggested_daily_reduction': float(suggested_daily_reduction),
                    'monthly_savings': float(suggested_daily_reduction * 30),
                })
        
        # So sánh số tiền cần tiết kiệm với số tiền có thể cắt giảm
        if total_reducible >= goal.daily_savings_needed:
            suggestions['is_achievable'] = True
            suggestions['recommendations'].append({
                'type': 'success',
                'message': f'✅ Mục tiêu khả thi! Bạn có thể tiết kiệm {float(total_reducible):,.0f}đ/ngày bằng cách cắt giảm các danh mục đã chọn.'
            })
        else:
            gap = goal.daily_savings_needed - total_reducible
            suggestions['recommendations'].append({
                'type': 'warning',
                'message': f'⚠️ Cắt giảm các danh mục đã chọn chỉ đủ tiết kiệm {float(total_reducible):,.0f}đ/ngày. Bạn còn thiếu {float(gap):,.0f}đ/ngày. Hãy xem xét thêm các danh mục khác.'
            })
    else:
        # Nếu chưa chọn danh mục nào, phân tích tất cả danh mục
        suggestions['recommendations'].append({
            'type': 'info',
            'message': '💡 Hãy chọn các danh mục bạn muốn cắt giảm để nhận gợi ý chi tiết hơn.'
        })
        
        # Liệt kê top danh mục chi tiêu nhiều nhất
        top_categories = recent_expenses.values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:5]
        
        for cat in top_categories:
            if cat['category__name']:
                cat_total = cat['total']
                cat_daily = cat_total / 30
                suggestions['category_analysis'].append({
                    'category_name': cat['category__name'],
                    'total_30days': float(cat_total),
                    'daily_average': float(cat_daily),
                    'suggested_reduction_pct': 50,
                    'suggested_daily_reduction': float(cat_daily * Decimal('0.5')),
                    'monthly_savings': float(cat_daily * Decimal('0.5') * 30),
                })
    
    # Kế hoạch tuần/tháng
    days = goal.days_remaining
    if days > 0:
        suggestions['weekly_plan'] = {
            'amount': float(goal.daily_savings_needed * 7),
            'description': f'Tiết kiệm {float(goal.daily_savings_needed * 7):,.0f}đ mỗi tuần'
        }
        suggestions['monthly_plan'] = {
            'amount': float(goal.daily_savings_needed * 30),
            'description': f'Tiết kiệm {float(goal.daily_savings_needed * 30):,.0f}đ mỗi tháng'
        }
    
    # Thêm gợi ý chung
    if goal.daily_savings_needed > 0:
        # Gợi ý cụ thể dựa trên số tiền cần tiết kiệm
        daily_needed = float(goal.daily_savings_needed)
        
        if daily_needed < 50000:  # < 50k/ngày
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': f'💰 Mẹo: Bỏ 1 ly cafe/trà sữa mỗi ngày (40-50k) là đủ để đạt mục tiêu!'
            })
        elif daily_needed < 100000:  # < 100k/ngày
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': f'💰 Mẹo: Tự nấu ăn thay vì ăn ngoài, mang cơm trưa đi làm có thể tiết kiệm 50-100k/ngày.'
            })
        elif daily_needed < 200000:  # < 200k/ngày
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': f'💰 Mẹo: Cắt giảm shopping và giải trí không cần thiết, đi lại bằng phương tiện công cộng.'
            })
        else:  # >= 200k/ngày
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': f'💰 Số tiền cần tiết kiệm khá lớn ({daily_needed:,.0f}đ/ngày). Hãy xem xét tăng thu nhập hoặc kéo dài thời gian mục tiêu.'
            })
    
    return suggestions


# ======================== CHATBOT / VOICE ASSISTANT ========================

@login_required
def chat_assistant(request):
    """
    Trang giao diện Trợ lý ảo (Chat + Voice input)
    """
    # Lấy các category của user để hiển thị
    categories = Category.objects.filter(user=request.user)
    
    # Lấy 10 chi tiêu gần nhất để hiển thị context
    recent_expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')[:10]
    
    context = {
        'categories': categories,
        'recent_expenses': recent_expenses,
    }
    
    return render(request, 'ep1/chat_assistant.html', context)


def _recurring_chat_preview(text, structured, user, intent):
    from datetime import date
    from app_expenses.utils.nlp_parser import ExpenseNLPParser

    amount = structured.get('amount')
    if not amount:
        amount = ExpenseNLPParser()._extract_amount(text.lower())
    if not amount:
        return None

    frequency = structured.get('frequency')
    if frequency not in {'daily', 'weekly', 'monthly', 'yearly'}:
        frequency_map = {
            'ngày': 'daily', 'hàng ngày': 'daily', 'mỗi ngày': 'daily',
            'tuần': 'weekly', 'hàng tuần': 'weekly', 'mỗi tuần': 'weekly',
            'tháng': 'monthly', 'hàng tháng': 'monthly', 'mỗi tháng': 'monthly',
            'năm': 'yearly', 'hàng năm': 'yearly', 'mỗi năm': 'yearly',
        }
        frequency = next((value for key, value in frequency_map.items() if key in text.lower()), 'monthly')

    date_value = structured.get('date')
    try:
        start_date = date.fromisoformat(date_value) if date_value else timezone.now().date()
    except (TypeError, ValueError):
        start_date = timezone.now().date()

    description = structured.get('description') or text.strip()
    category_hint = structured.get('category_hint')
    category = None
    if category_hint:
        category = Category.objects.filter(user=user, name__icontains=category_hint).first()

    return {
        'amount': amount,
        'description': description,
        'name': description[:200],
        'category_id': category.id if category else None,
        'category_name': category.name if category else category_hint,
        'source_name': structured.get('source_name') or description[:100],
        'frequency': frequency,
        'start_date': start_date.isoformat(),
        'end_date': structured.get('end_date'),
        '_type': 'recurring_income' if intent == 'CREATE_RECURRING_INCOME' else 'recurring_expense',
    }


def _chat_expense_action_preview(text, user, intent):
    """Find one user-owned expense for an explicit edit/delete confirmation."""
    from app_expenses.utils.nlp_parser import ExpenseNLPParser

    expenses = Expense.objects.filter(user=user).select_related('category')
    amount = ExpenseNLPParser()._extract_amount(text.lower())
    if amount:
        expenses = expenses.filter(amount=amount)

    search_terms = re.sub(
        r'\b(sửa|sửa khoản chi|sửa chi tiêu|đổi|cập nhật|xóa|xóa khoản chi|'
        r'xóa chi tiêu|xóa giao dịch|bỏ|khoản|chi tiêu|giao dịch|giúp|tôi|cho tôi)\b',
        ' ', text.lower()
    )
    meaningful_terms = [term for term in search_terms.split() if len(term) > 2]
    if meaningful_terms:
        term_query = Q()
        for term in meaningful_terms:
            term_query |= Q(description__icontains=term) | Q(category__name__icontains=term)
        expenses = expenses.filter(term_query)

    expense = expenses.order_by('-date', '-id').first()
    if not expense:
        return None
    return {
        'expense_id': expense.id,
        'amount': float(expense.amount),
        'description': expense.description or '',
        'date': expense.date.isoformat(),
        'category_id': expense.category_id,
        'category_name': expense.category.name if expense.category else 'Khác',
        'action': 'delete' if intent == 'DELETE_EXPENSE' else 'edit',
        '_type': 'expense_action',
    }


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
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.exception('Chat processing failed: user_id=%s', request.user.id)
        return JsonResponse({
            'success': False,
            'error': f'Lỗi xử lý: {error_msg}'
        }, status=500)


@login_required
def save_income_from_chat_api(request):
    """Lưu thu nhập sau khi người dùng xác nhận preview từ chatbot."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    from datetime import datetime
    from decimal import Decimal
    from app_expenses.models import IncomeSource, Income

    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', '')))
        description = str(data.get('description', '')).strip()[:500]
        source_name = str(data.get('source_name', 'Khác')).strip()[:100] or 'Khác'
        date_str = data.get('date')
        if amount <= 0 or not date_str:
            return JsonResponse({'success': False, 'error': 'Dữ liệu thu nhập không hợp lệ'}, status=400)
        income_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (json.JSONDecodeError, TypeError, ValueError, ArithmeticError):
        return JsonResponse({'success': False, 'error': 'Dữ liệu thu nhập không hợp lệ'}, status=400)

    income_source, _ = IncomeSource.objects.get_or_create(
        user=request.user,
        name=source_name,
    )
    income = Income.objects.create(
        user=request.user,
        source=income_source,
        amount=amount,
        description=description,
        date=income_date,
    )
    return JsonResponse({'success': True, 'income_id': income.id})


@login_required
def save_recurring_from_chat_api(request):
    """Lưu mẫu chi tiêu hoặc thu nhập định kỳ sau khi người dùng xác nhận."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    from datetime import datetime, timedelta
    from decimal import Decimal
    from dateutil.relativedelta import relativedelta

    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', '')))
        name = str(data.get('name') or data.get('description') or '').strip()[:200]
        frequency = data.get('frequency')
        start_date = datetime.strptime(data.get('start_date', ''), '%Y-%m-%d').date()
        end_date_value = data.get('end_date')
        end_date = datetime.strptime(end_date_value, '%Y-%m-%d').date() if end_date_value else None
        transaction_type = data.get('transaction_type')
        if amount <= 0 or not name or frequency not in {'daily', 'weekly', 'monthly', 'yearly'}:
            raise ValueError
        if end_date and end_date <= start_date:
            raise ValueError
    except (json.JSONDecodeError, TypeError, ValueError, ArithmeticError):
        return JsonResponse({'success': False, 'error': 'Dữ liệu định kỳ không hợp lệ'}, status=400)

    next_due_date = start_date + {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': relativedelta(months=1),
        'yearly': relativedelta(years=1),
    }[frequency]

    if transaction_type == 'recurring_income':
        source_name = str(data.get('source_name') or name).strip()[:100]
        source, _ = IncomeSource.objects.get_or_create(user=request.user, name=source_name)
        recurring = RecurringIncome.objects.create(
            user=request.user,
            source=source,
            name=name,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_due_date=next_due_date,
            description=data.get('description', '')[:500],
        )
    else:
        category = None
        category_id = data.get('category_id')
        if category_id:
            category = Category.objects.filter(id=category_id, user=request.user).first()
        recurring = RecurringExpense.objects.create(
            user=request.user,
            name=name,
            amount=amount,
            category=category,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_due_date=next_due_date,
            description=data.get('description', '')[:500],
        )

    return JsonResponse({'success': True, 'recurring_id': recurring.id})


@login_required
def manage_expense_from_chat_api(request):
    """Edit or delete a user-owned expense after chatbot confirmation."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import json
    from datetime import datetime
    from decimal import Decimal

    try:
        data = json.loads(request.body)
        expense = Expense.objects.get(pk=data.get('expense_id'), user=request.user)
        action = data.get('action')
        if action not in {'edit', 'delete'}:
            raise ValueError
    except (json.JSONDecodeError, TypeError, ValueError, Expense.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Giao dịch không hợp lệ'}, status=400)

    if action == 'delete':
        expense.delete()
        logger.info('Chat expense deleted: user_id=%s expense_id=%s', request.user.id, data.get('expense_id'))
        return JsonResponse({'success': True, 'action': 'delete'})

    try:
        amount = Decimal(str(data.get('amount', expense.amount)))
        date_value = datetime.strptime(data.get('date', expense.date.isoformat()), '%Y-%m-%d').date()
        description = str(data.get('description', expense.description or '')).strip()[:500]
        if amount <= 0 or not description:
            raise ValueError
        category_id = data.get('category_id')
        category = Category.objects.filter(id=category_id, user=request.user).first() if category_id else None
        expense.amount = amount
        expense.date = date_value
        expense.description = description
        expense.category = category
        expense.save(update_fields=['amount', 'date', 'description', 'category'])
    except (TypeError, ValueError, ArithmeticError):
        return JsonResponse({'success': False, 'error': 'Dữ liệu cập nhật không hợp lệ'}, status=400)

    logger.info('Chat expense edited: user_id=%s expense_id=%s', request.user.id, expense.id)
    return JsonResponse({'success': True, 'action': 'edit', 'expense_id': expense.id})


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
    from decimal import Decimal
    from datetime import datetime
    import traceback
    
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        
        # Validate dữ liệu
        amount = data.get('amount')
        description = data.get('description', '').strip()
        category_id = data.get('category_id')
        date_str = data.get('date')
        
        if not amount:
            return JsonResponse({'success': False, 'error': 'Thiếu số tiền'}, status=400)
        
        if not date_str:
            return JsonResponse({'success': False, 'error': 'Thiếu ngày tháng'}, status=400)
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return JsonResponse({'success': False, 'error': 'Số tiền phải lớn hơn 0'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Số tiền không hợp lệ: {str(e)}'}, status=400)
        
        try:
            # Handle both ISO format and simple date format
            if 'T' in date_str:
                expense_date = datetime.fromisoformat(date_str).date()
            else:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ngày tháng không hợp lệ ({date_str}): {str(e)}'}, status=400)
        
        # Kiểm tra category
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id, user=request.user)
            except Category.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'Danh mục không tồn tại (ID: {category_id})'}, status=400)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Lỗi kiểm tra danh mục: {str(e)}'}, status=400)
        
        # Tạo expense
        expense = Expense.objects.create(
            user=request.user,
            amount=amount,
            description=description,
            category=category,
            date=expense_date
        )
        
        # Kiểm tra budget warning
        warning_message = None
        try:
            budget = Budget.objects.get(user=request.user)
            current_total = Expense.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
            
            if current_total > budget.total:
                over_amount = current_total - budget.total
                warning_message = f'⚠️ Bạn đã vượt quá ngân sách {over_amount:,.0f} ₫!'
        except Budget.DoesNotExist:
            pass
        except Exception as e:
            print(f"Lỗi kiểm tra budget: {e}")
        
        # Train model trong background
        try:
            thread = threading.Thread(target=train_model, args=(request.user,))
            thread.start()
        except Exception as e:
            print(f"Lỗi chạy background task: {e}")
        
        return JsonResponse({
            'success': True,
            'expense_id': expense.id,
            'warning': warning_message
        })
        
    except Exception as e:
        # Catch-all for unexpected errors
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Lỗi lưu chi tiêu: {str(e)}'
        }, status=500)
        budget = Budget.objects.get(user=request.user)
        current_total = Expense.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
        
        if current_total > budget.total:
            over_amount = current_total - budget.total
            warning_message = f'⚠️ Bạn đã vượt quá ngân sách {over_amount:,.0f} ₫!'
    except Budget.DoesNotExist:
        pass
    
    # Train model trong background
    try:
        thread = threading.Thread(target=train_model, args=(request.user,))
        thread.start()
    except Exception as e:
        print(f"Lỗi chạy background task: {e}")
    
    return JsonResponse({
        'success': True,
        'expense_id': expense.id,
        'warning': warning_message
    })


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
    
    expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')[:limit]
    
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
    return redirect('ep1:recurring_list')