from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import *
from django.contrib.auth.views import LoginView, LogoutView
from .forms import ClientForm, SizechartForm, SizesFormSet, colorchartForm, modelchartForm, ProductForm, StockEntryForm, OrderForm, OrderItemFormSet, ProductImageFormSet, PaymentMethodForm, BankAccountForm
from django.shortcuts import redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from .services.order_stock import reserve_stock, release_stock, finalize_stock, create_variants
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware
from datetime import datetime
from django.db.models import Sum, Count
from datetime import date
from django.db.models.functions import TruncMonth
from .models import Client ,Orders, Product
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Count, Prefetch
from django.db.models.functions import TruncMonth
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.forms import inlineformset_factory
from datetime import timedelta
from decimal import Decimal
from .models import FinancialMovement, FinancialMovementParcel
from .forms import FinancialMovementForm, FinancialParcelFormSet, PaymentMethodForm, BankAccountForm, ParcelPayForm, OrderPaymentFormSet
import calendar

@login_required
def home(request):
    today = date.today()
    business = request.user.business

    # ============================
    # 📊 KPIs GERAIS
    # ============================
    total_clients = Client.objects.filter(
        business=business
    ).count()

    total_products = Product.objects.filter(
        business=business
    ).count()

    products = Product.objects.filter(business=business)
    total_stock = sum(p.stock_real for p in products)

    orders = Orders.objects.filter(business=business)

    # 🔥 FILTRO PADRÃO DO MÊS ATUAL
    orders_month_qs = orders.filter(
        created_at__year=today.year,
        created_at__month=today.month
    )

    orders_today = orders.filter(
        created_at__date=today
    ).count()

    orders_month = orders_month_qs.count()

    # ============================
    # 💵 FATURAMENTO (MÊS ATUAL)
    # ============================

    revenue_month = orders_month_qs.filter(
        status=Orders.STATUS_FATURADO
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')

    # 🔥 TOTAL FATURADO AGORA TAMBÉM É DO MÊS
    revenue_total = revenue_month

    ticket_medio = (
        revenue_month / orders_month
        if orders_month > 0 else Decimal('0.00')
    )

    # ============================
    # 💰 FLUXO DE CAIXA (MÊS ATUAL)
    # ============================
    parcels = FinancialMovementParcel.objects.filter(
        movement__business=business,
        deadline__year=today.year,
        deadline__month=today.month
    )

    entradas_recebidas = parcels.filter(
        movement__type='in',
        payed=True
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    saidas_pagas = parcels.filter(
        movement__type='out',
        payed=True
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    contas_receber = parcels.filter(
        movement__type='in',
        payed=False
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    contas_vencidas = parcels.filter(
        movement__type='in',
        payed=False,
        deadline__lt=today
    ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

    saldo_mes = entradas_recebidas - saidas_pagas

    # ============================
    # 📊 GRÁFICOS
    # ============================
    sales_by_month = (
        orders.filter(status=Orders.STATUS_FATURADO)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('total_amount'))
        .order_by('month')
    )

    sales_by_month_data = [
        {
            'month': item['month'].strftime('%Y-%m'),
            'total': float(item['total'] or 0)
        }
        for item in sales_by_month
    ]

    orders_by_status = (
        orders
        .values('status')
        .annotate(total=Count('id'))
    )

    orders_by_status_data = [
        {
            'status': item['status'],
            'total': item['total']
        }
        for item in orders_by_status
    ]

    last_orders = (
        orders
        .select_related('client')
        .order_by('-created_at')[:8]
    )

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

        # 💰 Fluxo de caixa
        'entradas_recebidas': entradas_recebidas,
        'saidas_pagas': saidas_pagas,
        'saldo_mes': saldo_mes,
        'contas_receber': contas_receber,
        'contas_vencidas': contas_vencidas,
    }

    return render(request, 'auth/home.html', context)

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'

    def get_success_url(self):
        return reverse_lazy('home')
    
class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')


@login_required
def client_list(request):
    search = request.GET.get('q', '')

    # Base queryset (SEM paginação ainda)
    base_qs = Client.objects.filter(
        business=request.user.business
    )

    if search:
        base_qs = base_qs.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(document__icontains=search)
        )

    base_qs = base_qs.order_by('name')

    # 📊 DASHBOARD TOTALS (usar queryset sem paginação)
    total_clients = base_qs.count()
    clients_with_email = base_qs.exclude(email__isnull=True)\
                                .exclude(email__exact='')\
                                .count()

    clients_with_phone = base_qs.exclude(phone__isnull=True)\
                                .exclude(phone__exact='')\
                                .count()

    # 📄 PAGINAÇÃO
    paginator = Paginator(base_qs, 10)
    page = request.GET.get('page')
    clients = paginator.get_page(page)

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

    return render(request, 'clients/form.html', {
        'form': form
    })


# @login_required
# def client_update(request, pk):
#     client = get_object_or_404(
#         Client,
#         pk=pk,
#         business=request.user.business
#     )

#     form = ClientForm(request.POST or None, instance=client)

#     if request.method == 'POST' and form.is_valid():
#         form.save()
#         return redirect('client_list')

#     return render(request, 'clients/form.html', {
#         'form': form,
#         'edit': True
#     })

@login_required
def client_update(request, pk):
    client = get_object_or_404(
        Client,
        pk=pk,
        business=request.user.business
    )

    form = ClientForm(request.POST or None, instance=client)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente alterado com sucesso!")
            return redirect(reverse('client_update', kwargs={'pk': client.pk}))
        else:
            messages.error(request, "Erro ao salvar o cliente.")

    return render(request, 'clients/form.html', {
        'form': form,
        'edit': True
    })

@login_required
def client_delete(request, pk):
    client = get_object_or_404(
        Client,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        client.delete()
        return redirect('client_list')

    return render(request, 'clients/delete.html', {
        'client': client
    })

@login_required
def sizechart_list(request):
    search = request.GET.get('q', '')

    sizecharts = Sizechart.objects.filter(
        business=request.user.business,
        name__icontains=search
    ).order_by('name')

    paginator = Paginator(sizecharts, 10)
    page = request.GET.get('page')
    sizecharts = paginator.get_page(page)

    return render(request, 'sizecharts/list.html', {
        'sizecharts': sizecharts,
        'search': search
    })

@login_required
def sizechart_create(request):
    form = SizechartForm(request.POST or None)
    formset = SizesFormSet(request.POST or None)

    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            sizechart = form.save(commit=False)
            sizechart.business = request.user.business
            sizechart.save()

            formset.instance = sizechart
            formset.save()

            return redirect('sizechart_list')

    return render(request, 'sizecharts/form.html', {
        'form': form,
        'formset': formset
    })

@login_required
def sizechart_update(request, pk):
    sizechart = get_object_or_404(
        Sizechart,
        pk=pk,
        business=request.user.business
    )

    form = SizechartForm(request.POST or None, instance=sizechart)
    formset = SizesFormSet(request.POST or None, instance=sizechart)

    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('sizechart_list')

    return render(request, 'sizecharts/form.html', {
        'form': form,
        'formset': formset,
        'edit': True
    })

@login_required
def sizechart_delete(request, pk):
    sizechart = get_object_or_404(
        Sizechart,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        sizechart.delete()
        return redirect('sizechart_list')

    return render(request, 'sizecharts/delete.html', {
        'sizechart': sizechart
    })

@login_required
def colorchart_list(request):
    search = request.GET.get('q', '')

    colorcharts = colorchart.objects.filter(
        business=request.user.business,
        name__icontains=search
    ).order_by('name')

    paginator = Paginator(colorcharts, 10)
    page = request.GET.get('page')
    colorcharts = paginator.get_page(page)

    return render(request, 'colorcharts/list.html', {
        'colorcharts': colorcharts,
        'search': search
    })
@login_required
def colorchart_create(request):
    form = colorchartForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        colorchart_instance = form.save(commit=False)
        colorchart_instance.business = request.user.business
        colorchart_instance.save()
        return redirect('colorchart_list')

    return render(request, 'colorcharts/form.html', {
        'form': form
    })
@login_required
def colorchart_update(request, pk):
    colorchart_instance = get_object_or_404(
        colorchart,
        pk=pk,
        business=request.user.business
    )

    form = colorchartForm(request.POST or None, instance=colorchart_instance)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('colorchart_list')

    return render(request, 'colorcharts/form.html', {
        'form': form,
        'edit': True
    })
@login_required
def colorchart_delete(request, pk):
    colorchart_instance = get_object_or_404(
        colorchart,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        colorchart_instance.delete()
        return redirect('colorchart_list')

    return render(request, 'colorcharts/delete.html', {
        'colorchart': colorchart_instance
    })
@login_required
def modelchart_list(request):
    search = request.GET.get('q', '')

    modelcharts = modelchart.objects.filter(
        business=request.user.business,
        name__icontains=search
    ).order_by('name')

    paginator = Paginator(modelcharts, 10)
    page = request.GET.get('page')
    modelcharts = paginator.get_page(page)

    return render(request, 'modelcharts/list.html', {
        'modelcharts': modelcharts,
        'search': search
    })
@login_required
def modelchart_create(request):
    form = modelchartForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        modelchart_instance = form.save(commit=False)
        modelchart_instance.business = request.user.business
        modelchart_instance.save()
        return redirect('modelchart_list')

    return render(request, 'modelcharts/form.html', {
        'form': form
    })
@login_required
def modelchart_update(request, pk): 
    modelchart_instance = get_object_or_404(
        modelchart,
        pk=pk,
        business=request.user.business
    )

    form = modelchartForm(request.POST or None, instance=modelchart_instance)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('modelchart_list')

    return render(request, 'modelcharts/form.html', {
        'form': form,
        'edit': True
    })
@login_required
def modelchart_delete(request, pk):
    modelchart_instance = get_object_or_404(
        modelchart,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        modelchart_instance.delete()
        return redirect('modelchart_list')

    return render(request, 'modelcharts/delete.html', {
        'modelchart': modelchart_instance
    })  

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models import Prefetch

@login_required
def product_list(request):
    search = request.GET.get('q', '')

    base_qs = (
        Product.objects
        .filter(business=request.user.business)
        .prefetch_related(
            'variants__stock_entries',
            Prefetch(
                'images',
                queryset=ProductImage.objects.filter(order=0),
                to_attr='cover_image'
            )
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

    # ===============================
    # 📊 DASHBOARD (CÁLCULO REAL)
    # ===============================

    total_products = base_qs.count()

    total_stock = 0
    low_stock_count = 0
    total_stock_value = 0

    for product in base_qs:
        for variant in product.variants.all():
            available = variant.stock_available
            total_stock += available
            total_stock_value += available * product.cost

            if available < 5:
                low_stock_count += 1

    # ===============================
    # 📄 PAGINAÇÃO
    # ===============================

    paginator = Paginator(base_qs, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

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
        form = ProductForm(
            request.POST,
            business=request.user.business
        )

        if form.is_valid():

            product = form.save(commit=False)
            product.business = request.user.business
            product.save()

            create_variants(product)

            return redirect('product_update', product.id)  # 🔥 importante

        else:
            print(form.errors)  # debug

    else:
        form = ProductForm(business=request.user.business)

    return render(request, 'products/form.html', {
        'form': form
    })

@login_required
def product_update(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            form.save()
            create_variants(product)
            return redirect('product_list')

    else:
        form = ProductForm(instance=product)

    return render(request, 'products/form.html', {
        'form': form,
        'product': product,
        'edit': True
    })


@login_required
def product_delete(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        product.delete()
        return redirect('product_list')

    return render(request, 'products/delete.html', {
         'product': product
    })

@login_required
def stock_movement(request, variant_id):
    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        product__business=request.user.business
    )

    movements = variant.stock_entries.order_by('-timestamp')

    form = StockEntryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.variant = variant

        # 🔎 Verifica se já existe alguma movimentação
        has_movements = variant.stock_entries.exists()

        if not has_movements:
            entry.movement_type = StockEntry.MovementType.INITIAL
        else:
            entry.movement_type = StockEntry.MovementType.ADJUST

        entry.save()

        return redirect('stock_movement', variant_id=variant.id)

    return render(request, 'stock/movement.html', {
        'variant': variant,
        'movements': movements,
        'form': form
    })


@login_required
def stock_entry_delete(request, pk):
    entry = get_object_or_404(
        StockEntry,
        pk=pk,
        variant__product__business=request.user.business
    )

    variant = entry.variant

    if request.method == 'POST':
        entry.delete()
        return redirect('stock_movement', variant_id=variant.id)

    return render(request, 'stock/delete.html', {
        'entry': entry
    })


@login_required
@transaction.atomic
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.business = request.user.business
            order.total_amount = 0
            order.save()

            messages.success(request, 'Pedido criado. Agora inclua os itens.')
            return redirect('order_update', order.id)
    else:
        form = OrderForm(user=request.user)

    return render(request, 'orders/form_create.html', {
        'form': form,
        'title': 'Novo Pedido'
    })

@login_required
def order_list(request):
    base_qs = (
        Orders.objects
        .filter(business=request.user.business)
        .select_related('client')
    )

    orders = base_qs.order_by('-created_at')

    # 🔍 FILTROS
    client_id = request.GET.get('client')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if client_id:
        orders = orders.filter(client_id=client_id)

    if status:
        orders = orders.filter(status=status)

    if start_date:
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        orders = orders.filter(created_at__gte=start_date)

    if end_date:
        end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        orders = orders.filter(created_at__lte=end_date)

    # 📊 RESUMO
    summary = base_qs.aggregate(
    total_orders=Count('id'),
    total_value=Sum('total_amount'),

    orcamento_value=Sum(
        'total_amount',
        filter=models.Q(status=Orders.STATUS_ORCAMENTO)
    ),

    em_separacao_value=Sum(
        'total_amount',
        filter=models.Q(status=Orders.STATUS_EM_SEPARACAO)
    ),

    separado_value=Sum(
        'total_amount',
        filter=models.Q(status=Orders.STATUS_SEPARADO)
    ),

    faturado_value=Sum(
        'total_amount',
        filter=models.Q(status=Orders.STATUS_FATURADO)
    ),
)


    # 📄 PAGINAÇÃO
    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
    order = get_object_or_404(
        Orders,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST' and not order.can_edit():
        messages.error(request, 'Este pedido não pode mais ser alterado.')
        return redirect('order_list')

    if request.method == 'POST':

        form = OrderForm(request.POST, instance=order, user=request.user)

        formset = OrderItemFormSet(
            request.POST,
            instance=order,
            prefix='items'
        )

        payment_formset = OrderPaymentFormSet(
            request.POST,
            instance=order,
            prefix='payments'
        )

        if form.is_valid() and formset.is_valid() and payment_formset.is_valid():

            form.save()

            total = Decimal('0.00')

            # ===============================
            # ITENS
            # ===============================
            for form_item in formset:

                if form_item.cleaned_data.get('DELETE'):
                    if form_item.instance.pk:
                        form_item.instance.delete()
                    continue

                item = form_item.save(commit=False)
                item.order = order
                item.save()

                total += item.subtotal

            order.total_amount = total
            order.save(update_fields=['total_amount'])

            # ===============================
            # PAGAMENTOS
            # ===============================
            for payment_form in payment_formset:

                if payment_form.cleaned_data.get('DELETE'):
                    if payment_form.instance.pk:
                        payment_form.instance.delete()
                    continue

                payment = payment_form.save(commit=False)
                payment.order = order
                payment.save()

                payment.parcels_records.all().delete()
                payment.generate_parcels()

            messages.success(request, 'Pedido salvo com sucesso.')
            # return redirect('order_list')
            return redirect('order_update', pk=order.pk)

    else:
        form = OrderForm(instance=order, user=request.user)

        formset = OrderItemFormSet(
            instance=order,
            prefix='items'
        )

        payment_formset = OrderPaymentFormSet(
            instance=order,
            prefix='payments'
        )

    # ===============================
    # 🔥 SALDO
    # ===============================
    from django.db.models import Sum

    total_order = order.total_amount or Decimal('0.00')

    total_payments = order.payments.aggregate(
        total=Sum('total_value')
    )['total'] or Decimal('0.00')

    saldo = total_order - total_payments

    return render(request, 'orders/form_update.html', {
        'form': form,
        'formset': formset,
        'payment_formset': payment_formset,
        'order': order,
        'total_order': total_order,
        'total_payments': total_payments,
        'saldo': saldo,
        'payments_with_parcels': order.payments.prefetch_related('parcels_records')
    })

@login_required
def order_delete(request, pk):
    order = get_object_or_404(
        Orders,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        order.delete()
        return redirect('order_list')

    return render(request, 'orders/delete.html', {
        'order': order
    })

@login_required
@transaction.atomic
def order_change_status(request, order_id):
    order = get_object_or_404(
        Orders,
        id=order_id,
        business=request.user.business
    )

    new_status = request.POST.get('status')

    if not order.can_change_status_to(new_status):
        messages.error(
            request,
            f'Não é permitido mudar de {order.get_status_display()} '
            f'para {dict(Orders.STATUS_CHOICES).get(new_status)}'
        )
        return redirect('order_update', order.id)

    try:
        # EM_SEPARAÇÃO → reserva estoque
        if new_status == Orders.STATUS_EM_SEPARACAO:
            reserve_stock(order)

        # CANCELADO → libera estoque se estava reservado
        elif new_status == Orders.STATUS_CANCELADO:
            release_stock(order)

        # FATURADO → confirma a reserva (baixa definitiva)
        elif new_status == Orders.STATUS_FATURADO:
            finalize_stock(order)
            order.generate_financial()

        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(
            request,
            f'Status alterado para {order.get_status_display()}'
        )

    except ValidationError as e:
        messages.error(request, e.message)

    return redirect('order_update', order.id)

@login_required
@transaction.atomic
def order_advance_status(request, order_id):
    order = get_object_or_404(
        Orders,
        id=order_id,
        business=request.user.business
    )

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

        messages.success(
            request,
            f'Status alterado para {order.get_status_display()}'
        )

    except ValidationError as e:
        messages.error(request, e.message)

    return redirect('order_update', order.id)

@login_required
@transaction.atomic
def order_cancel(request, order_id):
    order = get_object_or_404(
        Orders,
        id=order_id,
        business=request.user.business
    )

    # se faturado → devolve estoque real
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

    # se reservado → libera
    release_stock(order)

    order.status = Orders.STATUS_CANCELADO
    order.save(update_fields=['status'])

    messages.success(request, 'Pedido cancelado com sucesso.')
    return redirect('order_update', order.id)

@login_required
@require_POST
def product_image_upload(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk,
        business=request.user.business
    )

    image = request.FILES.get("image")

    if image:
        img = ProductImage.objects.create(
            product=product,
            image=image,
            description=request.POST.get("description", ""),
            order=request.POST.get("order", 0)
        )

        return JsonResponse({
            "id": img.id,
            "url": img.image.url,
            "description": img.description,
            "order": img.order
        })

    return JsonResponse({"error": "Sem imagem"}, status=400)

@login_required
@require_POST
def product_image_delete(request, pk):

    image = get_object_or_404(
        ProductImage,
        pk=pk,
        product__business=request.user.business
    )

    image.delete()

    return JsonResponse({"success": True})

@login_required
def product_images_json(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk,
        business=request.user.business
    )

    images = product.images.all()

    data = [
        {
            "id": img.id,
            "url": img.image.url,
            "description": img.description,
            "order": img.order
        }
        for img in images
    ]

    return JsonResponse(data, safe=False)

@login_required
def search_variants(request):
    term = request.GET.get('q', '').strip()

    business = getattr(request.user, 'business', None)
    if not business:
        return JsonResponse({"results": []})

    variants = (
        ProductVariant.objects
        .filter(product__business=business)
        .select_related('product', 'size', 'color', 'product__model')
    )

    if term:
        variants = variants.filter(
            Q(product__name__icontains=term) |
            Q(product__model__name__icontains=term) |
            Q(size__name__icontains=term)
        )

    results = []

    for v in variants[:20]:
        results.append({
            "id": v.id,
            "text": f"{v.product.name} - {v.size if v.size else ''} - {v.color if v.color else ''}",
            "price": float(v.product.price or 0),
            "price1": float(v.product.price1 or 0),
        })

    return JsonResponse({"results": results})


@login_required
def financial_list(request):
    business = request.user.business
    today = date.today()

    # 🔎 Filtros GET
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    status = request.GET.get('status')
    client_id = request.GET.get('client')

    # 📅 Mês atual como padrão
    if not start_date_str and not end_date_str:
        first_day = today.replace(day=1)
        last_day = today.replace(
            day=calendar.monthrange(today.year, today.month)[1]
        )
        start_date = first_day
        end_date = last_day
    else:
        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if start_date_str else None
        )
        end_date = (
            datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date_str else None
        )

    # 🔹 Base Query
    parcels = FinancialMovementParcel.objects.filter(
        movement__business=business
    ).select_related(
        'movement',
        'movement__client'
    )

    # 📅 Filtro por data
    if start_date:
        parcels = parcels.filter(deadline__gte=start_date)

    if end_date:
        parcels = parcels.filter(deadline__lte=end_date)

    # 📌 Filtro por status
    if status == 'paid':
        parcels = parcels.filter(payed=True)
    elif status == 'open':
        parcels = parcels.filter(payed=False)

    # 👤 Filtro por cliente
    if client_id:
        parcels = parcels.filter(movement__client_id=client_id)

    # 📊 Separar por tipo
    entradas = parcels.filter(movement__type='in')
    saidas = parcels.filter(movement__type='out')

    # 💰 Totais pagos
    total_entradas = entradas.filter(payed=True).aggregate(
        total=Sum('value')
    )['total'] or 0

    total_saidas = saidas.filter(payed=True).aggregate(
        total=Sum('value')
    )['total'] or 0

    saldo = total_entradas - total_saidas

    # 📋 Lista de clientes para o select
    clients = Client.objects.filter(
        business=business
    ).order_by('name')

    return render(request, 'financial/list.html', {
        'entradas': entradas,
        'saidas': saidas,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo': saldo,
        'clients': clients,
        'client_id': client_id,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'status': status,
    })



def financial_create(request):
    business = request.user.business

    if request.method == 'POST':
        form = FinancialMovementForm(request.POST)
        formset = FinancialParcelFormSet(request.POST, prefix='parcels')

        if form.is_valid() and formset.is_valid():
            movement = form.save(commit=False)
            movement.business = business
            movement.save()

            formset.instance = movement
            formset.save()

            messages.success(request, "Lançamento criado com sucesso.")
            return redirect('financial_list')

    else:
        form = FinancialMovementForm()
        formset = FinancialParcelFormSet()

    return render(request, 'financial/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Novo Lançamento'
    })


@login_required
@transaction.atomic
def financial_update(request, pk):
    business = request.user.business

    movement = get_object_or_404(
        FinancialMovement,
        pk=pk,
        business=business
    )

    # 🔒 Bloqueia edição se veio de pedido
    if movement.order is not None:
        messages.error(
            request,
            "Este lançamento foi gerado por um pedido e não pode ser editado."
        )
        return redirect('financial_list')

    if request.method == 'POST':
        form = FinancialMovementForm(request.POST, instance=movement)
        formset = FinancialParcelFormSet(request.POST, instance=movement)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()

            messages.success(request, "Lançamento atualizado com sucesso.")
            return redirect('financial_list')

    else:
        form = FinancialMovementForm(instance=movement)
        formset = FinancialParcelFormSet(instance=movement)

    return render(request, 'financial/form.html', {
        'form': form,
        'formset': formset,
        'movement': movement,
        'title': 'Editar Lançamento'
    })


@login_required
def financial_delete(request, pk):
    business = request.user.business

    movement = get_object_or_404(
        FinancialMovement,
        pk=pk,
        business=business
    )

    if movement.order is not None:
        messages.error(
            request,
            "Este lançamento foi gerado por um pedido e não pode ser excluído."
        )
        return redirect('financial_list')

    if request.method == 'POST':
        movement.delete()
        messages.success(request, "Lançamento excluído com sucesso.")
        return redirect('financial_list')

    return render(request, 'financial/delete.html', {
        'movement': movement
    })

@login_required
def paymentmethod_list(request):
    business = request.user.business

    methods = PaymentMethod.objects.filter(
        business=business
    ).order_by('name')

    return render(request, 'financial/paymentmethod_list.html', {
        'methods': methods
    })

@login_required
def paymentmethod_create(request):
    business = request.user.business

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)

        if form.is_valid():
            method = form.save(commit=False)
            method.business = business
            method.save()

            messages.success(request, "Forma de pagamento criada com sucesso.")
            return redirect('paymentmethod_list')

    else:
        form = PaymentMethodForm()

    return render(request, 'financial/paymentmethod_form.html', {
        'form': form,
        'title': 'Nova Forma de Pagamento'
    })

@login_required
def paymentmethod_update(request, pk):
    business = request.user.business

    method = get_object_or_404(
        PaymentMethod,
        pk=pk,
        business=business
    )

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)

        if form.is_valid():
            form.save()
            messages.success(request, "Forma de pagamento atualizada.")
            return redirect('paymentmethod_list')

    else:
        form = PaymentMethodForm(instance=method)

    return render(request, 'financial/paymentmethod_form.html', {
        'form': form,
        'title': 'Editar Forma de Pagamento'
    })

@login_required
def paymentmethod_delete(request, pk):
    business = request.user.business

    method = get_object_or_404(
        PaymentMethod,
        pk=pk,
        business=business
    )

    if request.method == 'POST':
        method.delete()
        messages.success(request, "Forma de pagamento excluída.")
        return redirect('paymentmethod_list')

    return render(request, 'financial/paymentmethod_delete.html', {
        'method': method
    })


@login_required
def bank_list(request):
    business = request.user.business

    banks = BankAccount.objects.filter(
        business=business
    ).order_by('name')

    return render(request, 'financial/bank_list.html', {
        'banks': banks
    })


@login_required
def bank_create(request):
    business = request.user.business

    if request.method == 'POST':
        form = BankAccountForm(request.POST)

        if form.is_valid():
            bank = form.save(commit=False)
            bank.business = business
            bank.save()

            messages.success(request, "Conta bancária criada com sucesso.")
            return redirect('bank_list')
    else:
        form = BankAccountForm()

    return render(request, 'financial/bank_form.html', {
        'form': form,
        'title': 'Nova Conta Bancária'
    })

@login_required
def bank_update(request, pk):
    business = request.user.business

    bank = get_object_or_404(
        BankAccount,
        pk=pk,
        business=business
    )

    if request.method == 'POST':
        form = BankAccountForm(request.POST, instance=bank)

        if form.is_valid():
            form.save()
            messages.success(request, "Conta bancária atualizada.")
            return redirect('bank_list')
    else:
        form = BankAccountForm(instance=bank)

    return render(request, 'financial/bank_form.html', {
        'form': form,
        'title': 'Editar Conta Bancária'
    })

@login_required
def bank_delete(request, pk):
    business = request.user.business

    bank = get_object_or_404(
        BankAccount,
        pk=pk,
        business=business
    )

    if request.method == 'POST':
        bank.delete()
        messages.success(request, "Conta bancária excluída.")
        return redirect('bank_list')

    return render(request, 'financial/bank_delete.html', {
        'bank': bank
    })

@login_required
@transaction.atomic
def parcel_pay(request, pk):
    business = request.user.business

    parcel = get_object_or_404(
        FinancialMovementParcel,
        pk=pk,
        movement__business=business
    )

    if parcel.payed:
        messages.warning(request, "Parcela já está paga.")
        return redirect('financial_list')

    parcel.payed = True
    parcel.paydate = timezone.now().date()
    parcel.save()

    messages.success(request, "Parcela paga com sucesso.")
    return redirect('financial_list')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

@login_required
def parcel_pay(request, pk):

    parcel = get_object_or_404(
        FinancialMovementParcel,
        pk=pk,
        movement__business=request.user.business
    )

    if parcel.payed:
        return redirect('financial_list')

    form = ParcelPayForm(
        request.POST or None,
        instance=parcel,
        initial={
            'paydate': timezone.now().date()
        }
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('financial_list')

    return render(request, 'financial/parcel_pay.html', {
        'parcel': parcel,
        'form': form
    })

@login_required
def financial_history(request):

    business = request.user.business

    parcels = (
        FinancialMovementParcel.objects
        .filter(movement__business=business, payed=True)
        .select_related(
            'movement',
            'movement__bank',
            'movement__payment_method'
        )
        .order_by('-paydate', '-id')
    )

    # calcular saldo progressivo
    balance = 0
    history = []

    for parcel in reversed(parcels):

        value = parcel.subtotal

        if parcel.movement.type == 'in':
            balance += value
        else:
            balance -= value

        history.append({
            'parcel': parcel,
            'balance': balance
        })

    history.reverse()

    return render(request, 'financial/history.html', {
        'history': history
    })

from decimal import Decimal
from datetime import timedelta

from decimal import Decimal
from datetime import timedelta
from django.db import transaction

def generate_financial_from_order(order):

    if order.financial_movements.exists():
        return

    for payment in order.payments.all():

        movement = FinancialMovement.objects.create(
            business=order.business,
            client=order.client,
            order=order,
            movement_type='in',  # 🔥 AJUSTE SE NECESSÁRIO
            description=f'Pedido #{order.id}',
            total_amount=payment.total_value,
            issue_date=order.created_at.date(),
        )

        parcels = payment.parcels.all()

        if parcels.exists():
            for parcel in parcels:
                FinancialMovementParcel.objects.create(
                    movement=movement,
                    due_date=parcel.due_date,
                    amount=parcel.amount,
                )
        else:
            FinancialMovementParcel.objects.create(
                movement=movement,
                due_date=order.created_at.date(),
                amount=payment.amount,
            )

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from core.models import ProductVariant


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from core.models import ProductVariant


@login_required
def ajax_variants(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return JsonResponse({"results": []})

    variants = ProductVariant.objects.filter(
        product__business=request.user.business
    ).filter(
        Q(product__name__icontains=query) |
        Q(sku__icontains=query) |
        Q(ean13__iexact=query)
    ).select_related('product', 'size')[:30]

    results = []

    for v in variants:
        size_text = f" - {v.size.name}" if v.size else ""

        results.append({
            "id": v.id,
            "text": (
                f"{v.product.name}"
                f"{size_text} "
                f"{v.color.name if v.color else ''} "
                f"| SKU: {v.sku or '-'} "
                f"| EAN: {v.ean13 or '-'} "
                f"| Estoque: {v.stock_available}"  # 🔥 NOVO
            ),
            "price": str(v.product.price or 0),
            "price1": str(v.product.price1 or 0),
            "stock": v.stock_available  # 🔥 NOVO
        })

    return JsonResponse({"results": results})

from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Business
from .forms import BusinessForm

class BusinessListView(LoginRequiredMixin, ListView):
    model = Business
    template_name = 'business/list.html'
    context_object_name = 'businesses'

class BusinessCreateView(LoginRequiredMixin, CreateView):
    model = Business
    form_class = BusinessForm
    template_name = 'business/form.html'
    success_url = reverse_lazy('business_list')

class BusinessUpdateView(LoginRequiredMixin, UpdateView):
    model = Business
    form_class = BusinessForm
    template_name = 'business/form.html'

    def form_valid(self, form):
        messages.success(self.request, "Empresa alterada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('business_update', kwargs={'pk': self.object.pk})

class BusinessDeleteView(LoginRequiredMixin, DeleteView):
    model = Business
    template_name = 'business/confirm_delete.html'
    success_url = reverse_lazy('business_list')

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from .models import User, Business
from .forms import CustomUserCreationForm

class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'users/list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.filter(
            business=self.request.user.business
        )
    
class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.business = self.request.user.business  # 🔥 vincula automaticamente
        user.plan = self.request.user.business.plan  # opcional
        user.save()
        return super().form_valid(form)


class NcmListView(LoginRequiredMixin, ListView):
    model = NCM
    template_name = 'ncm/list.html'
    context_object_name = 'ncms'

    def get_queryset(self):
        return NCM.objects.filter(
            business=self.request.user.business
        ).order_by('code')


class NcmCreateView(LoginRequiredMixin, CreateView):
    model = NCM
    fields = ['category', 'code', 'description', 'cest', 'mono']
    template_name = 'ncm/form.html'
    success_url = reverse_lazy('ncm_list')

    def form_valid(self, form):
        ncm = form.save(commit=False)
        ncm.business = self.request.user.business
        ncm.save()
        messages.success(self.request, "NCM cadastrado com sucesso.")
        return super().form_valid(form)

class NcmUpdateView(LoginRequiredMixin, UpdateView):
    model = NCM
    fields = ['category', 'code', 'description', 'cest', 'mono']
    template_name = 'ncm/form.html'
    success_url = reverse_lazy('ncm_list')

    def get_queryset(self):
        return NCM.objects.filter(
            business=self.request.user.business
        )

    def form_valid(self, form):
        messages.success(self.request, "NCM alterado com sucesso.")
        return super().form_valid(form)


class NcmDeleteView(LoginRequiredMixin, DeleteView):
    model = NCM
    template_name = 'ncm/confirm_delete.html'
    success_url = reverse_lazy('ncm_list')

    def get_queryset(self):
        return NCM.objects.filter(
            business=self.request.user.business
        )

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "NCM excluído com sucesso.")
        return super().delete(request, *args, **kwargs)
    
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages

from .models import NCMGroup, NCMGroupItem, FiscalOperation
from .forms import NCMGroupForm, NCMGroupItemForm, FiscalOperationForm


# ===============================
# NCM GROUP
# ===============================

class NCMGroupListView(LoginRequiredMixin, ListView):
    model = NCMGroup
    template_name = 'fiscal/ncm_group_list.html'

    def get_queryset(self):
        return NCMGroup.objects.filter(
            business=self.request.user.business
        )


class NCMGroupCreateView(LoginRequiredMixin, CreateView):
    model = NCMGroup
    form_class = NCMGroupForm
    template_name = 'fiscal/ncm_group_form.html'
    success_url = reverse_lazy('ncm_group_list')

    def form_valid(self, form):
        group = form.save(commit=False)
        group.business = self.request.user.business
        group.save()
        messages.success(self.request, "Grupo criado com sucesso.")
        return redirect(self.success_url)


class NCMGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = NCMGroup
    form_class = NCMGroupForm
    template_name = 'fiscal/ncm_group_form.html'
    success_url = reverse_lazy('ncm_group_list')

    def get_queryset(self):
        return NCMGroup.objects.filter(
            business=self.request.user.business
        )


class NCMGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = NCMGroup
    template_name = 'fiscal/confirm_delete.html'
    success_url = reverse_lazy('ncm_group_list')

    def get_queryset(self):
        return NCMGroup.objects.filter(
            business=self.request.user.business
        )


# ===============================
# GERENCIAR ITENS DO GRUPO
# ===============================

def manage_ncm_group_items(request, pk):
    group = get_object_or_404(
        NCMGroup,
        pk=pk,
        business=request.user.business
    )

    # 🔎 BUSCA
    query = request.GET.get('q', '')

    available_ncms = NCM.objects.all()

    if query:
        available_ncms = available_ncms.filter(
            code__icontains=query
        )

    available_ncms = available_ncms.order_by('code')[:100]

    # 🔥 ADICIONAR NCM
    if request.method == 'POST':
        ncm_id = request.POST.get('ncm_id')

        if ncm_id:
            ncm = get_object_or_404(NCM, id=ncm_id)

            NCMGroupItem.objects.get_or_create(
                group=group,
                ncm=ncm
            )

            messages.success(request, "NCM adicionado.")
            return redirect('ncm_group_items', pk=group.pk)

    return render(request, 'fiscal/ncm_group_items.html', {
        'group': group,
        'available_ncms': available_ncms,
        'query': query
    })

@login_required
def remove_ncm_from_group(request, group_id, ncm_id):
    group = get_object_or_404(
        NCMGroup.objects.prefetch_related("items"),
        pk=group_id,
        business=request.user.business
    )

    item = get_object_or_404(
        NCMGroupItem,
        group=group,
        ncm_id=ncm_id
    )

    item.delete()

    messages.success(request, "NCM removido do grupo com sucesso.")

    return redirect('ncm_group_items', pk=group.pk)

@login_required
def ajax_ncm_search(request):
    query = request.GET.get('q', '')

    ncms = NCM.objects.filter(
        Q(code__icontains=query) |
        Q(description__icontains=query)
    )[:20]

    data = [
        {
            "id": n.id,
            "code": n.code,
            "description": n.description
        }
        for n in ncms
    ]

    return JsonResponse(data, safe=False)

# ===============================
# FISCAL OPERATION
# ===============================

class FiscalOperationListView(LoginRequiredMixin, ListView):
    model = FiscalOperation
    template_name = 'fiscal/operation_list.html'

    def get_queryset(self):
        return FiscalOperation.objects.filter(
            business=self.request.user.business
        )


class FiscalOperationCreateView(LoginRequiredMixin, CreateView):
    model = FiscalOperation
    form_class = FiscalOperationForm
    template_name = 'fiscal/operation_form.html'
    success_url = reverse_lazy('operation_list')

    def form_valid(self, form):
        operation = form.save(commit=False)
        operation.business = self.request.user.business
        operation.save()
        messages.success(self.request, "Operação criada com sucesso.")
        return redirect(self.success_url)


class FiscalOperationUpdateView(LoginRequiredMixin, UpdateView):
    model = FiscalOperation
    form_class = FiscalOperationForm
    template_name = 'fiscal/operation_form.html'
    success_url = reverse_lazy('operation_list')

    def get_queryset(self):
        return FiscalOperation.objects.filter(
            business=self.request.user.business
        )

    def form_valid(self, form):
        messages.success(self.request, "Operação atualizada com sucesso.")
        return super().form_valid(form)


class FiscalOperationDeleteView(LoginRequiredMixin, DeleteView):
    model = FiscalOperation
    template_name = 'fiscal/confirm_delete.html'
    success_url = reverse_lazy('operation_list')

    def get_queryset(self):
        return FiscalOperation.objects.filter(
            business=self.request.user.business
        )
    from django.contrib import messages

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Operação excluída com sucesso.")
        return super().delete(request, *args, **kwargs)