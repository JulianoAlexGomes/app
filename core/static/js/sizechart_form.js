document.addEventListener('DOMContentLoaded', function () {

    const container = document.getElementById('sizes-container');
    const totalFormsInput = document.querySelector(
        'input[name$="-TOTAL_FORMS"]'
    );
    const emptyFormTemplate = document.getElementById('empty-form-template').innerHTML;
    const autoBtn = document.getElementById('auto-sizes');
    const addBtn = document.getElementById('add-size');

    function updateOrder() {
        const forms = container.querySelectorAll('.size-form');
        let index = 1;

        forms.forEach(form => {
            if (form.style.display === 'none') return;

            const orderInput = form.querySelector('input[name$="-order"]');
            if (orderInput) {
                orderInput.value = index;
                index++;
            }
        });
    }

    function bindRemoveButtons() {
        container.querySelectorAll('.remove-size').forEach(btn => {
            btn.onclick = function () {
                const formDiv = btn.closest('.size-form');
                const deleteInput = formDiv.querySelector('input[name$="-DELETE"]');

                if (deleteInput) {
                    deleteInput.checked = true;
                }

                formDiv.style.display = 'none';
                updateOrder();
            };
        });
    }

    function addNewForm(value = '') {
        const formCount = parseInt(totalFormsInput.value, 10);
        const html = emptyFormTemplate.replace(/__prefix__/g, formCount);

        container.insertAdjacentHTML('beforeend', html);
        totalFormsInput.value = formCount + 1;

        const newForm = container.lastElementChild;
        const nameInput = newForm.querySelector('input[name$="-name"]');

        if (value && nameInput) {
            nameInput.value = value;
        }

        bindRemoveButtons();
        updateOrder();
    }

    // ➕ adicionar manual
    if (addBtn && !addBtn.dataset.bound) {
        addBtn.dataset.bound = 'true';

        addBtn.addEventListener('click', function () {
            addNewForm();
        });
    }


    // 🔁 auto P/M/G (UMA ÚNICA VEZ)
    if (autoBtn && !autoBtn.dataset.bound) {
        autoBtn.dataset.bound = 'true';

        autoBtn.addEventListener('click', function () {
            ['P', 'M', 'G'].forEach(size => addNewForm(size));
        });
    }


    bindRemoveButtons();
    updateOrder();
});
