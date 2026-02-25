function money(v) {
    return 'R$ ' + (v || 0).toFixed(2).replace('.', ',');
}

function recalcTotal() {
    let total = 0;

    document.querySelectorAll('#items-table tr').forEach(row => {
        const subtotal = parseFloat(row.dataset.subtotal || 0);
        total += subtotal;
    });

    document.getElementById('total').innerText = money(total);
}

function updateSubtotal(row) {
    const qty = parseFloat(row.querySelector('[name$="-quantity"]').value || 0);
    const price = parseFloat(row.querySelector('[name$="-price"]').value || 0);
    const discount = parseFloat(row.querySelector('[name$="-discount"]').value || 0);
    const addition = parseFloat(row.querySelector('[name$="-addition"]').value || 0);

    const subtotal = (qty * price) - discount + addition;

    row.dataset.subtotal = subtotal;
    row.querySelector('.subtotal').innerText = money(subtotal);

    recalcTotal();
}

function bindRowEvents(row) {
    row.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('input', () => updateSubtotal(row));
        el.addEventListener('change', () => updateSubtotal(row));
    });

    const removeBtn = row.querySelector('.remove-item');
    if (removeBtn) {
        removeBtn.onclick = () => {
            const del = row.querySelector('[name$="-DELETE"]');
            if (del) del.checked = true;

            row.style.display = 'none';
            row.dataset.subtotal = 0;

            recalcTotal();
        };
    }
}

function addItemFromForm(variantId, price, qty, discount, addition) {

    const rows = document.querySelectorAll('#items-table tr');

    // 🔥 Verifica se já existe
    for (let row of rows) {

        const variantField = row.querySelector('[name$="-variant"]');

        if (variantField && variantField.value == variantId && row.style.display !== 'none') {

            const qtyInput = row.querySelector('[name$="-quantity"]');
            const currentQty = parseFloat(qtyInput.value || 0);

            qtyInput.value = currentQty + qty;

            updateSubtotal(row);

            return; // 🔥 Para aqui — não cria nova linha
        }
    }

    // 🔥 Se não existir, cria normalmente
    const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');
    const index = parseInt(totalFormsInput.value);

    const template = document.getElementById('empty-form-template')
        .innerHTML.replace(/__prefix__/g, index);

    const temp = document.createElement('tbody');
    temp.innerHTML = template;

    const row = temp.firstElementChild;

    document.getElementById('items-table').appendChild(row);

    totalFormsInput.value = index + 1;

    row.querySelector('[name$="-variant"]').value = variantId;
    row.querySelector('[name$="-quantity"]').value = qty;
    row.querySelector('[name$="-price"]').value = price;
    row.querySelector('[name$="-discount"]').value = discount;
    row.querySelector('[name$="-addition"]').value = addition;

    bindRowEvents(row);
    updateSubtotal(row);
}


document.addEventListener('DOMContentLoaded', function () {

    /* ==============================
       🔎 SELECT2 - BUSCA PROFISSIONAL
    ============================== */

    $('#product').select2({
        placeholder: 'Buscar produto ou tamanho...',
        minimumInputLength: 1,
        ajax: {
            url: '/ajax/variants/',
            dataType: 'json',
            delay: 300,
            data: function (params) {
                return {
                    q: params.term
                };
            },
            processResults: function (data) {
                return {
                    results: data.results.map(item => ({
                        id: item.id,
                        text: item.text,
                        price: item.price,
                        price1: item.price1
                    }))
                };
            },
            cache: true
        }
    });

    /* ==============================
       💰 AUTO PREÇO AO SELECIONAR
    ============================== */

    $('#product').on('select2:select', function (e) {
        const data = e.params.data;
        const priceType = document.getElementById('price_type').value;

        const price = priceType === 'price1'
            ? data.price1
            : data.price;

        document.getElementById('price').value =
            price ? parseFloat(price).toFixed(2) : '';
    });

    /* ==============================
       🔄 TROCA TIPO PREÇO
    ============================== */

    document.getElementById('price_type').addEventListener('change', function () {

        const selected = $('#product').select2('data');

        if (!selected.length) return;

        const data = selected[0];

        const price = this.value === 'price1'
            ? data.price1
            : data.price;

        document.getElementById('price').value =
            price ? parseFloat(price).toFixed(2) : '';
    });

    /* ==============================
       ➕ ADICIONAR ITEM
    ============================== */

    document.getElementById('add-item-btn').onclick = function () {

        const selected = $('#product').select2('data');

        if (!selected.length) return;

        const variantId = selected[0].id;

        addItemFromForm(
            variantId,
            parseFloat(document.getElementById('price').value || 0),
            parseFloat(document.getElementById('quantity').value || 1),
            parseFloat(document.getElementById('discount').value || 0),
            parseFloat(document.getElementById('addition').value || 0)
        );

        // Reset visual
        $('#product').val(null).trigger('change');
        document.getElementById('quantity').value = 1;
        document.getElementById('discount').value = 0;
        document.getElementById('addition').value = 0;
        document.getElementById('price').value = '';
    };

    /* ==============================
       📦 ITENS JÁ EXISTENTES
    ============================== */

    document.querySelectorAll('.item-form').forEach(row => {
        updateSubtotal(row);
        bindRowEvents(row);
    });

});
