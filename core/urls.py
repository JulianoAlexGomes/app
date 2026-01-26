from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import (
    CustomLoginView,
    client_list,
    client_create,
    client_update,
    client_delete,
    sizechart_list,
    sizechart_create,
    sizechart_update,
    sizechart_delete,
    colorchart_list,
    colorchart_create,
    colorchart_update,
    colorchart_delete,
    modelchart_list,
    modelchart_create,
    modelchart_update,
    modelchart_delete,
    product_list,
    product_create,
    product_update,
    product_delete,
    stock_movement,
    stock_entry_delete,
    order_list,
    order_create,
    order_update,
    order_delete,
    home,
    # check_stock,
    order_change_status,
    # upload_product_image,
    order_advance_status,
    order_cancel,
)

urlpatterns = [
    
    # Login/Logout
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Página inicial
    path('', home, name='home'),

    # Cadastro de Clientes
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
        # Upload de Imagens de Produtos
        # path('products/<int:product_id>/upload-image/', upload_product_image, name='upload_product_image'),

    # Movimentações de Estoque
    path('products/<int:product_id>/stock/', stock_movement, name='stock_movement'),
    path('stock-entry/<int:pk>/delete/',stock_entry_delete, name='stock_entry_delete'),

    # Pedidos (Orders) - To be implemented
    path('pedidos/', order_list, name='order_list'),
    path('pedidos/novo/', order_create, name='order_create'),
    path('pedidos/<int:pk>/editar/', order_update, name='order_update'),
    path('pedidos/<int:pk>/excluir/', order_delete, name='order_delete'),
    path('pedidos/<int:order_id>/status/',order_change_status,name='order_change_status'),
    path('pedidos/<int:order_id>/avancar/', order_advance_status, name='order_advance_status'),
    path('pedidos/<int:order_id>/cancelar/', order_cancel, name='order_cancel'),


]