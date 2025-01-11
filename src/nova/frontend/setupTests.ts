/// <reference types="jest" />
import '@testing-library/jest-dom/extend-expect';
import { jest } from '@jest/globals';

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockImplementation(() => ({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
}));
(window as any).IntersectionObserver = mockIntersectionObserver;

// Mock ResizeObserver
const mockResizeObserver = jest.fn();
mockResizeObserver.mockImplementation(() => ({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
}));
(window as any).ResizeObserver = mockResizeObserver;

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock localStorage
const localStorageMock: Storage = {
  length: 0,
  clear: jest.fn(),
  getItem: jest.fn(),
  key: jest.fn(),
  removeItem: jest.fn(),
  setItem: jest.fn(),
  [Symbol.iterator]: function* () {
    yield* [];
  },
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock sessionStorage
const sessionStorageMock: Storage = {
  length: 0,
  clear: jest.fn(),
  getItem: jest.fn(),
  key: jest.fn(),
  removeItem: jest.fn(),
  setItem: jest.fn(),
  [Symbol.iterator]: function* () {
    yield* [];
  },
};
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// Mock fetch
(global as any).fetch = jest.fn();

// Mock Chart.js
jest.mock('chart.js');

// Initialize Chart.js mock
const chartMock = {
  Chart: {
    register: jest.fn(),
  },
  registerables: [],
};

(global as any).Chart = chartMock.Chart; 