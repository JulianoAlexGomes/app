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
        """
        Cria FinancialMovement + FinancialMovementParcel para cada OrderPayment.
        Usa as datas de OrderPaymentParcel (editadas pelo usuário no pedido).
        Idempotente: não duplica se já existir.
        """
        if self.financial_movements.exists():
            return

        for payment in self.payments.prefetch_related('parcels_records').all():

            movement = FinancialMovement.objects.create(
                business=self.business,
                client=self.client,
                order=self,
                bank=payment.bank,
                payment_method=payment.payment_method,
                type='in',
                total_value=payment.total_value,
                description=f'Pedido #{self.id}',
            )

            parcels = payment.parcels_records.all()

            if parcels.exists():
                # Usa as parcelas reais (com datas que o usuário definiu)
                for p in parcels:
                    FinancialMovementParcel.objects.create(
                        movement=movement,
                        parcel=p.parcel_number,
                        value=p.value,
                        deadline=p.due_date,
                    )
            else:
                # Fallback: gera parcelas na hora se por algum motivo não existirem
                from decimal import Decimal
                from datetime import timedelta
                from django.utils import timezone

                total    = Decimal(payment.total_value)
                n        = payment.parcels or 1
                base     = (total / n).quantize(Decimal('0.01'))
                acum     = Decimal('0.00')
                today    = timezone.now().date()

                for i in range(n):
                    is_last = (i == n - 1)
                    value   = (total - acum) if is_last else base
                    if not is_last:
                        acum += base
                    due = today + timedelta(days=(i + 1) * (payment.interval_days or 30))
                    FinancialMovementParcel.objects.create(
                        movement=movement,
                        parcel=i + 1,
                        value=value,
                        deadline=due,
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

    # def save(self, *args, **kwargs):
    #     creating = self.pk is None
    #     super().save(*args, **kwargs)

    #     if creating:
    #         self.generate_parcels()

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

        """
fiscal/models.py

Models de NF-e / NFC-e integrados com o projeto existente.

Referências ao projeto:
  core.Business    → emitente (nfe_last_number, certificate_file, tax_regime, etc.)
  core.Orders      → pedido origem (document_model, nature_operation, freight_mode, etc.)
  core.OrderItem   → itens com campos fiscais já preenchidos por apply_fiscal_rules
  core.OrderPayment → pagamentos com PaymentMethod.payment_type (códigos SEFAZ)
  core.Client      → destinatário com city_ibge, taxpayer_type, etc.

Novos models:
  Invoice          → cabeçalho snapshot da NF (imutável após autorização)
  InvoiceItem      → snapshot dos itens do pedido
  InvoicePayment   → snapshot dos pagamentos
  InvoiceTransport → dados de frete / transportadora
  InvoiceEvent     → cancelamento, carta de correção
  InvoiceLog       → log imutável de todas as transmissões
"""

import uuid
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# CHOICES
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceStatus(models.TextChoices):
    RASCUNHO    = 'RASCUNHO',    'Rascunho'
    PENDENTE    = 'PENDENTE',    'Pendente de Transmissão'
    AUTORIZADA  = 'AUTORIZADA',  'Autorizada'
    REJEITADA   = 'REJEITADA',   'Rejeitada'
    CANCELADA   = 'CANCELADA',   'Cancelada'
    INUTILIZADA = 'INUTILIZADA', 'Inutilizada'
    DENEGADA    = 'DENEGADA',    'Denegada'


class InvoiceModel(models.TextChoices):
    NFE  = '55', 'NF-e (55)'
    NFCE = '65', 'NFC-e (65)'


class TipoEmissao(models.TextChoices):
    NORMAL       = '1', 'Emissão Normal'
    CONTINGENCIA = '9', 'Contingência Off-line'


class ModalidadeFrete(models.TextChoices):
    EMITENTE     = '0', 'Remetente (CIF)'
    DESTINATARIO = '1', 'Destinatário (FOB)'
    TERCEIROS    = '2', 'Terceiros'
    PROPRIO_EMIT = '3', 'Próprio – Emitente'
    PROPRIO_DEST = '4', 'Próprio – Destinatário'
    SEM_FRETE    = '9', 'Sem Frete'


class TipoEvento(models.TextChoices):
    CANCELAMENTO = '110111', 'Cancelamento'
    CARTA_CORR   = '110110', 'Carta de Correção'
    INUTILIZACAO = '110112', 'Inutilização'


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE — Cabeçalho da NF (snapshot imutável após transmissão)
# ─────────────────────────────────────────────────────────────────────────────

class Invoice(models.Model):
    """
    Cabeçalho da NF-e / NFC-e.
    Criado ao clicar em "Gerar NF-e" no pedido faturado.
    Todos os campos do emitente e destinatário são snapshot do
    momento da emissão — não mudam se o Business/Client for editado depois.
    """

    uid    = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Pedido de origem — PROTECT para não perder a NF se o pedido for deletado
    order  = models.ForeignKey(
        'core.Orders',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='Pedido'
    )

    # ── Identificação ──────────────────────────────────────────────────────
    model         = models.CharField('Modelo', max_length=2,
                                     choices=InvoiceModel.choices)
    serie         = models.CharField('Série', max_length=3)
    number        = models.PositiveIntegerField('Número')
    code_nf       = models.CharField('cNF (8 dígitos)', max_length=8, blank=True)
    access_key    = models.CharField('Chave de Acesso', max_length=44,
                                     blank=True, db_index=True)
    dv            = models.PositiveSmallIntegerField('Dígito Verificador',
                                                     null=True, blank=True)

    # ── Ambiente / Emissão ─────────────────────────────────────────────────
    # Espelha Business.nfe_environment no momento da geração
    environment   = models.CharField('Ambiente', max_length=1,
                                     choices=[('1', 'Produção'), ('2', 'Homologação')])
    emission_type = models.CharField('Tipo de Emissão', max_length=1,
                                     choices=TipoEmissao.choices,
                                     default=TipoEmissao.NORMAL)

    # ── Datas ──────────────────────────────────────────────────────────────
    issue_date    = models.DateTimeField('Data de Emissão', default=timezone.now)
    exit_date     = models.DateTimeField('Data de Saída/Entrada', null=True, blank=True)

    # ── Operação (espelha campos de Orders) ───────────────────────────────
    nature_operation   = models.CharField('Natureza da Operação', max_length=60)
    operation_type     = models.CharField('Tipo Operação', max_length=1,
                                          choices=[('0', 'Entrada'), ('1', 'Saída')],
                                          default='1')
    finality           = models.CharField('Finalidade', max_length=1,
                                          choices=[('1', 'Normal'), ('2', 'Complementar'),
                                                   ('3', 'Ajuste'), ('4', 'Devolução')],
                                          default='1')
    presence_indicator = models.CharField('Indicador de Presença', max_length=1,
                                          choices=[('0', 'Não se aplica'),
                                                   ('1', 'Presencial'),
                                                   ('2', 'Internet'),
                                                   ('3', 'Teleatendimento'),
                                                   ('9', 'Outros')],
                                          default='0')

    # ── Emitente — snapshot de Business ───────────────────────────────────
    emit_name         = models.CharField('Razão Social', max_length=255)
    emit_fantasy      = models.CharField('Fantasia', max_length=255, blank=True)
    emit_cnpj         = models.CharField('CNPJ', max_length=14)       # apenas dígitos
    emit_ie           = models.CharField('IE', max_length=20, blank=True)
    emit_im           = models.CharField('IM', max_length=20, blank=True)
    # 1=Simples, 2=Simples Excesso, 3=Normal — espelha Business.tax_regime
    emit_tax_regime   = models.CharField('Regime Tributário', max_length=1,
                                         choices=[('1', 'Simples Nacional'),
                                                  ('2', 'Simples Nacional – Excesso'),
                                                  ('3', 'Regime Normal')])
    emit_street       = models.CharField('Logradouro', max_length=255)
    emit_number       = models.CharField('Número', max_length=20)
    emit_complement   = models.CharField('Complemento', max_length=60, blank=True)
    emit_district     = models.CharField('Bairro', max_length=60)
    emit_city         = models.CharField('Cidade', max_length=60)
    emit_city_code    = models.CharField('IBGE Município', max_length=7)
    emit_state        = models.CharField('UF', max_length=2)
    emit_zip_code     = models.CharField('CEP', max_length=8)          # apenas dígitos
    emit_country_code = models.CharField('Cód. País', max_length=4, default='1058')
    emit_phone        = models.CharField('Fone', max_length=14, blank=True)

    # ── Destinatário — snapshot de Client ─────────────────────────────────
    dest_name          = models.CharField('Nome', max_length=255)
    dest_cnpj          = models.CharField('CNPJ', max_length=14, blank=True)
    dest_cpf           = models.CharField('CPF', max_length=11, blank=True)
    dest_ie            = models.CharField('IE', max_length=20, blank=True)
    # Espelha Client.taxpayer_type
    dest_taxpayer_type = models.CharField('Indicador IE', max_length=1,
                                          choices=[('1', 'Contribuinte'),
                                                   ('2', 'Isento'),
                                                   ('9', 'Não Contribuinte')],
                                          default='9')
    dest_email         = models.EmailField('E-mail', blank=True)
    dest_phone         = models.CharField('Fone', max_length=14, blank=True)
    dest_street        = models.CharField('Logradouro', max_length=255, blank=True)
    dest_number        = models.CharField('Número', max_length=20, blank=True)
    dest_complement    = models.CharField('Complemento', max_length=60, blank=True)
    dest_neighborhood  = models.CharField('Bairro', max_length=60, blank=True)
    dest_city          = models.CharField('Cidade', max_length=60, blank=True)
    dest_city_code     = models.CharField('IBGE Município', max_length=7, blank=True)  # Client.city_ibge
    dest_state         = models.CharField('UF', max_length=2, blank=True)
    dest_zip_code      = models.CharField('CEP', max_length=8, blank=True)
    dest_country_code  = models.CharField('Cód. País', max_length=4, default='1058')
    dest_country       = models.CharField('País', max_length=60, default='Brasil')

    # ── Totais ─────────────────────────────────────────────────────────────
    total_products    = models.DecimalField('Produtos', max_digits=15, decimal_places=2, default=0)
    total_discount    = models.DecimalField('Desconto', max_digits=15, decimal_places=2, default=0)
    total_freight     = models.DecimalField('Frete', max_digits=15, decimal_places=2, default=0)
    total_insurance   = models.DecimalField('Seguro', max_digits=15, decimal_places=2, default=0)
    total_other       = models.DecimalField('Outras Desp.', max_digits=15, decimal_places=2, default=0)
    total_bc_icms     = models.DecimalField('BC ICMS', max_digits=15, decimal_places=2, default=0)
    total_icms        = models.DecimalField('ICMS', max_digits=15, decimal_places=2, default=0)
    total_bc_st       = models.DecimalField('BC ST', max_digits=15, decimal_places=2, default=0)
    total_icms_st     = models.DecimalField('ICMS ST', max_digits=15, decimal_places=2, default=0)
    total_ipi         = models.DecimalField('IPI', max_digits=15, decimal_places=2, default=0)
    total_pis         = models.DecimalField('PIS', max_digits=15, decimal_places=2, default=0)
    total_cofins      = models.DecimalField('COFINS', max_digits=15, decimal_places=2, default=0)
    total_nf          = models.DecimalField('Total NF', max_digits=15, decimal_places=2, default=0)

    # ── Informações adicionais ─────────────────────────────────────────────
    additional_info   = models.TextField('Informações Complementares', blank=True)
    fiscal_info       = models.TextField('Informações ao Fisco', blank=True)

    # ── Status e transmissão ───────────────────────────────────────────────
    status         = models.CharField('Status', max_length=20,
                                      choices=InvoiceStatus.choices,
                                      default=InvoiceStatus.RASCUNHO,
                                      db_index=True)
    protocol       = models.CharField('Protocolo', max_length=60, blank=True)
    authorized_at  = models.DateTimeField('Data Autorização', null=True, blank=True)
    return_code    = models.CharField('Código Retorno SEFAZ', max_length=10, blank=True)
    return_message = models.TextField('Mensagem Retorno', blank=True)

    # ── XMLs ───────────────────────────────────────────────────────────────
    xml_sent       = models.TextField('XML Enviado', blank=True)
    xml_return     = models.TextField('XML Retorno', blank=True)
    xml_cancel     = models.TextField('XML Cancelamento', blank=True)
    pdf_danfe      = models.FileField('DANFE PDF', upload_to='danfe/', null=True, blank=True)

    # ── NF referenciada (devolução, complementar, etc.) ───────────────────
    ref_invoice    = models.ForeignKey('self', null=True, blank=True,
                                       on_delete=models.SET_NULL,
                                       related_name='derived_invoices',
                                       verbose_name='NF Referenciada')
    ref_access_key = models.CharField('Chave NF Ref. Externa', max_length=44, blank=True)

    # ── Auditoria ──────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        'core.User', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Nota Fiscal'
        verbose_name_plural = 'Notas Fiscais'
        # Um pedido pode ter no máximo 1 NF-e E 1 NFC-e
        unique_together     = [('order', 'model')]
        ordering            = ['-issue_date']
        indexes             = [
            models.Index(fields=['status', 'model']),
            models.Index(fields=['access_key']),
        ]

    def __str__(self):
        return f'NF {self.get_model_display()} {self.serie}/{self.number} – {self.get_status_display()}'

    @property
    def is_editable(self):
        """Pode editar só em rascunho ou após rejeição."""
        return self.status in [InvoiceStatus.RASCUNHO, InvoiceStatus.REJEITADA]

    @property
    def is_cancelable(self):
        """Pode cancelar somente se autorizada."""
        return self.status == InvoiceStatus.AUTORIZADA

    @property
    def short_key(self):
        if self.access_key:
            return f'{self.access_key[:8]}...{self.access_key[-6:]}'
        return '—'


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE ITEM
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceItem(models.Model):
    """
    Snapshot de cada OrderItem no momento da emissão.
    Os campos fiscais vêm diretamente do OrderItem,
    já preenchidos pelo apply_fiscal_rules no momento de salvar o pedido.
    """

    invoice      = models.ForeignKey(Invoice, on_delete=models.CASCADE,
                                     related_name='items')
    # Referência ao item original — PROTECT para rastreabilidade
    order_item   = models.ForeignKey(
        'core.OrderItem', on_delete=models.PROTECT,
        null=True, blank=True, related_name='invoice_items'
    )
    item_number  = models.PositiveSmallIntegerField('Nº Item')

    # ── Produto (snapshot de ProductVariant/Product) ───────────────────────
    product_code = models.CharField('Código', max_length=60)  # ProductVariant.sku
    ean          = models.CharField('EAN/GTIN', max_length=14, blank=True, default='SEM GTIN')  # ProductVariant.ean13
    description  = models.CharField('Descrição', max_length=120)   # Product.name
    ncm          = models.CharField('NCM', max_length=8)             # OrderItem.ncm (string)
    cest         = models.CharField('CEST', max_length=7, blank=True)
    cfop         = models.CharField('CFOP', max_length=4)            # OrderItem.cfop
    unit         = models.CharField('Unidade', max_length=6, default='UN')
    origin       = models.CharField('Origem', max_length=1, default='0')  # Product.origin

    # ── Quantidades e valores ──────────────────────────────────────────────
    quantity     = models.DecimalField('Quantidade', max_digits=15, decimal_places=4)
    unit_price   = models.DecimalField('Preço Unitário', max_digits=15, decimal_places=10)
    gross_total  = models.DecimalField('Total Bruto', max_digits=15, decimal_places=2)
    discount     = models.DecimalField('Desconto', max_digits=15, decimal_places=2, default=0)
    addition     = models.DecimalField('Acréscimo', max_digits=15, decimal_places=2, default=0)
    freight      = models.DecimalField('Frete Item', max_digits=15, decimal_places=2, default=0)
    insurance    = models.DecimalField('Seguro Item', max_digits=15, decimal_places=2, default=0)
    other        = models.DecimalField('Outras Desp.', max_digits=15, decimal_places=2, default=0)

    # ── ICMS (vem de OrderItem.icms_*) ────────────────────────────────────
    # Regime Normal  → preenche icms_cst
    # Simples Nacional → preenche icms_csosn
    icms_cst     = models.CharField('CST ICMS', max_length=3, blank=True)    # OrderItem.icms_cst
    icms_csosn   = models.CharField('CSOSN', max_length=3, blank=True)       # OrderItem.icms_csosn
    icms_bc      = models.DecimalField('BC ICMS', max_digits=15, decimal_places=2, default=0)
    icms_rate    = models.DecimalField('Alíq. ICMS %', max_digits=7, decimal_places=4, default=0)
    icms_value   = models.DecimalField('Valor ICMS', max_digits=15, decimal_places=2, default=0)

    # ICMS ST
    icms_st_bc   = models.DecimalField('BC ST', max_digits=15, decimal_places=2, default=0)
    icms_st_rate = models.DecimalField('Alíq. ST %', max_digits=7, decimal_places=4, default=0)
    icms_st_value = models.DecimalField('Valor ST', max_digits=15, decimal_places=2, default=0)

    # Crédito SN (CSOSN 101, 201, 900)
    sn_credit_rate  = models.DecimalField('% Crédito SN', max_digits=7, decimal_places=4, default=0)
    sn_credit_value = models.DecimalField('Valor Crédito SN', max_digits=15, decimal_places=2, default=0)

    # ── PIS (vem de OrderItem.pis_*) ──────────────────────────────────────
    pis_cst      = models.CharField('CST PIS', max_length=2, blank=True)
    pis_bc       = models.DecimalField('BC PIS', max_digits=15, decimal_places=2, default=0)
    pis_rate     = models.DecimalField('Alíq. PIS %', max_digits=7, decimal_places=4, default=0)
    pis_value    = models.DecimalField('Valor PIS', max_digits=15, decimal_places=2, default=0)

    # ── COFINS (vem de OrderItem.cofins_*) ────────────────────────────────
    cofins_cst   = models.CharField('CST COFINS', max_length=2, blank=True)
    cofins_bc    = models.DecimalField('BC COFINS', max_digits=15, decimal_places=2, default=0)
    cofins_rate  = models.DecimalField('Alíq. COFINS %', max_digits=7, decimal_places=4, default=0)
    cofins_value = models.DecimalField('Valor COFINS', max_digits=15, decimal_places=2, default=0)

    item_info    = models.CharField('Info Adicional Item', max_length=500, blank=True)

    class Meta:
        verbose_name        = 'Item da NF'
        verbose_name_plural = 'Itens da NF'
        unique_together     = [('invoice', 'item_number')]
        ordering            = ['item_number']

    def __str__(self):
        return f'Item {self.item_number} – {self.description}'

    @property
    def net_total(self):
        return self.gross_total - self.discount + self.addition


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE PAYMENT
# ─────────────────────────────────────────────────────────────────────────────

class InvoicePayment(models.Model):
    """
    Snapshot dos pagamentos no momento da emissão.
    O código SEFAZ vem de PaymentMethod.payment_type (já mapeado com os
    mesmos valores do XML: 01=Dinheiro, 03=Cartão Crédito, 17=PIX, etc.)
    """

    PAYMENT_CHOICES = [
        ('01', 'Dinheiro'),        ('02', 'Cheque'),
        ('03', 'Cartão Crédito'),  ('04', 'Cartão Débito'),
        ('05', 'Crédito Loja'),    ('10', 'Vale Alimentação'),
        ('11', 'Vale Refeição'),   ('12', 'Vale Presente'),
        ('13', 'Vale Combustível'),('14', 'Duplicata'),
        ('15', 'Boleto'),          ('16', 'Depósito'),
        ('17', 'PIX'),             ('90', 'Sem Pagamento'),
        ('99', 'Outros'),
    ]

    CARD_FLAG_CHOICES = [
        ('01', 'Visa'), ('02', 'Mastercard'), ('03', 'Amex'),
        ('04', 'Sorocred'), ('05', 'Diners'), ('06', 'Elo'),
        ('07', 'Hipercard'), ('08', 'Aura'), ('09', 'Cabal'), ('99', 'Outros'),
    ]

    invoice       = models.ForeignKey(Invoice, on_delete=models.CASCADE,
                                      related_name='payments')
    # Referência ao pagamento original para rastreabilidade
    order_payment = models.ForeignKey(
        'core.OrderPayment', on_delete=models.PROTECT,
        null=True, blank=True, related_name='invoice_payments'
    )

    # Código de 2 dígitos do XML (convertido de PaymentMethod.payment_type)
    payment_code  = models.CharField('Forma (SEFAZ)', max_length=2,
                                     choices=PAYMENT_CHOICES)
    value         = models.DecimalField('Valor', max_digits=15, decimal_places=2)
    change        = models.DecimalField('Troco', max_digits=15, decimal_places=2, default=0)

    # Dados de cartão (grupo <card> do XML — opcional)
    card_integration = models.CharField('Tipo Integração', max_length=1,
                                        choices=[('1', 'Integrado TEF'), ('2', 'Não Integrado')],
                                        blank=True)
    card_cnpj     = models.CharField('CNPJ Credenciadora', max_length=14, blank=True)
    card_flag     = models.CharField('Bandeira', max_length=2,
                                     choices=CARD_FLAG_CHOICES, blank=True)
    card_auth     = models.CharField('NSU/Autorização', max_length=20, blank=True)

    class Meta:
        verbose_name        = 'Pagamento da NF'
        verbose_name_plural = 'Pagamentos da NF'

    def __str__(self):
        return f'{self.get_payment_code_display()} – R$ {self.value}'


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE TRANSPORT
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceTransport(models.Model):
    """Grupo transp da NF. Um registro por Invoice."""

    invoice         = models.OneToOneField(Invoice, on_delete=models.CASCADE,
                                           related_name='transport')
    # Espelha Orders.freight_mode
    freight_mode    = models.CharField('Modalidade Frete', max_length=1,
                                       choices=ModalidadeFrete.choices,
                                       default=ModalidadeFrete.SEM_FRETE)

    # Transportadora
    carrier_name    = models.CharField('Nome', max_length=60, blank=True)
    carrier_cnpj    = models.CharField('CNPJ', max_length=14, blank=True)
    carrier_cpf     = models.CharField('CPF', max_length=11, blank=True)
    carrier_ie      = models.CharField('IE', max_length=20, blank=True)
    carrier_address = models.CharField('Endereço', max_length=60, blank=True)
    carrier_city    = models.CharField('Cidade', max_length=60, blank=True)
    carrier_state   = models.CharField('UF', max_length=2, blank=True)

    # Veículo
    vehicle_plate   = models.CharField('Placa', max_length=8, blank=True)
    vehicle_state   = models.CharField('UF Placa', max_length=2, blank=True)
    vehicle_rntc    = models.CharField('RNTC', max_length=20, blank=True)

    # Volumes
    volume_qty      = models.DecimalField('Qtde Volumes', max_digits=15, decimal_places=4,
                                          null=True, blank=True)
    volume_species  = models.CharField('Espécie', max_length=60, blank=True)
    volume_brand    = models.CharField('Marca', max_length=60, blank=True)
    volume_numbering = models.CharField('Numeração', max_length=60, blank=True)
    net_weight      = models.DecimalField('Peso Líquido (kg)', max_digits=15, decimal_places=3,
                                          null=True, blank=True)
    gross_weight    = models.DecimalField('Peso Bruto (kg)', max_digits=15, decimal_places=3,
                                          null=True, blank=True)
    seals           = models.JSONField('Lacres', default=list, blank=True)

    class Meta:
        verbose_name        = 'Transporte da NF'
        verbose_name_plural = 'Transportes das NFs'

    def __str__(self):
        return f'Transporte NF {self.invoice_id} – {self.get_freight_mode_display()}'


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE EVENT
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceEvent(models.Model):
    """Eventos da NF: cancelamento, carta de correção, inutilização."""

    invoice        = models.ForeignKey(Invoice, on_delete=models.CASCADE,
                                       related_name='events')
    event_type     = models.CharField('Tipo', max_length=6, choices=TipoEvento.choices)
    sequence       = models.PositiveSmallIntegerField('Sequência', default=1)
    event_date     = models.DateTimeField('Data', default=timezone.now)
    justification  = models.TextField('Justificativa / Texto')
    event_protocol = models.CharField('Protocolo', max_length=60, blank=True)
    return_code    = models.CharField('Código Retorno', max_length=10, blank=True)
    return_message = models.TextField('Mensagem Retorno', blank=True)
    xml_event      = models.TextField('XML Evento', blank=True)
    xml_return     = models.TextField('XML Retorno', blank=True)
    created_by     = models.ForeignKey('core.User', null=True, blank=True,
                                       on_delete=models.SET_NULL)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Evento de NF'
        verbose_name_plural = 'Eventos de NF'
        ordering            = ['-event_date']

    def __str__(self):
        return f'{self.get_event_type_display()} – NF {self.invoice_id}'


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE LOG — imutável, apenas inserção
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceLog(models.Model):

    class Action(models.TextChoices):
        GENERATE   = 'GENERATE',   'Geração'
        SIGN       = 'SIGN',       'Assinatura XML'
        TRANSMIT   = 'TRANSMIT',   'Transmissão SEFAZ'
        QUERY      = 'QUERY',      'Consulta Status'
        CANCEL     = 'CANCEL',     'Cancelamento'
        VOID       = 'VOID',       'Inutilização'
        CORRECTION = 'CORRECTION', 'Carta de Correção'
        DANFE      = 'DANFE',      'Geração DANFE'

    class Result(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Sucesso'
        ERROR   = 'ERROR',   'Erro'
        WARNING = 'WARNING', 'Aviso'

    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE,
                                    related_name='logs')
    action      = models.CharField('Ação', max_length=20, choices=Action.choices)
    result      = models.CharField('Resultado', max_length=10, choices=Result.choices)
    return_code = models.CharField('Código', max_length=10, blank=True)
    message     = models.TextField('Mensagem')
    detail      = models.TextField('Detalhe / Stacktrace', blank=True)
    xml_sent    = models.TextField('XML Enviado (snapshot)', blank=True)
    xml_return  = models.TextField('XML Retorno (snapshot)', blank=True)
    duration_ms = models.PositiveIntegerField('Duração (ms)', null=True, blank=True)
    created_by  = models.ForeignKey('core.User', null=True, blank=True,
                                    on_delete=models.SET_NULL)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Log de NF'
        verbose_name_plural = 'Logs de NF'
        ordering            = ['-created_at']

    def __str__(self):
        ts = self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else '—'
        return f'[{self.result}] {self.get_action_display()} – NF {self.invoice_id} – {ts}'