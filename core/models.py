import uuid
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.utils import timezone

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Business(models.Model):

    REGIME_CHOICES = (
        (1, 'Simples Nacional'),
        (2, 'Simples Nacional - Excesso Sublimite'),
        (3, 'Regime Normal'),
    )

    AMBIENTE_CHOICES = (
        (1, 'Produção'),
        (2, 'Homologação'),
    )

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # =============================
    # DADOS EMPRESA
    # =============================
    name = models.CharField(max_length=255)  # Razão Social
    fantasy_name = models.CharField(max_length=255, blank=True, null=True)
    document = models.CharField(max_length=18, unique=True)  # CNPJ
    state_registration = models.CharField(max_length=20, default=1)  # IE
    municipal_registration = models.CharField(max_length=20, blank=True, null=True)

    tax_regime = models.IntegerField(choices=REGIME_CHOICES, default=1)

    # =============================
    # ENDEREÇO
    # =============================
    street = models.CharField(max_length=255, default=1)
    number = models.CharField(max_length=20, default=1)
    complement = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, default=1)
    city = models.CharField(max_length=100, default=1)
    city_code = models.CharField(max_length=10, default=1) 
    state = models.CharField(max_length=2, default=1)
    zip_code = models.CharField(max_length=9, default=1)
    country_code = models.CharField(max_length=4, default='1058', editable=False)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # =============================
    # CONFIG GERAL
    # =============================
    nfe_environment = models.IntegerField(
        choices=AMBIENTE_CHOICES,
        default=2
    )

    # NF-e
    nfe_series = models.CharField(max_length=3, default='1')
    nfe_last_number = models.PositiveIntegerField(default=0)

    # NFC-e
    nfce_series = models.CharField(max_length=3, default='1')
    nfce_last_number = models.PositiveIntegerField(default=0)

    # =============================
    # CSC (NFC-e)
    # =============================
    nfce_csc = models.CharField(max_length=255, blank=True, null=True)
    nfce_csc_id = models.CharField(max_length=10, blank=True, null=True)

    # =============================
    # CERTIFICADO DIGITAL A1
    # =============================
    certificate_file = models.FileField(
        upload_to='certificates/',
        blank=True,
        null=True
    )

    certificate_password = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    certificate_expiration = models.DateField(
        blank=True,
        null=True
    )

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    plan = models.ForeignKey('Plan', on_delete=models.SET_NULL, null=True, blank=True)

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
    uid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='clients'
    )

    # ─────────────────────────────────────────────
    # 🧾 IDENTIFICAÇÃO
    # ─────────────────────────────────────────────
    name = models.CharField(
        'Nome / Razão Social',
        max_length=255
    )

    supplier = models.BooleanField(
        'Fornecedor',
        default=False
    )

    fantasy_name = models.CharField(
        'Nome Fantasia',
        max_length=255,
        blank=True,
        null=True
    )

    document = models.CharField(
        'CPF / CNPJ',
        max_length=20
    )

    state_registration = models.CharField(
        'Inscrição Estadual',
        max_length=20,
        blank=True,
        null=True,
        help_text='Deixe em branco se ISENTO'
    )

    is_exempt = models.BooleanField(
        'Isento de Inscrição Estadual',
        default=False
    )

    # ─────────────────────────────────────────────
    # 📍 ENDEREÇO (OBRIGATÓRIO NA NF-e)
    # ─────────────────────────────────────────────
    zip_code = models.CharField(
        'CEP',
        max_length=9,
        blank=True,
        null=True
    )

    street = models.CharField(
        'Logradouro',
        max_length=255,
        blank=True,
        null=True
    )

    number = models.CharField(
        'Número',
        max_length=20,
        blank=True,
        null=True
    )

    complement = models.CharField(
        'Complemento',
        max_length=100,
        blank=True,
        null=True
    )

    neighborhood = models.CharField(
        'Bairro',
        max_length=100,
        blank=True,
        null=True
    )

    city = models.CharField(
        'Cidade',
        max_length=100,
        blank=True,
        null=True
    )

    state = models.CharField(
        'UF',
        max_length=2,
        blank=True,
        null=True
    )

    city_ibge = models.CharField(
        'Código IBGE do Município',
        max_length=7,
        blank=True,
        null=True
    )

    country = models.CharField(
        'País',
        max_length=50,
        default='Brasil'
    )

    country_ibge = models.CharField(
        'Código do País',
        max_length=4,
        default='1058'  # Brasil
    )

    # ─────────────────────────────────────────────
    # 📞 CONTATO
    # ─────────────────────────────────────────────
    email = models.EmailField(
        blank=True,
        null=True
    )

    phone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True,
        null=True
    )

    # ─────────────────────────────────────────────
    # 💰 DADOS FISCAIS (ICMS)
    # ─────────────────────────────────────────────
    taxpayer_type = models.CharField(
        'Tipo de Contribuinte ICMS',
        max_length=1,
        choices=[
            ('1', 'Contribuinte ICMS'),
            ('2', 'Isento'),
            ('9', 'Não Contribuinte'),
        ],
        default='9'
    )

    # ─────────────────────────────────────────────
    # 🕒 CONTROLE
    # ─────────────────────────────────────────────
    created_at = models.DateTimeField(
        auto_now_add=True
    )

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
    
