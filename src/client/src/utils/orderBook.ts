import type { DepthLevel } from '../types/api';

/** 买盘按价格降序（最高价在前，最佳买在前） */
export function sortBids(levels: DepthLevel[]): DepthLevel[] {
  return [...levels]
    .filter(([, qty]) => parseFloat(qty) > 0)
    .sort((a, b) => parseFloat(b[0]) - parseFloat(a[0]));
}

/** 卖盘按价格升序（最低价在前，最佳卖在前） */
export function sortAsks(levels: DepthLevel[]): DepthLevel[] {
  return [...levels]
    .filter(([, qty]) => parseFloat(qty) > 0)
    .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));
}
