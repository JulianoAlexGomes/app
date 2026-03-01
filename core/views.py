from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import *
from django.contrib.auth.views import LoginView, LogoutView
from .forms import (
    ClientForm, SizechartForm, SizesFormSet, colorchartForm, modelchartForm,
    ProductForm, StockEntryForm, OrderForm, OrderItemFormSet, PaymentMethodForm,
    BankAccountForm, FinancialMovementForm, FinancialParcelFormSet, ParcelPayForm,
    OrderPaymentFormSet, FiscalOperationForm, OrderPaymentParcelFormSet,
    CustomUserCreationForm, CustomUserChangeForm,
    AdminBusinessForm, AdminUserCreateForm, AdminUserChangeForm, AdminPlanForm,  # ← adicione esta linha
)
from django.shortcuts import redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from .services.order_stock import reserve_stock, release_stock, finalize_stock, create_variants
from .services.fiscal_rules import apply_fiscal_rules  # 🔥 FISCAL
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware
from datetime import datetime, date
from django.db.models import Sum, Count, Q, Prefetch
from django.db.models.functions import TruncMonth
from django.urls import reverse_lazy, reverse
from decimal import Decimal
from .models import Client, Orders, Product, FinancialMovement, FinancialMovementParcel
import calendar
from core.services.nf_generator import gerar_nota_fiscal
from core.models import Invoice, InvoiceStatus
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView  # ← TemplateView aqui
)

# Staff

from .mixins import SaasAdminMixin

# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
class SaasDashboardView(SaasAdminMixin, TemplateView):
    template_name = 'saas/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_businesses'] = Business.objects.count()
        ctx['total_users']      = User.objects.filter(is_staff=False).count()
        ctx['total_plans']      = Plan.objects.filter(active=True).count()
        ctx['recent_businesses'] = Business.objects.select_related('plan').order_by('-created_at')[:8]
        return ctx


# ══════════════════════════════════════════════
# PLANOS
# ══════════════════════════════════════════════
class SaasPlanListView(SaasAdminMixin, ListView):
    model               = Plan
    template_name       = 'saas/plan/list.html'
    context_object_name = 'plans'
    ordering            = ['price']


