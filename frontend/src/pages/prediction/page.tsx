import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Navbar from '@/components/feature/Navbar';
import Button from '@/components/base/Button';
import Badge from '@/components/base/Badge';
import RiskBadge from '@/components/base/RiskBadge';
import Card from '@/components/base/Card';
import { type PredictionResult, type RuleHit, type MechanismPath, type HistoricalEvent } from '@/mocks/predictions';
import { fetchPrediction } from '@/services/predictionApi';
import { buildChatContext } from '@/mocks/chatResponses';
import { useSetChatContext } from '@/hooks/useChatContext';
import { ambiguityLabel, calibrationLabel, scoreLabel } from '@/services/predictionSemantics';

type Tab = 'overview' | 'features' | 'rules' | 'mechanisms' | 'history';

export default function PredictionDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const navState = (location.state as { activeTab?: Tab } | null);
  const [activeTab, setActiveTab] = useState<Tab>(navState?.activeTab || 'overview');

  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const setChatContext = useSetChatContext();

  useEffect(() => {
    if (!id) {
      setLoadError(t('prediction.missingId'));
      return;
    }
    let cancelled = false;
    fetchPrediction(id)
      .then((result) => { if (!cancelled) { setPrediction(result); setLoadError(null); } })
      .catch((error: unknown) => { if (!cancelled) setLoadError(error instanceof Error ? error.message : t('prediction.loadError')); });
    return () => { cancelled = true; };
  }, [id, t]);

  useEffect(() => {
    if (prediction) {
      setChatContext(buildChatContext(prediction));
    }
    return () => setChatContext(null);
  }, [prediction, setChatContext]);

  if (!prediction) {
    return (
      <div className="min-h-screen bg-background-50">
        <Navbar />
        <div className="flex items-center justify-center h-[60vh]">
          <div className="text-center">
            <i className="ri-error-warning-line text-4xl text-foreground-300"></i>
            <p className="text-foreground-500 mt-3">{loadError || t('prediction.loadingRecord')}</p>
            <Button variant="outline" className="mt-4" onClick={() => navigate('/')}>{t('common.backHome')}</Button>
          </div>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: string; count?: number }[] = [
    { key: 'overview', label: t('prediction.tabs.overview'), icon: 'ri-radar-line' },
    { key: 'features', label: t('prediction.tabs.features'), icon: 'ri-bar-chart-2-line', count: prediction.features.length },
    { key: 'rules', label: t('prediction.tabs.rules'), icon: 'ri-checkbox-multiple-line', count: prediction.ruleHits.filter((r) => r.met).length },
    { key: 'mechanisms', label: t('prediction.tabs.mechanisms'), icon: 'ri-git-branch-line', count: prediction.mechanisms.length },
    { key: 'history', label: t('prediction.tabs.history'), icon: 'ri-history-line', count: prediction.similarEvents.length },
  ];

  return (
    <div className="min-h-screen bg-background-50">
      <Navbar />

      <main className="w-full px-6 md:px-8 py-6">
        <div className="max-w-[1200px] mx-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-3">
              <button onClick={() => navigate(-1)} className="p-2 rounded-md hover:bg-background-100 cursor-pointer text-foreground-500">
                <i className="ri-arrow-left-line"></i>
              </button>
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="font-heading text-xl text-foreground-900">
                    {t('prediction.headerTitle', { hazard: prediction.hazardLabel, region: prediction.regionName })}
                  </h1>
                  <RiskBadge level={prediction.riskLevel} size="md" />
                </div>
                <p className="text-sm text-foreground-500 mt-1">
                  {t('prediction.subheader', {
                    id: prediction.predictionId,
                    time: prediction.initialTime.replace('T', ' ').slice(0, 16),
                    hours: prediction.leadTimeHours,
                  })}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                icon="ri-share-box-line"
                onClick={() => navigate(`/prediction/${prediction.predictionId}/graph`)}
              >
                {t('prediction.viewGraph')}
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 border-b border-background-200/70 mb-6">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium cursor-pointer border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.key
                    ? 'border-primary-500 text-primary-700'
                    : 'border-transparent text-foreground-500 hover:text-foreground-700'
                }`}
              >
                <i className={`${tab.icon} text-sm`}></i>
                {tab.label}
                {tab.count !== undefined && (
                  <span className={`ml-1 px-1.5 py-0.5 rounded-full text-xs ${
                    activeTab === tab.key ? 'bg-primary-100 text-primary-700' : 'bg-background-100 text-foreground-500'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="animate-[fadeIn_0.2s_ease-in-out]">
            {activeTab === 'overview' && <OverviewTab prediction={prediction} />}
            {activeTab === 'features' && <FeaturesTab prediction={prediction} />}
            {activeTab === 'rules' && <RulesTab rules={prediction.ruleHits} />}
            {activeTab === 'mechanisms' && <MechanismsTab mechanisms={prediction.mechanisms} />}
            {activeTab === 'history' && <HistoryTab events={prediction.similarEvents} />}
          </div>
        </div>
      </main>

      <footer className="border-t border-background-200/70 bg-background-100 mt-12">
        <div className="max-w-[1280px] mx-auto px-6 md:px-8 py-5">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-foreground-500">
              <i className="ri-shield-check-line text-accent-600"></i>
              <span>{t('common.disclaimer')}</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-foreground-400">
              <span>{t('prediction.footer.dataHash', { value: prediction.inputHash })}</span>
              <span>{t('prediction.footer.model', { name: prediction.modelName, version: prediction.modelVersion })}</span>
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
}

function OverviewTab({ prediction }: { prediction: PredictionResult }) {
  const { t, i18n } = useTranslation();
  const lang: 'zh' | 'en' = i18n.language?.startsWith('zh') ? 'zh' : 'en';
  return (
    <div className="space-y-6">
      {/* Key metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">{scoreLabel(prediction, lang)}</p>
          <p className="text-3xl font-heading text-primary-600">
            {(prediction.decisionScore * 100).toFixed(0)}/100
          </p>
          <div className="mt-2 w-full bg-background-200 rounded-full h-1.5">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-700"
              style={{ width: `${prediction.decisionScore * 100}%` }}
            ></div>
          </div>
        </Card>
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">{t('prediction.overview.calibrationStatus')}</p>
          <p className="text-2xl font-heading text-foreground-900">{calibrationLabel(prediction, lang)}</p>
          <p className="text-xs text-foreground-400 mt-1">{t('prediction.overview.rawScore', { value: (prediction.probability * 100).toFixed(0) })}</p>
        </Card>
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">{t('prediction.overview.ambiguity')}</p>
          <p className="text-3xl font-heading text-foreground-900">
            {(prediction.ambiguity * 100).toFixed(0)}/100
          </p>
          <p className="text-xs text-foreground-400 mt-1">
            {ambiguityLabel(prediction.ambiguity, lang)} · {t('prediction.overview.notConfidenceInterval')}
          </p>
        </Card>
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">{t('prediction.overview.riskLevel')}</p>
          <div className="flex justify-center mt-1">
            <RiskBadge level={prediction.riskLevel} size="lg" />
          </div>
        </Card>
      </div>

      {/* Risk description */}
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-3">{t('prediction.overview.riskExplanation')}</h3>
        <div className="bg-background-100 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <i className="ri-information-line text-primary-500 mt-0.5"></i>
            <p className="text-sm text-foreground-700 leading-relaxed">{prediction.riskDescription}</p>
          </div>
        </div>
      </Card>

      {/* Metadata */}
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-3">{t('prediction.overview.metadata')}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <MetadataItem label={t('prediction.overview.meta.predictionId')} value={prediction.predictionId} />
          <MetadataItem label={t('prediction.overview.meta.caseId')} value={prediction.caseId} />
          <MetadataItem label={t('prediction.overview.meta.model')} value={`${prediction.modelName} ${prediction.modelVersion}`} />
          <MetadataItem label={t('prediction.overview.meta.region')} value={prediction.regionName} />
          <MetadataItem label={t('prediction.overview.meta.hazard')} value={prediction.hazardLabel} />
          <MetadataItem label={t('prediction.overview.meta.targetTime')} value={prediction.targetTime.replace('T', ' ').slice(0, 16)} />
          <MetadataItem label={t('prediction.overview.meta.initialTime')} value={prediction.initialTime.replace('T', ' ').slice(0, 16)} />
          <MetadataItem label={t('prediction.overview.meta.leadTime')} value={t('prediction.overview.meta.leadTimeValue', { hours: prediction.leadTimeHours })} />
          <MetadataItem label={t('prediction.overview.meta.inputHash')} value={prediction.inputHash} />
          {prediction.forecastSource && <MetadataItem label={t('prediction.overview.meta.forecastSource')} value={prediction.forecastSource} />}
          {prediction.forecastSnapshotId && <MetadataItem label={t('prediction.overview.meta.snapshotId')} value={prediction.forecastSnapshotId} />}
        </div>
      </Card>
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-background-100 rounded-md p-3">
      <p className="text-xs text-foreground-500">{label}</p>
      <p className="text-sm text-foreground-900 font-medium mt-0.5">{value}</p>
    </div>
  );
}

function FeaturesTab({ prediction }: { prediction: PredictionResult }) {
  const { t } = useTranslation();
  const features = prediction.features;
  const verifiedTreeShap = prediction.attributionMethod === 'tree_shap';
  const attributionUnavailable = prediction.attributionMethod?.startsWith('unavailable:') ?? false;
  const maxContrib = Math.max(...features.map((f) => Math.abs(f.contribution)), 0.01);
  const contributionSum = features.reduce((sum, feature) => sum + feature.contribution, 0);
  const signed = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(4)}`;

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">
          {verifiedTreeShap ? t('prediction.features.treeShapTitle') : attributionUnavailable ? t('prediction.features.unavailableTitle') : t('prediction.features.legacyTitle')}
        </h3>
        <p className="text-xs text-foreground-500 mb-2">
          {verifiedTreeShap
            ? t('prediction.features.treeShapDesc')
            : attributionUnavailable
              ? t('prediction.features.unavailableDesc')
              : t('prediction.features.legacyDesc')}
        </p>
        {verifiedTreeShap && prediction.attributionBaseValue != null && prediction.attributionModelOutput != null && (
          <p className="text-xs text-foreground-600 bg-background-100 rounded-md px-3 py-2 mb-5 font-mono">
            {t('prediction.features.baseline', {
              base: prediction.attributionBaseValue.toFixed(4),
              sum: signed(contributionSum),
              output: prediction.attributionModelOutput.toFixed(4),
            })}
          </p>
        )}
        <div className="space-y-3">
          {features.length === 0 && (
            <div className="rounded-md border border-background-200 bg-background-100 px-4 py-5 text-sm text-foreground-500">
              {t('prediction.features.noAttribution')}
            </div>
          )}
          {features.map((feat) => (
            <div key={feat.feature} className="flex items-center gap-4">
              <div className="w-28 flex-shrink-0">
                <p className="text-sm font-medium text-foreground-900">{feat.featureLabel}</p>
                <p className="text-xs text-foreground-400">{feat.feature}</p>
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-foreground-500">
                    {t('prediction.features.actualValue', { value: feat.actualValue != null ? `${feat.actualValue} ${feat.unit}` : '—' })}
                    {feat.normalValue != null ? t('prediction.features.referenceValue', { value: `${feat.normalValue} ${feat.unit}` }) : ''}
                  </span>
                  <span className={`text-xs font-medium ${feat.contribution >= 0 ? 'text-red-500' : 'text-accent-600'}`}>
                    {signed(feat.contribution)}
                  </span>
                </div>
                <div className="w-full bg-background-200 rounded-full h-2">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${feat.contribution >= 0 ? 'bg-red-400' : 'bg-accent-500'}`}
                    style={{ width: `${(Math.abs(feat.contribution) / maxContrib) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Feature comparison table */}
      {features.length > 0 && <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-3">{t('prediction.features.comparisonTitle')}</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-background-200/70">
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">{t('prediction.features.table.indicator')}</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">{t('prediction.features.table.normal')}</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">{t('prediction.features.table.actual')}</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">{t('prediction.features.table.deviation')}</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">{t('prediction.features.table.contribution')}</th>
              </tr>
            </thead>
            <tbody>
              {features.map((feat) => {
                const deviation = feat.actualValue != null && feat.normalValue != null && feat.normalValue !== 0
                  ? ((feat.actualValue - feat.normalValue) / Math.abs(feat.normalValue) * 100).toFixed(0)
                  : null;
                const isPositive = deviation != null && Number(deviation) > 0;
                return (
                  <tr key={feat.feature} className="border-b border-background-200/50">
                    <td className="px-4 py-2.5 font-medium text-foreground-900">{feat.featureLabel}</td>
                    <td className="px-4 py-2.5 text-foreground-700">{feat.normalValue != null ? `${feat.normalValue} ${feat.unit}` : '—'}</td>
                    <td className="px-4 py-2.5 text-foreground-900">{feat.actualValue != null ? `${feat.actualValue} ${feat.unit}` : '—'}</td>
                    <td className="px-4 py-2.5">
                      {deviation == null ? '—' : (
                        <span className={isPositive ? 'text-red-500' : 'text-accent-600'}>
                          {isPositive ? '+' : ''}{deviation}%
                        </span>
                      )}
                    </td>
                    <td className={`px-4 py-2.5 font-medium ${feat.contribution >= 0 ? 'text-red-500' : 'text-accent-600'}`}>{signed(feat.contribution)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>}
    </div>
  );
}

function RulesTab({ rules }: { rules: RuleHit[] }) {
  const { t } = useTranslation();
  const triggered = rules.filter((r) => r.met);
  const notTriggered = rules.filter((r) => !r.met);

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">{t('prediction.rules.title')}</h3>
        <p className="text-xs text-foreground-500 mb-5">{t('prediction.rules.subtitle')}</p>

        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground-500 mb-2">{t('prediction.rules.triggered', { count: triggered.length })}</p>
          {triggered.map((rule) => (
            <div key={rule.ruleId} className="bg-accent-50 border border-accent-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <i className="ri-checkbox-circle-fill text-accent-500"></i>
                  <span className="font-medium text-foreground-900 text-sm">{rule.ruleName}</span>
                  <Badge variant="accent" size="sm">{t('prediction.rules.weight', { value: rule.weight })}</Badge>
                </div>
              </div>
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-foreground-500">{t('prediction.rules.condition')}</span>
                  <span className="text-foreground-700 font-mono">{rule.condition}</span>
                </div>
                <div>
                  <span className="text-foreground-500">{t('prediction.rules.actualValue')}</span>
                  <span className="text-foreground-700 font-mono">{rule.actualValue}</span>
                  <span className="text-foreground-500 ml-2">{t('prediction.rules.threshold')}</span>
                  <span className="text-foreground-700 font-mono">{rule.threshold}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {notTriggered.length > 0 && (
          <div className="mt-5 space-y-2">
            <p className="text-xs font-medium text-foreground-500 mb-2">{t('prediction.rules.notTriggered', { count: notTriggered.length })}</p>
            {notTriggered.map((rule) => (
              <div key={rule.ruleId} className="bg-background-100 border border-background-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <i className="ri-checkbox-blank-circle-line text-foreground-300"></i>
                  <span className="text-sm text-foreground-600">{rule.ruleName}</span>
                </div>
                <div className="mt-1 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-foreground-500">
                  <span className="font-mono">{rule.condition}</span>
                  <span>{t('prediction.rules.actualShort', { value: rule.actualValue, threshold: rule.threshold })}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function MechanismsTab({ mechanisms }: { mechanisms: MechanismPath[] }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">{t('prediction.mechanisms.title')}</h3>
        <p className="text-xs text-foreground-500 mb-5">{t('prediction.mechanisms.subtitle')}</p>

        <div className="space-y-6">
          {mechanisms.map((mech, mi) => (
            <div key={mech.pathId}>
              <div className="flex items-center gap-3 mb-4">
                <h4 className="font-medium text-foreground-900">{mech.pathName}</h4>
                <Badge variant={mech.confidence === 'high' ? 'success' : mech.confidence === 'medium' ? 'warning' : 'secondary'}>
                  {mech.confidence === 'high' ? t('prediction.mechanisms.confidenceHigh') : mech.confidence === 'medium' ? t('prediction.mechanisms.confidenceMedium') : t('prediction.mechanisms.confidenceLow')}
                </Badge>
                {mech.supportScore !== undefined && <Badge variant="primary">{t('prediction.mechanisms.supportScore', { value: (mech.supportScore * 100).toFixed(0) })}</Badge>}
              </div>
              {mech.summary && <p className="text-xs text-foreground-500 mb-4">{mech.summary}</p>}

              <div className="relative pl-8">
                <div className="absolute left-[15px] top-3 bottom-3 w-[2px] bg-background-300"></div>
                <div className="space-y-4">
                  {mech.steps.map((step, si) => (
                    <div key={si} className="relative">
                      <div className="absolute left-[-32px] top-1.5 w-5 h-5 rounded-full bg-background-50 border-2 border-accent-400 flex items-center justify-center">
                        <span className="text-[10px] font-bold text-accent-600">{step.step}</span>
                      </div>
                      <div className="bg-background-100 rounded-lg p-4">
                        <p className="text-sm text-foreground-900 mb-1">{step.description}</p>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-foreground-500">{t('prediction.mechanisms.indicator', { indicator: step.indicator })}</span>
                          <span className="font-medium text-accent-600">{step.value}</span>
                          {step.compatibility !== undefined && <span className="text-foreground-500">{t('prediction.mechanisms.compatibility', { value: (step.compatibility * 100).toFixed(0) })}</span>}
                        </div>
                      </div>
                      {si < mech.steps.length - 1 && (
                        <div className="ml-0 my-1 pl-3 border-l-2 border-accent-200 py-2">
                          <i className="ri-arrow-down-fill text-accent-400 text-xs"></i>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {mi < mechanisms.length - 1 && (
                <div className="mt-6 pt-4 border-t border-background-200/50"></div>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="flex items-start gap-3">
          <i className="ri-information-line text-foreground-400 mt-0.5"></i>
          <div className="text-xs text-foreground-500">
            <p className="mb-1 font-medium text-foreground-700">{t('prediction.mechanisms.noteTitle')}</p>
            <p>{t('prediction.mechanisms.noteBody')}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function HistoryTab({ events }: { events: HistoricalEvent[] }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">{t('prediction.history.title')}</h3>
        <p className="text-xs text-foreground-500 mb-5">{t('prediction.history.subtitle')}</p>

        <div className="space-y-3">
          {events.map((evt) => (
            <div key={evt.eventId} className="bg-background-100 border border-background-200/70 rounded-lg p-4">
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-medium text-foreground-900 text-sm">{evt.date}</span>
                    <Badge variant="secondary">{evt.region}</Badge>
                    <Badge variant="accent">{evt.hazard}</Badge>
                    <Badge variant="primary">{t('prediction.history.similarity', { value: (evt.similarity * 100).toFixed(0) })}</Badge>
                    {evt.verificationStatus && <Badge variant="secondary">{evt.verificationStatus}</Badge>}
                  </div>
                  <p className="text-sm text-foreground-700 mb-2">{evt.description}</p>
                  <div className="flex flex-wrap gap-3 text-xs text-foreground-500">
                    {evt.maxRainfall != null && <span>{t('prediction.history.maxRainfall', { value: evt.maxRainfall })}</span>}
                    {evt.maxTemp != null && <span>{t('prediction.history.maxTemp', { value: evt.maxTemp })}</span>}
                    <span className="text-orange-600">{t('prediction.history.impact', { value: evt.impact })}</span>
                    {evt.dataCoverage !== undefined && <span>{t('prediction.history.dataCoverage', { value: (evt.dataCoverage * 100).toFixed(0) })}</span>}
                  </div>
                  {evt.similarityDimensions && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3">
                      {evt.similarityDimensions.map((dimension) => (
                        <div key={dimension.key} className="bg-background-50 rounded p-2 text-xs">
                          <div className="flex justify-between"><span className="text-foreground-600">{dimension.label}</span><span className="font-medium">{(dimension.score * 100).toFixed(0)}%</span></div>
                          <p className="text-foreground-400 mt-1">{t('prediction.history.weight', { weight: (dimension.weight * 100).toFixed(0), explanation: dimension.explanation })}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {evt.sourceTitle && <p className="text-[11px] text-foreground-400 mt-3">{t('prediction.history.source', { value: evt.sourceTitle })}</p>}
                </div>
                <div className="flex-shrink-0">
                  <div className="w-14 h-14 rounded-full border-2 border-primary-200 flex items-center justify-center">
                    <span className="text-sm font-heading text-primary-600">{(evt.similarity * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
