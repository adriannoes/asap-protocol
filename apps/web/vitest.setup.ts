import '@testing-library/jest-dom';

// Radix UI Select uses ResizeObserver (not in jsdom)
if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class ResizeObserver {
        observe() { }
        unobserve() { }
        disconnect() { }
    } as typeof ResizeObserver;
}

// Mock window.scrollTo to prevent "Not implemented" warnings in JSDOM
Object.defineProperty(window, 'scrollTo', { value: () => { }, writable: true });

// Mock IndexedDB for idb-keyval to prevent ReferenceError in tests
if (typeof globalThis.indexedDB === 'undefined') {
    globalThis.indexedDB = {} as IDBFactory;
}
