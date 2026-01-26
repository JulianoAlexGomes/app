let total = 0;

function updateTotal() {
    document.getElementById('total').innerText =
        'R$ ' + total.toFixed(2).replace('.', ',');
}

function updatePrice() {
    const product = document.getElementById('product');
    const priceType = document.getElementById('price_type').value;
    const priceInput = document.getElementById('price');

    if (!product.value) {
        priceInput.value = '';
        return;
    }

    const opt = product.selectedOptions[0];
    const price = priceType === 'price1'
        ? opt.dataset.price1
        : opt.dataset.price;

    priceInput.value = parseFloat(price).toFixed(2);
}

function getNextIndex() {
    return document.querySelectorAll(
        '[name^="items-"][name$="-product"]'
    ).length;
}

function updateTotalForms() {
    document.getElementById('id_items-TOTAL_FORMS').value =
        document.querySelectorAll('[name^="items-"][name$="-product"]').length;
}

function addItem() {
    const product = document.getElementById('product');
    const qty = parseFloat(document.getElementById('quantity').value);
    const price = parseFloat(document.getElementById('price').value);
    const discount = parseFloat(document.getElementById('discount').value || 0);
    const addition = parseFloat(document.getElementById('addition').value || 0);

    if (!product.value || qty <= 0 || !price) {
        alert('Dados inválidos');
        return;
    }

    const index = getNextIndex();
    const subtotal = (qty * price) - discount + addition;
    total += subtotal;

    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${product.selectedOptions[0].text}</td>
        <td>${qty}</td>
        <td>${price.toFixed(2)}</td>
        <td>${discount.toFixed(2)}</td>
        <td>${addition.toFixed(2)}</td>
        <td>R$ ${subtotal.toFixed(2)}</td>
        <td>
            <button type="button" class="btn btn-danger btn-sm">✕</button>
        </td>
    `;

    row.querySelector('button').onclick = () => {
        total -= subtotal;

        // ⚠️ SOMENTE AQUI criamos o DELETE
        document.getElementById('formset-container').insertAdjacentHTML(
            'beforeend',
            `<input type="hidden" name="items-${index}-DELETE" value="on">`
        );

        row.remove();
        updateTotal();
    };

    document.getElementById('items-table').appendChild(row);

    // ✅ CAMPOS DO FORMSET (SEM DELETE)
    document.getElementById('formset-container').insertAdjacentHTML(
        'beforeend',
        `
        <input type="hidden" name="items-${index}-id" value="">
        <input type="hidden" name="items-${index}-product" value="${product.value}">
        <input type="hidden" name="items-${index}-quantity" value="${qty}">
        <input type="hidden" name="items-${index}-price" value="${price}">
        <input type="hidden" name="items-${index}-discount" value="${discount}">
        <input type="hidden" name="items-${index}-addition" value="${addition}">
        `
    );

    updateTotalForms();
    updateTotal();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('#items-table tr').forEach(row => {
        const value = row.children[5]?.innerText
            ?.replace('R$', '')
            ?.replace(',', '.')
            ?.trim();

        if (value) {
            total += parseFloat(value);
        }
    });

    updateTotal();

    document.getElementById('add-item-btn').onclick = addItem;
    document.getElementById('product').onchange = updatePrice;
    document.getElementById('price_type').onchange = updatePrice;
});
