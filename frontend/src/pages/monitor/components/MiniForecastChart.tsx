import { useTranslation } from 'react-i18next';
import type { ForecastPoint } from '@/mocks/monitor';

interface MiniForecastChartProps {
  forecast: ForecastPoint[];
}

export default function MiniForecastChart({ forecast }: MiniForecastChartProps) {
  const { t } = useTranslation();
  if (!forecast || forecast.length < 4) {
    return (
      <div className="h-14 flex items-center justify-center text-[10px] text-foreground-400">
        {t('monitor.chart.noData')}
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
  const BAR_MAX_H = 12;
  const BAR_BASE_Y = H - PAD_BOTTOM;

  const n = forecast.length;
  const stepX = INNER_W / (n - 1);

  const temps = forecast.map((f) => f.temperature);
  const minTemp = Math.min(...temps);
  const maxTemp = Math.max(...temps);
  const tempRange = maxTemp - minTemp || 1;
  const tempPad = tempRange * 0.15;
  const tempLow = minTemp - tempPad;
  const tempHigh = maxTemp + tempPad;
  const tempSpan = tempHigh - tempLow;

  const maxPrecip = Math.max(...forecast.map((f) => f.precipitation), 0.1);

  // Temperature line path
  const tempLineD = forecast
    .map((f, i) => {
      const x = PAD_LEFT + i * stepX;
      const y = PAD_TOP + INNER_H - ((f.temperature - tempLow) / tempSpan) * INNER_H;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  // Area fill path
  const areaD = `${tempLineD} L${W - PAD_RIGHT},${BAR_BASE_Y} L${PAD_LEFT},${BAR_BASE_Y} Z`;

  // Precipitation bars — one every 2 hours to keep it clean
  const barWidth = Math.max(stepX * 0.8, 1.2);
  const bars: { x: number; w: number; h: number }[] = [];
  for (let i = 0; i < n; i += 2) {
    const p = forecast[i].precipitation;
    if (p > 0) {
      const x = PAD_LEFT + i * stepX;
      bars.push({
        x: x - barWidth / 2,
        w: barWidth,
        h: (p / maxPrecip) * BAR_MAX_H,
      });
    }
  }

  // Time labels — now, +24h, +48h
  const labelIndices = [0, Math.floor(n / 2), n - 1];
  const labelTexts = [t('monitor.chart.now'), '+24h', '+48h'];

  // Color stops based on temperature range
  const getTempColor = (t: number) => {
    if (t >= 45) return 'oklch(var(--red-500))';
    if (t >= 40) return 'oklch(var(--orange-400))';
    if (t >= 35) return 'oklch(var(--yellow-500))';
    return 'oklch(var(--primary-500))';
  };

  const midTempColor = getTempColor((minTemp + maxTemp) / 2);

  return (
    <div className="mt-2">
      {/* Dual legend */}
      <div className="flex items-center justify-between mb-1 px-0.5">
        <div className="flex items-center gap-1.5">
          <svg width="14" height="4" viewBox="0 0 14 4">
            <line x1="0" y1="2" x2="14" y2="2" stroke={midTempColor} strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className="text-[9px] text-foreground-400">{t('monitor.chart.temperature')}</span>
          <span className="text-[9px] font-medium text-foreground-700">{minTemp.toFixed(0)}° – {maxTemp.toFixed(0)}°</span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="10" height="4" viewBox="0 0 10 4">
            <rect x="0" y="0" width="10" height="4" rx="1" fill="oklch(var(--accent-400) / 0.5)" />
          </svg>
          <span className="text-[9px] text-foreground-400">{t('monitor.chart.precipitation')}</span>
          <span className="text-[9px] font-medium text-foreground-700">
            {maxPrecip.toFixed(1)}mm
          </span>
        </div>
      </div>

      {/* Chart */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        aria-label={t('monitor.chart.ariaMini')}
      >
        {/* Grid lines */}
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

        {/* Precipitation bars */}
        {bars.map((b, idx) => (
          <rect
            key={idx}
            x={b.x}
            y={BAR_BASE_Y - b.h}
            width={b.w}
            height={b.h}
            fill="oklch(var(--accent-400) / 0.4)"
            rx="0.8"
          />
        ))}

        {/* Temperature area fill */}
        <path d={areaD} fill="oklch(var(--primary-500) / 0.07)" />

        {/* Temperature line */}
        <path
          d={tempLineD}
          fill="none"
          stroke={midTempColor}
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

        {/* Start/end temperature labels */}
        <text
          x={PAD_LEFT + 2}
          y={PAD_TOP + INNER_H - ((forecast[0].temperature - tempLow) / tempSpan) * INNER_H + 3}
          className="text-[7px]"
          fill="oklch(var(--foreground-500))"
          textAnchor="start"
        >
          {forecast[0].temperature.toFixed(0)}°
        </text>
        <text
          x={W - PAD_RIGHT - 2}
          y={PAD_TOP + INNER_H - ((forecast[n - 1].temperature - tempLow) / tempSpan) * INNER_H + 3}
          className="text-[7px]"
          fill="oklch(var(--foreground-500))"
          textAnchor="end"
        >
          {forecast[n - 1].temperature.toFixed(0)}°
        </text>
      </svg>
    </div>
  );
}