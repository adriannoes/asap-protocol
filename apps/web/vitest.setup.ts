import '@testing-library/jest-dom';

// Radix UI Select uses ResizeObserver (not in jsdom)
if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class ResizeObserver {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as typeof ResizeObserver;
}
