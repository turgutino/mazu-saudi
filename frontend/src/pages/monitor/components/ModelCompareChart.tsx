import type { ForecastPoint } from '@/mocks/monitor';

interface ModelCompareChartProps {
  forecastOm: ForecastPoint[];
  forecastCma: ForecastPoint[];
}

export default function ModelCompareChart({ forecastOm, forecastCma }: ModelCompareChartProps) {
  if (!forecastOm || forecastOm.length < 4) {
    return (
      <div className="h-14 flex items-center justify-center text-[10px] text-foreground-400">
        暂无预报数据
      </div>
    );
  }

  const W = 260;
  const H = 56;
  const PAD_TOP = 5;
  const PAD_BOTTOM = 12;
  const PAD_LEFT = 1;
  const PAD_RIGHT = 1;
  const INNER_H = H - PAD_TOP - PAD_BOTTOM;
  const INNER_W = W - PAD_LEFT - PAD_RIGHT;
  const BAR_MAX_H = 10;
  const BAR_BASE_Y = H - PAD_BOTTOM;

  const n = forecastOm.length;
  const stepX = INNER_W / (n - 1);

  // Temperature range (union of both models)
  const allTemps = [...forecastOm.map((f) => f.temperature), ...forecastCma.map((f) => f.temperature)];
  const minTemp = Math.min(...allTemps);
  const maxTemp = Math.max(...allTemps);
  const tempRange = maxTemp - minTemp || 1;
  const tempPad = tempRange * 0.15;
  const tempLow = minTemp - tempPad;
  const tempHigh = maxTemp + tempPad;
  const tempSpan = tempHigh - tempLow;

  // Precipitation bars from Open-Meteo
  const maxPrecip = Math.max(...forecastOm.map((f) => f.precipitation), 0.1);
  const barWidth = Math.max(stepX * 0.8, 1.2);
  const bars: { x: number; w: number; h: number }[] = [];
  for (let i = 0; i < n; i += 2) {
    const p = forecastOm[i].precipitation;
    if (p > 0) {
      const x = PAD_LEFT + i * stepX;
      bars.push({ x: x - barWidth / 2, w: barWidth, h: (p / maxPrecip) * BAR_MAX_H });
    }
  }

  // Open-Meteo line path (solid)
  const omLineD = forecastOm
    .map((f, i) => {
      const x = PAD_LEFT + i * stepX;
      const y = PAD_TOP + INNER_H - ((f.temperature - tempLow) / tempSpan) * INNER_H;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  // CMA line path (dashed)
  const cmaLineD = forecastCma
    .slice(0, n)
    .map((f, i) => {
      const x = PAD_LEFT + i * stepX;
      const y = PAD_TOP + INNER_H - ((f.temperature - tempLow) / tempSpan) * INNER_H;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  // Open-Meteo area fill
  const omAreaD = `${omLineD} L${W - PAD_RIGHT},${BAR_BASE_Y} L${PAD_LEFT},${BAR_BASE_Y} Z`;

  // Time labels
  const labelIndices = [0, Math.floor(n / 2), n - 1];
  const labelTexts = ['现在', '+24h', '+48h'];

  return (
    <div className="mt-2">
      {/* Dual legend */}
      <div className="flex items-center justify-between mb-1 px-0.5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <svg width="14" height="4" viewBox="0 0 14 4">
              <line x1="0" y1="2" x2="14" y2="2" stroke="oklch(var(--primary-500))" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span className="text-[9px] text-foreground-400">ECMWF</span>
          </div>
          <div className="flex items-center gap-1">
            <svg width="14" height="4" viewBox="0 0 14 4">
              <line x1="0" y1="2" x2="14" y2="2" stroke="oklch(var(--accent-500))" strokeWidth="2" strokeDasharray="3,2" strokeLinecap="round" />
            </svg>
            <span className="text-[9px] text-foreground-400">CMA</span>
          </div>
        </div>
        <span className="text-[9px] text-foreground-500">
          {minTemp.toFixed(0)}° – {maxTemp.toFixed(0)}°
        </span>
      </div>

      {/* Chart */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        aria-label="48小时双模型温度对比预报"
      >
        {/* Grid */}
        {[0.25, 0.5, 0.75].map((pct) => (
          <line
            key={pct}
            x1={PAD_LEFT}
            y1={PAD_TOP + INNER_H * (1 - pct)}
            x2={W - PAD_RIGHT}
            y2={PAD_TOP + INNER_H * (1 - pct)}
            stroke="oklch(var(--foreground-700) / 0.08)"
            strokeWidth="0.5"
          />
        ))}

        {/* Precip bars from Open-Meteo */}
        {bars.map((b, idx) => (
          <rect
            key={idx}
            x={b.x}
            y={BAR_BASE_Y - b.h}
            width={b.w}
            height={b.h}
            fill="oklch(var(--accent-400) / 0.35)"
            rx="0.8"
          />
        ))}

        {/* Open-Meteo area fill */}
        <path d={omAreaD} fill="oklch(var(--primary-500) / 0.05)" />

        {/* CMA line (dashed) */}
        <path
          d={cmaLineD}
          fill="none"
          stroke="oklch(var(--accent-500))"
          strokeWidth="1.4"
          strokeDasharray="3,2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Open-Meteo line (solid) */}
        <path
          d={omLineD}
          fill="none"
          stroke="oklch(var(--primary-500))"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Time labels */}
        {labelIndices.map((idx, labelIdx) => {
          const x = PAD_LEFT + idx * stepX;
          return (
            <text
              key={labelIdx}
              x={labelIdx === 0 ? PAD_LEFT : labelIdx === 2 ? W - PAD_RIGHT : x}
              y={H - 1}
              textAnchor={labelIdx === 0 ? 'start' : labelIdx === 2 ? 'end' : 'middle'}
              className="text-[7px]"
              fill="oklch(var(--foreground-400))"
            >
              {labelTexts[labelIdx]}
            </text>
          );
        })}

        {/* End temp labels */}
        <text
          x={PAD_LEFT + 2}
          y={PAD_TOP + INNER_H - ((forecastOm[0].temperature - tempLow) / tempSpan) * INNER_H + 3}
          className="text-[7px]"
          fill="oklch(var(--foreground-500))"
          textAnchor="start"
        >
          {forecastOm[0].temperature.toFixed(0)}°
        </text>
        <text
          x={W - PAD_RIGHT - 2}
          y={PAD_TOP + INNER_H - ((forecastOm[n - 1].temperature - tempLow) / tempSpan) * INNER_H + 3}
          className="text-[7px]"
          fill="oklch(var(--foreground-500))"
          textAnchor="end"
        >
          {forecastOm[n - 1].temperature.toFixed(0)}°
        </text>
      </svg>
    </div>
  );
}