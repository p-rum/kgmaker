import React from 'react';
export function process(value: number): string;
export function process(value: string): string;
export function process(value: number | string): string { return String(value); }
export function App() {
  const handle = () => process(7);
  return <button onClick={handle}>{process('typed')}</button>;
}
