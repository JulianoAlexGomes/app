document.addEventListener("DOMContentLoaded", function () {

    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
    const gallery = document.getElementById("imageGallery");

    if (!gallery) return;

    const productId = window.location.pathname.split("/")[2];

    function loadImages() {

        fetch(`/produtos/${productId}/imagens/`)
            .then(response => response.json())
            .then(images => {

                gallery.innerHTML = "";

                if (!images.length) {
                    gallery.innerHTML = `<div class="text-muted">Nenhuma imagem cadastrada.</div>`;
                    return;
                }

                images.forEach(img => {

                    gallery.innerHTML += `
                        <div class="col-md-3" data-id="${img.id}">
                            <div class="card shadow-sm">
                                <img src="${img.url}"
                                     class="card-img-top preview-image"
                                     style="height:180px; object-fit:cover; cursor:pointer;"
                                     data-url="${img.url}">

                                <div class="card-body text-center">
                                    <small>${img.description || ""}</small>
                                    <br>
                                    <small class="text-muted">
                                        Ordem: ${img.order || 0}
                                    </small>
                                    <br>
                                    <button class="btn btn-sm btn-danger mt-2 delete-image"
                                            data-id="${img.id}">
                                        🗑
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });

            });
    }

    // =========================
    // PREVIEW
    // =========================
    document.addEventListener("click", function (e) {
        if (e.target.classList.contains("preview-image")) {

            const imageUrl = e.target.dataset.url;
            const modalImg = document.getElementById("modalPreviewImage");

            modalImg.src = imageUrl;

            const modal = new bootstrap.Modal(
                document.getElementById("imagePreviewModal")
            );
            modal.show();
        }
    });

    // =========================
    // UPLOAD
    // =========================
    const uploadBtn = document.getElementById("uploadImageBtn");

    if (uploadBtn) {
        uploadBtn.addEventListener("click", function () {

            const fileInput = document.getElementById("newImageInput");

            if (!fileInput.files.length) {
                alert("Selecione uma imagem.");
                return;
            }

            const formData = new FormData();
            formData.append("image", fileInput.files[0]);
            formData.append("description", document.getElementById("newImageDescription").value);
            formData.append("order", document.getElementById("newImageOrder").value);

            fetch(`/produtos/${productId}/adicionarimagem/`, {
                method: "POST",
                body: formData,
                headers: { "X-CSRFToken": csrfToken }
            })
            .then(response => response.json())
            .then(data => {

                fileInput.value = "";
                document.getElementById("newImageDescription").value = "";
                document.getElementById("newImageOrder").value = "";

                loadImages();
            });
        });
    }

    // =========================
    // DELETE
    // =========================
    gallery.addEventListener("click", function (e) {

        if (e.target.classList.contains("delete-image")) {

            const imageId = e.target.dataset.id;

            fetch(`/produtos/imagens/${imageId}/excluir/`, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken }
            })
            .then(() => loadImages());
        }

    });

    loadImages();

});
