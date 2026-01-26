from django import forms
from django.forms import inlineformset_factory
from .models import Client, Sizechart, colorchart, modelchart, Product, StockEntry, Orders, OrderItem

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone', 'document']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'document': forms.TextInput(attrs={'class': 'form-control'}),
        }

class SizechartForm(forms.ModelForm):
    class Meta:
        model = Sizechart
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }
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
        fields = ['name', 'description', 'price', 'price1', 'cost', 'size', 'color', 'model', 'weight', 'brand', 'ean13']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'price1': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'color': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'ean13': forms.TextInput(attrs={'class': 'form-control'}),
        }

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

class OrderForm(forms.ModelForm):
    class Meta:
        model = Orders
        fields = ['client']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
        }


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price', 'discount', 'addition']


OrderItemFormSet = inlineformset_factory(
    Orders,
    OrderItem,
    form=OrderItemForm,
    extra=0,
    can_delete=True
)


# class ProductImageForm(forms.ModelForm):
#     class Meta:
#         model = ProductImage
#         fields = ['image', 'description', 'colorchart', 'modelchart', 'sizechart']

#         widgets = {
#             'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
#             'description': forms.TextInput(attrs={'class': 'form-control'}),
#             'colorchart': forms.Select(attrs={'class': 'form-control'}),
#             'modelchart': forms.Select(attrs={'class': 'form-control'}),
#             'sizechart': forms.Select(attrs={'class': 'form-control'}),
#         }
