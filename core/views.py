from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Client, Sizechart, colorchart, modelchart, Product, StockEntry, Orders, OrderItem, Business
from django.contrib.auth.views import LoginView
from .forms import ClientForm, SizechartForm, colorchartForm, modelchartForm, ProductForm, StockEntryForm, OrderForm, OrderItemFormSet
from django.shortcuts import redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from .services.order_stock import reserve_stock, release_stock, finalize_stock
from django.core.exceptions import ValidationError

def home(request):
    return render(request, 'auth/home.html')

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'

    def get_success_url(self):
        return '/clientes/'

@login_required
def client_list(request):
    search = request.GET.get('q', '')

    clients = Client.objects.filter(
        business=request.user.business,
        name__icontains=search
    ).order_by('name')

    paginator = Paginator(clients, 10)
    page = request.GET.get('page')
    clients = paginator.get_page(page)

    return render(request, 'clients/list.html', {
        'clients': clients,
        'search': search
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

@login_required
def client_update(request, pk):
    client = get_object_or_404(
        Client,
        pk=pk,
        business=request.user.business
    )

    form = ClientForm(request.POST or None, instance=client)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('client_list')

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

    if request.method == 'POST' and form.is_valid():
        sizechart = form.save(commit=False)
        sizechart.business = request.user.business
        sizechart.save()
        return redirect('sizechart_list')

    return render(request, 'sizecharts/form.html', {
        'form': form
    })
@login_required
def sizechart_update(request, pk):
    sizechart = get_object_or_404(
        Sizechart,
        pk=pk,
        business=request.user.business
    )

    form = SizechartForm(request.POST or None, instance=sizechart)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('sizechart_list')

    return render(request, 'sizecharts/form.html', {
        'form': form,
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

@login_required
def product_list(request):
    search = request.GET.get('q', '')

    products = Product.objects.filter(
        business=request.user.business,
        name__icontains=search
    ).order_by('name')

    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    return render(request, 'products/list.html', {
        'products': products,
        'search': search
    })

@login_required
def product_create(request):
    form = ProductForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.business = request.user.business
        product.save()
        return redirect('product_list')

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

    form = ProductForm(request.POST or None, instance=product)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('product_list')

    return render(request, 'products/form.html', {
        'form': form,
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
def stock_movement(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        business=request.user.business
    )

    movements = StockEntry.objects.filter(
        product=product
    ).order_by('-timestamp')

    paginator = Paginator(movements, 10)
    page = request.GET.get('page')
    movements = paginator.get_page(page)

    form = StockEntryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.product = product
        entry.save()

        # 🚫 NÃO atualiza Product
        # 🚫 NÃO existe mais product.storage

        return redirect('stock_movement', product_id=product.id)

    return render(request, 'stock/movement.html', {
        'product': product,
        'movements': movements,
        'form': form
    })

@login_required
def stock_entry_delete(request, pk):
    entry = get_object_or_404(
        StockEntry,
        pk=pk,
        product__business=request.user.business
    )

    product = entry.product

    if request.method == 'POST':
        # 🚫 NÃO estorna no Product
        entry.delete()

        return redirect('stock_movement', product_id=product.id)

    return render(request, 'stock/delete.html', {
        'entry': entry
    })

@login_required
@transaction.atomic
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.business = request.user.business
            order.total_amount = 0
            order.save()

            messages.success(request, 'Pedido criado. Agora inclua os itens.')
            return redirect('order_update', order.id)
    else:
        form = OrderForm()

    return render(request, 'orders/form_create.html', {
        'form': form,
        'title': 'Novo Pedido'
    })

@login_required
def order_list(request):
    orders = Orders.objects.filter(business=request.user.business).order_by('-created_at')

    return render(request, 'orders/list.html', {
        'orders': orders
    })

@login_required
@transaction.atomic
def order_update(request, pk):
    order = get_object_or_404(
        Orders,
        pk=pk,
        business=request.user.business
    )

    if request.method == 'POST':
        print('POST DATA:', dict(request.POST))
        form = OrderForm(request.POST, instance=order)
        formset = OrderItemFormSet(
            request.POST,
            instance=order,
            prefix='items'
        )

        if form.is_valid() and formset.is_valid():
            print('FORMS COUNT:', len(formset.forms))

            for i, f in enumerate(formset.forms):
                print(f'--- FORM {i} ---')
                print('has_changed:', f.has_changed())
                print('cleaned_data:', f.cleaned_data)
                print('instance.pk BEFORE:', f.instance.pk)

            form.save()

            total = 0

            for form_item in formset.forms:
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

            messages.success(request, 'Pedido atualizado com sucesso!')
            return redirect('order_update', order.id)

        else:
            print('FORM ERRORS:', form.errors)
            print('FORMSET ERRORS:', formset.errors)
            print('NON FORM ERRORS:', formset.non_form_errors())
            messages.error(request, 'Erro ao salvar itens do pedido.')

    else:
        form = OrderForm(instance=order)
        formset = OrderItemFormSet(
            instance=order,
            prefix='items'
        )

    return render(request, 'orders/form_update.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'products': Product.objects.filter(
            business=request.user.business
        ),
        'title': 'Editar Pedido'
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

        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(
            request,
            f'Status alterado para {order.get_status_display()}'
        )

    except ValidationError as e:
        messages.error(request, e.message)

    return redirect('order_update', order.id)

#@login_required
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

    if order.status == Orders.STATUS_FATURADO:
        for item in order.items.select_related('product'):
            StockEntry.objects.create(
                product=item.product,
                order_item=item,
                entry_type='in',    
                movement_type=StockEntry.MovementType.RELEASE,
                quantity=item.quantity
        )

    try:
        # Se tiver reserva → libera
        release_stock(order)

        order.status = Orders.STATUS_CANCELADO
        order.save(update_fields=['status'])

        messages.success(request, 'Pedido cancelado com sucesso.')

    except ValidationError as e:
        messages.error(request, e.message)

    return redirect('order_update', order.id)
