import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Navbar from '@/components/feature/Navbar';
import Button from '@/components/base/Button';
import Badge from '@/components/base/Badge';
import Card from '@/components/base/Card';
import type { Region } from '@/mocks/regions';
import type { HazardType } from '@/mocks/hazards';
import { type ModelInfo, type ModelMetrics, METRIC_LABELS } from '@/mocks/models';
import { createPrediction, fetchRegions, fetchHazards, fetchModels } from '@/services/predictionApi';

type PredictionMode = 'live' | 'historical';
type Step = 'mode' | 'region' | 'hazard' | 'leadtime' | 'model' | 'confirm';

const STEP_ORDER: Step[] = ['mode', 'region', 'hazard', 'leadtime', 'model', 'confirm'];

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
  const { t } = useTranslation();
  const m = metrics[hazardId];
  if (!m) return <p className="text-xs text-foreground-400 italic">{t('workspace.model.noEvalData')}</p>;

  const metricKeys = Object.keys(METRIC_LABELS) as (keyof ModelMetrics)[];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[11px] text-foreground-500 uppercase tracking-wider">{t('workspace.model.performanceMetrics')}</span>
        <div className="flex-1 h-px bg-background-200/70"></div>
      </div>
      {metricKeys.map((key) => (
        <MetricBar key={key} value={m[key]} higherIsBetter={METRIC_LABELS[key].higherIsBetter} label={t(METRIC_LABELS[key].nameKey)} />
      ))}
    </div>
  );
}

function isHistoricalModel(model: ModelInfo) {
  return model.id.startsWith('joblib-');
}

function historicalFeatureDateFor(initialDate: string, leadTimeHours: number) {
  const target = new Date(`${initialDate}T00:00:00Z`);
  target.setUTCHours(target.getUTCHours() + leadTimeHours);
  target.setUTCDate(target.getUTCDate() - 1);
  return target.toISOString().slice(0, 10);
}

function ModelAvailability({ model }: { model: ModelInfo }) {
  const { t } = useTranslation();
  const historical = isHistoricalModel(model);
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <Badge variant={historical ? 'secondary' : 'success'} size="sm">
        {historical ? t('workspace.model.availability.historical') : t('workspace.model.availability.live')}
      </Badge>
      <span className="text-[10px] text-foreground-400">
        {historical ? t('workspace.model.availability.historicalDesc') : t('workspace.model.availability.liveDesc')}
      </span>
    </div>
  );
}

