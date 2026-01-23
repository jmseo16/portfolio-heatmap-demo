'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';

type Holding = {
  symbol: string;
  name: string;
  shares: number;
};

type PriceState = {
  price: number;     // current
  prevClose: number; // baseline for % change
};

const HOLDINGS: Holding[] = [
  { symbol: 'AAPL', name: 'Apple', shares: 10 },
  { symbol: 'TSLA', name: 'Tesla', shares: 5 },
  // User said "S&P 100주" — demo uses SPY as S&P exposure proxy
  { symbol: 'SPY', name: 'S&P 500 ETF (Proxy)', shares: 100 },
];

// simple deterministic-ish RNG
function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6D2B79F5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

// Map % change to a red/green scale (Finviz-ish). Negative => red, positive => green.
function pctToColor(pct: number) {
  const p = clamp(pct, -8, 8); // cap for nicer colors
  if (p === 0) return '#3b3b3b';

  const t = Math.abs(p) / 8;

  if (p > 0) {
    // green
    const r = Math.round(20 + (60 - 20) * (1 - t));
    const g = Math.round(110 + (220 - 110) * t);
    const b = Math.round(20 + (60 - 20) * (1 - t));
    return `rgb(${r},${g},${b})`;
  } else {
    // red
    const r = Math.round(140 + (230 - 140) * t);
    const g = Math.round(25 + (60 - 25) * (1 - t));
    const b = Math.round(25 + (60 - 25) * (1 - t));
    return `rgb(${r},${g},${b})`;
  }
}

