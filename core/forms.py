from django import forms
from django.forms import inlineformset_factory
from .models import Client, Sizechart, colorchart, modelchart, Product, StockEntry, Orders, OrderItem, ProductImage, Sizes, ProductVariant, FinancialMovement, FinancialMovementParcel, PaymentMethod, BankAccount, OrderPayment, OrderPaymentParcel, Business, Plan, User
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class AdminBusinessForm(forms.ModelForm):
    class Meta:
        model  = Business
        fields = [
            'name', 'fantasy_name', 'document',
            'state_registration', 'municipal_registration',
            'tax_regime',
            'street', 'number', 'complement', 'district',
            'city', 'city_code', 'state', 'zip_code', 'phone',
            'nfe_environment', 'nfe_series', 'nfce_series',
            'plan', 'active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = Plan.objects.filter(active=True)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

class AdminUserCreateForm(UserCreationForm):
    """Cria usuário já vinculado a uma empresa."""

    class Meta:
        model  = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'role', 'password1', 'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

class AdminUserChangeForm(forms.ModelForm):
    """Edita usuário sem redefinir senha."""

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class AdminPlanForm(forms.ModelForm):
    class Meta:
        model  = Plan
        fields = ['name', 'price', 'max_users', 'active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


UF_CHOICES = [
    ('', 'Selecione'),
    ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
    ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
    ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
    ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
    ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
    ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
    ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
]


class ClientForm(forms.ModelForm):

    state = forms.ChoiceField(
        choices=UF_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Client
        fields = [
            # Identificação
            'name',
            'supplier',
            'fantasy_name',
            'document',

            # Endereço
            'zip_code',
            'street',
            'number',
            'complement',
            'neighborhood',
            'city',
            'state',
            'city_ibge',

            # Dados fiscais
            'state_registration',
            'is_exempt',
            'taxpayer_type',

            # Contato
            'email',
            'phone',
        ]

        widgets = {
            # Identificação
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razão social ou nome completo',
                'required': True
            }),
            'fantasy_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome fantasia (opcional)'
            }),
            'document': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CPF ou CNPJ',
                'required': True
            }),

            # Endereço
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000',
                'required': True
            }),
            'street': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'complement': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'neighborhood': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'city_ibge': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código IBGE do município',
                'required': True
            }),

            # Dados fiscais
            'state_registration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inscrição Estadual'
            }),
            'is_exempt': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'taxpayer_type': forms.Select(attrs={
                'class': 'form-select'
            }),

            # Contato
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
        }

    # ─────────────────────────────
    # VALIDAÇÕES FISCAIS
    # ─────────────────────────────

    def clean(self):
        cleaned = super().clean()

        is_exempt = cleaned.get('is_exempt')
        ie = cleaned.get('state_registration')
        taxpayer_type = cleaned.get('taxpayer_type')

        if is_exempt:
            cleaned['state_registration'] = ''
            cleaned['taxpayer_type'] = '2'  # Isento
        else:
            if taxpayer_type == '1' and not ie:
                self.add_error(
                    'state_registration',
                    'Informe a Inscrição Estadual ou marque como Isento.'
                )

        return cleaned

    # ─────────────────────────────
    # NORMALIZAÇÃO (REMOVE MÁSCARAS)
    # ─────────────────────────────

    def clean_document(self):
        return ''.join(filter(str.isdigit, self.cleaned_data['document']))

    def clean_zip_code(self):
        return ''.join(filter(str.isdigit, self.cleaned_data['zip_code']))

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            return ''.join(filter(str.isdigit, phone))
        return phone


class SizechartForm(forms.ModelForm):
    class Meta:
        model = Sizechart
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }

class SizesForm(forms.ModelForm):
    class Meta:
        model = Sizes
        fields = ('name', 'order')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()

        if self.cleaned_data.get('DELETE'):
            return cleaned

        if not cleaned.get('name'):
            raise ValidationError('O tamanho não pode ser vazio.')

        return cleaned

class BaseSizesFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        names = set()

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            name = form.cleaned_data.get('name')

            if not name:
                raise ValidationError('Todos os tamanhos devem ter nome.')

            key = name.strip().lower()

            if key in names:
                raise ValidationError(f'Tamanho duplicado: {name}')

            names.add(key)