class SaasPlanCreateView(SaasAdminMixin, CreateView):
    model         = Plan
    form_class    = AdminPlanForm
    template_name = 'saas/plan/form.html'
    success_url   = reverse_lazy('saas_plan_list')

    def form_valid(self, form):
        messages.success(self.request, '✅ Plano criado com sucesso.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Novo Plano'
        return ctx


class SaasPlanUpdateView(SaasAdminMixin, UpdateView):
    model         = Plan
    form_class    = AdminPlanForm
    template_name = 'saas/plan/form.html'
    success_url   = reverse_lazy('saas_plan_list')

    def form_valid(self, form):
        messages.success(self.request, '✅ Plano atualizado com sucesso.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Plano'
        return ctx


class SaasPlanDeleteView(SaasAdminMixin, DeleteView):
    model         = Plan
    template_name = 'saas/plan/delete.html'
    success_url   = reverse_lazy('saas_plan_list')

    def post(self, request, *args, **kwargs):
        messages.success(request, '✅ Plano excluído.')
        return super().post(request, *args, **kwargs)


# ══════════════════════════════════════════════
# EMPRESAS
# ══════════════════════════════════════════════
class SaasBusinessListView(SaasAdminMixin, ListView):
    model               = Business
    template_name       = 'saas/business/list.html'
    context_object_name = 'businesses'
    paginate_by         = 20

    def get_queryset(self):
        qs = Business.objects.select_related('plan').order_by('-created_at')
        q  = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(document__icontains=q) |
                Q(fantasy_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('q', '')
        return ctx


class SaasBusinessCreateView(SaasAdminMixin, CreateView):
    model         = Business
    form_class    = AdminBusinessForm
    template_name = 'saas/business/form.html'
    success_url   = reverse_lazy('saas_business_list')

    def form_valid(self, form):
        messages.success(self.request, '✅ Empresa criada com sucesso.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nova Empresa'
        return ctx


class SaasBusinessUpdateView(SaasAdminMixin, UpdateView):
    model         = Business
    form_class    = AdminBusinessForm
    template_name = 'saas/business/form.html'
    success_url   = reverse_lazy('saas_business_list')

    def form_valid(self, form):
        messages.success(self.request, '✅ Empresa atualizada com sucesso.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Empresa'
        return ctx


class SaasBusinessDeleteView(SaasAdminMixin, DeleteView):
    model         = Business
    template_name = 'saas/business/delete.html'
    success_url   = reverse_lazy('saas_business_list')

    def post(self, request, *args, **kwargs):
        messages.success(request, '✅ Empresa excluída.')
        return super().post(request, *args, **kwargs)


# ══════════════════════════════════════════════
# USUÁRIOS DA EMPRESA  (visão do SaaS admin)
# ══════════════════════════════════════════════
class SaasUserListView(SaasAdminMixin, ListView):
    model               = User
    template_name       = 'saas/user/list.html'
    context_object_name = 'users'
    paginate_by         = 20

    def get_queryset(self):
        # Lista usuários de UMA empresa específica
        self.business = get_object_or_404(Business, pk=self.kwargs['business_pk'])
        return User.objects.filter(business=self.business).order_by('username')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['business'] = self.business
        plan = self.business.plan
        ctx['max_users']  = plan.max_users if plan else '—'
        ctx['total_users'] = User.objects.filter(business=self.business).count()
        return ctx


class SaasUserCreateView(SaasAdminMixin, CreateView):
    model         = User
    form_class    = AdminUserCreateForm
    template_name = 'saas/user/form.html'

    def get_success_url(self):
        return reverse_lazy('saas_user_list', kwargs={'business_pk': self.kwargs['business_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['business'] = get_object_or_404(Business, pk=self.kwargs['business_pk'])
        ctx['title']    = 'Novo Usuário'
        return ctx

    def form_valid(self, form):
        business      = get_object_or_404(Business, pk=self.kwargs['business_pk'])

        # Valida limite do plano
        plan      = business.plan
        max_users = plan.max_users if plan else 1
        total     = User.objects.filter(business=business).count()
        if total >= max_users:
            form.add_error(None, f'Limite de {max_users} usuário(s) atingido para este plano.')
            return self.form_invalid(form)

        user          = form.save(commit=False)
        user.business = business
        user.plan     = plan
        user.save()
        messages.success(self.request, f'✅ Usuário {user.username} criado com sucesso.')
        return redirect(self.get_success_url())


class SaasUserUpdateView(SaasAdminMixin, UpdateView):
    model         = User
    form_class    = AdminUserChangeForm
    template_name = 'saas/user/form.html'

    def get_queryset(self):
        self.business = get_object_or_404(Business, pk=self.kwargs['business_pk'])
        return User.objects.filter(business=self.business)

    def get_success_url(self):
        return reverse_lazy('saas_user_list', kwargs={'business_pk': self.kwargs['business_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['business'] = self.business
        ctx['title']    = 'Editar Usuário'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, '✅ Usuário atualizado.')
        return super().form_valid(form)


class SaasUserDeleteView(SaasAdminMixin, DeleteView):
    model         = User
    template_name = 'saas/user/delete.html'

    def get_queryset(self):
        self.business = get_object_or_404(Business, pk=self.kwargs['business_pk'])
        return User.objects.filter(business=self.business)

    def get_success_url(self):
        return reverse_lazy('saas_user_list', kwargs={'business_pk': self.kwargs['business_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['business'] = self.business
        return ctx

    def post(self, request, *args, **kwargs):
        messages.success(request, '✅ Usuário excluído.')
        return super().post(request, *args, **kwargs)



# ─────────────────────────────────────────────────────────────────────────────
# HOME / DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def home(request):
    today = date.today()
    business = request.user.business

    total_clients = Client.objects.filter(business=business).count()
    total_products = Product.objects.filter(business=business).count()

    products = Product.objects.filter(business=business)
    total_stock = sum(p.stock_real for p in products)

    orders = Orders.objects.filter(business=business)

    orders_month_qs = orders.filter(
        created_at__year=today.year,
        created_at__month=today.month
    )

    orders_today = orders.filter(created_at__date=today).count()
    orders_month = orders_month_qs.count()

    revenue_month = orders_month_qs.filter(
        status=Orders.STATUS_FATURADO
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    revenue_total = revenue_month

    ticket_medio = (
        revenue_month / orders_month
        if orders_month > 0 else Decimal('0.00')
    )

    parcels = FinancialMovementParcel.objects.filter(
        movement__business=business,
        deadline__year=today.year,
        deadline__month=today.month
    )

    entradas_recebidas = parcels.filter(
        movement__type='in', payed=True
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    saidas_pagas = parcels.filter(
        movement__type='out', payed=True
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    contas_receber = parcels.filter(
        movement__type='in', payed=False
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    contas_vencidas = parcels.filter(
        movement__type='in', payed=False, deadline__lt=today
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    saldo_mes = entradas_recebidas - saidas_pagas

    sales_by_month = (
        orders.filter(status=Orders.STATUS_FATURADO)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('total_amount'))
        .order_by('month')
    )

    sales_by_month_data = [
        {'month': item['month'].strftime('%Y-%m'), 'total': float(item['total'] or 0)}
        for item in sales_by_month
    ]

    orders_by_status = orders.values('status').annotate(total=Count('id'))
    orders_by_status_data = [
        {'status': item['status'], 'total': item['total']}
        for item in orders_by_status
    ]

    last_orders = orders.select_related('client').order_by('-created_at')[:8]

    context = {
        'total_clients': total_clients,
        'total_products': total_products,
        'total_stock': total_stock,
        'orders_month': orders_month,
        'orders_today': orders_today,
        'revenue_month': revenue_month,
        'revenue_total': revenue_total,
        'ticket_medio': ticket_medio,
        'sales_by_month': sales_by_month_data,
        'orders_by_status': orders_by_status_data,
        'last_orders': last_orders,
        'entradas_recebidas': entradas_recebidas,
        'saidas_pagas': saidas_pagas,
        'saldo_mes': saldo_mes,
        'contas_receber': contas_receber,
        'contas_vencidas': contas_vencidas,
    }

    return render(request, 'auth/home.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'

    def get_success_url(self):
        return reverse_lazy('home')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')


# ─────────────────────────────────────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def client_list(request):
    search = request.GET.get('q', '')

    base_qs = Client.objects.filter(business=request.user.business)

    if search:
        base_qs = base_qs.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(document__icontains=search)
        )

    base_qs = base_qs.order_by('name')

    total_clients      = base_qs.count()
    clients_with_email = base_qs.exclude(email__isnull=True).exclude(email__exact='').count()
    clients_with_phone = base_qs.exclude(phone__isnull=True).exclude(phone__exact='').count()

    paginator = Paginator(base_qs, 10)
    clients   = paginator.get_page(request.GET.get('page'))

    return render(request, 'clients/list.html', {
        'clients': clients,
        'search': search,
        'total_clients': total_clients,
        'clients_with_email': clients_with_email,
        'clients_with_phone': clients_with_phone,
    })


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        client = form.save(commit=False)
        client.business = request.user.business
        client.save()
        return redirect('client_list')

    return render(request, 'clients/form.html', {'form': form})


@login_required
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk, business=request.user.business)
    form   = ClientForm(request.POST or None, instance=client)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente alterado com sucesso!')
            return redirect(reverse('client_update', kwargs={'pk': client.pk}))
        else:
            messages.error(request, 'Erro ao salvar o cliente.')

    return render(request, 'clients/form.html', {'form': form, 'edit': True})


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk, business=request.user.business)

    if request.method == 'POST':
        client.delete()
        return redirect('client_list')

    return render(request, 'clients/delete.html', {'client': client})


# ─────────────────────────────────────────────────────────────────────────────
# TAMANHOS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def sizechart_list(request):
    search     = request.GET.get('q', '')
    sizecharts = Sizechart.objects.filter(
        business=request.user.business, name__icontains=search
    ).order_by('name')

    paginator  = Paginator(sizecharts, 10)
    sizecharts = paginator.get_page(request.GET.get('page'))

    return render(request, 'sizecharts/list.html', {'sizecharts': sizecharts, 'search': search})


@login_required
def sizechart_create(request):
    form    = SizechartForm(request.POST or None)
    formset = SizesFormSet(request.POST or None)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        sizechart          = form.save(commit=False)
        sizechart.business = request.user.business
        sizechart.save()
        formset.instance = sizechart
        formset.save()
        return redirect('sizechart_list')

    return render(request, 'sizecharts/form.html', {'form': form, 'formset': formset})


@login_required
def sizechart_update(request, pk):
    sizechart = get_object_or_404(Sizechart, pk=pk, business=request.user.business)
    form      = SizechartForm(request.POST or None, instance=sizechart)
    formset   = SizesFormSet(request.POST or None, instance=sizechart)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        return redirect('sizechart_list')

    return render(request, 'sizecharts/form.html', {'form': form, 'formset': formset, 'edit': True})


@login_required
def sizechart_delete(request, pk):
    sizechart = get_object_or_404(Sizechart, pk=pk, business=request.user.business)

    if request.method == 'POST':
        sizechart.delete()
        return redirect('sizechart_list')

    return render(request, 'sizecharts/delete.html', {'sizechart': sizechart})


# ─────────────────────────────────────────────────────────────────────────────
# CORES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def colorchart_list(request):
    search      = request.GET.get('q', '')
    colorcharts = colorchart.objects.filter(
        business=request.user.business, name__icontains=search
    ).order_by('name')

    paginator   = Paginator(colorcharts, 10)
    colorcharts = paginator.get_page(request.GET.get('page'))

    return render(request, 'colorcharts/list.html', {'colorcharts': colorcharts, 'search': search})


@login_required
def colorchart_create(request):
    form = colorchartForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        instance          = form.save(commit=False)
        instance.business = request.user.business
        instance.save()
        return redirect('colorchart_list')

    return render(request, 'colorcharts/form.html', {'form': form})


@login_required
def colorchart_update(request, pk):
    instance = get_object_or_404(colorchart, pk=pk, business=request.user.business)
    form     = colorchartForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('colorchart_list')

    return render(request, 'colorcharts/form.html', {'form': form, 'edit': True})


@login_required
def colorchart_delete(request, pk):
    instance = get_object_or_404(colorchart, pk=pk, business=request.user.business)

    if request.method == 'POST':
        instance.delete()
        return redirect('colorchart_list')

    return render(request, 'colorcharts/delete.html', {'colorchart': instance})


# ─────────────────────────────────────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def modelchart_list(request):
    search      = request.GET.get('q', '')
    modelcharts = modelchart.objects.filter(
        business=request.user.business, name__icontains=search
    ).order_by('name')

    paginator   = Paginator(modelcharts, 10)
    modelcharts = paginator.get_page(request.GET.get('page'))

    return render(request, 'modelcharts/list.html', {'modelcharts': modelcharts, 'search': search})


@login_required
def modelchart_create(request):
    form = modelchartForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        instance          = form.save(commit=False)
        instance.business = request.user.business
        instance.save()
        return redirect('modelchart_list')

    return render(request, 'modelcharts/form.html', {'form': form})


@login_required
def modelchart_update(request, pk):
    instance = get_object_or_404(modelchart, pk=pk, business=request.user.business)
    form     = modelchartForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('modelchart_list')

    return render(request, 'modelcharts/form.html', {'form': form, 'edit': True})


@login_required
def modelchart_delete(request, pk):
    instance = get_object_or_404(modelchart, pk=pk, business=request.user.business)

    if request.method == 'POST':
        instance.delete()
        return redirect('modelchart_list')

    return render(request, 'modelcharts/delete.html', {'modelchart': instance})


# ─────────────────────────────────────────────────────────────────────────────
# PRODUTOS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def product_list(request):
    search = request.GET.get('q', '')

    base_qs = (
        Product.objects
        .filter(business=request.user.business)
        .prefetch_related(
            'variants__stock_entries',
            Prefetch('images', queryset=ProductImage.objects.filter(order=0), to_attr='cover_image')
        )
    )

    if search:
        base_qs = base_qs.filter(
            Q(name__icontains=search) |
            Q(model__name__icontains=search) |
            Q(color__name__icontains=search) |
            Q(variants__sku__icontains=search) |
            Q(variants__ean13__icontains=search)
        ).distinct()

    base_qs = base_qs.order_by('name')

    total_products    = base_qs.count()
    total_stock       = 0
    low_stock_count   = 0
    total_stock_value = 0

    for product in base_qs:
        for variant in product.variants.all():
            available          = variant.stock_available
            total_stock       += available
            total_stock_value += available * product.cost
            if available < 5:
                low_stock_count += 1

    paginator = Paginator(base_qs, 10)
    products  = paginator.get_page(request.GET.get('page'))

    return render(request, 'products/list.html', {
        'products': products,
        'search': search,
        'total_products': total_products,
        'total_stock': total_stock,
        'low_stock_count': low_stock_count,
        'total_stock_value': total_stock_value,
    })


@login_required
@transaction.atomic
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, business=request.user.business)

        if form.is_valid():
            product          = form.save(commit=False)
            product.business = request.user.business
            product.save()
            create_variants(product)
            return redirect('product_update', product.id)
        else:
            print(form.errors)
    else:
        form = ProductForm(business=request.user.business)

    return render(request, 'products/form.html', {'form': form})


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk, business=request.user.business)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            form.save()
            create_variants(product)
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/form.html', {'form': form, 'product': product, 'edit': True})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, business=request.user.business)

    if request.method == 'POST':
        product.delete()
        return redirect('product_list')

    return render(request, 'products/delete.html', {'product': product})


# ─────────────────────────────────────────────────────────────────────────────
# ESTOQUE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def stock_movement(request, variant_id):
    variant   = get_object_or_404(ProductVariant, id=variant_id, product__business=request.user.business)
    movements = variant.stock_entries.order_by('-timestamp')
    form      = StockEntryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        entry         = form.save(commit=False)
        entry.variant = variant
        entry.movement_type = (
            StockEntry.MovementType.INITIAL
            if not variant.stock_entries.exists()
            else StockEntry.MovementType.ADJUST
        )
        entry.save()
        return redirect('stock_movement', variant_id=variant.id)

    return render(request, 'stock/movement.html', {
        'variant': variant,
        'movements': movements,
        'form': form,
    })


@login_required
def stock_entry_delete(request, pk):
    entry   = get_object_or_404(StockEntry, pk=pk, variant__product__business=request.user.business)
    variant = entry.variant

    if request.method == 'POST':
        entry.delete()
        return redirect('stock_movement', variant_id=variant.id)

    return render(request, 'stock/delete.html', {'entry': entry})


# ─────────────────────────────────────────────────────────────────────────────
# PEDIDOS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@transaction.atomic
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)

        if form.is_valid():
            order              = form.save(commit=False)
            order.business     = request.user.business
            order.total_amount = 0
            order.save()
            messages.success(request, 'Pedido criado. Agora inclua os itens.')
            return redirect('order_update', order.id)
    else:
        form = OrderForm(user=request.user)

    return render(request, 'orders/form_create.html', {'form': form, 'title': 'Novo Pedido'})


@login_required
def order_list(request):
    base_qs = Orders.objects.filter(business=request.user.business).select_related('client')
    orders  = base_qs.order_by('-created_at')

    client_id  = request.GET.get('client')
    status     = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date   = request.GET.get('end_date')

    if client_id:
        orders = orders.filter(client_id=client_id)
    if status:
        orders = orders.filter(status=status)
    if start_date:
        orders = orders.filter(created_at__gte=make_aware(datetime.strptime(start_date, '%Y-%m-%d')))
    if end_date:
        orders = orders.filter(created_at__lte=make_aware(datetime.strptime(end_date, '%Y-%m-%d')))

    summary = base_qs.aggregate(
        total_orders=Count('id'),
        total_value=Sum('total_amount'),
        orcamento_value=Sum('total_amount', filter=models.Q(status=Orders.STATUS_ORCAMENTO)),
        em_separacao_value=Sum('total_amount', filter=models.Q(status=Orders.STATUS_EM_SEPARACAO)),
        separado_value=Sum('total_amount', filter=models.Q(status=Orders.STATUS_SEPARADO)),
        faturado_value=Sum('total_amount', filter=models.Q(status=Orders.STATUS_FATURADO)),
    )

    paginator = Paginator(orders, 15)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'orders/list.html', {
        'orders': page_obj,
        'page_obj': page_obj,
        'clients': Client.objects.filter(business=request.user.business),
        'status_choices': Orders.STATUS_CHOICES,
        'summary': summary,
        'current_status': status,
    })

@login_required
@transaction.atomic
def order_update(request, pk):
    order    = get_object_or_404(Orders, pk=pk, business=request.user.business)
    business = request.user.business

    if request.method == 'POST' and not order.can_edit():
        messages.error(request, 'Este pedido não pode mais ser alterado.')
        return redirect('order_list')

    if request.method == 'POST':
        form            = OrderForm(request.POST, instance=order, user=request.user)
        formset         = OrderItemFormSet(request.POST, instance=order, prefix='items')
        payment_formset = OrderPaymentFormSet(request.POST, instance=order, prefix='payments')

        # Coleta formsets de parcelas para cada payment (pelo índice do form)
        parcel_formsets = {}
        for i, pf in enumerate(payment_formset.forms):
            prefix = f'parcels-{i}'
            parcel_formsets[i] = OrderPaymentParcelFormSet(
                request.POST,
                instance=pf.instance if pf.instance.pk else None,
                prefix=prefix,
            )

        payments_valid = payment_formset.is_valid()
        parcels_valid  = all(pfs.is_valid() for pfs in parcel_formsets.values())

        if form.is_valid() and formset.is_valid() and payments_valid and parcels_valid:

            form.save()
            total = Decimal('0.00')

            # ── ITENS ──────────────────────────────────────────────────
            for form_item in formset:
                if form_item.cleaned_data.get('DELETE'):
                    if form_item.instance.pk:
                        form_item.instance.delete()
                    continue

                item       = form_item.save(commit=False)
                item.order = order

                try:
                    found = apply_fiscal_rules(item, raise_on_missing=False)
                    if not found:
                        messages.warning(
                            request,
                            f'Item "{item.variant.product.name}": nenhuma operação fiscal encontrada.'
                        )
                except Exception as e:
                    messages.error(request, f'Erro ao aplicar regra fiscal: {e}')

                item.save()
                total += item.subtotal

            order.total_amount = total
            order.save(update_fields=['total_amount'])

            # ── VALIDAÇÃO: soma pagamentos == total ────────────────────
            # ── PAGAMENTOS + PARCELAS ──────────────────────────────

            # 1) Salva o formset para popular deleted_objects
            payment_formset.save(commit=False)  # popula .deleted_objects sem salvar no DB

            # 2) Deleta payments marcados para exclusão
            for obj in payment_formset.deleted_objects:
                obj.delete()

            # 3) Salva / atualiza cada payment e suas parcelas
            for form_idx, pf in enumerate(payment_formset.forms):
                if not pf.cleaned_data:
                    continue

                if pf.cleaned_data.get('DELETE'):
                    if pf.instance.pk:
                        pf.instance.delete()
                    continue

                payment       = pf.save(commit=False)
                payment.order = order
                payment.save()

                # Parcelas deste payment
                pf_set          = parcel_formsets[form_idx]
                pf_set.instance = payment

                # Popula deleted_objects das parcelas
                pf_set.save(commit=False)

                # Deleta parcelas marcadas para exclusão
                for obj in pf_set.deleted_objects:
                    obj.delete()

                # Salva parcelas novas/alteradas
                parcels = pf_set.save(commit=False)
                for parcel in parcels:
                    parcel.payment = payment
                    parcel.save()

                # Só gera automaticamente se não há nenhuma parcela ativa enviada
                active_parcel_rows = [
                    f for f in pf_set.forms
                    if f.cleaned_data and not f.cleaned_data.get('DELETE')
                ]
                if not active_parcel_rows:
                    payment.generate_parcels()

    else:
        form            = OrderForm(instance=order, user=request.user)
        formset         = OrderItemFormSet(instance=order, prefix='items')
        payment_formset = OrderPaymentFormSet(instance=order, prefix='payments')

    # Monta parcelas por pagamento para o template
    payments_with_parcel_forms = []
    for i, pf in enumerate(payment_formset.forms):
        prefix = f'parcels-{i}'
        if pf.instance.pk:
            pf_set = OrderPaymentParcelFormSet(instance=pf.instance, prefix=prefix)
        else:
            pf_set = OrderPaymentParcelFormSet(prefix=prefix)
        payments_with_parcel_forms.append((pf, pf_set))

    total_order    = order.total_amount or Decimal('0.00')
    total_payments = order.payments.aggregate(total=Sum('total_value'))['total'] or Decimal('0.00')
    saldo          = total_order - total_payments

    invoice_ativa = Invoice.objects.filter(
        order=order,
        status__in=[InvoiceStatus.RASCUNHO, InvoiceStatus.PENDENTE, InvoiceStatus.AUTORIZADA],
    ).first()

    # Config de formas de pagamento para o JS
    import json
    payment_methods_json = json.dumps([
        {
            'id':              pm.pk,
            'default_parcels': pm.default_parcels,
            'interval_days':   pm.interval_days,
            'default_bank':    pm.default_bank_id or '',
        }
        for pm in PaymentMethod.objects.filter(business=business, active=True)
    ])

    return render(request, 'orders/form_update.html', {
        'form':                       form,
        'formset':                    formset,
        'payment_formset':            payment_formset,
        'payments_with_parcel_forms': payments_with_parcel_forms,
        'order':                      order,
        'total_order':                total_order,
        'total_payments':             total_payments,
        'saldo':                      saldo,
        'invoice_ativa':              invoice_ativa,
        'payment_methods_json':       payment_methods_json,
    })

@login_required
def order_delete(request, pk):
    order = get_object_or_404(Orders, pk=pk, business=request.user.business)

    if request.method == 'POST':
        order.delete()
        return redirect('order_list')

    return render(request, 'orders/delete.html', {'order': order})


@login_required
@transaction.atomic
def order_change_status(request, order_id):
    order      = get_object_or_404(Orders, id=order_id, business=request.user.business)
    new_status = request.POST.get('status')

    if not order.can_change_status_to(new_status):
        messages.error(
            request,
            f'Não é permitido mudar de {order.get_status_display()} '
            f'para {dict(Orders.STATUS_CHOICES).get(new_status)}'
        )
        return redirect('order_update', order.id)

    try:
        if new_status == Orders.STATUS_EM_SEPARACAO:
            reserve_stock(order)
        elif new_status == Orders.STATUS_CANCELADO:
            release_stock(order)
        elif new_status == Orders.STATUS_FATURADO:
            finalize_stock(order)
            order.generate_financial()

        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(request, f'Status alterado para {order.get_status_display()}')

    except ValidationError as e:
        messages.error(request, e.message)

    return redirect('order_update', order.id)


@login_required
@transaction.atomic
def order_advance_status(request, order_id):
    order       = get_object_or_404(Orders, id=order_id, business=request.user.business)
    next_status = order.next_status()

    if not next_status:
        messages.error(request, 'Pedido já está no status final.')
        return redirect('order_update', order.id)

    try:
        if next_status == Orders.STATUS_EM_SEPARACAO:
            reserve_stock(order)
        elif next_status == Orders.STATUS_FATURADO:
            finalize_stock(order)
            order.generate_financial()

        order.status = next_status
        order.save(update_fields=['status'])
        messages.success(request, f'Status alterado para {order.get_status_display()}')

    except ValidationError as e:
        messages.error(request, e.message)

    return redirect('order_update', order.id)


@login_required
@transaction.atomic
def order_cancel(request, order_id):
    order = get_object_or_404(Orders, id=order_id, business=request.user.business)

    if order.status == Orders.STATUS_FATURADO:
        for item in order.items.select_related('variant'):
            StockEntry.objects.create(
                variant=item.variant,
                order_item=item,
                entry_type='in',
                movement_type=StockEntry.MovementType.ADJUST,
                quantity=item.quantity
            )

    if order.financial_movements.exists():
        order.financial_movements.all().delete()

    release_stock(order)

    order.status = Orders.STATUS_CANCELADO
    order.save(update_fields=['status'])

    messages.success(request, 'Pedido cancelado com sucesso.')
    return redirect('order_update', order.id)

@login_required
@transaction.atomic
def gerar_nfe(request, order_id):
    order = get_object_or_404(Orders, pk=order_id, business=request.user.business)

    if request.method != 'POST':
        return redirect('order_update', pk=order_id)

    try:
        invoice = gerar_nota_fiscal(order=order, usuario=request.user)
        messages.success(
            request,
            f'✅ {invoice.get_model_display()} {invoice.serie}/{invoice.number} gerada com sucesso!'
        )
        return redirect('invoice_detail', pk=invoice.pk)

    except ValueError as e:
        messages.error(request, str(e))

    except Exception as e:
        messages.error(request, f'Erro ao gerar NF: {str(e)}')

    return redirect('order_update', pk=order_id)

# ─────────────────────────────────────────────────────────────────────────────
# AJAX — VARIANTES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def ajax_variants(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return JsonResponse({'results': []})

    variants = ProductVariant.objects.filter(
        product__business=request.user.business
    ).filter(
        Q(product__name__icontains=query) |
        Q(sku__icontains=query) |
        Q(ean13__iexact=query)
    ).select_related('product', 'size', 'color')[:30]

    results = []
    for v in variants:
        size_text = f' - {v.size.name}' if v.size else ''
        results.append({
            'id':     v.id,
            'text': (
                f'{v.product.name}{size_text} '
                f'{v.color.name if v.color else ""} '
                f'| SKU: {v.sku or "-"} '
                f'| EAN: {v.ean13 or "-"} '
                f'| Estoque: {v.stock_available}'
            ),
            'price':  str(v.product.price or 0),
            'price1': str(v.product.price1 or 0),
            'stock':  v.stock_available,
        })

    return JsonResponse({'results': results})


# ─────────────────────────────────────────────────────────────────────────────
# AJAX — DADOS FISCAIS DO ITEM (preview ao selecionar variante)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def ajax_fiscal_item(request):
    """
    GET params: variant_id, order_id, quantity, price, discount, addition
    Retorna os campos fiscais calculados sem gravar no banco.
    Útil para exibir preview dos tributos ao digitar o item.
    """

    variant_id = request.GET.get('variant_id')
    order_id   = request.GET.get('order_id')
    quantity   = request.GET.get('quantity', 1)
    price      = request.GET.get('price', 0)
    discount   = request.GET.get('discount', 0)
    addition   = request.GET.get('addition', 0)

    if not variant_id or not order_id:
        return JsonResponse({'error': 'variant_id e order_id são obrigatórios'}, status=400)

    try:
        variant = ProductVariant.objects.select_related(
            'product', 'product__ncm'
        ).get(id=variant_id, product__business=request.user.business)

        order = Orders.objects.get(id=order_id, business=request.user.business)

    except (ProductVariant.DoesNotExist, Orders.DoesNotExist):
        return JsonResponse({'error': 'Variante ou pedido não encontrado'}, status=404)

    # Instância temporária — não salva no banco
    item = OrderItem(
        order=order,
        variant=variant,
        quantity=int(float(quantity)),
        price=Decimal(str(price)),
        discount=Decimal(str(discount)),
        addition=Decimal(str(addition)),
    )

    found = apply_fiscal_rules(item, raise_on_missing=False)

    if not found:
        return JsonResponse({
            'found':   False,
            'warning': 'Nenhuma operação fiscal encontrada para este produto.',
        })

    return JsonResponse({
        'found':        True,
        'cfop':         item.cfop,
        'ncm':          item.ncm,
        'icms_cst':     item.icms_cst,
        'icms_csosn':   item.icms_csosn,
        'icms_rate':    str(item.icms_rate),
        'icms_base':    str(item.icms_base),
        'icms_value':   str(item.icms_value),
        'pis_cst':      item.pis_cst,
        'pis_rate':     str(item.pis_rate),
        'pis_value':    str(item.pis_value),
        'cofins_cst':   item.cofins_cst,
        'cofins_rate':  str(item.cofins_rate),
        'cofins_value': str(item.cofins_value),
    })


# ─────────────────────────────────────────────────────────────────────────────
# IMAGENS DE PRODUTO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def product_image_upload(request, pk):
    product = get_object_or_404(Product, pk=pk, business=request.user.business)
    image   = request.FILES.get('image')

    if image:
        img = ProductImage.objects.create(
            product=product,
            image=image,
            description=request.POST.get('description', ''),
            order=request.POST.get('order', 0)
        )
        return JsonResponse({'id': img.id, 'url': img.image.url, 'description': img.description, 'order': img.order})

    return JsonResponse({'error': 'Sem imagem'}, status=400)


@login_required
@require_POST
def product_image_delete(request, pk):
    image = get_object_or_404(ProductImage, pk=pk, product__business=request.user.business)
    image.delete()
    return JsonResponse({'success': True})


@login_required
def product_images_json(request, pk):
    product = get_object_or_404(Product, pk=pk, business=request.user.business)
    data    = [
        {'id': img.id, 'url': img.image.url, 'description': img.description, 'order': img.order}
        for img in product.images.all()
    ]
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────────────────────
# FINANCEIRO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def financial_list(request):
    business = request.user.business
    today    = date.today()

    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str   = request.GET.get('end_date', '').strip()
    status         = request.GET.get('status', '')
    client_id      = request.GET.get('client', '')

    # Padrão: mês atual — só aplica se NENHUMA data foi enviada
    if not start_date_str and not end_date_str:
        start_date = today.replace(day=1)
        end_date   = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        except ValueError:
            start_date = None
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            end_date = None

    parcels = FinancialMovementParcel.objects.filter(
        movement__business=business
    ).select_related('movement', 'movement__client').order_by('deadline')

    if start_date:
        parcels = parcels.filter(deadline__gte=start_date)
    if end_date:
        parcels = parcels.filter(deadline__lte=end_date)
    if status == 'paid':
        parcels = parcels.filter(payed=True)
    elif status == 'open':
        parcels = parcels.filter(payed=False)
    if client_id:
        parcels = parcels.filter(movement__client_id=client_id)

    entradas = parcels.filter(movement__type='in')
    saidas   = parcels.filter(movement__type='out')

    total_entradas = entradas.filter(payed=True).aggregate(total=Sum('value'))['total'] or 0
    total_saidas   = saidas.filter(payed=True).aggregate(total=Sum('value'))['total'] or 0
    saldo          = total_entradas - total_saidas

    clients = Client.objects.filter(business=business).order_by('name')

    return render(request, 'financial/list.html', {
        'entradas':       entradas,
        'saidas':         saidas,
        'total_entradas': total_entradas,
        'total_saidas':   total_saidas,
        'saldo':          saldo,
        'clients':        clients,
        'client_id':      client_id,
        'start_date':     start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date':       end_date.strftime('%Y-%m-%d')   if end_date   else '',
        'status':         status,
        'banks':          BankAccount.objects.filter(business=business),  # ← adicione esta linha
        'payment_methods': PaymentMethod.objects.filter(business=business),
        'today':          today,  # necessário para row-overdue no template
    })

@login_required
def parcel_unpay(request, pk):
    from django.http import JsonResponse

    parcel = get_object_or_404(
        FinancialMovementParcel, pk=pk,
        movement__business=request.user.business
    )

    if not parcel.payed:
        return JsonResponse({'ok': False, 'error': 'Parcela não está paga.'})

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método não permitido.'})

    parcel.payed   = False
    parcel.paydate = None
    parcel.save(update_fields=['payed', 'paydate'])

    return JsonResponse({'ok': True})

@login_required
def financial_create(request):
    business = request.user.business

    if request.method == 'POST':
        form    = FinancialMovementForm(request.POST)
        formset = FinancialParcelFormSet(request.POST, prefix='parcels')

        form.fields['client'].queryset         = Client.objects.filter(business=business)
        form.fields['payment_method'].queryset = PaymentMethod.objects.filter(business=business)
        form.fields['bank'].queryset           = BankAccount.objects.filter(business=business)

        if form.is_valid() and formset.is_valid():
            # ── Valida soma das parcelas == total_value ───────────────────
            total_value  = form.cleaned_data['total_value']
            total_parcel = sum(
                f.cleaned_data.get('value') or 0
                for f in formset
                if f.cleaned_data and not f.cleaned_data.get('DELETE')
            )
            if total_parcel != total_value:
                form.add_error(
                    'total_value',
                    f'A soma das parcelas (R$ {total_parcel:.2f}) deve ser igual ao valor total (R$ {total_value:.2f}).'
                )
            else:
                movement          = form.save(commit=False)
                movement.business = business
                movement.save()
                formset.instance = movement
                formset.save()
                messages.success(request, '✅ Lançamento criado com sucesso.')
                return redirect('financial_list')
    else:
        form    = FinancialMovementForm()
        formset = FinancialParcelFormSet(prefix='parcels')
        form.fields['client'].queryset         = Client.objects.filter(business=business)
        form.fields['payment_method'].queryset = PaymentMethod.objects.filter(business=business)
        form.fields['bank'].queryset           = BankAccount.objects.filter(business=business)

    # Serializa formas de pagamento para o JS auto-preencher parcelas
    import json
    payment_methods_json = json.dumps([
        {
            'id':             pm.pk,
            'default_parcels': pm.default_parcels,
            'interval_days':  pm.interval_days,
            'default_bank':   pm.default_bank_id or '',
        }
        for pm in PaymentMethod.objects.filter(business=business)
    ])

    return render(request, 'financial/form.html', {
        'form':                 form,
        'formset':              formset,
        'title':                'Novo Lançamento',
        'payment_methods_json': payment_methods_json,
    })


@login_required
@transaction.atomic
def financial_update(request, pk):
    business = request.user.business
    movement = get_object_or_404(FinancialMovement, pk=pk, business=business)

    if movement.order is not None:
        messages.error(request, 'Este lançamento foi gerado por um pedido e não pode ser editado.')
        return redirect('financial_list')

    if request.method == 'POST':
        form    = FinancialMovementForm(request.POST, instance=movement)
        formset = FinancialParcelFormSet(request.POST, instance=movement, prefix='parcels')

        form.fields['client'].queryset         = Client.objects.filter(business=business)
        form.fields['payment_method'].queryset = PaymentMethod.objects.filter(business=business)
        form.fields['bank'].queryset           = BankAccount.objects.filter(business=business)

        if form.is_valid() and formset.is_valid():
            total_value  = form.cleaned_data['total_value']
            total_parcel = sum(
                f.cleaned_data.get('value') or 0
                for f in formset
                if f.cleaned_data and not f.cleaned_data.get('DELETE')
            )
            if total_parcel != total_value:
                form.add_error(
                    'total_value',
                    f'A soma das parcelas (R$ {total_parcel:.2f}) deve ser igual ao valor total (R$ {total_value:.2f}).'
                )
            else:
                form.save()
                formset.save()
                messages.success(request, '✅ Lançamento atualizado com sucesso.')
                return redirect('financial_list')
    else:
        form    = FinancialMovementForm(instance=movement)
        formset = FinancialParcelFormSet(instance=movement, prefix='parcels')
        form.fields['client'].queryset         = Client.objects.filter(business=business)
        form.fields['payment_method'].queryset = PaymentMethod.objects.filter(business=business)
        form.fields['bank'].queryset           = BankAccount.objects.filter(business=business)

    import json
    payment_methods_json = json.dumps([
        {
            'id':              pm.pk,
            'default_parcels': pm.default_parcels,
            'interval_days':   pm.interval_days,
            'default_bank':    pm.default_bank_id or '',
        }
        for pm in PaymentMethod.objects.filter(business=business)
    ])

    return render(request, 'financial/form.html', {
        'form':                 form,
        'formset':              formset,
        'movement':             movement,
        'title':                'Editar Lançamento',
        'payment_methods_json': payment_methods_json,
    })


@login_required
def financial_delete(request, pk):
    business = request.user.business
    movement = get_object_or_404(FinancialMovement, pk=pk, business=business)

    if movement.order is not None:
        messages.error(request, 'Este lançamento foi gerado por um pedido e não pode ser excluído.')
        return redirect('financial_list')

    if request.method == 'POST':
        movement.delete()
        messages.success(request, '✅ Lançamento excluído com sucesso.')
        return redirect('financial_list')

    return render(request, 'financial/delete.html', {'movement': movement})


# ─── AJAX — retorna config da forma de pagamento ─────────────────────────────
@login_required
def ajax_payment_method_config(request):
    from django.http import JsonResponse
    pk = request.GET.get('pk')
    try:
        pm = PaymentMethod.objects.get(pk=pk, business=request.user.business)
        return JsonResponse({
            'default_parcels': pm.default_parcels,
            'interval_days':   pm.interval_days,
            'default_bank':    pm.default_bank_id or '',
        })
    except PaymentMethod.DoesNotExist:
        return JsonResponse({}, status=404)

@login_required
def parcel_pay(request, pk):
    from django.http import JsonResponse

    parcel = get_object_or_404(
        FinancialMovementParcel, pk=pk,
        movement__business=request.user.business
    )

    if parcel.payed:
        return JsonResponse({'ok': False, 'error': 'Parcela já registrada como paga.'})

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método não permitido.'})

    form = ParcelPayForm(request.POST, instance=parcel)
    form.fields['bank'].queryset = BankAccount.objects.filter(
        business=request.user.business
    )
    form.fields['payment_method'].queryset = PaymentMethod.objects.filter(
        business=request.user.business
    )

    if form.is_valid():
        form.save()
        return JsonResponse({'ok': True})

    return JsonResponse({'ok': False, 'error': str(form.errors)})

@login_required
def financial_history(request):
    business = request.user.business

    parcels = (
        FinancialMovementParcel.objects
        .filter(movement__business=business, payed=True)
        .select_related('movement', 'movement__bank', 'movement__payment_method')
        .order_by('-paydate', '-id')
    )

    balance = 0
    history = []

    for parcel in reversed(list(parcels)):
        value = parcel.subtotal
        if parcel.movement.type == 'in':
            balance += value
        else:
            balance -= value
        history.append({'parcel': parcel, 'balance': balance})

    history.reverse()

    return render(request, 'financial/history.html', {'history': history})

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction

@login_required
@transaction.atomic
def financial_replicate(request, pk):
    business = request.user.business
    movement = get_object_or_404(FinancialMovement, pk=pk, business=business)

    # Só permite replicar se for Saída e Fixa
    if movement.type != 'out' or movement.expense_type != 2:
        messages.error(request, 'Somente despesas fixas podem ser replicadas.')
        return redirect('financial_list')

    if request.method == 'POST':
        months = int(request.POST.get('months', 1))

        for i in range(1, months + 1):
            # Clona movimento
            new_movement = FinancialMovement.objects.create(
                business=movement.business,
                client=movement.client,
                order=None,
                bank=movement.bank,
                payment_method=movement.payment_method,
                type=movement.type,
                expense_type=movement.expense_type,
                total_value=movement.total_value,
                description=movement.description,
                # ❌ Removido: parent_movement=movement,
                # ❌ Removido: is_replicated=True,
            )

            # Clona parcelas
            for parcel in movement.parcels.all():
                new_deadline = parcel.deadline + relativedelta(months=i)

                parcel.pk = None  # ⚠️ força criação de novo registro
                parcel.movement = new_movement
                parcel.deadline = new_deadline
                parcel.payed = False
                parcel.save()

        messages.success(request, f'{months} lançamentos replicados com sucesso.')
        return redirect('financial_list')

    return render(request, 'financial/replicate.html', {
        'movement': movement
    })

# ─────────────────────────────────────────────────────────────────────────────
# FORMAS DE PAGAMENTO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def paymentmethod_list(request):
    methods = PaymentMethod.objects.filter(business=request.user.business).order_by('name')
    return render(request, 'financial/paymentmethod_list.html', {'methods': methods})


@login_required
def paymentmethod_create(request):
    form = PaymentMethodForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        method          = form.save(commit=False)
        method.business = request.user.business
        method.save()
        messages.success(request, 'Forma de pagamento criada com sucesso.')
        return redirect('paymentmethod_list')

    return render(request, 'financial/paymentmethod_form.html', {'form': form, 'title': 'Nova Forma de Pagamento'})


@login_required
def paymentmethod_update(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk, business=request.user.business)
    form   = PaymentMethodForm(request.POST or None, instance=method)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Forma de pagamento atualizada.')
        return redirect('paymentmethod_list')

    return render(request, 'financial/paymentmethod_form.html', {'form': form, 'title': 'Editar Forma de Pagamento'})


@login_required
def paymentmethod_delete(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk, business=request.user.business)

    if request.method == 'POST':
        method.delete()
        messages.success(request, 'Forma de pagamento excluída.')
        return redirect('paymentmethod_list')

    return render(request, 'financial/paymentmethod_delete.html', {'method': method})


# ─────────────────────────────────────────────────────────────────────────────
# CONTAS BANCÁRIAS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def bank_list(request):
    banks = BankAccount.objects.filter(business=request.user.business).order_by('name')
    return render(request, 'financial/bank_list.html', {'banks': banks})


@login_required
def bank_create(request):
    form = BankAccountForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        bank          = form.save(commit=False)
        bank.business = request.user.business
        bank.save()
        messages.success(request, 'Conta bancária criada com sucesso.')
        return redirect('bank_list')

    return render(request, 'financial/bank_form.html', {'form': form, 'title': 'Nova Conta Bancária'})


@login_required
def bank_update(request, pk):
    bank = get_object_or_404(BankAccount, pk=pk, business=request.user.business)
    form = BankAccountForm(request.POST or None, instance=bank)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Conta bancária atualizada.')
        return redirect('bank_list')

    return render(request, 'financial/bank_form.html', {'form': form, 'title': 'Editar Conta Bancária'})


@login_required
def bank_delete(request, pk):
    bank = get_object_or_404(BankAccount, pk=pk, business=request.user.business)

    if request.method == 'POST':
        bank.delete()
        messages.success(request, 'Conta bancária excluída.')
        return redirect('bank_list')

    return render(request, 'financial/bank_delete.html', {'bank': bank})


# ─────────────────────────────────────────────────────────────────────────────
# EMPRESA
# ─────────────────────────────────────────────────────────────────────────────

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Business
from .forms import BusinessForm

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models import Business
from core.forms import BusinessForm
from core.services.fiscal.certificate_utils import encrypt_password, is_password_encrypted


class BusinessListView(LoginRequiredMixin, ListView):
    model               = Business
    template_name       = 'business/list.html'
    context_object_name = 'businesses'


class BusinessCreateView(LoginRequiredMixin, CreateView):
    model         = Business
    form_class    = BusinessForm
    template_name = 'business/form.html'
    success_url   = reverse_lazy('business_list')

    def form_valid(self, form):
        business = form.save(commit=False)

        # Criptografa a senha do certificado se foi informada
        senha = form.cleaned_data.get('certificate_password', '')
        if senha:
            business.certificate_password = encrypt_password(senha)
        else:
            business.certificate_password = ''

        business.save()
        messages.success(self.request, 'Empresa criada com sucesso!')
        return super(CreateView, self).form_valid(form)  # pula o save() duplo


class BusinessUpdateView(LoginRequiredMixin, UpdateView):
    model         = Business
    form_class    = BusinessForm
    template_name = 'business/form.html'

    def form_valid(self, form):
        business = form.save(commit=False)

        senha_digitada = form.cleaned_data.get('certificate_password', '')

        if senha_digitada:
            # Usuário digitou uma nova senha → criptografa e salva
            if not is_password_encrypted(senha_digitada):
                business.certificate_password = encrypt_password(senha_digitada)
            else:
                # Já veio criptografada (improvável, mas protege)
                business.certificate_password = senha_digitada
        else:
            # Campo em branco → mantém a senha que já está no banco
            business.certificate_password = Business.objects.get(pk=business.pk).certificate_password

        business.save()
        messages.success(self.request, 'Empresa alterada com sucesso!')
        return super(UpdateView, self).form_valid(form)  # pula o save() duplo

    def get_success_url(self):
        return reverse('business_update', kwargs={'pk': self.object.pk})


class BusinessDeleteView(LoginRequiredMixin, DeleteView):
    model         = Business
    template_name = 'business/confirm_delete.html'
    success_url   = reverse_lazy('business_list')
# ─────────────────────────────────────────────────────────────────────────────
# USUÁRIOS
# ─────────────────────────────────────────────────────────────────────────────

class UserListView(LoginRequiredMixin, ListView):
    model               = User
    template_name       = 'users/list.html'
    context_object_name = 'users'

    def get_queryset(self):
        qs = User.objects.filter(business=self.request.user.business)
        q  = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                models.Q(username__icontains=q) |
                models.Q(first_name__icontains=q) |
                models.Q(last_name__icontains=q) |
                models.Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx      = super().get_context_data(**kwargs)
        business = self.request.user.business
        plan     = business.plan

        total        = User.objects.filter(business=business).count()
        max_users    = plan.max_users if plan else 1

        ctx['total_users']      = total
        ctx['max_users']        = max_users
        ctx['slots_used']       = total
        ctx['can_add']          = total < max_users
        ctx['users_with_email'] = User.objects.filter(business=business).exclude(email='').exclude(email=None).count()
        ctx['search']           = self.request.GET.get('q', '')
        return ctx


class UserCreateView(LoginRequiredMixin, CreateView):
    model         = User
    form_class    = CustomUserCreationForm
    template_name = 'users/form.html'
    success_url   = reverse_lazy('user_list')

    def dispatch(self, request, *args, **kwargs):
        business  = request.user.business
        plan      = business.plan
        max_users = plan.max_users if plan else 1
        total     = User.objects.filter(business=business).count()

        if total >= max_users:
            messages.error(
                request,
                f'Seu plano permite no máximo {max_users} usuário(s). '
                f'Faça upgrade para adicionar mais.'
            )
            return redirect('user_list')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user          = form.save(commit=False)
        user.business = self.request.user.business
        user.plan     = self.request.user.business.plan
        user.save()
        messages.success(self.request, '✅ Usuário criado com sucesso.')
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model         = User
    form_class    = CustomUserChangeForm  # veja item 3
    template_name = 'users/form.html'
    success_url   = reverse_lazy('user_list')

    def get_queryset(self):
        # Empresa só edita seus próprios usuários
        return User.objects.filter(business=self.request.user.business)

    def form_valid(self, form):
        messages.success(self.request, '✅ Usuário atualizado com sucesso.')
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, DeleteView):
    model        = User
    template_name = 'users/delete.html'
    success_url  = reverse_lazy('user_list')

    def get_queryset(self):
        # Empresa só exclui seus próprios usuários
        return User.objects.filter(business=self.request.user.business)

    def dispatch(self, request, *args, **kwargs):
        # Impede que o usuário exclua a si mesmo
        obj = self.get_object()
        if obj == request.user:
            messages.error(request, 'Você não pode excluir seu próprio usuário.')
            return redirect('user_list')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        messages.success(request, '✅ Usuário excluído com sucesso.')
        return super().post(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# NCM
# ─────────────────────────────────────────────────────────────────────────────

class NcmListView(LoginRequiredMixin, ListView):
    model               = NCM
    template_name       = 'ncm/list.html'
    context_object_name = 'ncms'

    def get_queryset(self):
        return NCM.objects.all().order_by('code')


class NcmCreateView(LoginRequiredMixin, CreateView):
    model         = NCM
    fields        = ['category', 'code', 'description', 'cest', 'mono']
    template_name = 'ncm/form.html'
    success_url   = reverse_lazy('ncm_list')

    def form_valid(self, form):
        messages.success(self.request, 'NCM cadastrado com sucesso.')
        return super().form_valid(form)


class NcmUpdateView(LoginRequiredMixin, UpdateView):
    model         = NCM
    fields        = ['category', 'code', 'description', 'cest', 'mono']
    template_name = 'ncm/form.html'
    success_url   = reverse_lazy('ncm_list')

    def form_valid(self, form):
        messages.success(self.request, 'NCM alterado com sucesso.')
        return super().form_valid(form)


class NcmDeleteView(LoginRequiredMixin, DeleteView):
    model         = NCM
    template_name = 'ncm/confirm_delete.html'
    success_url   = reverse_lazy('ncm_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'NCM excluído com sucesso.')
        return super().delete(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# GRUPOS NCM
# ─────────────────────────────────────────────────────────────────────────────

from .models import NCMGroup, NCMGroupItem, FiscalOperation
from .forms import NCMGroupForm, NCMGroupItemForm, FiscalOperationForm


class NCMGroupListView(LoginRequiredMixin, ListView):
    model         = NCMGroup
    template_name = 'fiscal/ncm_group_list.html'

    def get_queryset(self):
        return NCMGroup.objects.filter(business=self.request.user.business)


class NCMGroupCreateView(LoginRequiredMixin, CreateView):
    model         = NCMGroup
    form_class    = NCMGroupForm
    template_name = 'fiscal/ncm_group_form.html'
    success_url   = reverse_lazy('ncm_group_list')

    def form_valid(self, form):
        group          = form.save(commit=False)
        group.business = self.request.user.business
        group.save()
        messages.success(self.request, 'Grupo criado com sucesso.')
        return redirect(self.success_url)


class NCMGroupUpdateView(LoginRequiredMixin, UpdateView):
    model         = NCMGroup
    form_class    = NCMGroupForm
    template_name = 'fiscal/ncm_group_form.html'
    success_url   = reverse_lazy('ncm_group_list')

    def get_queryset(self):
        return NCMGroup.objects.filter(business=self.request.user.business)


class NCMGroupDeleteView(LoginRequiredMixin, DeleteView):
    model         = NCMGroup
    template_name = 'fiscal/confirm_delete.html'
    success_url   = reverse_lazy('ncm_group_list')

    def get_queryset(self):
        return NCMGroup.objects.filter(business=self.request.user.business)


@login_required
def manage_ncm_group_items(request, pk):
    group = get_object_or_404(NCMGroup, pk=pk, business=request.user.business)
    query = request.GET.get('q', '')

    available_ncms = NCM.objects.all()
    if query:
        available_ncms = available_ncms.filter(code__icontains=query)
    available_ncms = available_ncms.order_by('code')[:100]

    if request.method == 'POST':
        ncm_id = request.POST.get('ncm_id')
        if ncm_id:
            ncm = get_object_or_404(NCM, id=ncm_id)
            NCMGroupItem.objects.get_or_create(group=group, ncm=ncm)
            messages.success(request, 'NCM adicionado.')
            return redirect('ncm_group_items', pk=group.pk)

    return render(request, 'fiscal/ncm_group_items.html', {
        'group': group,
        'available_ncms': available_ncms,
        'query': query,
    })


@login_required
def remove_ncm_from_group(request, group_id, ncm_id):
    group = get_object_or_404(NCMGroup, pk=group_id, business=request.user.business)
    item  = get_object_or_404(NCMGroupItem, group=group, ncm_id=ncm_id)
    item.delete()
    messages.success(request, 'NCM removido do grupo com sucesso.')
    return redirect('ncm_group_items', pk=group.pk)


@login_required
def ajax_ncm_search(request):
    query = request.GET.get('q', '')
    ncms  = NCM.objects.filter(
        Q(code__icontains=query) | Q(description__icontains=query)
    )[:20]

    data = [{'id': n.id, 'code': n.code, 'description': n.description} for n in ncms]
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────────────────────
# OPERAÇÕES FISCAIS
# ─────────────────────────────────────────────────────────────────────────────

class FiscalOperationListView(LoginRequiredMixin, ListView):
    model         = FiscalOperation
    template_name = 'fiscal/operation_list.html'

    def get_queryset(self):
        return FiscalOperation.objects.filter(business=self.request.user.business)


class FiscalOperationCreateView(LoginRequiredMixin, CreateView):
    model         = FiscalOperation
    form_class    = FiscalOperationForm
    template_name = 'fiscal/operation_form.html'
    success_url   = reverse_lazy('operation_list')

    def form_valid(self, form):
        operation          = form.save(commit=False)
        operation.business = self.request.user.business
        operation.save()
        messages.success(self.request, 'Operação criada com sucesso.')
        return redirect(self.success_url)


class FiscalOperationUpdateView(LoginRequiredMixin, UpdateView):
    model         = FiscalOperation
    form_class    = FiscalOperationForm
    template_name = 'fiscal/operation_form.html'
    success_url   = reverse_lazy('operation_list')

    def get_queryset(self):
        return FiscalOperation.objects.filter(business=self.request.user.business)

    def form_valid(self, form):
        messages.success(self.request, 'Operação atualizada com sucesso.')
        return super().form_valid(form)


class FiscalOperationDeleteView(LoginRequiredMixin, DeleteView):
    model         = FiscalOperation
    template_name = 'fiscal/confirm_delete.html'
    success_url   = reverse_lazy('operation_list')

    def get_queryset(self):
        return FiscalOperation.objects.filter(business=self.request.user.business)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Operação excluída com sucesso.')
        return super().delete(request, *args, **kwargs)
    

@login_required
def invoice_detail(request, pk):
    """
    Tela de detalhe da NF-e / NFC-e.
    Exibe cabeçalho, itens, totais, pagamentos, transporte e log.
    """
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        order__business=request.user.business
    )
    return render(request, 'fiscal/invoice_detail.html', {
        'invoice': invoice,
    })

# @login_required
# @transaction.atomic
# def invoice_update(request, pk):
#     invoice = get_object_or_404(Invoice, pk=pk)

#     # BLOQUEIO FISCAL
#     if invoice.status not in ['RASCUNHO', 'REJEITADA']:
#         messages.error(request, "Esta NF não pode ser editada.")
#         return redirect('invoice_detail', pk=pk)

#     if request.method == 'POST':
#         form = InvoiceForm(request.POST, instance=invoice)
#         formset = InvoiceItemFormSet(request.POST, instance=invoice)

#         if form.is_valid() and formset.is_valid():
#             form.save()
#             formset.save()
#             messages.success(request, "Nota atualizada com sucesso.")
#             return redirect('invoice_detail', pk=pk)
#     else:
#         form = InvoiceForm(instance=invoice)
#         formset = InvoiceItemFormSet(instance=invoice)

#     return render(request, 'fiscal/invoice_edit_full.html', {
#         'form': form,
#         'formset': formset,
#         'invoice': invoice
#     })

# ─────────────────────────────────────────────────────────────────────────────
# INVOICE VIEWS — cole no final de core/views.py
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        order__business=request.user.business,
    )
    return render(request, 'fiscal/invoice_detail.html', {'invoice': invoice})


@login_required
@transaction.atomic
def invoice_update(request, pk):
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        order__business=request.user.business,
    )

    if not invoice.is_editable:
        messages.error(request, 'Esta NF não pode ser editada no status atual.')
        return redirect('invoice_detail', pk=pk)

    from .forms import InvoiceForm, InvoiceItemFormSet, InvoicePaymentFormSet

    if request.method == 'POST':
        form            = InvoiceForm(request.POST, instance=invoice)
        item_formset    = InvoiceItemFormSet(request.POST, instance=invoice, prefix='items')
        payment_formset = InvoicePaymentFormSet(request.POST, instance=invoice, prefix='payments')

        form_ok     = form.is_valid()
        items_ok    = item_formset.is_valid()
        payments_ok = payment_formset.is_valid()

        if form_ok and items_ok and payments_ok:
            form.save()
            item_formset.save()
            payment_formset.save()

            # Transporte
            try:
                t = invoice.transport
                t.freight_mode   = request.POST.get('freight_mode', t.freight_mode)
                t.carrier_name   = request.POST.get('carrier_name', '') or ''
                t.carrier_cnpj   = request.POST.get('carrier_cnpj', '') or ''
                t.vehicle_plate  = request.POST.get('vehicle_plate', '') or ''
                t.vehicle_state  = request.POST.get('vehicle_state', '') or ''
                vol   = request.POST.get('volume_qty', '').strip()
                gross = request.POST.get('gross_weight', '').strip()
                net   = request.POST.get('net_weight', '').strip()
                t.volume_qty     = vol   if vol   else None
                t.volume_species = request.POST.get('volume_species', '') or ''
                t.gross_weight   = gross if gross else None
                t.net_weight     = net   if net   else None
                t.save()
            except Exception:
                pass

            _recalcular_totais_invoice(invoice)

            messages.success(request, '✅ NF atualizada com sucesso!')
            return redirect('invoice_detail', pk=invoice.pk)

        else:
            if not form_ok:
                for field, errs in form.errors.items():
                    messages.error(request, f'Campo "{field}": {errs.as_text()}')
            if not items_ok:
                for i, f in enumerate(item_formset):
                    for field, errs in f.errors.items():
                        messages.error(request, f'Item {i+1} – "{field}": {errs.as_text()}')
                if item_formset.non_form_errors():
                    messages.error(request, str(item_formset.non_form_errors()))
            if not payments_ok:
                for i, f in enumerate(payment_formset):
                    for field, errs in f.errors.items():
                        messages.error(request, f'Pagamento {i+1} – "{field}": {errs.as_text()}')

    else:
        form            = InvoiceForm(instance=invoice)
        item_formset    = InvoiceItemFormSet(instance=invoice, prefix='items')
        payment_formset = InvoicePaymentFormSet(instance=invoice, prefix='payments')

    return render(request, 'fiscal/invoice_edit.html', {
        'form':            form,
        'item_formset':    item_formset,
        'payment_formset': payment_formset,
        'invoice':         invoice,
    })


def _recalcular_totais_invoice(invoice):
    from decimal import Decimal
    invoice.refresh_from_db()
    items = list(invoice.items.all())

    total_products = sum(i.gross_total    for i in items) or Decimal('0')
    total_discount = sum(i.discount       for i in items) or Decimal('0')
    total_bc_icms  = sum(i.icms_bc        for i in items) or Decimal('0')
    total_icms     = sum(i.icms_value     for i in items) or Decimal('0')
    total_pis      = sum(i.pis_value      for i in items) or Decimal('0')
    total_cofins   = sum(i.cofins_value   for i in items) or Decimal('0')
    total_bc_st    = sum(i.icms_st_bc     for i in items) or Decimal('0')
    total_icms_st  = sum(i.icms_st_value  for i in items) or Decimal('0')

    frete  = invoice.total_freight   or Decimal('0')
    seguro = invoice.total_insurance or Decimal('0')
    outras = invoice.total_other     or Decimal('0')

    invoice.total_products = total_products
    invoice.total_discount = total_discount
    invoice.total_bc_icms  = total_bc_icms
    invoice.total_icms     = total_icms
    invoice.total_pis      = total_pis
    invoice.total_cofins   = total_cofins
    invoice.total_bc_st    = total_bc_st
    invoice.total_icms_st  = total_icms_st
    invoice.total_nf       = total_products - total_discount + frete + seguro + outras

    invoice.save(update_fields=[
        'total_products', 'total_discount',
        'total_bc_icms',  'total_icms',
        'total_pis',      'total_cofins',
        'total_bc_st',    'total_icms_st',
        'total_nf',
    ])


# @login_required
# @transaction.atomic
# def invoice_transmit(request, pk):
#     invoice = get_object_or_404(
#         Invoice,
#         pk=pk,
#         order__business=request.user.business,
#     )

#     if request.method != 'POST':
#         return redirect('invoice_detail', pk=pk)

#     if invoice.status not in ['RASCUNHO', 'REJEITADA']:
#         messages.error(request, 'Esta NF não pode ser transmitida no status atual.')
#         return redirect('invoice_detail', pk=pk)

#     try:
#         from core.services.fiscal.xml_builder import build_xml
#         from core.services.fiscal.signer import assinar_xml
#         from core.services.fiscal.sefaz_client import transmitir

#         xml_str      = build_xml(invoice)
#         xml_assinado = assinar_xml(invoice, xml_str)
#         resultado    = transmitir(invoice, xml_assinado)

#         if resultado['sucesso']:
#             messages.success(
#                 request,
#                 f'✅ NF Autorizada! Protocolo: {resultado["protocolo"]}'
#             )
#         else:
#             messages.error(
#                 request,
#                 f'❌ Rejeição SEFAZ ({resultado["codigo"]}): {resultado["mensagem"]}'
#             )

#     except Exception as e:
#         messages.error(request, f'Erro ao transmitir: {str(e)}')

#     return redirect('invoice_detail', pk=pk)


@login_required
@transaction.atomic
def invoice_transmit(request, pk):
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        order__business=request.user.business,
    )

    if request.method != 'POST':
        return redirect('invoice_detail', pk=pk)

    # ── Modo debug: ?debug=1 exibe o XML sem transmitir ──────────────────
    debug = request.GET.get('debug') == '1'

    if invoice.status not in ['RASCUNHO', 'REJEITADA']:
        messages.error(request, 'Esta NF não pode ser transmitida no status atual.')
        return redirect('invoice_detail', pk=pk)

    try:
        from core.services.fiscal.xml_builder import build_xml
        from core.services.fiscal.signer import assinar_xml
        from core.services.fiscal.sefaz_client import transmitir
        from django.http import HttpResponse

        xml_str = build_xml(invoice)

        if debug:
            # Retorna o XML formatado no browser — não transmite nem assina
            from lxml import etree
            try:
                root        = etree.fromstring(xml_str.encode())
                xml_bonito  = etree.tostring(root, pretty_print=True, encoding='unicode')
            except Exception:
                xml_bonito = xml_str
            return HttpResponse(xml_bonito, content_type='text/xml; charset=utf-8')

        xml_assinado = assinar_xml(invoice, xml_str)
        resultado    = transmitir(invoice, xml_assinado)

        if resultado['sucesso']:
            messages.success(
                request,
                f'✅ NF Autorizada! Protocolo: {resultado["protocolo"]}'
            )
        else:
            messages.error(
                request,
                f'❌ Rejeição SEFAZ ({resultado["codigo"]}): {resultado["mensagem"]}'
            )

    except Exception as e:
        import traceback
        messages.error(request, f'Erro ao transmitir: {str(e)}')
        # Detalhe completo no terminal do servidor
        traceback.print_exc()

    return redirect('invoice_detail', pk=pk)

@login_required
@transaction.atomic
def invoice_cancel(request, pk):
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        order__business=request.user.business,
    )

    if request.method != 'POST':
        return redirect('invoice_detail', pk=pk)

    justificativa = request.POST.get('justificativa', '').strip()

    if len(justificativa) < 15:
        messages.error(request, 'A justificativa deve ter no mínimo 15 caracteres.')
        return redirect('invoice_detail', pk=pk)

    try:
        from core.services.fiscal.sefaz_client import cancelar
        resultado = cancelar(invoice, justificativa)

        if resultado['sucesso']:
            messages.success(request, f'✅ NF Cancelada! Protocolo: {resultado["protocolo"]}')
        else:
            messages.error(
                request,
                f'❌ Erro ao cancelar ({resultado["codigo"]}): {resultado["mensagem"]}'
            )

    except Exception as e:
        messages.error(request, f'Erro ao cancelar: {str(e)}')

    return redirect('invoice_detail', pk=pk)

# ── Substitua invoice_xml_debug em core/views.py ─────────────────────────────

@login_required
def invoice_xml_debug(request, pk):
    import json
    from lxml import etree

    invoice = get_object_or_404(
        Invoice, pk=pk, order__business=request.user.business
    )

    xml_content = ''
    xml_raw     = ''
    erro        = ''

    try:
        from core.services.fiscal.xml_builder import build_xml
        xml_str = build_xml(invoice)

        # Formata com indentação
        try:
            root        = etree.fromstring(xml_str.encode())
            xml_bonito  = etree.tostring(root, pretty_print=True, encoding='unicode')
        except Exception:
            xml_bonito = xml_str

        xml_content = xml_bonito
        xml_raw     = xml_bonito

    except Exception as e:
        import traceback
        erro = f'{str(e)}\n\n{traceback.format_exc()}'

    return render(request, 'fiscal/invoice_xml_debug.html', {
        'invoice':     invoice,
        'xml_content': xml_content,
        'xml_raw':     json.dumps(xml_raw),   # seguro para uso no JS
        'erro':        erro,
    })

@login_required
def invoice_list(request):
    from django.db.models import Q

    invoices = Invoice.objects.filter(
        order__business=request.user.business
    ).select_related('order').order_by('-issue_date', '-number')

    # Filtros
    status = request.GET.get('status', '')
    modelo = request.GET.get('modelo', '')
    busca  = request.GET.get('q', '')

    if status:
        invoices = invoices.filter(status=status)
    if modelo:
        invoices = invoices.filter(model=modelo)
    if busca:
        invoices = invoices.filter(
            Q(number__icontains=busca) |
            Q(dest_name__icontains=busca) |
            Q(access_key__icontains=busca) |
            Q(nature_operation__icontains=busca)
        )

    return render(request, 'fiscal/invoice_list.html', {
        'invoices':       invoices,
        'status_filter':  status,
        'modelo_filter':  modelo,
        'busca':          busca,
        'status_choices': [
            ('RASCUNHO',  'Rascunho'),
            ('PENDENTE',  'Pendente'),
            ('AUTORIZADA','Autorizada'),
            ('REJEITADA', 'Rejeitada'),
            ('CANCELADA', 'Cancelada'),
            ('DENEGADA',  'Denegada'),
        ],
    })