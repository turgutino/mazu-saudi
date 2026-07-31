import { useState, useEffect, useMemo } from 'react';
import type { MonitorRegionData } from '@/mocks/monitor';

interface SaudiMapProps {
  regions: MonitorRegionData[];
  selectedRegionId: string | null;
  onSelectRegion: (id: string) => void;
  activeHazardId: string | null;
  tioEnabled?: boolean;
}

const riskDotBg: Record<string, string> = {
  green: 'bg-emerald-500',
  yellow: 'bg-yellow-500',
  orange: 'bg-orange-500',
  red: 'bg-red-500',
};

const riskRing: Record<string, string> = {
  green: 'ring-emerald-200',
  yellow: 'ring-yellow-200',
  orange: 'ring-orange-200',
  red: 'ring-red-200',
};

const riskPulse: Record<string, string> = {
  green: 'bg-emerald-400/20',
  yellow: 'bg-yellow-400/25',
  orange: 'bg-orange-400/30',
  red: 'bg-red-400/35',
};

const riskSize: Record<string, string> = {
  green: 'w-3 h-3',
  yellow: 'w-3.5 h-3.5',
  orange: 'w-4 h-4',
  red: 'w-4.5 h-4.5',
};

// Google Maps embed URL — 沙特全境, zoom 6, 地形图, 无 UI
const MAP_SRC = 'https://www.google.com/maps?q=Saudi+Arabia&z=6&t=m&output=embed';

