import uuid
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser
from django.db.models import Sum

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Business(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    document = models.CharField(max_length=20, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('user', 'Usuário'),
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user'
    )

    plan = models.ForeignKey(
    Plan,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)


    def __str__(self):
        return self.username


class Client(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='clients'
    )

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    document = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Sizechart(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='sizecharts'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class colorchart(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='colorcharts'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class modelchart(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='modelcharts'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(Business,on_delete=models.CASCADE,related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)  
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.ForeignKey(modelchart,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
    size = models.ForeignKey(Sizechart,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
    color = models.ForeignKey(colorchart,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
    ean13 = models.CharField(max_length=13, blank=True)

    @property
    def stock_real(self):
        entrada = self.stock_entries.filter(entry_type='in').aggregate(
            total=Sum('quantity')
        )['total'] or 0

        saida = self.stock_entries.filter(entry_type='out').aggregate(
            total=Sum('quantity')
        )['total'] or 0

        print(f"---------------------")
        print(f"Entrada:{entrada}")
        print(f"Saida:{saida}")
        return entrada - saida

    @property
    def stock_reserved(self):
        reservado = self.stock_entries.filter(
            movement_type='RESERVE',
        ).aggregate(total=Sum('quantity'))['total'] or 0

        liberado = self.stock_entries.filter(
            movement_type='RELEASE'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        print(f"---------------------")
        print(f"Reservado:{reservado}")
        print(f"Liberado:{liberado}")

        return reservado - liberado
        

    @property
    def stock_available(self):
        return self.stock_real 

    
class ProductImage(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image = models.ImageField(upload_to='product_images/')
    descriotion = models.CharField(max_length=255, blank=True)
    colorchart = models.ForeignKey(colorchart,on_delete=models.SET_NULL,null=True,blank=True,related_name='product_images')
    modelchart = models.ForeignKey(modelchart,on_delete=models.SET_NULL,null=True,blank=True,related_name='product_images')
    sizechart = models.ForeignKey(Sizechart,on_delete=models.SET_NULL,null=True,blank=True,related_name='product_images')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"
    
# class StockEntry(models.Model):
#     ENTRY_TYPE_CHOICES = (
#         ('in', 'Entrada'),
#         ('out', 'Saída'),
#     )

#     product = models.ForeignKey(
#         Product,
#         on_delete=models.CASCADE,
#         related_name='stock_entries'
#     )
#     entry_type = models.CharField(
#         max_length=3,
#         choices=ENTRY_TYPE_CHOICES
#     )
#     quantity = models.IntegerField()
#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.entry_type} - {self.product.name} - {self.quantity}"

class StockEntry(models.Model):
    class MovementType(models.TextChoices):
        INITIAL = 'INITIAL', 'Estoque Inicial'
        RESERVE = 'RESERVE', 'Reserva'
        RELEASE = 'RELEASE', 'Liberação de Reserva'
        SALE = 'SALE', 'Saída por Venda'
        ADJUST = 'ADJUST', 'Ajuste Manual'

    ENTRY_TYPE_CHOICES = (
        ('in', 'Entrada'),
        ('out', 'Saída'),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_entries'
    )

    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='stock_entries',
        null=True,
        blank=True
    )

    entry_type = models.CharField(
        max_length=3,
        choices=ENTRY_TYPE_CHOICES
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices
    )

    quantity = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} | "
            f"{self.product.name} | "
            f"{self.entry_type} {self.quantity}"
        )


class Orders(models.Model):
    STATUS_DIGITACAO = 'DIGITACAO'
    STATUS_ORCAMENTO = 'ORCAMENTO'
    STATUS_EM_SEPARACAO = 'EM_SEPARACAO'
    STATUS_SEPARADO = 'SEPARADO'
    STATUS_FATURADO = 'FATURADO'
    STATUS_CANCELADO = 'CANCELADO'

    STATUS_CHOICES = [
        (STATUS_DIGITACAO, 'Em Digitação'),
        (STATUS_ORCAMENTO, 'Orçamento'),
        (STATUS_EM_SEPARACAO, 'Em Separação'),
        (STATUS_SEPARADO, 'Separado'),
        (STATUS_FATURADO, 'Faturado'),
        (STATUS_CANCELADO, 'Cancelado'),
    ]

    # 🔒 REGRAS DE TRANSIÇÃO
    STATUS_TRANSITIONS = {
        STATUS_DIGITACAO: [
            STATUS_ORCAMENTO,
            STATUS_EM_SEPARACAO,
            STATUS_CANCELADO,
        ],
        STATUS_ORCAMENTO: [
            STATUS_EM_SEPARACAO,
            STATUS_CANCELADO,
        ],
        STATUS_EM_SEPARACAO: [
            STATUS_SEPARADO,
            STATUS_CANCELADO,
        ],
        STATUS_SEPARADO: [
            STATUS_FATURADO,
            STATUS_CANCELADO,
        ],
    }

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='orders')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DIGITACAO)
    created_at = models.DateTimeField(auto_now_add=True)

    def can_change_status_to(self, new_status):
        return new_status in self.STATUS_TRANSITIONS.get(self.status, [])
    
    def next_status(self):
        transitions = self.STATUS_TRANSITIONS.get(self.status, [])
        for status in transitions:
            if status != self.STATUS_CANCELADO:
                return status
        return None




class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    addition = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    reserved = models.BooleanField(default=False)  # 🔥 CONTROLE

    @property
    def subtotal(self):
        return (self.quantity * self.price) - self.discount + self.addition

# class StockReservation(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     quantity = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)
