export function mapValue<T, U>(value: T, callback: (value: T) => U): U {
  return callback(value);
}
export function convert(value: number): number;
export function convert(value: string): string;
export function convert(value: number | string): number | string { return value; }
export function overloadedMap(value: number, callback: (value: number) => string): string;
export function overloadedMap(value: string, callback: (value: string) => number): number;
export function overloadedMap(value: any, callback: (value: any) => any): any {
  return callback(value);
}
