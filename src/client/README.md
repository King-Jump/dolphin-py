# Dolphin 交易前端 - K 线与盘口

基于 API 文档实现的现货 K 线图与盘口深度展示，界面参考 Binance，K 线使用 [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) 开源版。

## 功能

- **K 线图**：TradingView Lightweight Charts 蜡烛图 + 成交量柱状图，支持 1m / 1h / 1d 周期切换
- **盘口**：买卖盘深度（价格、数量、累计），买盘绿/卖盘红，带累计占比背景条
- **实时更新**：通过 WebSocket 订阅 `depth`、`trade`，盘口与最新价实时刷新
- **REST 数据**：首屏从 `/api/v3/klines`、`/api/v3/depth`、`/api/v3/ticker/price` 拉取

## 运行

1. 安装依赖（需先启动后端或能访问 npm registry）：

```bash
pnpm install
```

2. 启动开发：

```bash
pnpm dev
```

浏览器打开 http://localhost:5173。Vite 会把 `/api`、`/fapi` 代理到 `http://localhost:8763`。

3. 构建：

```bash
pnpm build
```

## 环境说明

- 后端 REST：默认 `http://localhost:8763`（通过 Vite proxy 代理，无需改前端）
- WebSocket：默认 `ws://localhost:8765/spot`（在 `useWebSocket.ts` 中可改 `WS_BASE`）
- 当前交易对写死为 `BTCUSDT`，与 API 文档一致
