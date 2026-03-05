import {
  createChart,
  ColorType,
  type IChartApi,
  type CandlestickData,
  type HistogramData,
  type UTCTimestamp,
} from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';
import type { KlineBar } from '../types/api';

function barToCandlestick(bar: KlineBar): CandlestickData {
  return {
    time: Math.floor(bar.ot / 1000) as UTCTimestamp,
    open: parseFloat(bar.o),
    high: parseFloat(bar.h),
    low: parseFloat(bar.l),
    close: parseFloat(bar.c),
  };
}

function barToVolume(bar: KlineBar): HistogramData {
  const o = parseFloat(bar.o);
  const c = parseFloat(bar.c);
  return {
    time: Math.floor(bar.ot / 1000) as UTCTimestamp,
    value: parseFloat(bar.v),
    color: c >= o ? 'rgba(0, 177, 128, 0.5)' : 'rgba(246, 61, 85, 0.5)',
  };
}

const CHART_COLORS = {
  background: '#0b0e11',
  text: '#848e9c',
  grid: '#2b3139',
  up: '#00b180',
  down: '#f63d55',
  upBorder: '#00b180',
  downBorder: '#f63d55',
};

interface KlineChartProps {
  data: KlineBar[];
  height?: number;
}

export function KlineChart({ data, height }: KlineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<{ setData: (data: CandlestickData[]) => void } | null>(null);
  const volumeRef = useRef<{ setData: (data: HistogramData[]) => void } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const w = el.clientWidth;
    const h = el.clientHeight || (height ?? 400);
    if (w <= 0) return;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: CHART_COLORS.background },
        textColor: CHART_COLORS.text,
      },
      grid: {
        vertLines: { color: CHART_COLORS.grid },
        horzLines: { color: CHART_COLORS.grid },
      },
      width: w,
      height: h,
      rightPriceScale: {
        borderColor: CHART_COLORS.grid,
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      timeScale: {
        borderColor: CHART_COLORS.grid,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { labelBackgroundColor: CHART_COLORS.up },
        horzLine: { labelBackgroundColor: CHART_COLORS.up },
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: CHART_COLORS.up,
      downColor: CHART_COLORS.down,
      borderUpColor: CHART_COLORS.upBorder,
      borderDownColor: CHART_COLORS.downBorder,
      wickUpColor: CHART_COLORS.up,
      wickDownColor: CHART_COLORS.down,
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
      borderVisible: false,
    });

    if (data.length) {
      const candleData = data.map(barToCandlestick);
      const volumeData = data.map(barToVolume);
      candleSeries.setData(candleData);
      volumeSeries.setData(volumeData);
      chart.timeScale().fitContent();
    }

    chartRef.current = chart;
    candleRef.current = candleSeries;
    volumeRef.current = volumeSeries;

    const ro = new ResizeObserver(() => {
      if (!el || !chartRef.current) return;
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (w > 0 && h > 0) chartRef.current.applyOptions({ width: w, height: h });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!candleRef.current || !volumeRef.current || !data.length) return;
    const candleData = data.map(barToCandlestick);
    const volumeData = data.map(barToVolume);
    candleRef.current.setData(candleData);
    volumeRef.current.setData(volumeData);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', minHeight: 0, flex: 1 }}
    />
  );
}
