document.addEventListener('DOMContentLoaded', function () {

  const sidebar      = document.getElementById('sidebar');
  const main         = document.getElementById('main');
  const toggleBtn    = document.getElementById('toggle-sidebar');
  const mobileToggle = document.getElementById('mobile-toggle');
  const overlay      = document.getElementById('sidebarOverlay');

  // ── Restore collapsed state (desktop only) ──────────────────────────
  if (window.innerWidth >= 992 && localStorage.getItem('sidebar') === 'collapsed') {
    sidebar.classList.add('sidebar-collapsed');
    main.classList.add('sidebar-collapsed-main');
  }

  // ── Desktop toggle ───────────────────────────────────────────────────
  toggleBtn.addEventListener('click', function () {
    if (window.innerWidth >= 992) {
      const isCollapsed = sidebar.classList.toggle('sidebar-collapsed');
      main.classList.toggle('sidebar-collapsed-main', isCollapsed);
      localStorage.setItem('sidebar', isCollapsed ? 'collapsed' : 'open');

      // when collapsing: close all open submenus so Bootstrap state is clean
      if (isCollapsed) {
        document.querySelectorAll('.submenu.show').forEach(function (el) {
          bootstrap.Collapse.getOrCreateInstance(el).hide();
        });
      }
    } else {
      openMobileSidebar();
    }
  });

  // ── Mobile toggle ────────────────────────────────────────────────────
  if (mobileToggle) {
    mobileToggle.addEventListener('click', openMobileSidebar);
  }

  function openMobileSidebar() {
    sidebar.classList.add('mobile-open');
    overlay.classList.add('active');
  }

  // ── Close sidebar on overlay click (mobile) ──────────────────────────
  overlay.addEventListener('click', function () {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('active');
  });

  // ── Hover: open/close submenus when sidebar is collapsed (desktop) ───
  sidebar.addEventListener('mouseenter', function () {
    if (!sidebar.classList.contains('sidebar-collapsed')) return;
    // restore previously open submenus that were hidden on collapse
    const saved = sessionStorage.getItem('openSubmenus');
    if (saved) {
      JSON.parse(saved).forEach(function (id) {
        const el = document.getElementById(id);
        if (el) bootstrap.Collapse.getOrCreateInstance(el, { toggle: false }).show();
      });
    }
  });

  sidebar.addEventListener('mouseleave', function () {
    if (!sidebar.classList.contains('sidebar-collapsed')) return;
    // save which submenus are open, then hide them
    const open = [];
    document.querySelectorAll('.submenu.show').forEach(function (el) {
      open.push(el.id);
      bootstrap.Collapse.getOrCreateInstance(el).hide();
    });
    if (open.length) {
      sessionStorage.setItem('openSubmenus', JSON.stringify(open));
    } else {
      sessionStorage.removeItem('openSubmenus');
    }
  });

  // ── Recalculate on resize ─────────────────────────────────────────────
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 992) {
      sidebar.classList.remove('mobile-open');
      overlay.classList.remove('active');

      const saved = localStorage.getItem('sidebar');
      if (saved === 'collapsed') {
        sidebar.classList.add('sidebar-collapsed');
        main.classList.add('sidebar-collapsed-main');
      } else {
        sidebar.classList.remove('sidebar-collapsed');
        main.classList.remove('sidebar-collapsed-main');
      }
    } else {
      sidebar.classList.remove('sidebar-collapsed');
      main.classList.remove('sidebar-collapsed-main');
    }
  });

  // ── Rotate chevron for collapse submenus ─────────────────────────────
  document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(function (btn) {
    const icon   = btn.querySelector('.rotate');
    const target = document.querySelector(btn.getAttribute('href'));

    if (!target || !icon) return;

    if (target.classList.contains('show')) {
      icon.classList.add('open');
    }

    target.addEventListener('show.bs.collapse', function () {
      icon.classList.add('open');
    });

    target.addEventListener('hide.bs.collapse', function () {
      icon.classList.remove('open');
    });
  });

});
