import type { MonitorRegionData } from '@/mocks/monitor';
import { hazardTypes } from '@/mocks/monitor';
import RiskBadge from '@/components/base/RiskBadge';
import MiniForecastChart from './MiniForecastChart';
import ModelCompareChart from './ModelCompareChart';

interface MonitorSidebarProps {
  regions: MonitorRegionData[];
  regionsCma: MonitorRegionData[] | null;
  selectedRegionId: string | null;
  onSelectRegion: (id: string) => void;
  activeHazardId: string | null;
  onSetHazard: (id: string | null) => void;
  showComparison: boolean;
  cmaEnabled: boolean;
  cmaLoading: boolean;
  cmaError: string | null;
  tioEnabled: boolean;
  tioLoading: boolean;
  tioError: string | null;
}

const riskOrder: Record<string, number> = { red: 4, orange: 3, yellow: 2, green: 1 };

export default function MonitorSidebar({
  regions,
  regionsCma,
  selectedRegionId,
  onSelectRegion,
  activeHazardId,
  onSetHazard,
  showComparison,
  cmaEnabled,
  cmaLoading,
  cmaError,
  tioEnabled,
  tioLoading,
  tioError,
}: MonitorSidebarProps) {
  const sortedRegions = [...regions].sort(
    (a, b) => riskOrder[b.highestRiskLevel] - riskOrder[a.highestRiskLevel],
  );

  const totalAlerts = regions.reduce((sum, r) => sum + r.activeAlertCount, 0);

  // Hazard-level counts
  const hazardCounts = hazardTypes.map((ht) => {
    const count = regions.filter((r) =>
      r.hazards.some((h) => h.hazardId === ht.id && h.riskLevel !== 'green'),
    ).length;
    return { ...ht, count };
  });

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-background-200/70">
        <h2 className="font-heading text-sm text-foreground-900">监测区域概览</h2>
        <p className="text-xs text-foreground-400 mt-0.5">
          {regions.length} 个区域 · {totalAlerts} 个活跃预警
        </p>
      </div>

      {/* Hazard filter */}
      <div className="px-4 py-3 border-b border-background-200/70">
        <p className="text-xs text-foreground-500 mb-2">灾种图层筛选</p>
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => onSetHazard(null)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap cursor-pointer transition-colors ${
              activeHazardId === null
                ? 'bg-primary-500 text-white'
                : 'bg-background-100 text-foreground-600 hover:bg-background-200'
            }`}
          >
            全部
          </button>
          {hazardCounts.map((h) => (
            <button
              key={h.id}
              onClick={() => onSetHazard(h.id)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap cursor-pointer transition-colors flex items-center gap-1 ${
                activeHazardId === h.id
                  ? 'bg-primary-500 text-white'
                  : 'bg-background-100 text-foreground-600 hover:bg-background-200'
              }`}
            >
              <i className={`${h.icon} text-[10px]`} />
              {h.name}
              {h.count > 0 && (
                <span
                  className={`ml-0.5 inline-flex items-center justify-center min-w-[14px] h-[14px] rounded-full text-[9px] font-bold ${
                    activeHazardId === h.id ? 'bg-white/20 text-white' : 'bg-red-500 text-white'
                  }`}
                >
                  {h.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Region list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {sortedRegions.map((region) => {
          const isSelected = selectedRegionId === region.regionId;
          const topHazard = region.hazards.reduce((top, h) =>
            riskOrder[h.riskLevel] > riskOrder[top.riskLevel] ? h : top,
          );
          const cmaRegion = regionsCma?.find((r) => r.regionId === region.regionId);
          const showCompare = showComparison && cmaEnabled && cmaRegion && !cmaLoading;
          const showCmaLoading = showComparison && cmaEnabled && cmaLoading;

          return (
            <div
              key={region.regionId}
              onClick={() => onSelectRegion(region.regionId)}
              className={`p-3 rounded-lg cursor-pointer transition-all duration-200 border ${
                isSelected
                  ? 'bg-primary-50 border-primary-200 shadow-sm'
                  : 'bg-background-50 border-background-200/50 hover:bg-background-100 hover:border-background-200'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground-900">
                    {region.regionName}
                  </span>
                  <span className="text-[10px] text-foreground-400">{region.nameEn}</span>
                </div>
                <RiskBadge level={region.highestRiskLevel} size="sm" showLabel={false} />
              </div>

              {/* Active hazards */}
              {region.activeAlertCount > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {region.hazards
                    .filter((h) => h.riskLevel !== 'green')
                    .map((h) => (
                      <span
                        key={h.hazardId}
                        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          h.riskLevel === 'orange'
                            ? 'bg-orange-50 text-orange-700'
                            : h.riskLevel === 'yellow'
                              ? 'bg-yellow-50 text-yellow-700'
                              : 'bg-red-50 text-red-700'
                        }`}
                      >
                        <i
                          className={`${hazardTypes.find((ht) => ht.id === h.hazardId)?.icon || ''} text-[9px]`}
                        />
                        {h.hazardName} {(h.probability * 100).toFixed(0)}%
                        <i
                          className={`text-[9px] ${
                            h.trend === 'rising'
                              ? 'ri-arrow-up-line text-red-500'
                              : h.trend === 'falling'
                                ? 'ri-arrow-down-line text-accent-500'
                                : 'ri-subtract-line text-foreground-400'
                          }`}
                        />
                      </span>
                    ))}
                </div>
              )}

              {/* Mini readings row */}
              <div className="grid grid-cols-4 gap-1 text-[10px]">
                <div className="text-center">
                  <p className="text-foreground-400">温度</p>
                  <p className="font-medium text-foreground-700">{region.readings.temperature}°</p>
                </div>
                <div className="text-center">
                  <p className="text-foreground-400">湿度</p>
                  <p className="font-medium text-foreground-700">{region.readings.humidity}%</p>
                </div>
                <div className="text-center">
                  <p className="text-foreground-400">风速</p>
                  <p className="font-medium text-foreground-700">{region.readings.windSpeed}</p>
                </div>
                <div className="text-center">
                  <p className="text-foreground-400">CAPE</p>
                  <p className="font-medium text-foreground-700">{region.readings.cape}</p>
                </div>
              </div>

              {/* Tomorrow.io enhanced indicators */}
              {tioEnabled && (
                <div className="mt-2 pt-2 border-t border-dashed border-background-200/50">
                  <div className="flex items-center gap-1 mb-1.5">
                    <i className="ri-flashlight-line text-[9px] text-emerald-500" />
                    <span className="text-[9px] text-foreground-400">Tomorrow.io 增强指标</span>
                    {tioLoading && (
                      <div className="w-2 h-2 border border-emerald-300 border-t-emerald-500 rounded-full animate-spin ml-0.5" />
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-1 text-[10px]">
                    <div className="text-center">
                      <p className="text-foreground-400 flex items-center justify-center gap-0.5">
                        <i className="ri-windy-line text-[8px]" />
                        阵风
                      </p>
                      <p className="font-medium text-foreground-700">
                        {region.readings.windGust > 0 ? `${region.readings.windGust}` : '—'}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-foreground-400 flex items-center justify-center gap-0.5">
                        <i className="ri-fire-line text-[8px]" />
                        火险
                      </p>
                      <p className={`font-medium ${region.readings.fireIndex >= 4 ? 'text-red-600' : region.readings.fireIndex >= 2 ? 'text-orange-500' : 'text-foreground-700'}`}>
                        {region.readings.fireIndex > 0 ? `${region.readings.fireIndex}` : '—'}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-foreground-400 flex items-center justify-center gap-0.5">
                        <i className="ri-thunderstorms-line text-[8px]" />
                        雷暴
                      </p>
                      <p className={`font-medium ${region.readings.thunderstormProb >= 50 ? 'text-red-600' : region.readings.thunderstormProb >= 30 ? 'text-orange-500' : 'text-foreground-700'}`}>
                        {region.readings.thunderstormProb > 0 ? `${region.readings.thunderstormProb}%` : '—'}
                      </p>
                    </div>
                  </div>
                  {tioError && (
                    <p className="text-[9px] text-yellow-600 mt-1 flex items-center gap-1">
                      <i className="ri-error-warning-line" />
                      {tioError}
                    </p>
                  )}
                </div>
              )}

              {/* Forecast chart */}
              {showCompare && cmaRegion && cmaRegion.forecast ? (
                <ModelCompareChart
                  forecastOm={region.forecast ?? []}
                  forecastCma={cmaRegion.forecast}
                />
              ) : (
                region.forecast && region.forecast.length > 0 && (
                  <MiniForecastChart forecast={region.forecast} />
                )
              )}

              {/* CMA loading indicator */}
              {showCmaLoading && (
                <div className="mt-2 flex items-center gap-1.5 text-[10px] text-foreground-400">
                  <div className="w-3 h-3 border border-foreground-300 border-t-primary-500 rounded-full animate-spin" />
                  CMA 数据同步中...
                </div>
              )}

              {/* CMA error indicator */}
              {showComparison && cmaEnabled && cmaError && (
                <div className="mt-2 flex items-center gap-1.5 text-[10px] text-yellow-600">
                  <i className="ri-error-warning-line" />
                  CMA 数据异常
                </div>
              )}

              {/* Show top hazard detail when selected */}
              {isSelected && topHazard.riskLevel !== 'green' && (
                <div className="mt-2 pt-2 border-t border-background-200/50">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-foreground-500">最高风险灾种</span>
                    <span className="font-medium text-foreground-700">{topHazard.hazardName}</span>
                  </div>
                  <div className="mt-1.5">
                    <div className="flex items-center justify-between text-[10px] text-foreground-500 mb-1">
                      <span>监测风险指数</span>
                      <span className="font-medium text-foreground-700">
                        {(topHazard.probability * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-background-200 rounded-full h-1.5">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          topHazard.riskLevel === 'orange'
                            ? 'bg-orange-500'
                            : topHazard.riskLevel === 'yellow'
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                        }`}
                        style={{ width: `${topHazard.probability * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-background-200/70 bg-background-50">
        <div className="flex items-center justify-between text-[10px] text-foreground-400">
          <span>更新于 2026-07-31 06:30</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-500 animate-pulse" />
            实时同步中
          </span>
        </div>
      </div>
    </div>
  );
}
