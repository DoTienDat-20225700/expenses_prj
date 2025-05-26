from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
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

from django.db.models.functions import TruncDate

@login_required
def ep1_lists(request):
    expenses = Expense.objects.filter(user=request.user)

    # Lọc theo danh mục
    category_id = request.GET.get('category')
    if category_id:
        expenses = expenses.filter(category_id=category_id)

    # Lọc theo khoảng ngày
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from and date_to:
        expenses = expenses.filter(date__range=[date_from, date_to])
    elif date_from:
        expenses = expenses.filter(date__gte=date_from)
    elif date_to:
        expenses = expenses.filter(date__lte=date_to)

    # Lấy tham số sắp xếp
    sort_amount = request.GET.get('sort_amount')
    sort_date = request.GET.get('sort_date')

    # Gom sắp xếp vào 1 list
    order_fields = []
    if sort_amount == 'asc':
        order_fields.append('amount')
    elif sort_amount == 'desc':
        order_fields.append('-amount')

    if sort_date == 'asc':
        order_fields.append('date')
    elif sort_date == 'desc':
        order_fields.append('-date')

    # Nếu có sắp xếp thì order, nếu không thì mặc định order theo ngày giảm dần
    if order_fields:
        expenses = expenses.order_by(*order_fields)
    else:
        expenses = expenses.order_by('-date')

    # Phần còn lại giữ nguyên (tính tổng, category_data...)
    total_spent = expenses.aggregate(sum=Sum('amount'))['sum'] or 0

    category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    labels = [item['category__name'] for item in category_data]
    data = [float(item['total']) for item in category_data]

    from django.db.models.functions import TruncDate
    daily_data = (
        expenses
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    labels_day = [item['day'].strftime('%d/%m/%Y') for item in daily_data]
    data_day = [float(item['total']) for item in daily_data]

    top = category_data.first()
    top_category = top['category__name'] if top else '—'

    budget_obj, _ = Budget.objects.get_or_create(user=request.user)

    if request.method == 'POST' and 'budget_submit' in request.POST:
        b_form = BudgetForm(request.POST, instance=budget_obj)
        if b_form.is_valid():
            b_form.save()
            return redirect('ep1:ep1_lists')
    else:
        b_form = BudgetForm(instance=budget_obj)

    categories = Category.objects.filter(user=request.user)

    return render(request, 'ep1/ep1_lists.html', {
        'expenses': expenses,
        'total_spent': total_spent,
        'top_category': top_category,
        'remaining': budget_obj.total - total_spent,
        'b_form': b_form,
        'budget_obj': budget_obj,
        'chart_labels': labels,
        'chart_data': data,
        'chart_labels_day': labels_day,
        'chart_data_day': data_day,
        'categories': categories,
        'selected_category': int(category_id) if category_id else None,
        'sort_amount': sort_amount,
        'sort_date': sort_date,
        'date_from': date_from,
        'date_to': date_to,
    })

@login_required
def add_ep1(request):
    if not Category.objects.filter(user=request.user).exists():
        create_default_categories(request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = get_user(request) 
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