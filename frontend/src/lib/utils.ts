import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge class names, letting a caller's utility win over a component's default.
 *
 * `clsx` flattens conditionals; `twMerge` resolves Tailwind conflicts so that
 * `cn('px-3', 'px-5')` is `px-5` rather than both. Required by every shadcn-vue
 * component and by ours (ADR-0014).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
