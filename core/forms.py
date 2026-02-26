from django import forms
from django.forms import inlineformset_factory
from .models import Client, Sizechart, colorchart, modelchart, Product, StockEntry, Orders, OrderItem, ProductImage, Sizes, ProductVariant, FinancialMovement, FinancialMovementParcel, PaymentMethod, BankAccount, OrderPayment
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

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
            'payment_method',
            'bank',
            'total_value',
            'description',
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
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

class ParcelPayForm(forms.ModelForm):

    class Meta:
        model = FinancialMovementParcel
        fields = ['paydate']
        widgets = {
            'paydate': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            )
        }
        labels = {
            'paydate': 'Data do pagamento'
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.payed = True

        if commit:
            instance.save()

        return instance

from django.forms import inlineformset_factory

from decimal import Decimal, InvalidOperation
from django import forms

class OrderPaymentForm(forms.ModelForm):
    class Meta:
        model = OrderPayment
        fields = [
            'payment_method',
            'bank',
            'total_value',
            'parcels',
            'interval_days',
        ]

OrderPaymentFormSet = inlineformset_factory(
    Orders,
    OrderPayment,
    form=OrderPaymentForm,
    extra=0,
    can_delete=True
)


from django import forms
from .models import Business


from django import forms
from .models import Business


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
            'plan',
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