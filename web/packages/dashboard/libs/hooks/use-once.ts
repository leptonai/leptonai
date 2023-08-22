import { useRef } from "react";

type OnceValue<T> = { value: T };

export function useOnce<T>(fn: () => T): T {
  const ref = useRef<OnceValue<T> | null>(null);

  // use {value: fn()} to avoid recreating when fn() equals null
  if (ref.current === null) {
    ref.current = { value: fn() };
  }

  return ref.current?.value;
}