SizesFormSet = inlineformset_factory(
    Sizechart,
    Sizes,
    form=SizesForm,
    extra=0,
    can_delete=True,
    formset=BaseSizesFormSet
)

class colorchartForm(forms.ModelForm):
    class Meta:
        model = colorchart
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }
class modelchartForm(forms.ModelForm):
    class Meta:
        model = modelchart
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description',
            'price', 'price1', 'cost',
            'size', 'color', 'model',
            'weight', 'brand', 'ncm'
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),

            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'price1': forms.NumberInput(attrs={'class': 'form-control'}),

            'size': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.Select(attrs={'class': 'form-select'}),
            'model': forms.Select(attrs={'class': 'form-select'}),

            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'ncm': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)

        if business:
            self.fields['size'].queryset = Sizechart.objects.filter(business=business)
            self.fields['color'].queryset = colorchart.objects.filter(business=business)
            self.fields['model'].queryset = modelchart.objects.filter(business=business)


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'description', 'order']

        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            # 'colorchart': forms.Select(attrs={'class': 'form-control'}),
            # 'modelchart': forms.Select(attrs={'class': 'form-control'}),
            # 'sizechart': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=1,
    can_delete=True
)


class StockEntryForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ['entry_type', 'quantity']

        widgets = {
            'entry_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }

# Substitua a classe OrderForm no seu forms.py por esta versão

class OrderForm(forms.ModelForm):
    class Meta:
        model = Orders
        fields = ['document_model', 'client']
        widgets = {
            'document_model': forms.RadioSelect(),   # renderizado via cards no template
            'client': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # document_model obrigatório apenas na criação
        self.fields['document_model'].required = not bool(
            self.instance and self.instance.pk
        )

        if user:
            qs = Client.objects.filter(business=user.business)

            # garante que o cliente atual do pedido esteja no queryset
            if self.instance.pk and self.instance.client:
                qs = qs | Client.objects.filter(pk=self.instance.client.pk)

            self.fields['client'].queryset = qs

        # Na edição, bloqueia alteração do modelo de documento
        if self.instance and self.instance.pk:
            self.fields['document_model'].disabled = True


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['variant', 'quantity', 'price', 'discount', 'addition']

        widgets = {
            'variant': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control'}),
            'addition': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)

        if business:
            self.fields['variant'].queryset = ProductVariant.objects.filter(
                product__business=business
            ).select_related('product', 'size', 'color')


OrderItemFormSet = inlineformset_factory(
    Orders,
    OrderItem,
    form=OrderItemForm,
    extra=0,
    can_delete=True
)

from django import forms
from django.forms import inlineformset_factory
from .models import FinancialMovement, FinancialMovementParcel


class FinancialMovementForm(forms.ModelForm):
    class Meta:
        model = FinancialMovement
        fields = [
            'client',
            'type',
            'expense_type',
            'payment_method',
            'bank',
            'total_value',
            'description',
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'expense_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'bank': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
        }

class FinancialParcelForm(forms.ModelForm):
    class Meta:
        model = FinancialMovementParcel
        fields = [
            'parcel',
            'value',
            'discount',
            'addition',
            'deadline',
        ]
        widgets = {
            'parcel': forms.NumberInput(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control'}),
            'addition': forms.NumberInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

FinancialParcelFormSet = inlineformset_factory(
    FinancialMovement,
    FinancialMovementParcel,
    form=FinancialParcelForm,
    extra=0,
    can_delete=True
)

from django import forms
from .models import PaymentMethod


class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = [
            'name',
            'type',
            'default_bank',
            'default_parcels',
            'interval_days',
            'active',
            'payment_type',
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'default_bank': forms.Select(attrs={'class': 'form-select'}),
            'default_parcels': forms.NumberInput(attrs={'class': 'form-control'}),
            'interval_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
        }

from .models import BankAccount


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = [
            'name',
            'bank_name',
            'agency_number',
            'account_number',
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'agency_number': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

# forms.py — substitua ParcelPayForm

class ParcelPayForm(forms.ModelForm):

    bank = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        required=False,
        label='Banco',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        required=False,
        label='Forma de pagamento',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = FinancialMovementParcel
        fields = ['paydate']
        widgets = {
            'paydate': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {'paydate': 'Data do pagamento'}

    def save(self, commit=True):
        instance       = super().save(commit=False)
        instance.payed = True

        # Atualiza banco e/ou forma de pagamento na movement se informados
        movement_changed = False

        bank = self.cleaned_data.get('bank')
        if bank:
            instance.movement.bank = bank
            movement_changed = True

        payment_method = self.cleaned_data.get('payment_method')
        if payment_method:
            instance.movement.payment_method = payment_method
            movement_changed = True

        if movement_changed:
            instance.movement.save(update_fields=[
                f for f in ['bank', 'payment_method']
                if self.cleaned_data.get(f)
            ])

        if commit:
            instance.save()
        return instance
class OrderPaymentForm(forms.ModelForm):
    class Meta:
        model = OrderPayment
        fields = ['payment_method', 'bank', 'total_value', 'parcels', 'interval_days']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'bank':           forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'total_value':    forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end payment-total',
                'step': '0.01',
            }),
            'parcels':      forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-center',
                'min': '1', 'style': 'width:60px',
            }),
            'interval_days': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-center',
                'min': '0', 'style': 'width:70px',
            }),
        }

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        if business:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                business=business, active=True
            )
            self.fields['bank'].queryset = BankAccount.objects.filter(business=business)


