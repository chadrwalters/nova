declare module '@jest/globals' {
  export const describe: (name: string, fn: () => void) => void;
  export const it: (name: string, fn: () => void | Promise<void>) => void;
  export const expect: <T>(actual: T) => {
    toBe: (expected: T) => void;
    toEqual: (expected: T) => void;
    toBeLessThan: (expected: number) => void;
    toBeLessThanOrEqual: (expected: number) => void;
    toBeGreaterThan: (expected: number) => void;
    toBeGreaterThanOrEqual: (expected: number) => void;
    toHaveLength: (expected: number) => void;
  };
  export const beforeEach: (fn: () => void) => void;
  export const afterEach: (fn: () => void) => void;
  export const beforeAll: (fn: () => void) => void;
  export const afterAll: (fn: () => void) => void;
  export const jest: {
    fn: <T extends (...args: any[]) => any>(implementation?: T) => jest.Mock<ReturnType<T>, Parameters<T>>;
  };
}

declare module '@testing-library/jest-dom/extend-expect' {
  // This module augments Jest's expect
}

declare module '@testing-library/react-hooks' {
  export function renderHook<TProps, TResult>(
    callback: (props: TProps) => TResult,
    options?: {
      initialProps?: TProps;
      wrapper?: React.ComponentType<any>;
    }
  ): {
    result: { current: TResult };
    rerender: (props?: TProps) => void;
    unmount: () => void;
  };

  export function act(callback: () => void | Promise<void>): Promise<void>;
} 