function ComparisonRow({ model, hazardId, isBest, isSelected, onClick }: { model: ModelInfo; hazardId: string; isBest: boolean; isSelected: boolean; onClick: () => void }) {
  const { t } = useTranslation();
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

  const typeLabel = model.type === 'tree' ? t('workspace.model.type.tree') : model.type === 'deep' ? t('workspace.model.type.deep') : model.type === 'ensemble' ? t('workspace.model.type.ensemble') : model.type === 'rule' ? t('workspace.model.type.rule') : t('workspace.model.type.physical');

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
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<Step>('mode');
  const [regions, setRegions] = useState<Region[]>([]);
  const [hazards, setHazards] = useState<HazardType[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [selectedHazard, setSelectedHazard] = useState<HazardType | null>(null);
  const [selectedLeadTime, setSelectedLeadTime] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);
  const [predictionMode, setPredictionMode] = useState<PredictionMode | null>(null);
  const [historicalDate, setHistoricalDate] = useState('2025-06-01');
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
        setMetaError(error instanceof Error ? error.message : t('workspace.metaLoadFailed'));
      })
      .finally(() => {
        if (!cancelled) setMetaLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Re-run when the language toggle changes so region/hazard/model names
    // (localized server-side) are refetched in the newly-selected language.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t, i18n.language]);

  const availableModels = selectedHazard && predictionMode
    ? models.filter((model) =>
        model.supportedHazards.includes(selectedHazard.id)
        && (predictionMode === 'historical' ? isHistoricalModel(model) : model.id.startsWith('live-api-hgb-')))
    : [];

  const availableLeadTimes = selectedHazard
    ? (predictionMode === 'historical' ? [24] : selectedHazard.leadTimes)
    : [];
  const historicalFeatureDate = predictionMode === 'historical' && selectedLeadTime
    ? historicalFeatureDateFor(historicalDate, selectedLeadTime)
    : null;
  const historicalFeatureAvailable = historicalFeatureDate === null
    || (historicalFeatureDate >= '2025-01-01' && historicalFeatureDate <= '2025-12-31');

  const resetToStep = (step: Step) => {
    setCurrentStep(step);
    if (step === 'mode') {
      setSelectedRegion(null);
      setSelectedHazard(null);
      setSelectedLeadTime(null);
      setSelectedModel(null);
    } else if (step === 'region') {
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
    { key: 'mode', label: t('workspace.steps.mode'), number: 1 },
    { key: 'region', label: t('workspace.steps.region'), number: 2 },
    { key: 'hazard', label: t('workspace.steps.hazard'), number: 3 },
    { key: 'leadtime', label: t('workspace.steps.leadtime'), number: 4 },
    { key: 'model', label: t('workspace.steps.model'), number: 5 },
    { key: 'confirm', label: t('workspace.steps.confirm'), number: 6 },
  ];

  const canProceed = () => {
    switch (currentStep) {
      case 'mode': return !!predictionMode && (predictionMode === 'live' || !!historicalDate);
      case 'region': return !!selectedRegion;
      case 'hazard': return !!selectedHazard;
      case 'leadtime': return !!selectedLeadTime && historicalFeatureAvailable;
      case 'model': return !!selectedModel;
      case 'confirm': return true;
      default: return false;
    }
  };

  const handleNext = () => {
    const idx = STEP_ORDER.indexOf(currentStep);
    if (currentStep === 'leadtime') {
      setSelectedModel(availableModels[0] ?? null);
    }
    if (idx < STEP_ORDER.length - 1) setCurrentStep(STEP_ORDER[idx + 1]);
  };

  const handleRunPrediction = async () => {
    if (!predictionMode || !selectedRegion || !selectedHazard || !selectedLeadTime || !selectedModel) return;

    setIsRunning(true);
    setRunError(null);
    setProgressMessage(t('workspace.confirm.progressPreparing'));
    try {
      const result = await createPrediction({
        regionId: selectedRegion.id,
        hazard: selectedHazard.id,
        leadTimeHours: selectedLeadTime,
        modelId: selectedModel.id,
        predictionMode,
        ...(predictionMode === 'historical' ? { initialTime: `${historicalDate}T00:00:00Z` } : {}),
      });
      setProgressMessage(t('workspace.confirm.progressDone'));
      navigate(`/prediction/${result.predictionId}`);
    } catch (error) {
      setRunError(error instanceof Error ? error.message : t('workspace.confirm.runFailed'));
    } finally {
      setIsRunning(false);
    }
  };

  const regionSensitivityBadge = (sensitivity: 'high' | 'medium' | 'low') => {
    const config = {
      high: { label: t('workspace.sensitivity.high'), variant: 'danger' as const },
      medium: { label: t('workspace.sensitivity.medium'), variant: 'warning' as const },
      low: { label: t('workspace.sensitivity.low'), variant: 'success' as const },
    };
    const c = config[sensitivity];
    return <Badge variant={c.variant}>{c.label}</Badge>;
  };

  return (
    <div className="min-h-screen bg-background-50">
      <Navbar />

      <main className="w-full px-6 md:px-8 py-6">
        <div className="max-w-[960px] mx-auto">
          <div className="mb-8">
            <h1 className="font-heading text-2xl text-foreground-900">{t('workspace.title')}</h1>
            <p className="text-sm text-foreground-500 mt-1">{t('workspace.subtitle')}</p>
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
              <i className="ri-error-warning-line mr-2"></i>{t('workspace.metaError', { error: metaError })}
            </div>
          )}

          <Card className="p-6 min-h-[360px]">
            {metaLoading ? (
              <div className="flex items-center justify-center h-[300px] text-foreground-400">
                <i className="ri-loader-4-line animate-spin text-2xl mr-2"></i>{t('workspace.metaLoading')}
              </div>
            ) : (
            <>
            {/* Step 1: Mode */}
            {currentStep === 'mode' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">{t('workspace.mode.title')}</h2>
                <p className="text-sm text-foreground-500 mb-5">{t('workspace.mode.subtitle')}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button
                    onClick={() => {
                      setPredictionMode('live');
                      setSelectedRegion(null);
                      setSelectedHazard(null);
                      setSelectedLeadTime(null);
                      setSelectedModel(null);
                    }}
                    className={`text-left p-5 rounded-lg border cursor-pointer transition-all ${
                      predictionMode === 'live'
                        ? 'border-primary-400 bg-primary-50 ring-1 ring-primary-300'
                        : 'border-background-200/70 bg-background-50 hover:border-background-300'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <i className="ri-radar-line text-xl text-primary-600"></i>
                      <span className="font-medium text-foreground-900">{t('workspace.mode.live.title')}</span>
                      <Badge variant="success">{t('workspace.mode.live.badge')}</Badge>
                    </div>
                    <p className="text-xs text-foreground-500">{t('workspace.mode.live.desc')}</p>
                  </button>
                  <button
                    onClick={() => {
                      setPredictionMode('historical');
                      setSelectedRegion(null);
                      setSelectedHazard(null);
                      setSelectedLeadTime(null);
                      setSelectedModel(null);
                    }}
                    className={`text-left p-5 rounded-lg border cursor-pointer transition-all ${
                      predictionMode === 'historical'
                        ? 'border-secondary-400 bg-secondary-50 ring-1 ring-secondary-300'
                        : 'border-background-200/70 bg-background-50 hover:border-background-300'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <i className="ri-history-line text-xl text-secondary-600"></i>
                      <span className="font-medium text-foreground-900">{t('workspace.mode.historical.title')}</span>
                      <Badge variant="secondary">{t('workspace.mode.historical.badge')}</Badge>
                    </div>
                    <p className="text-xs text-foreground-500">{t('workspace.mode.historical.desc')}</p>
                  </button>
                </div>
                {predictionMode === 'historical' && (
                  <div className="mt-5 p-4 rounded-lg bg-background-100 border border-background-200">
                    <label htmlFor="historical-date" className="text-sm font-medium text-foreground-700 block mb-2">
                      {t('workspace.mode.historicalDate')}
                    </label>
                    <input
                      id="historical-date"
                      type="date"
                      min="2025-01-01"
                      max="2025-12-30"
                      value={historicalDate}
                      onChange={(event) => setHistoricalDate(event.target.value)}
                      className="w-full sm:w-64 px-3 py-2 text-sm rounded-md border border-background-200 bg-background-50 text-foreground-900 focus:outline-none focus:ring-1 focus:ring-secondary-300"
                    />
                    <p className="text-xs text-foreground-400 mt-2">{t('workspace.mode.historicalHint')}</p>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Region */}
            {currentStep === 'region' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">{t('workspace.region.title')}</h2>
                <p className="text-sm text-foreground-500 mb-5">{t('workspace.region.subtitle')}</p>
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
                      {t('workspace.region.selected', {
                        name: selectedRegion.name,
                        nameEn: selectedRegion.nameEn,
                        lat: selectedRegion.lat.toFixed(2),
                        lon: selectedRegion.lon.toFixed(2),
                      })}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Hazard */}
            {currentStep === 'hazard' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">{t('workspace.hazard.title')}</h2>
                <p className="text-sm text-foreground-500 mb-5">{t('workspace.hazard.subtitle')}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {hazards.map((hazard) => {
                    const unavailableInHistorical = predictionMode === 'historical'
                      && !models.some((model) => isHistoricalModel(model) && model.supportedHazards.includes(hazard.id));
                    return (
                      <button
                        key={hazard.id}
                        disabled={unavailableInHistorical}
                        onClick={() => setSelectedHazard(hazard)}
                        className={`text-left p-4 rounded-lg border transition-all duration-200 ${
                          unavailableInHistorical
                            ? 'border-background-200 bg-background-100 opacity-55 cursor-not-allowed'
                            : selectedHazard?.id === hazard.id
                            ? 'border-primary-400 bg-primary-50 ring-1 ring-primary-300 cursor-pointer'
                            : 'border-background-200/70 bg-background-50 hover:border-background-300 hover:bg-background-100 cursor-pointer'
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
                              {unavailableInHistorical && <Badge variant="warning">{t('workspace.hazard.noHistoricalModel')}</Badge>}
                            </div>
                            <p className="text-xs text-foreground-500 mt-1">{hazard.description}</p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 4: Lead Time */}
            {currentStep === 'leadtime' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">{t('workspace.leadtime.title')}</h2>
                <p className="text-sm text-foreground-500 mb-5">
                  {predictionMode === 'historical'
                    ? <>{t('workspace.leadtime.historicalOnly')} <Badge variant="secondary">{t('workspace.leadtime.historicalOnlyBadge')}</Badge></>
                    : <>{t('workspace.leadtime.chooseFor', { hazard: selectedHazard?.name ?? '' })}</>}
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
                      <span className="text-xs text-foreground-500 mt-1">{t('workspace.leadtime.hours')}</span>
                    </button>
                  ))}
                </div>
                {predictionMode === 'historical' && historicalFeatureDate && (
                  <div className={`mt-4 p-3 rounded-lg border text-xs ${
                    historicalFeatureAvailable
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : 'bg-red-50 border-red-200 text-red-700'
                  }`}>
                    <i className={`${historicalFeatureAvailable ? 'ri-checkbox-circle-line' : 'ri-error-warning-line'} mr-1.5`}></i>
                    {historicalFeatureAvailable
                      ? t('workspace.leadtime.featureAvailable', { date: historicalFeatureDate.replaceAll('-', '') })
                      : t('workspace.leadtime.featureUnavailable', { date: historicalFeatureDate })}
                  </div>
                )}
              </div>
            )}

            {/* Step 5: Model */}
            {currentStep === 'model' && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="font-heading text-lg text-foreground-900">{t('workspace.model.title')}</h2>
                  <div className="flex items-center gap-1 bg-background-100 rounded-lg p-1">
                    <button
                      onClick={() => setModelViewMode('cards')}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors whitespace-nowrap ${
                        modelViewMode === 'cards' ? 'bg-background-50 text-foreground-900 shadow-sm' : 'text-foreground-500 hover:text-foreground-700'
                      }`}
                    >
                      <i className="ri-layout-grid-line mr-1"></i>{t('workspace.model.cardsView')}
                    </button>
                    <button
                      onClick={() => setModelViewMode('compare')}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors whitespace-nowrap ${
                        modelViewMode === 'compare' ? 'bg-background-50 text-foreground-900 shadow-sm' : 'text-foreground-500 hover:text-foreground-700'
                      }`}
                    >
                      <i className="ri-table-line mr-1"></i>{t('workspace.model.compareView')}
                    </button>
                  </div>
                </div>
                <p className="text-sm text-foreground-500 mb-5">
                  {t('workspace.model.runningFor', { mode: predictionMode === 'historical' ? t('workspace.mode.historical.title') : t('workspace.mode.live.title') })}
                  {selectedHazard && (
                    <span className="ml-1 text-foreground-400">
                      {t('workspace.model.runningForSuffix', { region: selectedRegion?.name ?? '', hazard: selectedHazard.name })}
                    </span>
                  )}
                </p>

                {selectedHazard?.id === 'heavy-rain' && (
                  <div className="mb-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-800">
                    <i className="ri-information-line mr-1.5"></i>
                    {t('workspace.model.heavyRainNotice')}
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
                                  {isBestAuc && <Badge variant="accent" size="sm">{t('workspace.model.bestAuc')}</Badge>}
                                </div>
                                <p className="text-xs text-foreground-500 mt-0.5 truncate">{model.description}</p>
                                <div className="mt-1.5"><ModelAvailability model={model} /></div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0 ml-4">
                              <Badge variant={model.type === 'ensemble' ? 'accent' : model.type === 'deep' ? 'primary' : 'secondary'}>
                                {model.type === 'tree' ? t('workspace.model.type.tree') : model.type === 'deep' ? t('workspace.model.type.deep') : model.type === 'ensemble' ? t('workspace.model.type.ensemble') : model.type === 'rule' ? t('workspace.model.type.rule') : t('workspace.model.type.physical')}
                              </Badge>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedModel(isExpanded ? null : model.id);
                                }}
                                className="p-1.5 rounded-md hover:bg-background-200 cursor-pointer transition-colors"
                                title={isExpanded ? t('workspace.model.collapseMetrics') : t('workspace.model.expandMetrics')}
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
                                      <span className="text-[10px] text-foreground-400 whitespace-nowrap">{t(meta.nameKey)}</span>
                                      <span className={`text-xs font-semibold ${tierColor}`}>{pct}%</span>
                                    </div>
                                  );
                                })}
                                <span className="text-[10px] text-foreground-300 ml-auto">{t('workspace.model.expandHint')}</span>
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
                          <th className="py-2.5 px-3 text-xs font-medium text-foreground-500">{t('workspace.model.compareTable.model')}</th>
                          {(['auc', 'pod', 'far', 'csi', 'f1', 'brier'] as (keyof ModelMetrics)[]).map((key) => (
                            <th key={key} className="py-2.5 px-2 text-center text-xs font-medium text-foreground-500 cursor-help" title={t(METRIC_LABELS[key].descriptionKey)}>
                              {t(METRIC_LABELS[key].nameKey)}
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
                        {t('workspace.model.compareFootnote', { hazard: selectedHazard?.name ?? '' })}
                      </p>
                    </div>
                  </div>
                )}

                {availableModels.length === 0 && (
                  <div className="text-center py-8 text-foreground-400">
                    <i className="ri-emotion-sad-line text-2xl block mb-2"></i>
                    <p>{t('workspace.model.noAvailableModel')}</p>
                  </div>
                )}
              </div>
            )}

            {/* Step 6: Confirm */}
            {currentStep === 'confirm' && (
              <div>
                <h2 className="font-heading text-lg text-foreground-900 mb-1">{t('workspace.confirm.title')}</h2>
                <p className="text-sm text-foreground-500 mb-5">{t('workspace.confirm.subtitle')}</p>

                <div className="bg-background-100 rounded-lg p-5 mb-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">{t('workspace.confirm.mode')}</span>
                      <span className="text-sm font-medium text-foreground-900">
                        {predictionMode === 'historical' ? t('workspace.mode.historical.title') : t('workspace.mode.live.title')}
                      </span>
                      {predictionMode === 'historical' && (
                        <p className="text-xs text-foreground-400 mt-0.5">{t('workspace.confirm.initialDate', { date: historicalDate })}</p>
                      )}
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">{t('workspace.confirm.region')}</span>
                      <span className="text-sm font-medium text-foreground-900">{selectedRegion?.name} ({selectedRegion?.nameEn})</span>
                      <p className="text-xs text-foreground-400 mt-0.5">
                        {t('workspace.confirm.flashFloodSensitivity', {
                          value: selectedRegion?.sensitivity.flashFlood === 'high' ? t('workspace.sensitivity.high') : selectedRegion?.sensitivity.flashFlood === 'medium' ? t('workspace.sensitivity.medium') : t('workspace.sensitivity.low'),
                        })}
                        {' · '}
                        {t('workspace.confirm.heatwaveSensitivity', {
                          value: selectedRegion?.sensitivity.heatwave === 'high' ? t('workspace.sensitivity.high') : selectedRegion?.sensitivity.heatwave === 'medium' ? t('workspace.sensitivity.medium') : t('workspace.sensitivity.low'),
                        })}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">{t('workspace.confirm.hazard')}</span>
                      <div className="flex items-center gap-2">
                        <i className={`${selectedHazard?.icon}`} style={{ color: selectedHazard?.color }}></i>
                        <span className="text-sm font-medium text-foreground-900">{selectedHazard?.name}</span>
                      </div>
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">{t('workspace.confirm.leadTime')}</span>
                      <span className="text-sm font-medium text-foreground-900">{t('workspace.confirm.leadTimeValue', { hours: selectedLeadTime })}</span>
                    </div>
                    <div>
                      <span className="text-xs text-foreground-500 block mb-1">{t('workspace.confirm.model')}</span>
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
                                <span className="text-[10px] text-foreground-500">{t(meta.nameKey)}</span>
                                <span className={`text-xs font-semibold ${good ? 'text-accent-700' : 'text-foreground-600'}`}>{pct}%</span>
                              </div>
                            );
                          })}
                          <span className="text-[10px] text-foreground-400">{t('workspace.confirm.validationSet', { hazard: selectedHazard.name })}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Execution progress */}
                {isRunning && (
                  <div className="bg-background-100 rounded-lg p-5 mb-5">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-5 h-5 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm text-foreground-700 font-medium">{t('workspace.confirm.running')}</span>
                    </div>
                    <div className="space-y-2">
                      {[
                        t('workspace.confirm.steps.dataPrep'),
                        t('workspace.confirm.steps.modelPredict'),
                        t('workspace.confirm.steps.scoreSemantics'),
                        t('workspace.confirm.steps.riskDecision'),
                        t('workspace.confirm.steps.explanation'),
                        t('workspace.confirm.steps.graphBuild'),
                        t('workspace.confirm.steps.reportGen'),
                      ].map((label, idx) => {
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
                        <p className="mb-2">{t('workspace.confirm.pipelineIntro')}</p>
                        <ol className="list-decimal list-inside space-y-1">
                          <li>{t('workspace.confirm.pipeline.step1')}</li>
                          <li>{t('workspace.confirm.pipeline.step2')}</li>
                          <li>{predictionMode === 'historical' ? t('workspace.confirm.pipeline.step3Historical') : t('workspace.confirm.pipeline.step3Live')}</li>
                          <li>{t('workspace.confirm.pipeline.step4', { region: selectedRegion?.name ?? '' })}</li>
                          <li>{t('workspace.confirm.pipeline.step5')}</li>
                          <li>{t('workspace.confirm.pipeline.step6')}</li>
                          <li>{t('workspace.confirm.pipeline.step7')}</li>
                          <li>{t('workspace.confirm.pipeline.step8')}</li>
                        </ol>
                        <p className="mt-2 text-foreground-400">{t('workspace.confirm.pipelineFootnote')}</p>
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
                const idx = STEP_ORDER.indexOf(currentStep);
                if (idx > 0) setCurrentStep(STEP_ORDER[idx - 1]);
              }}
              disabled={currentStep === 'mode'}
            >
              {t('workspace.nav.prev')}
            </Button>

            {currentStep !== 'confirm' ? (
              <Button variant="primary" icon="ri-arrow-right-line" onClick={handleNext} disabled={!canProceed()}>
                {t('workspace.nav.next')}
              </Button>
            ) : (
              <Button
                variant="primary"
                icon="ri-play-fill"
                onClick={handleRunPrediction}
                disabled={isRunning}
              >
                {isRunning ? t('workspace.nav.running') : t('workspace.nav.run')}
              </Button>
            )}
          </div>
        </div>
      </main>

      <footer className="border-t border-background-200/70 bg-background-100 mt-12">
        <div className="max-w-[1280px] mx-auto px-6 md:px-8 py-5">
          <div className="flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-foreground-500">
              <i className="ri-shield-check-line text-accent-600"></i>
              <span>{t('common.disclaimer')}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
