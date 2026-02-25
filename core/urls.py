from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import NCM

urlpatterns = [
    
    # Login/Logout
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Página inicial
    path('', home, name='home'),

    # Cadastro de Clientes / Fornecedores
    path('clientes/', client_list, name='client_list'),
    path('clientes/novo/', client_create, name='client_create'),
    path('clientes/<int:pk>/editar/', client_update, name='client_update'),
    path('clientes/<int:pk>/excluir/', client_delete, name='client_delete'),

    # Cadastro de Tamanhos
    path('tamanhos/', sizechart_list, name='sizechart_list'),
    path('tamanhos/novo/', sizechart_create, name='sizechart_create'),
    path('tamanhos/<int:pk>/editar/', sizechart_update, name='sizechart_update'),
    path('tamanhos/<int:pk>/excluir/', sizechart_delete, name='sizechart_delete'),

    # Cadastro de Cores
    path('cores/', colorchart_list, name='colorchart_list'),
    path('cores/novo/', colorchart_create, name='colorchart_create'),
    path('cores/<int:pk>/editar/', colorchart_update, name='colorchart_update'),
    path('cores/<int:pk>/excluir/', colorchart_delete, name='colorchart_delete'),

    # Cadastro de Modelos
    path('modelos/', modelchart_list, name='modelchart_list'),
    path('modelos/novo/', modelchart_create, name='modelchart_create'),
    path('modelos/<int:pk>/editar/', modelchart_update, name='modelchart_update'),
    path('modelos/<int:pk>/excluir/', modelchart_delete, name='modelchart_delete'),

    # Cadastro de Produtos
    path('produtos/', product_list, name='product_list'),
    path('produtos/novo/', product_create, name='product_create'),
    path('produtos/<int:pk>/editar/', product_update, name='product_update'),
    path('produtos/<int:pk>/excluir/', product_delete, name='product_delete'),
    # Imagens de Produtos
    # path('produtos/image/<int:pk>/excluir/',product_image_delete,name='product_image_delete'),
    # path("produtos/<int:pk>/adicionarimagem/",product_image_upload,name="product_image_upload"),
    path("produtos/<int:pk>/imagens/",product_images_json,name='product_images_json'),
    path("produtos/<int:pk>/adicionarimagem/",product_image_upload,name='product_image_upload'),
    path("produtos/imagens/<int:pk>/excluir/",product_image_delete,name='product_image_delete'),

    # Movimentações de Estoque
    path('products/<int:variant_id>/stock/', stock_movement, name='stock_movement'),
    path('stock-entry/<int:pk>/delete/',stock_entry_delete, name='stock_entry_delete'),

    # Pedidos (Orders) - To be implemented
    path('pedidos/', order_list, name='order_list'),
    path('pedidos/novo/', order_create, name='order_create'),
    path('pedidos/<int:pk>/editar/', order_update, name='order_update'),
    path('pedidos/<int:pk>/excluir/', order_delete, name='order_delete'),
    path('pedidos/<int:order_id>/status/',order_change_status,name='order_change_status'),
    path('pedidos/<int:order_id>/avancar/', order_advance_status, name='order_advance_status'),
    path('pedidos/<int:order_id>/cancelar/', order_cancel, name='order_cancel'),
    path('ajax/variants/', ajax_variants, name='ajax_variants'),

    # Bank Accounts
    path('financeiro/bancos/', bank_list, name='bank_list'),
    path('financeiro/bancos/novo/', bank_create, name='bank_create'),
    path('financeiro/bancos/<int:pk>/editar/', bank_update, name='bank_update'),
    path('financeiro/bancos/<int:pk>/excluir/', bank_delete, name='bank_delete'),

    # Payment Methods
    path('financeiro/formas/', paymentmethod_list, name='paymentmethod_list'),
    path('financeiro/formas/nova/', paymentmethod_create, name='paymentmethod_create'),
    path('financeiro/formas/<int:pk>/editar/', paymentmethod_update, name='paymentmethod_update'),
    path('financeiro/formas/<int:pk>/excluir/', paymentmethod_delete, name='paymentmethod_delete'),

    # Financeiro - To be implemented 
    path('financeiro/', financial_list, name='financial_list'),
    path('financeiro/novo/', financial_create, name='financial_create'),
    path('financeiro/<int:pk>/editar/', financial_update, name='financial_update'),
    path('financeiro/<int:pk>/excluir/', financial_delete, name='financial_delete'),
        # Pagamento de parcelas
        path('financeiro/parcela/<int:pk>/pagar/',parcel_pay,name='parcel_pay'),
        path('financeiro/historico/',financial_history,name='financial_history'),

    # Empresa - To be implemented
    path('empresa/', BusinessListView.as_view(), name='business_list'),
    path('empresa/nova/', BusinessCreateView.as_view(), name='business_create'),
    path('empresa/<int:pk>/editar/', BusinessUpdateView.as_view(), name='business_update'),
    path('empresa/<int:pk>/excluir/', BusinessDeleteView.as_view(), name='business_delete'),

    # user profile
    path('usuario/', UserListView.as_view(), name='user_list'),
    path('usuario/novo/', UserCreateView.as_view(), name='user_create'),

    # NCM
    path('ncm/', NcmListView.as_view(), name='ncm_list'),
    path('ncm/novo/', NcmCreateView.as_view(), name='ncm_create'),
    path('ncm/<int:pk>/editar/', NcmUpdateView.as_view(), name='ncm_update'),
    path('ncm/<int:pk>/excluir/', NcmDeleteView.as_view(), name='ncm_delete'),

    # NCM GROUP
    path('fiscal/ncm-grupo/', NCMGroupListView.as_view(), name='ncm_group_list'),
    path('fiscal/ncm-grupo/novo/', NCMGroupCreateView.as_view(), name='ncm_group_create'),
    path('fiscal/ncm-grupo/<int:pk>/editar/', NCMGroupUpdateView.as_view(), name='ncm_group_update'),
    path('fiscal/ncm-grupo/<int:pk>/excluir/', NCMGroupDeleteView.as_view(), name='ncm_group_delete'),
    path('fiscal/ncm-grupo/<int:pk>/itens/', manage_ncm_group_items, name='ncm_group_items'),
    path('fiscal/ncm-grupo/<int:group_id>/remover/<int:ncm_id>/',remove_ncm_from_group,name='remove_ncm_from_group'),
    path('ajax/ncm/search/', ajax_ncm_search, name='ajax_ncm_search'),

    # FISCAL OPERATION
    path('fiscal/operacoes/', FiscalOperationListView.as_view(), name='operation_list'),
    path('fiscal/operacoes/nova/', FiscalOperationCreateView.as_view(), name='operation_create'),
    path('fiscal/operacoes/<int:pk>/editar/', FiscalOperationUpdateView.as_view(), name='operation_update'),
    path('fiscal/operacoes/<int:pk>/excluir/', FiscalOperationDeleteView.as_view(), name='operation_delete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
