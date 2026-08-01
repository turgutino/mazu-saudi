import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '@/components/feature/Navbar';
import Button from '@/components/base/Button';
import Badge from '@/components/base/Badge';
import Card from '@/components/base/Card';
import type { Region } from '@/mocks/regions';
import type { HazardType } from '@/mocks/hazards';
import { type ModelInfo, type ModelMetrics, METRIC_LABELS } from '@/mocks/models';
import { createPrediction, fetchRegions, fetchHazards, fetchModels } from '@/services/predictionApi';

type Step = 'region' | 'hazard' | 'leadtime' | 'model' | 'confirm';

function MetricBar({ value, higherIsBetter, label }: { value: number; higherIsBetter: boolean; label: string }) {
  const pct = Math.round(value * 100);
  const clampedPct = Math.min(pct, 100);
  const good = higherIsBetter ? value >= 0.8 : value <= 0.15;
  const medium = higherIsBetter ? value >= 0.7 : value <= 0.25;
  const tier = good ? 'bg-accent-500' : medium ? 'bg-secondary-500' : 'bg-foreground-300';

  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-foreground-500 w-14 flex-shrink-0 text-right whitespace-nowrap">{label}</span>
      <div className="flex-1 h-2 bg-background-200/70 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-300 ${tier}`} style={{ width: `${clampedPct}%` }}></div>
      </div>
      <span className={`text-[11px] font-medium w-9 flex-shrink-0 ${good ? 'text-accent-700' : medium ? 'text-foreground-600' : 'text-foreground-400'}`}>
        {pct}%
      </span>
    </div>
  );
}

function ModelMetricsPanel({ metrics, hazardId }: { metrics: Record<string, ModelMetrics>; hazardId: string }) {
  const m = metrics[hazardId];
  if (!m) return <p className="text-xs text-foreground-400 italic">该模型在此灾种上暂无评估数据</p>;

  const metricKeys = Object.keys(METRIC_LABELS) as (keyof ModelMetrics)[];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[11px] text-foreground-500 uppercase tracking-wider">性能指标</span>
        <div className="flex-1 h-px bg-background-200/70"></div>
      </div>
      {metricKeys.map((key) => (
        <MetricBar key={key} value={m[key]} higherIsBetter={METRIC_LABELS[key].higherIsBetter} label={METRIC_LABELS[key].name} />
      ))}
    </div>
  );
}

function isHistoricalModel(model: ModelInfo) {
  return model.id.startsWith('joblib-');
}

function ModelAvailability({ model }: { model: ModelInfo }) {
  const historical = isHistoricalModel(model);
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <Badge variant={historical ? 'secondary' : 'success'} size="sm">
        {historical ? '2025历史归档' : '实时预测'}
      </Badge>
      <span className="text-[10px] text-foreground-400">
        {historical ? '需要完整NetCDF指标' : 'CMA / Open-Meteo / Tomorrow.io'}
      </span>
    </div>
  );
}

function ComparisonRow({ model, hazardId, isBest, isSelected, onClick }: { model: ModelInfo; hazardId: string; isBest: boolean; isSelected: boolean; onClick: () => void }) {
  const m = model.metrics[hazardId];

  const metricKeys: (keyof ModelMetrics)[] = ['auc', 'pod', 'far', 'csi', 'f1', 'brier'];

  const cellColor = (key: keyof ModelMetrics) => {
    if (!m) return 'text-foreground-300';
    const v = m[key];
    const h = METRIC_LABELS[key].higherIsBetter;
    if (h) return v >= 0.85 ? 'text-accent-700 font-semibold' : v >= 0.75 ? 'text-foreground-700' : 'text-foreground-400';
    return v <= 0.12 ? 'text-accent-700 font-semibold' : v <= 0.20 ? 'text-foreground-700' : 'text-foreground-400';
  };

  const fmt = (v: number) => (v * 100).toFixed(1) + '%';

  const typeLabel = model.type === 'tree' ? '树模型' : model.type === 'deep' ? '深度学习' : model.type === 'ensemble' ? '集成模型' : '物理模型';

  return (
    <tr
      onClick={onClick}
      className={`border-b border-background-200/50 cursor-pointer transition-colors ${isSelected ? 'bg-primary-50 ring-1 ring-inset ring-primary-200' : isBest ? 'bg-accent-50/60 hover:bg-accent-50' : 'hover:bg-background-100'}`}
    >
      <td className="py-2.5 pl-3 pr-2">
        <div className="flex items-center gap-1.5">
          {isBest && <i className="ri-star-fill text-accent-500 text-xs"></i>}
          <span className="text-sm font-medium text-foreground-900">{model.name}</span>
          <Badge variant="secondary" size="sm">{model.version}</Badge>
        </div>
        <div className="mt-1"><ModelAvailability model={model} /></div>
        <span className="text-[10px] text-foreground-400">{typeLabel}</span>
      </td>
      {metricKeys.map((key) => (
        <td key={key} className={`py-2.5 px-2 text-center text-sm ${cellColor(key)}`}>
          {m ? fmt(m[key]) : '—'}
        </td>
      ))}
    </tr>
  );
}