class Sizes(models.Model):
    sizechart = models.ForeignKey(
        Sizechart,
        on_delete=models.CASCADE,
        related_name='sizes'
    )

    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('sizechart', 'name')
        ordering = ['order', 'id']  # 🔥 garante ordem correta

    def __str__(self):
        return f"{self.sizechart.name} - {self.name}"
    
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
    business = models.ForeignKey(Business,on_delete=models.CASCADE,related_name='modelcharts')
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

    # 🔥 FISCAL
    ncm = models.ForeignKey('NCM', on_delete=models.SET_NULL, null=True, blank=True)
    cest = models.CharField(max_length=7, blank=True, null=True)

    cfop_default = models.CharField(max_length=4)

    origin = models.CharField(
        max_length=1,
        choices=[
            ('0', 'Nacional'),
            ('1', 'Estrangeira - Importação Direta'),
            ('2', 'Estrangeira - Mercado Interno'),
            ('3', 'Nacional com Conteúdo Importação > 40%'),
            ('4', 'Nacional conforme processos produtivos'),
            ('5', 'Nacional Conteúdo Importação <= 40%'),
            ('6', 'Estrangeira - Importação Direta sem similar'),
            ('7', 'Estrangeira - Mercado Interno sem similar'),
        ],
        default='0'
    )

    @property
    def stock_real(self):
        return sum(v.stock_real for v in self.variants.all())

    @property
    def stock_reserved(self):
        return sum(v.stock_reserved for v in self.variants.all())

    @property
    def stock_available(self):
        return sum(v.stock_available for v in self.variants.all())


class ProductVariant(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='variants')
    size = models.ForeignKey(Sizes,on_delete=models.SET_NULL,null=True,blank=True)
    color = models.ForeignKey(colorchart,on_delete=models.SET_NULL,null=True,blank=True)
    sku = models.CharField(max_length=100, blank=True, db_index=True)
    ean13 = models.CharField(max_length=13, unique=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'size', 'color')

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"

    # 🔥 ESTOQUE REAL POR VARIANTE
    @property
    def stock_real(self):
        entrada = self.stock_entries.filter(entry_type='in').aggregate(
            total=Sum('quantity')
        )['total'] or 0

        saida = self.stock_entries.filter(entry_type='out').aggregate(
            total=Sum('quantity')
        )['total'] or 0

        return entrada - saida

    @property
    def stock_reserved(self):
        reservado = self.stock_entries.filter(
            movement_type='RESERVE'
        ).aggregate(total=Sum('quantity'))['total'] or 0

        liberado = self.stock_entries.filter(
            movement_type='RELEASE'
        ).aggregate(total=Sum('quantity'))['total'] or 0

        return reservado - liberado

    @property
    def stock_available(self):
        return self.stock_real - self.stock_reserved


