import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(value: number | undefined | null, decimals = 2): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '--'
  }
  return value.toFixed(decimals)
}

export function formatPercent(value: number | undefined | null, decimals = 2): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '--%'
  }
  return `${(value * 100).toFixed(decimals)}%`
}

export function formatCurrency(value: number | undefined | null, decimals = 0): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '¥--'
  }
  return `¥${value.toFixed(decimals)}`
}
