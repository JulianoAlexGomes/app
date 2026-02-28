"""fiscal/admin.py"""

from django.contrib import admin
from django.utils.html import format_html
from fiscal.models import (
    Invoice, InvoiceItem, InvoicePayment,
    InvoiceTransport, InvoiceEvent, InvoiceLog,
)

STATUS_CORES = {
    'RASCUNHO':    '#6c757d',
    'PENDENTE':    '#fd7e14',
    'AUTORIZADA':  '#28a745',
    'REJEITADA':   '#dc3545',
    'CANCELADA':   '#343a40',
    'INUTILIZADA': '#6c757d',
    'DENEGADA':    '#721c24',
}


# ── Inlines ──────────────────────────────────────────────────────────────────

class InvoiceItemInline(admin.TabularInline):
    model   = InvoiceItem
    extra   = 0
    fields  = ['item_number', 'description', 'ncm', 'cfop', 'quantity',
               'unit_price', 'gross_total', 'discount', 'icms_csosn',
               'icms_cst', 'icms_rate', 'icms_value', 'pis_value', 'cofins_value']


class InvoicePaymentInline(admin.TabularInline):
    model  = InvoicePayment
    extra  = 0
    fields = ['payment_code', 'value', 'change', 'card_flag', 'card_auth']


class InvoiceEventInline(admin.TabularInline):
    model           = InvoiceEvent
    extra           = 0
    readonly_fields = ['event_date', 'event_type', 'event_protocol',
                       'return_code', 'return_message', 'created_by']
    fields          = readonly_fields + ['justification']


class InvoiceLogInline(admin.TabularInline):
    model           = InvoiceLog
    extra           = 0
    readonly_fields = ['created_at', 'action', 'result', 'return_code',
                       'message', 'duration_ms']
    fields          = readonly_fields
    can_delete      = False

    def has_add_permission(self, request, obj=None):
        return False


# ── Invoice ───────────────────────────────────────────────────────────────────

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'order', 'model', 'serie', 'number',
                     'status_badge', 'issue_date', 'total_nf', 'short_key_display']
    list_filter   = ['status', 'model', 'environment', 'finality']
    search_fields = ['access_key', 'dest_name', 'dest_cnpj', 'dest_cpf',
                     'number', 'protocol']
    date_hierarchy = 'issue_date'
    readonly_fields = ['access_key', 'protocol', 'authorized_at', 'return_code',
                       'return_message', 'xml_sent', 'xml_return', 'xml_cancel',
                       'created_at', 'updated_at', 'created_by']
    inlines = [InvoiceItemInline, InvoicePaymentInline,
               InvoiceEventInline, InvoiceLogInline]

    fieldsets = (
        ('Identificação', {
            'fields': ('order', 'model', 'serie', 'number', 'code_nf',
                       'access_key', 'dv', 'environment', 'emission_type')
        }),
        ('Operação', {
            'fields': ('nature_operation', 'operation_type', 'finality',
                       'presence_indicator', 'issue_date', 'exit_date')
        }),
        ('Emitente (snapshot)', {
            'fields': ('emit_name', 'emit_cnpj', 'emit_ie', 'emit_tax_regime',
                       'emit_city', 'emit_state'),
            'classes': ('collapse',)
        }),
        ('Destinatário (snapshot)', {
            'fields': ('dest_name', 'dest_cnpj', 'dest_cpf', 'dest_ie',
                       'dest_taxpayer_type', 'dest_city', 'dest_state'),
            'classes': ('collapse',)
        }),
        ('Totais', {
            'fields': ('total_products', 'total_discount', 'total_freight',
                       'total_bc_icms', 'total_icms', 'total_pis',
                       'total_cofins', 'total_nf'),
        }),
        ('Informações Adicionais', {
            'fields': ('additional_info', 'fiscal_info'),
            'classes': ('collapse',)
        }),
        ('Status / Transmissão', {
            'fields': ('status', 'protocol', 'authorized_at',
                       'return_code', 'return_message'),
        }),
        ('XMLs', {
            'fields': ('xml_sent', 'xml_return', 'xml_cancel'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        cor = STATUS_CORES.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;'
            'border-radius:4px;font-size:0.8em;">{}</span>',
            cor, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def short_key_display(self, obj):
        return obj.short_key
    short_key_display.short_description = 'Chave'