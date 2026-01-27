/**
 * Responsive Helper
 * Compatível com Bootstrap 5
 * Mobile-first | iOS friendly
 */

(function () {
    'use strict';

    const Responsive = {
        isMobile: false,
        isTablet: false,
        isDesktop: false,

        init() {
            this.detectDevice();
            this.bindEvents();
            this.fixIOSViewport();
            this.fixButtonTouch();
        },

        detectDevice() {
            const width = window.innerWidth;

            this.isMobile = width < 768;
            this.isTablet = width >= 768 && width < 992;
            this.isDesktop = width >= 992;

            document.body.classList.toggle('is-mobile', this.isMobile);
            document.body.classList.toggle('is-tablet', this.isTablet);
            document.body.classList.toggle('is-desktop', this.isDesktop);
        },

        bindEvents() {
            window.addEventListener('resize', () => {
                this.detectDevice();
            });

            window.addEventListener('orientationchange', () => {
                setTimeout(() => this.detectDevice(), 300);
            });

            document.addEventListener('DOMContentLoaded', () => {
                this.detectDevice();
            });
        },

        /**
         * Corrige problemas clássicos do Safari iOS
         */
        fixIOSViewport() {
            if (!this.isIOS()) return;

            const viewport = document.querySelector('meta[name=viewport]');
            if (!viewport) return;

            viewport.setAttribute(
                'content',
                'width=device-width, initial-scale=1, maximum-scale=1'
            );
        },

        /**
         * Melhora área de toque (iOS)
         */
        fixButtonTouch() {
            document.querySelectorAll('.btn').forEach(btn => {
                btn.style.minHeight = '44px';
            });
        },

        isIOS() {
            return /iPad|iPhone|iPod/.test(navigator.userAgent)
                || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        }
    };

    // Inicializa
    Responsive.init();

    // Expor globalmente se quiser usar em outros scripts
    window.ResponsiveHelper = Responsive;

})();
