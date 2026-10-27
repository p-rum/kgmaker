import { apply, convert, asText, doubled } from './index';
const namedAlias = asText;
export function run(value: number): string { return apply(value, asText); }
export function inline(value: number): number { return apply(value, n => n + 1); }
export function direct(value: number): string { return namedAlias(value); }
export function ambiguous(flag: boolean, value: number): string | number {
  const selected = flag ? asText : doubled;
  return selected(value);
}
export function dynamic(callback: any, value: number): unknown { return callback(value); }
export function overloads(): [number, string] { return [convert(1), convert('one')]; }
import { otherText } from './handlers';
export function mutable(flag: boolean, value: number): string {
  let handler = asText;
  if (flag) handler = otherText;
  return handler(value);
}
import { overloadedMap } from './api';
export function overloadedCallback(value: number): string { return overloadedMap(value, asText); }
export function mutableProperty(flag: boolean, value: number): string {
  const holder = { handler: asText };
  if (flag) holder.handler = otherText;
  return holder.handler(value);
}