class ProductImage(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image = models.ImageField(upload_to='product_images/')
    description = models.CharField(max_length=255, blank=True)
    # colorchart = models.ForeignKey(colorchart,on_delete=models.SET_NULL,null=True,blank=True,related_name='product_images')
    # modelchart = models.ForeignKey(modelchart,on_delete=models.SET_NULL,null=True,blank=True,related_name='product_images')
    # sizechart = models.ForeignKey(Sizechart,on_delete=models.SET_NULL,null=True,blank=True,related_name='product_images')
    order = models.PositiveIntegerField(default=0)  # 👈 sequência/tab
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - imagem {self.order}"


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
    variant = models.ForeignKey(ProductVariant,on_delete=models.CASCADE,related_name='stock_entries')
    order_item = models.ForeignKey('OrderItem',on_delete=models.CASCADE,related_name='stock_entries',null=True,blank=True)
    entry_type = models.CharField(max_length=3,choices=ENTRY_TYPE_CHOICES,null=True,blank=True)
    movement_type = models.CharField(max_length=20,choices=MovementType.choices)
    quantity = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} | "
            f"{self.product.name} | "
            f"{self.entry_type} {self.quantity}"
        )

from decimal import Decimal

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

    # 🔥 CONFIG NOTA
    document_model = models.CharField(
        max_length=2,
        choices=[
            ('55', 'NF-e'),
            ('65', 'NFC-e'),
        ],
        blank=True,
        null=True
    )

    nature_operation = models.CharField(max_length=255, blank=True, null=True)
    cfop = models.CharField(max_length=4, blank=True, null=True)

    issue_datetime = models.DateTimeField(blank=True, null=True)

    freight_mode = models.CharField(
        max_length=1,
        choices=[
            ('0', 'Contratação do Frete por conta do Remetente'),
            ('1', 'Contratação do Frete por conta do Destinatário'),
            ('2', 'Por conta de Terceiros'),
            ('9', 'Sem Frete'),
        ],
        default='9'
    )

    finality = models.CharField(
        max_length=1,
        choices=[
            ('1', 'NF-e Normal'),
            ('2', 'Complementar'),
            ('3', 'Ajuste'),
            ('4', 'Devolução'),
        ],
        default='1'
    )

    presence_indicator = models.CharField(
        max_length=1,
        choices=[
            ('0', 'Não se aplica'),
            ('1', 'Operação Presencial'),
            ('2', 'Internet'),
            ('3', 'Teleatendimento'),
            ('9', 'Outros'),
        ],
        default='1'
    )

    access_key = models.CharField(max_length=44, blank=True, null=True)
    protocol = models.CharField(max_length=50, blank=True, null=True)
    xml = models.TextField(blank=True, null=True)

    nfe_number = models.PositiveIntegerField(blank=True, null=True)
    nfe_series = models.CharField(max_length=3, blank=True, null=True)

    def can_change_status_to(self, new_status):
        return new_status in self.STATUS_TRANSITIONS.get(self.status, [])

    def next_status(self):
        transitions = self.STATUS_TRANSITIONS.get(self.status, [])
        for status in transitions:
            print(f"Checking if can transition from {self.status} to {status}")
            if status != self.STATUS_CANCELADO:
                return status
        return None

    def can_edit(self):
        return self.status in [
            self.STATUS_DIGITACAO,
            self.STATUS_ORCAMENTO,
        ]

    def generate_financial(self):
        # 🔒 evita duplicar
        if self.financial_movements.exists():
            return

        for payment in self.payments.all():

            movement = FinancialMovement.objects.create(
                business=self.business,
                client=self.client,
                order=self,
                bank=payment.bank,
                payment_method=payment.payment_method,
                type='in',
                total_value=payment.total_value,
                description=f'Pedido #{self.id}'
            )

            for parcel in payment.parcels_records.all():
                FinancialMovementParcel.objects.create(
                    movement=movement,
                    parcel=parcel.parcel_number,
                    value=parcel.value,
                    deadline=parcel.due_date
                )

    # 🔥 HOOK AUTOMÁTICO AO FATURAR
    def save(self, *args, **kwargs):
        old_status = None

        if self.pk:
            old_status = Orders.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        if old_status != self.STATUS_FATURADO and self.status == self.STATUS_FATURADO:
            self.generate_financial()


