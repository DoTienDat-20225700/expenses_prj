import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.db.models.functions import TruncDate
from django.db.models import Sum
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import *
from .form import *
from django.contrib import messages
from django.contrib.auth import get_user


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
    base_expenses = Expense.objects.filter(user=request.user)

    # Áp dụng lọc và sắp xếp
    filtered_expenses = _apply_filters(base_expenses, request.GET)
    expenses = _apply_sorting(filtered_expenses, request.GET)

# --- ĐOẠN CODE PHÂN TRANG (MỚI) ---
    # Chia danh sách thành các trang, mỗi trang 10 dòng
    paginator = Paginator(expenses, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # ----------------------------------

    # Tính toán thống kê (Vẫn dùng biến 'expenses' gốc để tính tổng toàn bộ, không chỉ trang hiện tại)
    total_spent = expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    daily_data = expenses.annotate(day=TruncDate('date')).values('day').annotate(total=Sum('amount')).order_by('day')

    # Tính toán thống kê
    total_spent = expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    daily_data = expenses.annotate(day=TruncDate('date')).values('day').annotate(total=Sum('amount')).order_by('day')

    # Dữ liệu cho biểu đồ
    chart_labels = [item['category__name'] for item in category_data]
    chart_data = [float(item['total']) for item in category_data]
    chart_labels_day = [item['day'].strftime('%d/%m/%Y') for item in daily_data]
    chart_data_day = [float(item['total']) for item in daily_data]

    top_category_item = category_data.first()
    top_category = top_category_item['category__name'] if top_category_item else '—'

    # Xử lý Budget form
    budget_obj, _ = Budget.objects.get_or_create(user=request.user)
    if request.method == 'POST' and 'budget_submit' in request.POST:
        b_form = BudgetForm(request.POST, instance=budget_obj)
        if b_form.is_valid():
            b_form.save()
            return redirect('ep1:ep1_lists')
    else:
        b_form = BudgetForm(instance=budget_obj)

    context = {
        'expenses': page_obj, # QUAN TRỌNG: Truyền page_obj vào đây để bảng chỉ hiện 10 dòng
        'page_obj': page_obj, # Truyền thêm biến này để vẽ thanh điều hướng
        'total_spent': total_spent,
        'top_category': top_category,
        'remaining': budget_obj.total - total_spent,
        'b_form': b_form,
        'budget_obj': budget_obj,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'chart_labels_day': chart_labels_day,
        'chart_data_day': chart_data_day,
        'categories': Category.objects.filter(user=request.user),
        # Giữ lại các giá trị filter/sort trên UI
        'selected_category': int(request.GET.get('category')) if request.GET.get('category') else None,
        'sort_amount': request.GET.get('sort_amount'),
        'sort_date': request.GET.get('sort_date'),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
    }
    return render(request, 'ep1/ep1_lists.html', context)

@login_required
def add_ep1(request):
    # Tạo danh mục mặc định nếu chưa có (như cũ)
    if not Category.objects.filter(user=request.user).exists():
        create_default_categories(request.user)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user 
            
            # --- BẮT ĐẦU ĐOẠN LOGIC CẢNH BÁO NGÂN SÁCH ---
            try:
                # 1. Lấy ngân sách hiện tại của user
                budget = Budget.objects.get(user=request.user)
                
                # 2. Tính tổng tiền đã chi tiêu trước đó
                # (Dùng aggregate để tính tổng cột amount trong database)
                current_total = Expense.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
                
                # 3. Dự tính tổng mới (Tổng cũ + Số tiền sắp thêm)
                new_total = current_total + expense.amount
                
                # 4. So sánh và Cảnh báo
                if new_total > budget.total:
                    # Tính số tiền bị lố
                    over_amount = new_total - budget.total
                    messages.warning(
                        request, 
                        f'⚠️ Cảnh báo: Bạn đã vượt quá ngân sách {over_amount:,.0f} ₫!'
                    )
                else:
                    # Nếu không lố thì báo thành công bình thường
                    messages.success(request, 'Thêm chi tiêu thành công!')
                    
            except Budget.DoesNotExist:
                # Nếu chưa cài ngân sách thì bỏ qua, không cảnh báo
                pass
            # --- KẾT THÚC ĐOẠN LOGIC ---

            expense.save()
            return redirect('ep1:ep1_lists')
    else:
        form = ExpenseForm(user=request.user)
        
    return render(request, 'ep1/add_ep1.html', {'form': form})

@login_required
def edit_ep1(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('ep1:ep1_lists')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    
    return render(request, 'ep1/edit_ep1.html', {'form': form})

@login_required
def delete_ep1(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        return redirect('ep1:ep1_lists')
    
    return render(request, 'ep1/delete_ep1.html', {'expense': expense})

@login_required
def export_expenses_csv(request):
    """Xuất dữ liệu chi tiêu ra file CSV (Mở được bằng Excel)"""
    
    # 1. Lấy dữ liệu giống hệt như đang hiển thị ở danh sách (có lọc/sắp xếp)
    base_expenses = Expense.objects.filter(user=request.user)
    filtered_expenses = _apply_filters(base_expenses, request.GET)
    expenses = _apply_sorting(filtered_expenses, request.GET)

    # 2. Tạo response trả về file CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bao_cao_chi_tieu.csv"'
    
    # 3. Thêm BOM (Byte Order Mark) để Excel đọc được tiếng Việt UTF-8
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response)
    
    # 4. Viết dòng tiêu đề
    writer.writerow(['Ngày', 'Danh mục', 'Số tiền (VNĐ)', 'Mô tả'])

    # 5. Viết dữ liệu
    for expense in expenses:
        writer.writerow([
            expense.date.strftime('%d/%m/%Y'),
            expense.category.name if expense.category else 'Khác',
            int(expense.amount), # Chuyển về số nguyên cho đẹp
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
    # Kiểm tra xem danh mục này đã có chi tiêu nào chưa
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
    }) # Tận dụng lại template xóa cũ