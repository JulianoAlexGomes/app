document.addEventListener("DOMContentLoaded", function () {

    const input = document.getElementById("ncm-search");
    const resultsBox = document.getElementById("ncm-results");
    const hiddenInput = document.getElementById("ncm-id");

    if (!input) return;

    let debounceTimeout = null;
    let selectedId = hiddenInput.value || null;

    function clearSelection() {
        selectedId = null;
        hiddenInput.value = "";
    }

    function showLoading() {
        resultsBox.innerHTML = `
            <div class="list-group-item text-center text-muted">
                <div class="spinner-border spinner-border-sm me-2"></div>
                Buscando...
            </div>
        `;
        resultsBox.style.display = "block";
    }

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
                resultsBox.style.display = "none";
            });

            resultsBox.appendChild(item);
        });

        resultsBox.style.display = "block";
    }

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

            fetch(`/ajax/ncm/search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    renderResults(data);
                })
                .catch(() => {
                    resultsBox.style.display = "none";
                });

        }, 400);
    });

    document.addEventListener("click", function (e) {
        if (!input.contains(e.target) && !resultsBox.contains(e.target)) {
            resultsBox.style.display = "none";
        }
    });

});