OrderPaymentFormSet = inlineformset_factory(
    Orders,
    OrderPayment,
    form=OrderPaymentForm,
    extra=0,
    can_delete=True,
)

class OrderPaymentParcelForm(forms.ModelForm):
    class Meta:
        model = OrderPaymentParcel
        fields = ['parcel_number', 'value', 'due_date']
        widgets = {
            'parcel_number': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-center',
                'style': 'width:55px',
            }),
            'value': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end parcel-value',
                'step': '0.01',
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control form-control-sm',
            }),
        }

OrderPaymentParcelFormSet = inlineformset_factory(
    OrderPayment,
    OrderPaymentParcel,
    form=OrderPaymentParcelForm,
    extra=0,
    can_delete=True,
)

class BusinessForm(forms.ModelForm):

    UF_CHOICES = [
    ('', 'Selecione'),
    ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
    ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
    ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
    ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
    ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
    ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
    ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
]

    certificate_password = forms.CharField(
        widget=forms.PasswordInput(
            render_value=True,
            attrs={'class': 'form-control'}
        ),
        required=False,
        label='Senha do Certificado'
    )

    certificate_expiration = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        ),
        required=False,
        label='Validade do Certificado'
    )

    class Meta:
        model = Business
        exclude = (
            'uid',
            'created_at',
            'country_code',
        )

        widgets = {
            # ================= DADOS EMPRESA =================
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'fantasy_name': forms.TextInput(attrs={'class': 'form-control'}),
            'document': forms.TextInput(attrs={'class': 'form-control'}),
            'state_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'municipal_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_regime': forms.Select(attrs={'class': 'form-select'}),
            'nfe_environment': forms.Select(attrs={'class': 'form-select'}),

            # ================= ENDEREÇO =================
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'complement': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'city_code': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.Select(choices=UF_CHOICES, attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),

            # ================= NFCe =================
            'nfce_csc': forms.TextInput(attrs={'class': 'form-control'}),
            'nfce_csc_id': forms.TextInput(attrs={'class': 'form-control'}),

            # ================= SÉRIES =================
            'nfe_series': forms.TextInput(attrs={'class': 'form-control'}),
            'nfce_series': forms.TextInput(attrs={'class': 'form-control'}),

            # ================= ÚLTIMOS NUMEROS =================
            'nfe_last_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'nfce_last_number': forms.NumberInput(attrs={'class': 'form-control'}),

            # ================= CERTIFICADO =================
            'certificate_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),

            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        labels = {
            'name': 'Razão Social',
            'fantasy_name': 'Nome Fantasia',
            'document': 'CNPJ',
            'state_registration': 'Inscrição Estadual',
            'municipal_registration': 'Inscrição Municipal',
            'tax_regime': 'Regime Tributário',
            'zip_code': 'CEP',
            'street': 'Logradouro',
            'number': 'Número',
            'complement': 'Complemento',
            'district': 'Bairro',
            'city': 'Cidade',
            'city_code': 'Código IBGE',
            'state': 'UF',
            'phone': 'Telefone',
            'nfce_csc': 'CSC NFC-e',
            'nfce_csc_id': 'ID CSC',
            'nfe_series': 'Série NF-e',
            'nfce_series': 'Série NFC-e',
            'nfe_last_number': 'Último número NF-e',
            'nfce_last_number': 'Último número NFC-e',
            'nfe_environment': 'Ambiente',
            'certificate_file': 'Certificado A1',
            'active': 'Empresa Ativa',
        }

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'password1',
            'password2',
        ]