export default function Workspace() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<Step>('region');
  const [regions, setRegions] = useState<Region[]>([]);
  const [hazards, setHazards] = useState<HazardType[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [selectedHazard, setSelectedHazard] = useState<HazardType | null>(null);
  const [selectedLeadTime, setSelectedLeadTime] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);
  const [initialTime, setInitialTime] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');
  const [runError, setRunError] = useState<string | null>(null);
  const [modelViewMode, setModelViewMode] = useState<'cards' | 'compare'>('cards');
  const [expandedModel, setExpandedModel] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setMetaLoading(true);
    Promise.all([fetchRegions(), fetchHazards(), fetchModels()])
      .then(([regionsData, hazardsData, modelsData]) => {
        if (cancelled) return;
        setRegions(regionsData);
        setHazards(hazardsData);
        setModels(modelsData);
        setMetaError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setMetaError(error instanceof Error ? error.message : '基础数据加载失败');
      })
      .finally(() => {
        if (!cancelled) setMetaLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const availableModels = selectedHazard
    ? models.filter((m) => m.supportedHazards.includes(selectedHazard.id))
    : [];

  const availableLeadTimes = selectedHazard ? selectedHazard.leadTimes : [];

  const resetToStep = (step: Step) => {
    setCurrentStep(step);
    if (step === 'region') {
      setSelectedHazard(null);
      setSelectedLeadTime(null);
      setSelectedModel(null);
    } else if (step === 'hazard') {
      setSelectedLeadTime(null);
      setSelectedModel(null);
    } else if (step === 'leadtime') {
      setSelectedModel(null);
    }
  };

  const steps: { key: Step; label: string; number: number }[] = [
    { key: 'region', label: '选择区域', number: 1 },
    { key: 'hazard', label: '选择灾种', number: 2 },
    { key: 'leadtime', label: '预测时效', number: 3 },
    { key: 'model', label: '选择模型', number: 4 },
    { key: 'confirm', label: '确认执行', number: 5 },
  ];

  const canProceed = () => {
    switch (currentStep) {
      case 'region': return !!selectedRegion;
      case 'hazard': return !!selectedHazard;
      case 'leadtime': return !!selectedLeadTime;
      case 'model': return !!selectedModel;
      case 'confirm': return true;
      default: return false;
    }
  };

  const handleNext = () => {
    const order: Step[] = ['region', 'hazard', 'leadtime', 'model', 'confirm'];
    const idx = order.indexOf(currentStep);
    if (idx < order.length - 1) setCurrentStep(order[idx + 1]);
  };

  const handleRunPrediction = async () => {
    if (!selectedRegion || !selectedHazard || !selectedLeadTime || !selectedModel) return;

    setIsRunning(true);
    setRunError(null);
    setProgressMessage('预测服务正在执行数据解析、模型推理、校准、风险政策和知识检索…');
    try {
      const result = await createPrediction({
        regionId: selectedRegion.id,
        hazard: selectedHazard.id,
        leadTimeHours: selectedLeadTime,
        modelId: selectedModel.id,
        ...(initialTime ? { initialTime: new Date(initialTime).toISOString() } : {}),
      });
      setProgressMessage('预测与解释证据已生成，正在打开结果…');
      navigate(`/prediction/${result.predictionId}`);
    } catch (error) {
      setRunError(error instanceof Error ? error.message : '预测服务请求失败');
    } finally {
      setIsRunning(false);
    }
  };

  const regionSensitivityBadge = (sensitivity: 'high' | 'medium' | 'low') => {
    const config = { high: { label: '高敏感', variant: 'danger' as const }, medium: { label: '中敏感', variant: 'warning' as const }, low: { label: '低敏感', variant: 'success' as const } };
    const c = config[sensitivity];
    return <Badge variant={c.variant}>{c.label}</Badge>;
  };

  return (
    <div className="min-h-screen bg-background-50">
      <Navbar />

      <main className="w-full px-6 md:px-8 py-6">
        <div className="max-w-[960px] mx-auto">
          <div className="mb-8">
            <h1 className="font-heading text-2xl text-foreground-900">预测工作台</h1>
            <p className="text-sm text-foreground-500 mt-1">按步骤配置预测参数，智能体将自动编排预测流程</p>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-0 mb-8 overflow-x-auto">
            {steps.map((step, idx) => (
              <div key={step.key} className="flex items-center">
                <button
                  onClick={() => resetToStep(step.key)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors whitespace-nowrap ${
                    currentStep === step.key
                      ? 'bg-primary-500 text-background-50'
                      : step.number < steps.find((s) => s.key === currentStep)!.number
                      ? 'bg-accent-100 text-accent-700'
                      : 'bg-background-100 text-foreground-500'
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-background-50/30 flex items-center justify-center text-xs font-bold">
                    {step.number}
                  </span>
                  {step.label}
                </button>
                {idx < steps.length - 1 && (
                  <div className="w-8 h-[2px] bg-background-200 mx-1 flex-shrink-0"></div>
                )}
              </div>
            ))}
          </div>

          {metaError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-5 text-sm text-red-700">
              <i className="ri-error-warning-line mr-2"></i>基础数据加载失败：{metaError}
            </div>
          )}

          <Card className="p-6 min-h-[360px]">
            {metaLoading ? (
              <div className="flex items-center justify-center h-[300px] text-foreground-400">
                <i className="ri-loader-4-line animate-spin text-2xl mr-2"></i>正在加载区域/灾种/模型数据…
              </div>
            ) : (
            <>
            {/* Step 1: Region */}
            {currentStep === 'region' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">选择监测区域</h2>
                <p className="text-sm text-foreground-500 mb-5">选择需要进行极端天气预测的地理区域</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {regions.map((region) => (
                    <button
                      key={region.id}
                      onClick={() => setSelectedRegion(region)}
                      className={`text-left p-4 rounded-lg border cursor-pointer transition-all duration-200 ${
                        selectedRegion?.id === region.id
                          ? 'border-primary-400 bg-primary-50 ring-1 ring-primary-300'
                          : 'border-background-200/70 bg-background-50 hover:border-background-300 hover:bg-background-100'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-foreground-900">{region.name}</span>
                        <span className="text-xs text-foreground-400">{region.nameEn}</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {regionSensitivityBadge(region.sensitivity.flashFlood)}
                        {regionSensitivityBadge(region.sensitivity.heatwave)}
                        {regionSensitivityBadge(region.sensitivity.dustStorm)}
                      </div>
                    </button>
                  ))}
                </div>
                {selectedRegion && (
                  <div className="mt-4 p-3 bg-accent-50 border border-accent-200 rounded-lg">
                    <p className="text-sm text-accent-800">
                      已选择 <strong>{selectedRegion.name}</strong> ({selectedRegion.nameEn})
                      — 坐标: {selectedRegion.lat.toFixed(2)}°N, {selectedRegion.lon.toFixed(2)}°E
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Hazard */}
            {currentStep === 'hazard' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">选择预测灾种</h2>
                <p className="text-sm text-foreground-500 mb-5">选择需要预测的极端天气类型</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {hazards.map((hazard) => (
                    <button
                      key={hazard.id}
                      onClick={() => setSelectedHazard(hazard)}
                      className={`text-left p-4 rounded-lg border cursor-pointer transition-all duration-200 ${
                        selectedHazard?.id === hazard.id
                          ? 'border-primary-400 bg-primary-50 ring-1 ring-primary-300'
                          : 'border-background-200/70 bg-background-50 hover:border-background-300 hover:bg-background-100'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${hazard.color}15` }}>
                          <i className={`${hazard.icon} text-lg`} style={{ color: hazard.color }}></i>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground-900">{hazard.name}</span>
                            <span className="text-xs text-foreground-400">{hazard.nameEn}</span>
                          </div>
                          <p className="text-xs text-foreground-500 mt-1">{hazard.description}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 3: Lead Time */}
            {currentStep === 'leadtime' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">选择预测时效</h2>
                <p className="text-sm text-foreground-500 mb-5">
                  为 <Badge variant="primary">{selectedHazard?.name}</Badge> 选择提前预报的时间范围
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  {availableLeadTimes.map((lt) => (
                    <button
                      key={lt}
                      onClick={() => setSelectedLeadTime(lt)}
                      className={`p-4 rounded-lg border cursor-pointer transition-all duration-200 text-center ${
                        selectedLeadTime === lt
                          ? 'border-primary-400 bg-primary-50 ring-1 ring-primary-300'
                          : 'border-background-200/70 bg-background-50 hover:border-background-300 hover:bg-background-100'
                      }`}
                    >
                      <span className="text-2xl font-heading text-foreground-900 block">{lt}</span>
                      <span className="text-xs text-foreground-500 mt-1">小时</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 4: Model */}
            {currentStep === 'model' && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="font-heading text-lg text-foreground-900">选择预测模型</h2>
                  <div className="flex items-center gap-1 bg-background-100 rounded-lg p-1">
                    <button
                      onClick={() => setModelViewMode('cards')}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors whitespace-nowrap ${
                        modelViewMode === 'cards' ? 'bg-background-50 text-foreground-900 shadow-sm' : 'text-foreground-500 hover:text-foreground-700'
                      }`}
                    >
                      <i className="ri-layout-grid-line mr-1"></i>卡片视图
                    </button>
                    <button
                      onClick={() => setModelViewMode('compare')}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors whitespace-nowrap ${
                        modelViewMode === 'compare' ? 'bg-background-50 text-foreground-900 shadow-sm' : 'text-foreground-500 hover:text-foreground-700'
                      }`}
                    >
                      <i className="ri-table-line mr-1"></i>对比视图
                    </button>
                  </div>
                </div>
                <p className="text-sm text-foreground-500 mb-5">
                  为 {selectedRegion?.name} 的 {selectedHazard?.name} 展示 {availableModels.length} 个可用模型
                  {selectedHazard && (
                    <span className="ml-1 text-foreground-400">
                      — 系统会根据起报日期和数据完整性自动运行满足条件的模型
                    </span>
                  )}
                </p>

                {selectedHazard?.id === 'heavy-rain' && (
                  <div className="mb-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-800">
                    <i className="ri-information-line mr-1.5"></i>
                    暴雨暂无2025历史训练模型，因此仅显示实时多源融合模型。
                  </div>
                )}

                {modelViewMode === 'cards' && (
                  <div className="space-y-4">
                    {availableModels.map((model) => {
                      const isSelected = selectedModel?.id === model.id;
                      const isExpanded = expandedModel === model.id;
                      const metrics = selectedHazard ? model.metrics[selectedHazard.id] : null;
                      const hasMetrics = !!metrics;
                      const bestAuc = Math.max(...availableModels.map((m) => (selectedHazard ? (m.metrics[selectedHazard.id]?.auc ?? 0) : 0)));
                      const isBestAuc = hasMetrics && metrics!.auc === bestAuc && availableModels.length > 1;

                      return (
                        <div
                          key={model.id}
                          role="button"
                          tabIndex={0}
                          onClick={() => setSelectedModel(model)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') setSelectedModel(model);
                          }}
                          className={`w-full text-left rounded-lg border cursor-pointer transition-all duration-200 overflow-hidden ${
                            isSelected
                              ? 'border-primary-400 bg-primary-50 ring-1 ring-primary-300'
                              : 'border-background-200/70 bg-background-50 hover:border-background-300 hover:bg-background-100'
                          }`}
                        >
                          {/* Header row */}
                          <div className="flex items-center justify-between p-4">
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                                style={{ backgroundColor: model.type === 'ensemble' ? 'var(--accent-100)' : model.type === 'deep' ? 'var(--primary-100)' : 'var(--secondary-100)' }}>
                                <i className={`${model.icon} text-lg ${model.type === 'ensemble' ? 'text-accent-600' : model.type === 'deep' ? 'text-primary-600' : 'text-secondary-600'}`}></i>
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-foreground-900 text-sm">{model.name}</span>
                                  <Badge variant="secondary" size="sm">{model.version}</Badge>
                                  {isBestAuc && <Badge variant="accent" size="sm">最高 AUC</Badge>}
                                </div>
                                <p className="text-xs text-foreground-500 mt-0.5 truncate">{model.description}</p>
                                <div className="mt-1.5"><ModelAvailability model={model} /></div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0 ml-4">
                              <Badge variant={model.type === 'ensemble' ? 'accent' : model.type === 'deep' ? 'primary' : 'secondary'}>
                                {model.type === 'tree' ? '树模型' : model.type === 'deep' ? '深度学习' : model.type === 'ensemble' ? '集成模型' : '物理模型'}
                              </Badge>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedModel(isExpanded ? null : model.id);
                                }}
                                className="p-1.5 rounded-md hover:bg-background-200 cursor-pointer transition-colors"
                                title={isExpanded ? '收起指标' : '展开指标'}
                              >
                                <i className={`text-xs text-foreground-400 transition-transform duration-200 ${isExpanded ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'}`}></i>
                              </button>
                            </div>
                          </div>

                          {/* Expandable metrics panel */}
                          <div
                            className={`overflow-hidden transition-all duration-300 ease-in-out ${
                              isExpanded ? 'max-h-[400px] opacity-100' : 'max-h-0 opacity-0'
                            }`}
                          >
                            <div className="px-4 pb-4 border-t border-background-200/50 pt-4">
                              <ModelMetricsPanel metrics={model.metrics} hazardId={selectedHazard?.id ?? ''} />
                            </div>
                          </div>

                          {/* Collapsed metric preview */}
                          {!isExpanded && hasMetrics && (
                            <div className="pb-3 px-4">
                              <div className="flex items-center gap-4">
                                {(['auc', 'pod', 'f1', 'far'] as (keyof ModelMetrics)[]).map((key) => {
                                  const v = metrics![key];
                                  const meta = METRIC_LABELS[key];
                                  const pct = Math.round(v * 100);
                                  const good = meta.higherIsBetter ? v >= 0.85 : v <= 0.12;
                                  const tierColor = good ? 'text-accent-700' : 'text-foreground-600';
                                  return (
                                    <div key={key} className="flex items-center gap-1.5">
                                      <span className="text-[10px] text-foreground-400 whitespace-nowrap">{meta.name}</span>
                                      <span className={`text-xs font-semibold ${tierColor}`}>{pct}%</span>
                                    </div>
                                  );
                                })}
                                <span className="text-[10px] text-foreground-300 ml-auto">点击展开完整指标</span>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {modelViewMode === 'compare' && availableModels.length > 0 && (
                  <div className="overflow-x-auto rounded-lg border border-background-200/70">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="bg-background-100 border-b border-background-200/70">
                          <th className="py-2.5 px-3 text-xs font-medium text-foreground-500">模型</th>
                          {(['auc', 'pod', 'far', 'csi', 'f1', 'brier'] as (keyof ModelMetrics)[]).map((key) => (
                            <th key={key} className="py-2.5 px-2 text-center text-xs font-medium text-foreground-500 cursor-help" title={METRIC_LABELS[key].description}>
                              {METRIC_LABELS[key].name}
                            </th>
                          ))}
                          <th className="py-2.5 px-3 text-xs font-medium text-foreground-500"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {availableModels.map((model) => {
                          const metrics = selectedHazard ? model.metrics[selectedHazard.id] : null;
                          const bestAuc = Math.max(...availableModels.map((m) => (selectedHazard ? (m.metrics[selectedHazard.id]?.auc ?? 0) : 0)));
                          const isBestAuc = metrics && metrics.auc === bestAuc && availableModels.length > 1;
                          const isSelected = selectedModel?.id === model.id;

                          return (
                            <ComparisonRow key={model.id} model={model} hazardId={selectedHazard?.id ?? ''} isBest={isBestAuc} isSelected={isSelected} onClick={() => setSelectedModel(model)} />
                          );
                        })}
                      </tbody>
                    </table>
                    <div className="px-3 py-2 bg-background-100 border-t border-background-200/70">
                      <p className="text-[10px] text-foreground-400">
                        <i className="ri-information-line mr-1"></i>
                        指标基于 {selectedHazard?.name} 灾种的验证集评估（2025-2026 数据）。
                        “—”表示实时融合基线暂无独立验证集指标。
                        标 <i className="ri-star-fill text-accent-500 text-[9px]"></i> 为该指标当前最优模型。
                        点击模型行选择，指标说明悬停表头查看。
                      </p>
                    </div>
                  </div>
                )}

                {availableModels.length === 0 && (
                  <div className="text-center py-8 text-foreground-400">
                    <i className="ri-emotion-sad-line text-2xl block mb-2"></i>
                    <p>当前选中的组合没有可用的预测模型</p>
                  </div>
                )}
              </div>
            )}

            {/* Step 5: Confirm */}
            {currentStep === 'confirm' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">确认预测参数</h2>
                <p className="text-sm text-foreground-500 mb-5">检查所有预测配置，确认后智能体将自动编排执行</p>

                <div className="bg-background-100 rounded-lg p-5 mb-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">区域</span>
                      <span className="text-sm font-medium text-foreground-900">{selectedRegion?.name} ({selectedRegion?.nameEn})</span>
                      <p className="text-xs text-foreground-400 mt-0.5">
                        山洪敏感度: {selectedRegion?.sensitivity.flashFlood === 'high' ? '高' : selectedRegion?.sensitivity.flashFlood === 'medium' ? '中' : '低'}
                        {' · '}高温敏感度: {selectedRegion?.sensitivity.heatwave === 'high' ? '高' : selectedRegion?.sensitivity.heatwave === 'medium' ? '中' : '低'}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">灾种</span>
                      <div className="flex items-center gap-2">
                        <i className={`${selectedHazard?.icon}`} style={{ color: selectedHazard?.color }}></i>
                        <span className="text-sm font-medium text-foreground-900">{selectedHazard?.name}</span>
                      </div>
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">预测时效</span>
                      <span className="text-sm font-medium text-foreground-900">{selectedLeadTime} 小时</span>
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">模型</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground-900">{selectedModel?.name} <Badge variant="secondary" size="sm">{selectedModel?.version}</Badge></span>
                      </div>
                      {selectedModel && selectedHazard && selectedModel.metrics[selectedHazard.id] && (
                        <div className="flex items-center gap-3 mt-2 flex-wrap">
                          {(['auc', 'pod', 'csi'] as (keyof ModelMetrics)[]).map((key) => {
                            const v = selectedModel.metrics[selectedHazard.id][key];
                            const meta = METRIC_LABELS[key];
                            const pct = Math.round(v * 100);
                            const good = meta.higherIsBetter ? v >= 0.85 : v <= 0.12;
                            return (
                              <div key={key} className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-background-200/50">
                                <span className="text-[10px] text-foreground-500">{meta.name}</span>
                                <span className={`text-xs font-semibold ${good ? 'text-accent-700' : 'text-foreground-600'}`}>{pct}%</span>
                              </div>
                            );
                          })}
                          <span className="text-[10px] text-foreground-400">({selectedHazard.name} 验证集)</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="bg-background-100 rounded-lg p-5 mb-5">
                  <label htmlFor="initial-time" className="text-xs text-foreground-500 block mb-1">
                    起报时间（可选）
                  </label>
                  <input
                    id="initial-time"
                    type="datetime-local"
                    value={initialTime}
                    onChange={(e) => setInitialTime(e.target.value)}
                    className="w-full sm:w-64 px-3 py-2 text-sm rounded-md border border-background-200 bg-background-50 text-foreground-900 focus:outline-none focus:ring-1 focus:ring-primary-300"
                  />
                  <p className="text-xs text-foreground-400 mt-1.5">
                    不填默认使用当前时间与实时融合模型；选择2025年内日期且归档指标完整时，系统自动运行对应历史训练模型。
                  </p>
                </div>

                {/* Execution progress */}
                {isRunning && (
                  <div className="bg-background-100 rounded-lg p-5 mb-5">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-5 h-5 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm text-foreground-700 font-medium">智能体正在编排预测流程...</span>
                    </div>
                    <div className="space-y-2">
                      {['数据准备', '模型预测', '概率校准', '风险决策', '解释生成', '图谱构建', '报告生成'].map((label, idx) => {
                        const isActive = idx <= Math.floor(progressMessage.length / 30);
                        return (
                          <div key={label} className="flex items-center gap-2">
                            <i className={`text-xs ${isActive ? 'ri-checkbox-circle-fill text-accent-500' : 'ri-checkbox-blank-circle-line text-foreground-300'}`}></i>
                            <span className={`text-xs ${isActive ? 'text-foreground-700' : 'text-foreground-400'}`}>{label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {runError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-5 text-sm text-red-700">
                    <i className="ri-error-warning-line mr-2"></i>{runError}
                  </div>
                )}

                {!isRunning && (
                  <div className="bg-background-100 rounded-lg p-4 mb-5">
                    <div className="flex items-start gap-3">
                      <i className="ri-information-line text-foreground-400 mt-0.5"></i>
                      <div className="text-xs text-foreground-500">
                        <p className="mb-2">智能体将按以下流程执行：</p>
                        <ol className="list-decimal list-inside space-y-1">
                          <li>加载预测案例数据 (ForecastCase)</li>
                          <li>根据起报日期与数据完整性自动选择历史训练模型或实时融合模型</li>
                          <li>执行概率校准</li>
                          <li>运行 {selectedRegion?.name} 区域风险规则</li>
                          <li>调用解释引擎生成特征贡献和物理机制</li>
                          <li>查询相似历史事件</li>
                          <li>构建解释证据图谱</li>
                          <li>生成预测报告</li>
                        </ol>
                        <p className="mt-2 text-foreground-400">智能体不会编造预测概率，所有数值由模型计算产生。</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            </>
            )}
          </Card>

          {/* Navigation buttons */}
          <div className="flex items-center justify-between mt-6">
            <Button
              variant="ghost"
              icon="ri-arrow-left-line"
              onClick={() => {
                const order: Step[] = ['region', 'hazard', 'leadtime', 'model', 'confirm'];
                const idx = order.indexOf(currentStep);
                if (idx > 0) setCurrentStep(order[idx - 1]);
              }}
              disabled={currentStep === 'region'}
            >
              上一步
            </Button>

            {currentStep !== 'confirm' ? (
              <Button variant="primary" icon="ri-arrow-right-line" onClick={handleNext} disabled={!canProceed()}>
                下一步
              </Button>
            ) : (
              <Button
                variant="primary"
                icon="ri-play-fill"
                onClick={handleRunPrediction}
                disabled={isRunning}
              >
                {isRunning ? '执行中...' : '发起预测'}
              </Button>
            )}
          </div>
        </div>
      </main>

      <footer className="border-t border-background-200/70 bg-background-100 mt-12">
        <div className="max-w-[1280px] mx-auto px-6 md:px-8 py-5">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-foreground-500">
              <i className="ri-shield-check-line text-accent-600"></i>
              <span>预测结果仅供参考，实际预警以官方发布为准</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-foreground-400">
              <span>模型: HistGradientBoosting + 实时多源融合</span>
              <span>数据: ERA5 + 数值预报</span>
              <span>更新于 2025-06-30</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