export default function SaudiMap({
  regions,
  selectedRegionId,
  onSelectRegion,
  activeHazardId,
  tioEnabled,
}: SaudiMapProps) {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  const getEffectiveRisk = (region: MonitorRegionData) => {
    if (!activeHazardId) return region.highestRiskLevel;
    const hazard = region.hazards.find((h) => h.hazardId === activeHazardId);
    return hazard?.riskLevel ?? 'green';
  };

  const shouldDim = (region: MonitorRegionData) => {
    if (!activeHazardId) return false;
    const hazard = region.hazards.find((h) => h.hazardId === activeHazardId);
    return !hazard || hazard.riskLevel === 'green';
  };

  const riskOrder: Record<string, number> = { red: 4, orange: 3, yellow: 2, green: 1 };
  const sortedForRender = useMemo(
    () => [...regions].sort((a, b) => riskOrder[getEffectiveRisk(b)] - riskOrder[getEffectiveRisk(a)]),
    [regions, activeHazardId],
  );

  // Stats for info bar
  const alertCount = regions.filter((r) => r.activeAlertCount > 0).length;
  const orangePlusCount = regions.filter((r) => r.highestRiskLevel === 'orange' || r.highestRiskLevel === 'red').length;

  return (
    <div className="relative w-full h-full min-h-[400px] rounded-xl overflow-hidden select-none">
      {/* ---- Google Maps iframe ---- */}
      <iframe
        src={MAP_SRC}
        className="absolute inset-0 w-full h-full border-0"
        style={{ filter: 'saturate(0.85) contrast(1.05)' }}
        loading="lazy"
        allowFullScreen
        referrerPolicy="no-referrer-when-downgrade"
        title="沙特阿拉伯气象监测地图"
        onLoad={() => setMapLoaded(true)}
      />

      {/* Map overlay — 柔焦遮罩让标记点更突出 */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/15 via-transparent to-black/30 pointer-events-none z-[5]" />

      {/* ---- Markers layer ---- */}
      <div className="absolute inset-0 z-10">
        {sortedForRender.map((region) => {
          const isSelected = selectedRegionId === region.regionId;
          const effectiveRisk = getEffectiveRisk(region);
          const dimmed = shouldDim(region);
          const hasAlert = effectiveRisk !== 'green';
          const isHovered = hoveredRegion === region.regionId;

          return (
            <div
              key={region.regionId}
              className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-500 ${dimmed ? 'opacity-20 scale-90' : 'opacity-100'}`}
              style={{ left: `${region.mapX}%`, top: `${region.mapY}%` }}
              onClick={() => onSelectRegion(region.regionId)}
              onMouseEnter={() => setHoveredRegion(region.regionId)}
              onMouseLeave={() => setHoveredRegion(null)}
            >
              {/* Pulse ring */}
              {hasAlert && !dimmed && (
                <>
                  <div
                    className={`absolute inset-0 rounded-full ${riskPulse[effectiveRisk]}`}
                    style={{ animation: 'mapPing 2.8s cubic-bezier(0, 0, 0.2, 1) infinite', transform: 'scale(2.5)' }}
                  />
                  <div
                    className={`absolute inset-0 rounded-full ${riskPulse[effectiveRisk]}`}
                    style={{ animation: 'mapPing 2.8s cubic-bezier(0, 0, 0.2, 1) infinite 0.9s', transform: 'scale(2.5)' }}
                  />
                </>
              )}

              {/* Main dot */}
              <div
                className={`relative rounded-full transition-all duration-300 ${riskSize[effectiveRisk]} ${riskDotBg[effectiveRisk]} ${isSelected ? 'scale-[1.6] z-20 ring-[4px] ring-accent-500/50' : `z-10 ring-[3px] ring-white/90 ${riskRing[effectiveRisk]}`}`}
                style={{ boxShadow: isSelected ? '0 0 14px 3px oklch(var(--accent-500) / 0.45)' : hasAlert ? '0 0 8px 2px rgba(0,0,0,0.15)' : 'none' }}
              >
                {/* Inner glow dot */}
                <div className={`absolute inset-1 rounded-full ${isSelected ? 'bg-accent-300/50' : 'bg-white/30'} transition-opacity`} />
              </div>

              {/* Label */}
              <div
                className={`absolute top-full left-1/2 -translate-x-1/2 mt-1.5 whitespace-nowrap transition-all duration-300 ${isSelected || isHovered ? 'opacity-100 translate-y-0' : 'opacity-70 translate-y-0.5'}`}
              >
                <span className="px-1.5 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-white text-[11px] font-medium tracking-wide">
                  {region.regionName}
                </span>
                {region.activeAlertCount > 0 && !activeHazardId && (
                  <span className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-500 text-white text-[9px] font-bold ring-1 ring-white/60">
                    {region.activeAlertCount}
                  </span>
                )}
              </div>

              {/* Tooltip */}
              {isHovered && !dimmed && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 z-40 pointer-events-none">
                  <div className="bg-background-50/95 backdrop-blur-md border border-background-200/80 rounded-xl shadow-2xl p-4 min-w-[220px]">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <span className="text-sm font-semibold text-foreground-900">{region.regionName}</span>
                        <span className="text-[10px] text-foreground-400 ml-2">{region.nameEn}</span>
                      </div>
                      <span className={`w-3 h-3 rounded-full ${riskDotBg[effectiveRisk]} ring-2 ring-white`} />
                    </div>

                    {/* Readings grid */}
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs text-foreground-600 mb-3">
                      <span className="text-foreground-400">温度</span>
                      <span className="text-right font-semibold text-foreground-800">{region.readings.temperature}°C</span>
                      <span className="text-foreground-400">湿度</span>
                      <span className="text-right font-semibold text-foreground-800">{region.readings.humidity}%</span>
                      <span className="text-foreground-400">风速</span>
                      <span className="text-right font-semibold text-foreground-800">{region.readings.windSpeed} m/s</span>
                      <span className="text-foreground-400">CAPE</span>
                      <span className="text-right font-semibold text-foreground-800">{region.readings.cape} J/kg</span>
                    </div>

                    {/* Enhanced indicators */}
                    {tioEnabled && (
                      <div className="border-t border-background-200/50 pt-2 mb-2">
                        <p className="text-[10px] text-foreground-400 mb-1.5 flex items-center gap-1">
                          <i className="ri-flashlight-line text-emerald-500" />
                          Tomorrow.io 增强
                        </p>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div className="text-center bg-background-100 rounded-md py-1">
                            <p className="text-[9px] text-foreground-400">阵风</p>
                            <p className="font-bold text-foreground-700">{region.readings.windGust > 0 ? `${region.readings.windGust}` : '—'} <span className="text-[9px] font-normal">m/s</span></p>
                          </div>
                          <div className="text-center bg-background-100 rounded-md py-1">
                            <p className="text-[9px] text-foreground-400">火险</p>
                            <p className={`font-bold ${region.readings.fireIndex >= 4 ? 'text-red-600' : region.readings.fireIndex >= 2 ? 'text-orange-500' : 'text-foreground-700'}`}>
                              {region.readings.fireIndex > 0 ? region.readings.fireIndex : '—'}
                            </p>
                          </div>
                          <div className="text-center bg-background-100 rounded-md py-1">
                            <p className="text-[9px] text-foreground-400">雷暴</p>
                            <p className={`font-bold ${region.readings.thunderstormProb >= 50 ? 'text-red-600' : region.readings.thunderstormProb >= 30 ? 'text-orange-500' : 'text-foreground-700'}`}>
                              {region.readings.thunderstormProb > 0 ? `${region.readings.thunderstormProb}%` : '—'}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Alert badge */}
                    {region.activeAlertCount > 0 && (
                      <div className="pt-2 border-t border-background-200/50">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 text-red-700 text-[11px] font-medium">
                          <i className="ri-alert-line text-[10px]" />
                          {region.activeAlertCount} 个活跃预警
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ---- Map loading overlay ---- */}
      {!mapLoaded && (
        <div className="absolute inset-0 z-[6] flex items-center justify-center bg-background-100/60 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-2 border-primary-300 border-t-primary-500 rounded-full animate-spin" />
            <p className="text-sm text-foreground-500">地图加载中...</p>
          </div>
        </div>
      )}

      {/* ---- Compass ---- */}
      <div className="absolute top-4 right-4 z-20 w-12 h-12 rounded-full border border-white/30 bg-black/40 backdrop-blur-md flex items-center justify-center">
        <div className="relative w-full h-full">
          <span className="absolute top-0.5 left-1/2 -translate-x-1/2 text-[8px] font-bold text-white/90">N</span>
          <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 text-[8px] text-white/50">S</span>
          <span className="absolute left-0.5 top-1/2 -translate-y-1/2 text-[8px] text-white/50">W</span>
          <span className="absolute right-0.5 top-1/2 -translate-y-1/2 text-[8px] text-white/50">E</span>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-0 h-0 border-l-[4px] border-r-[4px] border-b-[6px] border-l-transparent border-r-transparent border-b-white/80" />
        </div>
      </div>

      {/* ---- Bottom info bar ---- */}
      <div className="absolute bottom-4 left-4 right-4 z-20 flex items-center justify-between">
        {/* Risk legend */}
        <div className="bg-black/50 backdrop-blur-md rounded-lg px-3 py-2 border border-white/15">
          <div className="flex items-center gap-3">
            {[
              { level: 'green', label: '低风险' },
              { level: 'yellow', label: '黄色预警' },
              { level: 'orange', label: '橙色预警' },
              { level: 'red', label: '红色预警' },
            ].map((item) => (
              <div key={item.level} className="flex items-center gap-1.5">
                <span className={`w-2.5 h-2.5 rounded-full ${riskDotBg[item.level]} ring-1 ring-white/40`} />
                <span className="text-[10px] text-white/80 font-medium">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stats badges */}
        <div className="flex items-center gap-3">
          <div className="bg-black/50 backdrop-blur-md rounded-lg px-3 py-2 border border-white/15">
            <span className="text-[11px] text-white/80">
              <strong className="text-white">{regions.length}</strong> 监测站 · {' '}
              <strong className="text-red-400">{alertCount}</strong> 预警区域 · {' '}
              <strong className="text-orange-400">{orangePlusCount}</strong> 橙色+
            </span>
          </div>

          {/* Data freshness indicator */}
          <div className="bg-black/50 backdrop-blur-md rounded-lg px-3 py-2 border border-white/15 flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full animate-pulse ${regions.length > 0 && regions[0].readings.temperature > 0 ? 'bg-emerald-400' : 'bg-yellow-400'}`} />
            <span className="text-[10px] text-white/70">
              {regions.length > 0 && regions[0].readings.temperature > 0 ? '实时数据' : '等待数据...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}