from django import forms
from .models import NCMGroup, NCMGroupItem, FiscalOperation, NCM


class NCMGroupForm(forms.ModelForm):
    class Meta:
        model = NCMGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class NCMGroupItemForm(forms.Form):
    ncm = forms.ModelMultipleChoiceField(
        queryset=NCM.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': 15
        })
    )


class FiscalOperationForm(forms.ModelForm):
    class Meta:
        model = FiscalOperation
        exclude = ['business']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.Select(attrs={'class': 'form-select'}),
            'cfop': forms.TextInput(attrs={'class': 'form-control'}),
            'ncm_group': forms.Select(attrs={'class': 'form-select'}),
            'icms_cst': forms.TextInput(attrs={'class': 'form-control'}),
            'icms_csosn': forms.TextInput(attrs={'class': 'form-control'}),
            'pis_cst': forms.TextInput(attrs={'class': 'form-control'}),
            'pis_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'cofins_cst': forms.TextInput(attrs={'class': 'form-control'}),
            'cofins_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# ─────────────────────────────────────────────────────────────────────────────
# SUBSTITUA o bloco de Invoice forms no final de core/forms.py
# ─────────────────────────────────────────────────────────────────────────────
# ===== INVOICE FORMS =====

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from decimal import Decimal
from .models import Invoice, InvoiceItem, InvoicePayment


PAYMENT_CHOICES = [
    ('01', 'Dinheiro'),       ('02', 'Cheque'),
    ('03', 'Cartão Crédito'), ('04', 'Cartão Débito'),
    ('05', 'Crédito Loja'),   ('10', 'Vale Alimentação'),
    ('11', 'Vale Refeição'),  ('12', 'Vale Presente'),
    ('13', 'Vale Combustível'),('14', 'Duplicata'),
    ('15', 'Boleto'),         ('16', 'Depósito'),
    ('17', 'PIX'),            ('90', 'Sem Pagamento'),
    ('99', 'Outros'),
]


