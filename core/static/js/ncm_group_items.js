document.addEventListener("DOMContentLoaded", function () {

    const input = document.getElementById("ncm-search");
    const resultsBox = document.getElementById("ncm-results");
    const hiddenInput = document.getElementById("ncm-id");
    const btnAdd = document.getElementById("btn-add-ncm");
    const form = document.getElementById("add-ncm-form");

    if (!input) return;

    let debounceTimeout = null;
    let selectedId = null;

    // ===============================
    // Função para limpar seleção
    // ===============================
    function clearSelection() {
        selectedId = null;
        hiddenInput.value = "";
        btnAdd.disabled = true;
    }

    // ===============================
    // Render loading
    // ===============================
    function showLoading() {
        resultsBox.innerHTML = `
            <div class="list-group-item text-center text-muted">
                <div class="spinner-border spinner-border-sm me-2"></div>
                Buscando...
            </div>
        `;
        resultsBox.style.display = "block";
    }

    // ===============================
    // Render resultados
    // ===============================
    function renderResults(data) {
        resultsBox.innerHTML = "";

        if (data.length === 0) {
            resultsBox.innerHTML = `
                <div class="list-group-item text-muted text-center">
                    Nenhum NCM encontrado
                </div>
            `;
            resultsBox.style.display = "block";
            return;
        }

        data.forEach(ncm => {

            const item = document.createElement("a");
            item.href = "#";
            item.classList.add("list-group-item", "list-group-item-action");

            item.innerHTML = `
                <strong>${ncm.code}</strong><br>
                <small class="text-muted">${ncm.description}</small>
            `;

            item.addEventListener("click", function (e) {
                e.preventDefault();

                input.value = `${ncm.code} - ${ncm.description}`;
                hiddenInput.value = ncm.id;

                selectedId = ncm.id;
                btnAdd.disabled = false;

                resultsBox.style.display = "none";
            });

            resultsBox.appendChild(item);
        });

        resultsBox.style.display = "block";
    }

    // ===============================
    // Evento de digitação
    // ===============================
    input.addEventListener("keyup", function () {

        const query = this.value.trim();

        clearSelection();

        if (query.length < 2) {
            resultsBox.style.display = "none";
            return;
        }

        clearTimeout(debounceTimeout);

        debounceTimeout = setTimeout(() => {

            showLoading();

            fetch(`${window.NCM_SEARCH_URL}?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    renderResults(data);
                })
                .catch(error => {
                    console.error("Erro na busca:", error);
                    resultsBox.style.display = "none";
                });

        }, 400);
    });

    // ===============================
    // Fecha dropdown ao clicar fora
    // ===============================
    document.addEventListener("click", function (e) {
        if (!input.contains(e.target) && !resultsBox.contains(e.target)) {
            resultsBox.style.display = "none";
        }
    });

    // ===============================
    // Validação antes de enviar
    // ===============================
    form.addEventListener("submit", function (e) {

        if (!selectedId) {
            e.preventDefault();
            input.classList.add("is-invalid");

            if (!document.getElementById("ncm-invalid-feedback")) {
                const feedback = document.createElement("div");
                feedback.id = "ncm-invalid-feedback";
                feedback.classList.add("invalid-feedback");
                feedback.innerText = "Selecione um NCM válido da lista.";
                input.parentNode.appendChild(feedback);
            }
        }
    });

});