class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant,on_delete=models.SET_NULL,null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    addition = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reserved = models.BooleanField(default=False)  # 🔥 CONTROLE

    # 🔥 DADOS FISCAIS FIXADOS NO MOMENTO DA VENDA
    cfop = models.CharField(max_length=4, blank=True, null=True)
    ncm = models.CharField(max_length=8, blank=True, null=True)

    # ICMS
    icms_cst = models.CharField(max_length=3, blank=True, null=True)
    icms_csosn = models.CharField(max_length=3, blank=True, null=True)
    icms_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    icms_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    icms_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # PIS
    pis_cst = models.CharField(max_length=2, blank=True, null=True)
    pis_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pis_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # COFINS
    cofins_cst = models.CharField(max_length=2, blank=True, null=True)
    cofins_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cofins_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return (self.quantity * self.price) - self.discount + self.addition

class BankAccount(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bank_accounts')
    name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    agency_number = models.CharField(max_length=20)
    account_number = models.CharField(max_length=20)

    @property
    def calculated_balance(self):
        entries = FinancialMovementParcel.objects.filter(
            movement__bank=self,
            movement__type='in',
            payed=True
        ).aggregate(total=Sum('value'))['total'] or 0

        exits = FinancialMovementParcel.objects.filter(
            movement__bank=self,
            movement__type='out',
            payed=True
        ).aggregate(total=Sum('value'))['total'] or 0

        return entries - exits

    def __str__(self):
        return f"{self.name} - {self.bank_name} ({self.account_number})"

class PaymentMethod(models.Model):
    
    TYPE_CHOICES = (
        (1, 'Dinheiro'),
        (2, 'Cheque'),
        (3, 'Cartão de Crédito'),
        (4, 'Cartão de Débito'),
        (5, 'Crédito Loja'),
        (10, 'Vale Alimentação'),
        (11, 'Vale Refeição'),
        (12, 'Vale Presente'),
        (13, 'Vale Combustível'),
        (14, 'Duplica'),
        (15, 'Boleto Bancário'),
        (16, 'Depósito Bancário'),
        (17, 'PIX'),
        (90, 'Sem Pagamento'),
        (99, 'Outros') 
    )

    business = models.ForeignKey(Business,on_delete=models.CASCADE,related_name='payment_methods')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10,choices=[('in', 'Entrada'), ('out', 'Saída')])
    default_bank = models.ForeignKey(BankAccount,on_delete=models.SET_NULL,null=True,blank=True)
    default_parcels = models.IntegerField(default=1)
    interval_days = models.IntegerField(default=30) 
    active = models.BooleanField(default=True)
    payment_type = models.IntegerField(choices=TYPE_CHOICES, default=1)

    def __str__(self):
        return self.name


class FinancialMovement(models.Model):
    business = models.ForeignKey(Business,on_delete=models.CASCADE,related_name='financial_movements')
    client = models.ForeignKey(Client,on_delete=models.SET_NULL,null=True,blank=True,related_name='financial_movements')
    order = models.ForeignKey(Orders,on_delete=models.CASCADE,related_name='financial_movements',null=True,blank=True)
    bank = models.ForeignKey(BankAccount,on_delete=models.SET_NULL,null=True,blank=True,related_name='financial_movements')
    payment_method = models.ForeignKey(PaymentMethod,on_delete=models.SET_NULL,null=True,blank=True,related_name='movements')
    type = models.CharField(max_length=10,
        choices=[('in', 'Entrada'), ('out', 'Saída')]
        )
    total_value = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - {self.total_value}"

    
class FinancialMovementParcel(models.Model):
    movement = models.ForeignKey(FinancialMovement, on_delete=models.CASCADE, related_name='parcels')
    parcel = models.IntegerField()  # número da parcela (1, 2, 3, ...)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    addition = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deadline = models.DateField()
    paydate = models.DateField(null=True, blank=True)
    payed = models.BooleanField(default=False)

    @property
    def subtotal(self):
        return self.value - self.discount + self.addition

from decimal import Decimal

from decimal import Decimal