class InvoiceForm(forms.ModelForm):
    """Dados gerais, destinatário, totais e info adicionais da NF."""

    class Meta:
        model = Invoice
        fields = [
            'nature_operation', 'finality', 'presence_indicator',
            'operation_type', 'exit_date',
            'dest_name', 'dest_cnpj', 'dest_cpf', 'dest_ie',
            'dest_taxpayer_type', 'dest_email',
            'dest_street', 'dest_number', 'dest_complement',
            'dest_neighborhood', 'dest_city', 'dest_state', 'dest_zip_code',
            'total_products', 'total_discount', 'total_freight',
            'total_insurance', 'total_other', 'total_nf',
            'additional_info', 'fiscal_info',
        ]
        widgets = {
            'nature_operation':   forms.TextInput(attrs={'class': 'form-control'}),
            'finality':           forms.Select(attrs={'class': 'form-select'}),
            'presence_indicator': forms.Select(attrs={'class': 'form-select'}),
            'operation_type':     forms.Select(attrs={'class': 'form-select'}),
            'exit_date':          forms.DateTimeInput(
                                    format='%Y-%m-%dT%H:%M',
                                    attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'dest_name':          forms.TextInput(attrs={'class': 'form-control'}),
            'dest_cnpj':          forms.TextInput(attrs={'class': 'form-control'}),
            'dest_cpf':           forms.TextInput(attrs={'class': 'form-control'}),
            'dest_ie':            forms.TextInput(attrs={'class': 'form-control'}),
            'dest_taxpayer_type': forms.Select(attrs={'class': 'form-select'}),
            'dest_email':         forms.EmailInput(attrs={'class': 'form-control'}),
            'dest_street':        forms.TextInput(attrs={'class': 'form-control'}),
            'dest_number':        forms.TextInput(attrs={'class': 'form-control'}),
            'dest_complement':    forms.TextInput(attrs={'class': 'form-control'}),
            'dest_neighborhood':  forms.TextInput(attrs={'class': 'form-control'}),
            'dest_city':          forms.TextInput(attrs={'class': 'form-control'}),
            'dest_state':         forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'dest_zip_code':      forms.TextInput(attrs={'class': 'form-control'}),
            'total_products':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_discount':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_freight':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_insurance':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_other':        forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_nf':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'additional_info':    forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'fiscal_info':        forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
        }


class InvoiceItemEditForm(forms.ModelForm):
    """
    Edição de item da NF.
    gross_total é calculado automaticamente pelo save() via clean().
    Campos com max_digits/decimal_places específicos recebem step adequado.
    """

    class Meta:
        model = InvoiceItem
        fields = [
            # Produto
            'description', 'ncm', 'cfop', 'unit',
            # Quantidades (gross_total calculado no save)
            'quantity', 'unit_price', 'discount',
            # ICMS
            'icms_cst', 'icms_csosn', 'icms_rate', 'icms_bc', 'icms_value',
            # PIS / COFINS
            'pis_cst', 'cofins_cst',
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'ncm':         forms.TextInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:100px', 'maxlength': '8'}),
            'cfop':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:65px', 'maxlength': '4'}),
            'unit':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:55px', 'maxlength': '6'}),
            # DecimalField(max_digits=15, decimal_places=4) → step 0.0001
            'quantity':    forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-center',
                'style': 'width:80px', 'step': '0.0001', 'min': '0',
            }),
            # DecimalField(max_digits=15, decimal_places=10) → step 0.01 é suficiente
            'unit_price':  forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'style': 'width:95px', 'step': '0.01', 'min': '0',
            }),
            'discount':    forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'style': 'width:88px', 'step': '0.01', 'min': '0',
            }),
            'icms_cst':    forms.TextInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width:58px', 'maxlength': '3'}),
            'icms_csosn':  forms.TextInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width:58px', 'maxlength': '3'}),
            # DecimalField(max_digits=7, decimal_places=4)
            'icms_rate':   forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-center',
                'style': 'width:70px', 'step': '0.0001', 'min': '0', 'max': '100',
            }),
            'icms_bc':     forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end', 'style': 'width:95px', 'step': '0.01', 'min': '0'}),
            'icms_value':  forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end', 'style': 'width:95px', 'step': '0.01', 'min': '0'}),
            'pis_cst':     forms.TextInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width:55px', 'maxlength': '2'}),
            'cofins_cst':  forms.TextInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width:55px', 'maxlength': '2'}),
        }

    def save(self, commit=True):
        """Calcula gross_total = quantity * unit_price antes de salvar."""
        item = super().save(commit=False)

        qty        = self.cleaned_data.get('quantity') or Decimal('0')
        unit_price = self.cleaned_data.get('unit_price') or Decimal('0')

        # gross_total = qtd × preço unitário (sem desconto — desconto é campo separado)
        item.gross_total = (qty * unit_price).quantize(Decimal('0.01'))

        if commit:
            item.save()
        return item


class InvoicePaymentEditForm(forms.ModelForm):

    class Meta:
        model = InvoicePayment
        fields = ['payment_code', 'value']
        widgets = {
            'payment_code': forms.Select(
                choices=PAYMENT_CHOICES,
                attrs={'class': 'form-select form-select-sm'},
            ),
            'value': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'step': '0.01', 'min': '0',
            }),
        }


# ─── FormSets ────────────────────────────────────────────────────────────────

InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemEditForm,
    extra=0,
    can_delete=True,
)

InvoicePaymentFormSet = inlineformset_factory(
    Invoice,
    InvoicePayment,
    form=InvoicePaymentEditForm,
    extra=1,
    can_delete=True,
)

from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model  = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'role', 'password1', 'password2',
        ]


class CustomUserChangeForm(forms.ModelForm):
    """Edição sem redefinir senha — senha tem fluxo próprio."""
    class Meta:
        model  = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'role',
        ]