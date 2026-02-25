document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('toggle-sidebar');
    const toggleMini = document.getElementById('toggle-sidebar-mini');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('page-content');
    const miniBar = document.getElementById('mini-bar');

    if (!sidebar || !content || !miniBar) return;

    function toggleSidebar() {
        sidebar.classList.toggle('sidebar-collapsed');
        content.classList.toggle('content-expanded');
        miniBar.classList.toggle('active', sidebar.classList.contains('sidebar-collapsed'));
    }

    // Botões de expandir/recolher
    if (toggle) toggle.addEventListener('click', toggleSidebar);
    if (toggleMini) toggleMini.addEventListener('click', toggleSidebar);

    // Tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Hover dropdown da mini-bar (não fecha sidebar)
    const miniIcons = document.querySelectorAll('.mini-icon[data-target]');
    miniIcons.forEach(icon => {
        icon.addEventListener('click', function (e) {
            e.preventDefault();
            const targetSelector = icon.getAttribute('data-target');
            const collapseEl = document.querySelector(targetSelector);
            if (collapseEl) {
                const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
                bsCollapse.toggle();
            }
        });
    });
});
