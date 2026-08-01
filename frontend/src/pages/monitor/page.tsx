import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '@/components/feature/Navbar';
import Button from '@/components/base/Button';
import SaudiMap from './components/SaudiMap';
import MonitorSidebar from './components/MonitorSidebar';
import { useWeatherData } from '@/hooks/useWeatherData';
import { useMirrorEarthData } from '@/hooks/useMirrorEarthData';
import { useTomorrowIoData } from '@/hooks/useTomorrowIoData';
import { mergeEnhancedIntoReading } from '@/services/tomorrowIoApi';

export default function MonitorPage() {
  const navigate = useNavigate();
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);
  const [activeHazardId, setActiveHazardId] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  const {
    regions: regionsRaw,
    loading,
    error,
    lastRefresh,
    isRealData,
    cacheHit,
    refresh: refreshOm,
  } = useWeatherData();

  const {
    regions: regionsCmaRaw,
    loading: loadingCma,
    error: errorCma,
    lastRefresh: lastRefreshCma,
    enabled: cmaEnabled,
    refresh: refreshCma,
  } = useMirrorEarthData();

  const {
    enhancedList,
    loading: loadingTio,
    error: errorTio,
    enabled: tioEnabled,
    refresh: refreshTio,
  } = useTomorrowIoData();

  // Merge Tomorrow.io enhanced data into Open-Meteo regions
  const regions = useMemo(() => {
    if (!regionsRaw) return [];
    if (!enhancedList) return regionsRaw;
    return regionsRaw.map((r, i) => {
      if (i < enhancedList.length && enhancedList[i]) {
        return {
          ...r,
          readings: mergeEnhancedIntoReading(r.readings, enhancedList[i]),
        };
      }
      return r;
    });
  }, [regionsRaw, enhancedList]);

  // Merge Tomorrow.io enhanced data into CMA regions
  const regionsCma = useMemo(() => {
    if (!regionsCmaRaw) return null;
    if (!enhancedList) return regionsCmaRaw;
    return regionsCmaRaw.map((r, i) => {
      if (i < enhancedList.length && enhancedList[i]) {
        return {
          ...r,
          readings: mergeEnhancedIntoReading(r.readings, enhancedList[i]),
        };
      }
      return r;
    });
  }, [regionsCmaRaw, enhancedList]);

  const handleSelectRegion = useCallback((id: string) => {
    setSelectedRegionId((prev) => (prev === id ? null : id));
  }, []);

  const handleSetHazard = useCallback((id: string | null) => {
    setActiveHazardId((prev) => (prev === id ? null : id));
  }, []);

  const selectedRegion = regions.find((r) => r.regionId === selectedRegionId);

  // Get CMA counterpart for selected region
  const selectedRegionCma = regionsCma?.find((r) => r.regionId === selectedRegionId) ?? null;

  // Summary from Open-Meteo
  const maxTemp = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.temperature)) : 0;
  const maxHumidity = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.humidity)) : 0;
  const maxWind = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.windSpeed)) : 0;
  const maxCape = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.cape)) : 0;
  const activeAlerts = regions.reduce((sum, r) => sum + r.activeAlertCount, 0);
  const orangeAlerts = regions.filter((r) => r.highestRiskLevel === 'orange').length;
  const tempRegion = regions.find((r) => r.readings.temperature === maxTemp)?.regionName ?? '—';
  const humRegion = regions.find((r) => r.readings.humidity === maxHumidity)?.regionName ?? '—';
  const windRegion = regions.find((r) => r.readings.windSpeed === maxWind)?.regionName ?? '—';
  const capeRegion = regions.find((r) => r.readings.cape === maxCape)?.regionName ?? '—';

  // Tomorrow.io enhanced metrics
  const maxWindGust = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.windGust)) : 0;
  const maxFireIndex = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.fireIndex)) : 0;
  const maxTstormProb = regions.length > 0 ? Math.max(...regions.map((r) => r.readings.thunderstormProb)) : 0;
  const windGustRegion = regions.find((r) => r.readings.windGust === maxWindGust)?.regionName ?? '—';
  const fireRegion = regions.find((r) => r.readings.fireIndex === maxFireIndex)?.regionName ?? '—';
  const tstormRegion = regions.find((r) => r.readings.thunderstormProb === maxTstormProb)?.regionName ?? '—';

  // CMA summary (if available)
  const cmaTemp = regionsCma && regionsCma.length > 0
    ? Math.max(...regionsCma.map((r) => r.readings.temperature))
    : null;
  const cmaTempRegion = regionsCma?.find((r) => r.readings.temperature === cmaTemp)?.regionName ?? null;

  const combinedLoading = loading || (showComparison && loadingCma) || loadingTio;

  const handleRefreshAll = useCallback(() => {
    refreshOm();
    if (cmaEnabled) refreshCma();
    if (tioEnabled) refreshTio();
  }, [refreshOm, refreshCma, refreshTio, cmaEnabled, tioEnabled]);

  return (
    <div className="min-h-screen bg-background-50">
      <Navbar />

      <main className="flex flex-col lg:flex-row" style={{ height: 'calc(100vh - 56px)' }}>
        {/* Map area */}
        <div className="flex-1 flex flex-col min-h-[400px] lg:min-h-0">
          {/* Toolbar */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-4 md:px-6 py-3 border-b border-background-200/70 bg-background-50">
            <div>
              <h1 className="font-heading text-base text-foreground-900 flex items-center gap-2">
                <i className="ri-radar-line text-primary-500 text-sm" />
                实时监测 · 沙特地区
              </h1>
              <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                <p className="text-xs text-foreground-400">
                  {regions.length} 个监测区域 · {activeAlerts} 个活跃预警
                </p>
                {isRealData && (
                  <span className="text-[10px] bg-accent-50 text-accent-700 px-1.5 py-0.5 rounded-full border border-accent-200">
                    {cacheHit ? 'Open-Meteo · 数据库缓存' : 'Open-Meteo · 新快照'}
                  </span>
                )}
                {!isRealData && !loading && (
                  <span className="text-[10px] bg-yellow-50 text-yellow-700 px-1.5 py-0.5 rounded-full border border-yellow-200">
                    模拟数据
                  </span>
                )}
                {cmaEnabled && (
                  <span className="text-[10px] bg-secondary-50 text-secondary-700 px-1.5 py-0.5 rounded-full border border-secondary-200">
                    CMA 已接入
                  </span>
                )}
                {tioEnabled && !loadingTio && !errorTio && (
                  <span className="text-[10px] bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded-full border border-emerald-200">
                    <i className="ri-flashlight-line mr-0.5" />
                    Tomorrow.io 增强
                  </span>
                )}
                {tioEnabled && loadingTio && (
                  <span className="text-[10px] bg-emerald-50 text-emerald-600 px-1.5 py-0.5 rounded-full border border-emerald-200 animate-pulse">
                    <div className="w-2 h-2 border border-emerald-400 border-t-emerald-600 rounded-full animate-spin inline-block mr-0.5 align-middle" />
                    Tomorrow.io 同步中
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {cmaEnabled && (
                <button
                  onClick={() => setShowComparison((p) => !p)}
                  className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap cursor-pointer transition-colors ${
                    showComparison
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-background-100 text-foreground-500 border border-background-200 hover:bg-background-200'
                  }`}
                >
                  <i className={`${showComparison ? 'ri-eye-line' : 'ri-eye-off-line'} mr-1`} />
                  {showComparison ? '双模型对比中' : '双模型对比'}
                </button>
              )}
              {selectedRegion && (
                <Button
                  variant="outline"
                  size="sm"
                  icon="ri-arrow-right-line"
                  onClick={() => {
                    navigate('/workspace');
                  }}
                >
                  为 {selectedRegion.regionName} 发起预测
                </Button>
              )}
              <button
                onClick={handleRefreshAll}
                disabled={combinedLoading}
                className="flex items-center gap-1.5 text-xs text-foreground-500 bg-background-100 px-3 py-1.5 rounded-full hover:bg-background-200 transition-colors cursor-pointer disabled:opacity-50"
              >
                <i className={`ri-refresh-line ${combinedLoading ? 'animate-spin' : ''}`} />
                {combinedLoading ? '同步中...' : lastRefresh || '等待中'}
              </button>
            </div>
          </div>

          {/* Map */}
          <div className="flex-1 p-3 md:p-4 relative">
            {loading && regions.length === 0 && (
              <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
                <div className="w-10 h-10 border-2 border-primary-200 border-t-primary-500 rounded-full animate-spin" />
                <p className="text-sm text-foreground-500 mt-3">正在读取监测快照...</p>
                <p className="text-xs text-foreground-400 mt-1">当前6小时时段无缓存时才会同步 8 个区域</p>
              </div>
            )}
            {error && regions.length === 0 && (
              <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
                <i className="ri-error-warning-line text-3xl text-yellow-500" />
                <p className="text-sm text-foreground-600 mt-2">实时数据获取失败</p>
                <p className="text-xs text-foreground-400 mt-1 max-w-xs text-center">{error}</p>
                <button
                  onClick={handleRefreshAll}
                  className="mt-3 text-xs text-primary-600 hover:text-primary-700 cursor-pointer"
                >
                  重试
                </button>
              </div>
            )}
            <SaudiMap
              regions={regions}
              selectedRegionId={selectedRegionId}
              onSelectRegion={handleSelectRegion}
              activeHazardId={activeHazardId}
              tioEnabled={tioEnabled}
            />
          </div>

          {/* Bottom summary bar */}
          <div className="px-4 md:px-6 py-3 border-t border-background-200/70 bg-background-50">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 xl:grid-cols-5 gap-3">
              <SummaryItem
                icon="ri-temp-hot-line"
                label="最高温度"
                value={`${maxTemp}°C`}
                sub={tempRegion}
              />
              <SummaryItem
                icon="ri-drop-line"
                label="最大湿度"
                value={`${maxHumidity}%`}
                sub={humRegion}
              />
              <SummaryItem
                icon="ri-windy-line"
                label="最大风速"
                value={`${maxWind} m/s`}
                sub={windRegion}
              />
              <SummaryItem
                icon="ri-flashlight-line"
                label="最高 CAPE"
                value={`${maxCape} J/kg`}
                sub={capeRegion}
              />
              <SummaryItem
                icon="ri-alert-line"
                label="活跃预警"
                value={`${activeAlerts}`}
                sub={`${orangeAlerts} 橙色`}
                highlight
              />
              <SummaryItem
                icon="ri-database-2-line"
                label="数据来源"
                value={isRealData ? 'Open-Meteo' : '模拟'}
                sub={tioEnabled ? 'Tomorrow.io 增强' : cmaEnabled ? 'CMA 已接入' : '单源'}
              />
              {tioEnabled && (
                <>
                  <SummaryItem
                    icon="ri-windy-line"
                    label="最大阵风"
                    value={`${maxWindGust} m/s`}
                    sub={windGustRegion}
                  />
                  <SummaryItem
                    icon="ri-fire-line"
                    label="最高火险指数"
                    value={`${maxFireIndex}`}
                    sub={fireRegion}
                  />
                  <SummaryItem
                    icon="ri-thunderstorms-line"
                    label="最高雷暴概率"
                    value={`${maxTstormProb}%`}
                    sub={tstormRegion}
                  />
                </>
              )}
            </div>

            {/* CMA comparison row (only when comparison active and data available) */}
            {showComparison && cmaEnabled && regionsCma && (
              <div className="mt-2 pt-2 border-t border-background-200/40">
                <p className="text-[10px] text-foreground-400 mb-1.5 flex items-center gap-1">
                  <i className="ri-line-chart-line" />
                  CMA 模型对比摘要
                  {errorCma && (
                    <span className="text-yellow-600 ml-1">· {errorCma}</span>
                  )}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <SummaryItem
                    icon="ri-temp-hot-line"
                    label="CMA 最高温度"
                    value={`${cmaTemp}°C`}
                    sub={cmaTempRegion ?? '—'}
                  />
                  <SummaryItem
                    icon="ri-arrow-up-down-line"
                    label="温差"
                    value={`${cmaTemp != null ? (cmaTemp - maxTemp).toFixed(1) : '—'}°C`}
                    sub={cmaTemp != null && cmaTemp > maxTemp ? 'CMA 偏高' : 'CMA 偏低'}
                  />
                  <SummaryItem
                    icon="ri-time-line"
                    label="CMA 更新"
                    value={lastRefreshCma || '—'}
                    sub="镜地球"
                  />
                  <SummaryItem
                    icon="ri-global-line"
                    label="CMA 分辨率"
                    value="12.5km"
                    sub="vs Open-Meteo 27km"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-80 xl:w-88 border-l border-background-200/70 bg-background-50 flex-shrink-0 h-[400px] lg:h-auto">
          <MonitorSidebar
            regions={regions}
            regionsCma={regionsCma}
            selectedRegionId={selectedRegionId}
            onSelectRegion={handleSelectRegion}
            activeHazardId={activeHazardId}
            onSetHazard={handleSetHazard}
            showComparison={showComparison}
            cmaEnabled={cmaEnabled}
            cmaLoading={loadingCma}
            cmaError={errorCma}
            tioEnabled={tioEnabled}
            tioLoading={loadingTio}
            tioError={errorTio}
          />
        </div>
      </main>
    </div>
  );
}

function SummaryItem({
  icon,
  label,
  value,
  sub,
  highlight,
}: {
  icon: string;
  label: string;
  value: string;
  sub: string | null;
  highlight?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg ${highlight ? 'bg-primary-50 border border-primary-100' : 'bg-background-100'}`}
    >
      <div
        className={`w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 ${highlight ? 'bg-primary-100 text-primary-600' : 'bg-background-200/60 text-foreground-500'}`}
      >
        <i className={`${icon} text-sm`} />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] text-foreground-400 leading-tight">{label}</p>
        <p className={`text-sm font-medium leading-tight ${highlight ? 'text-primary-700' : 'text-foreground-900'}`}>
          {value}
        </p>
        <p className="text-[10px] text-foreground-400 leading-tight truncate">{sub ?? ''}</p>
      </div>
    </div>
  );
}
