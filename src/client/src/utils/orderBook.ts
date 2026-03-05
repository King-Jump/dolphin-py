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

/**
 * 将 WebSocket 深度增量合并到当前盘口
 * 规则：同价格更新数量，数量为 0 表示撤档
 */
export function mergeDepth(
  prevBids: DepthLevel[],
  prevAsks: DepthLevel[],
  updateBids: DepthLevel[],
  updateAsks: DepthLevel[]
): { bids: DepthLevel[]; asks: DepthLevel[] } {
  const bidMap = new Map<string, string>();
  prevBids.forEach(([p, q]) => bidMap.set(p, q));
  updateBids.forEach(([p, q]) => {
    if (parseFloat(q) === 0) bidMap.delete(p);
    else bidMap.set(p, q);
  });

  const askMap = new Map<string, string>();
  prevAsks.forEach(([p, q]) => askMap.set(p, q));
  updateAsks.forEach(([p, q]) => {
    if (parseFloat(q) === 0) askMap.delete(p);
    else askMap.set(p, q);
  });

  const bids = sortBids(Array.from(bidMap.entries()).map(([p, q]) => [p, q] as DepthLevel));
  const asks = sortAsks(Array.from(askMap.entries()).map(([p, q]) => [p, q] as DepthLevel));
  return { bids, asks };
}