class OrderPayment(models.Model):
    order = models.ForeignKey(
        Orders,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, null=True, blank=True)
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True)

    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parcels = models.PositiveIntegerField(default=1)
    interval_days = models.PositiveIntegerField(default=30)

    def generate_parcels(self):
        if self.parcels_records.exists():
            return

        total = Decimal(self.total_value)
        parcels = self.parcels

        base_value = (total / parcels).quantize(Decimal('0.01'))
        accumulated = Decimal('0.00')

        for i in range(parcels):

            if i == parcels - 1:
                value = total - accumulated
            else:
                value = base_value
                accumulated += base_value

            due_date = timezone.now().date() + timedelta(days=i * self.interval_days)

            OrderPaymentParcel.objects.create(
                payment=self,
                parcel_number=i + 1,
                value=value,
                due_date=due_date
            )

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating:
            self.generate_parcels()

class OrderPaymentParcel(models.Model):
    payment = models.ForeignKey(
        OrderPayment,
        on_delete=models.CASCADE,
        related_name='parcels_records'
    )

    parcel_number = models.PositiveIntegerField()
    value = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['parcel_number']

def calcular_digito_ean13(ean_base):
    soma = 0
    for i, num in enumerate(ean_base):
        num = int(num)
        if (i % 2) == 0:
            soma += num
        else:
            soma += num * 3

    resto = soma % 10
    return 0 if resto == 0 else 10 - resto


def generate_sku(variant):
    business_id = variant.product.business.id
    product_id = variant.product.id
    size_id = variant.size.id if variant.size else 0
    color_id = variant.color.id if variant.color else 0

    return f"B{business_id}P{product_id}S{size_id}C{color_id}"


def generate_ean13(variant):
    base = (
        "1" +
        str(variant.product.id).zfill(6) +
        str(variant.id).zfill(5)
    )

    base = base[:12]

    digito = calcular_digito_ean13(base)
    return base + str(digito)

class NCM(models.Model):
    category = models.TextField()
    code = models.CharField(max_length=8, unique=True)
    description = models.TextField()
    cest = models.CharField(max_length=7, blank=True, null=True)
    mono = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.description}"
    
class NCMGroup(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='ncm_groups'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class NCMGroupItem(models.Model):
    group = models.ForeignKey(
        NCMGroup,
        on_delete=models.CASCADE,
        related_name='items'
    )

    ncm = models.ForeignKey(
        NCM,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('group', 'ncm')

from django.db import models

class ICMSOriginDestination(models.Model):

    origin_state = models.CharField(
        max_length=2,
        verbose_name="UF Origem"
    )

    destination_state = models.CharField(
        max_length=2,
        verbose_name="UF Destino"
    )

    imported = models.BooleanField(
        default=False,
        verbose_name="Produto Importado (4%)"
    )

    interstate_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Alíquota Interestadual (%)"
    )

    internal_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Alíquota Interna Destino (%)"
    )

    class Meta:
        db_table = "core_icmsorigindestination"
        unique_together = (
            "origin_state",
            "destination_state",
            "imported"
        )
        verbose_name = "ICMS Origem/Destino"
        verbose_name_plural = "ICMS Origem/Destino"

    def __str__(self):
        tipo = "Importado" if self.imported else "Nacional"
        return f"{self.origin_state} → {self.destination_state} ({tipo})"

class FiscalOperation(models.Model):

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='fiscal_operations'
    )

    name = models.CharField(max_length=255)

    model = models.CharField(
        max_length=2,
        choices=[
            ('55', 'NF-e'),
            ('65', 'NFC-e'),
        ]
    )

    cfop = models.CharField(max_length=4)

    ncm_group = models.ForeignKey(
        NCMGroup,
        on_delete=models.CASCADE
    )

    # ICMS
    icms_cst = models.CharField(max_length=3, blank=True, null=True)
    icms_csosn = models.CharField(max_length=3, blank=True, null=True)

    calculate_icms = models.BooleanField(default=True)
    use_origin_destination_table = models.BooleanField(default=True)

    # PIS
    pis_cst = models.CharField(max_length=2, blank=True, null=True)
    pis_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # COFINS
    cofins_cst = models.CharField(max_length=2, blank=True, null=True)
    cofins_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.cfop} - {self.name}"