export default function Page() {
  const [prices, setPrices] = useState<Record<string, PriceState>>({
    AAPL: { price: 190.0, prevClose: 188.5 },
    TSLA: { price: 230.0, prevClose: 232.0 },
    SPY: { price: 480.0, prevClose: 479.0 },
  });

  const seedRef = useRef<number>(123456);
  const rngRef = useRef<() => number>(mulberry32(seedRef.current));

  // simulate “real-time” price updates (1s tick)
  useEffect(() => {
    const id = setInterval(() => {
      setPrices((prev) => {
        const next: Record<string, PriceState> = { ...prev };
        for (const h of HOLDINGS) {
          const ps = prev[h.symbol];
          const r = rngRef.current();

          // symbol-specific volatility
          const vol = h.symbol === 'TSLA' ? 0.012 : h.symbol === 'AAPL' ? 0.006 : 0.003;

          // random walk: small drift + noise
          const shock = (r - 0.5) * 2 * vol; // [-vol, +vol]
          const drift = 0.0001; // tiny upward drift
          const newPrice = Math.max(1, ps.price * (1 + drift + shock));

          next[h.symbol] = { ...ps, price: Number(newPrice.toFixed(2)) };
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(id);
  }, []);

  const enriched = useMemo(() => {
    return HOLDINGS.map((h) => {
      const ps = prices[h.symbol];
      const price = ps?.price ?? 0;
      const prevClose = ps?.prevClose ?? price;
      const value = h.shares * price;

      const pct = prevClose === 0 ? 0 : ((price - prevClose) / prevClose) * 100;
      const pnl = (price - prevClose) * h.shares;

      return { ...h, price, prevClose, value, pct, pnl };
    });
  }, [prices]);

  const totalValue = enriched.reduce((acc, x) => acc + x.value, 0);

  const option = useMemo(() => {
    const data = enriched.map((x) => ({
      name: x.symbol,
      value: x.value, // treemap size
      itemStyle: { color: pctToColor(x.pct) },
      symbol: x.symbol,
      fullName: x.name,
      shares: x.shares,
      price: x.price,
      prevClose: x.prevClose,
      pct: x.pct,
      pnl: x.pnl,
      weight: totalValue ? (x.value / totalValue) * 100 : 0,
    }));

    return {
      backgroundColor: '#0b0f14',
      title: {
        text: 'Portfolio Heatmap (Demo)',
        left: 16,
        top: 12,
        textStyle: { color: '#e8eef6', fontSize: 16, fontWeight: '600' },
        subtext: 'Size = market value, Color = % change (vs prev close), Updates every 1s (simulated)',
        subtextStyle: { color: '#9fb0c3', fontSize: 12 },
      },
      tooltip: {
        confine: true,
        backgroundColor: 'rgba(16, 20, 28, 0.95)',
        borderColor: 'rgba(255,255,255,0.12)',
        textStyle: { color: '#e8eef6' },
        formatter: (params: any) => {
          const d = params.data || {};
          const sign = d.pct >= 0 ? '+' : '';
          const pnlSign = d.pnl >= 0 ? '+' : '';
          return `
            <div style="min-width:220px">
              <div style="font-size:14px;font-weight:700;margin-bottom:6px">${d.symbol} <span style="opacity:.8;font-weight:500">(${d.fullName})</span></div>
              <div style="display:flex;justify-content:space-between"><span>Shares</span><b>${d.shares}</b></div>
              <div style="display:flex;justify-content:space-between"><span>Price</span><b>$${Number(d.price).toFixed(2)}</b></div>
              <div style="display:flex;justify-content:space-between"><span>Prev Close</span><b>$${Number(d.prevClose).toFixed(2)}</b></div>
              <div style="display:flex;justify-content:space-between"><span>Change</span><b>${sign}${Number(d.pct).toFixed(2)}%</b></div>
              <div style="display:flex;justify-content:space-between"><span>PnL (vs prev close)</span><b>${pnlSign}$${Number(d.pnl).toFixed(2)}</b></div>
              <div style="display:flex;justify-content:space-between"><span>Weight</span><b>${Number(d.weight).toFixed(2)}%</b></div>
              <div style="display:flex;justify-content:space-between"><span>Value</span><b>$${Number(d.value).toFixed(2)}</b></div>
            </div>
          `;
        },
      },
      series: [
        {
          type: 'treemap',
          left: 12,
          right: 12,
          top: 74,
          bottom: 12,
          roam: false,
          nodeClick: false,
          breadcrumb: { show: false },
          label: {
            show: true,
            formatter: (p: any) => {
              const d = p.data || {};
              const sign = d.pct >= 0 ? '+' : '';
              return `${d.name}\n${sign}${Number(d.pct).toFixed(2)}%`;
            },
            color: '#e8eef6',
            fontWeight: 700,
            fontSize: 16,
            lineHeight: 18,
          },
          itemStyle: {
            borderColor: 'rgba(255,255,255,0.14)',
            borderWidth: 2,
            gapWidth: 4,
          },
          emphasis: { itemStyle: { borderColor: 'rgba(255,255,255,0.45)' } },
          data,
        },
      ],
    };
  }, [enriched, totalValue]);

  return (
    <div style={{ minHeight: '100vh', background: '#0b0f14' }}>
      <div style={{ padding: 12, maxWidth: 1200, margin: '0 auto' }}>
        <div
          style={{
            marginTop: 8,
            marginBottom: 10,
            display: 'flex',
            gap: 12,
            flexWrap: 'wrap',
            color: '#9fb0c3',
            fontSize: 12,
          }}
        >
          <div><b style={{ color: '#e8eef6' }}>Total Value:</b> ${totalValue.toFixed(2)}</div>
          <div><b style={{ color: '#e8eef6' }}>Holdings:</b> {HOLDINGS.map(h => `${h.symbol}(${h.shares})`).join(', ')}</div>
          <div><b style={{ color: '#e8eef6' }}>Update:</b> 1s simulated tick</div>
        </div>

        <div style={{ borderRadius: 14, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)' }}>
          <ReactECharts option={option} style={{ height: 520, width: '100%' }} />
        </div>

        <div style={{ marginTop: 12, color: '#9fb0c3', fontSize: 12 }}>
          Demo only: replace the simulated tick with a real price feed later.
        </div>
      </div>
    </div>
  );
}
