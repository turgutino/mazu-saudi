import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Navbar from '@/components/feature/Navbar';
import Button from '@/components/base/Button';
import Badge from '@/components/base/Badge';
import RiskBadge from '@/components/base/RiskBadge';
import Card from '@/components/base/Card';
import { type PredictionResult, type FeatureContribution, type RuleHit, type MechanismPath, type HistoricalEvent } from '@/mocks/predictions';
import { fetchPrediction } from '@/services/predictionApi';
import { buildChatContext } from '@/mocks/chatResponses';
import { useSetChatContext } from '@/hooks/useChatContext';

type Tab = 'overview' | 'features' | 'rules' | 'mechanisms' | 'history';

export default function PredictionDetail() {
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
      setLoadError('缺少预测 ID');
      return;
    }
    let cancelled = false;
    fetchPrediction(id)
      .then((result) => { if (!cancelled) { setPrediction(result); setLoadError(null); } })
      .catch((error: unknown) => { if (!cancelled) setLoadError(error instanceof Error ? error.message : '预测加载失败'); });
    return () => { cancelled = true; };
  }, [id]);

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
            <p className="text-foreground-500 mt-3">{loadError || '正在加载预测记录…'}</p>
            <Button variant="outline" className="mt-4" onClick={() => navigate('/')}>返回首页</Button>
          </div>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: string; count?: number }[] = [
    { key: 'overview', label: '预测概览', icon: 'ri-radar-line' },
    { key: 'features', label: '特征贡献', icon: 'ri-bar-chart-2-line', count: prediction.features.length },
    { key: 'rules', label: '命中规则', icon: 'ri-checkbox-multiple-line', count: prediction.ruleHits.filter((r) => r.met).length },
    { key: 'mechanisms', label: '物理机制', icon: 'ri-git-branch-line', count: prediction.mechanisms.length },
    { key: 'history', label: '相似事件', icon: 'ri-history-line', count: prediction.similarEvents.length },
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
                    {prediction.hazardLabel}预测 — {prediction.regionName}
                  </h1>
                  <RiskBadge level={prediction.riskLevel} size="md" />
                </div>
                <p className="text-sm text-foreground-500 mt-1">
                  {prediction.predictionId} · 起报 {prediction.initialTime.replace('T', ' ').slice(0, 16)} · 时效 {prediction.leadTimeHours}h
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
                查看图谱
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
            {activeTab === 'features' && <FeaturesTab features={prediction.features} />}
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
              <span>预测结果仅供参考，实际预警以官方发布为准</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-foreground-400">
              <span>数据哈希: {prediction.inputHash}</span>
              <span>模型: {prediction.modelName} {prediction.modelVersion}</span>
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
}

function OverviewTab({ prediction }: { prediction: PredictionResult }) {
  return (
    <div className="space-y-6">
      {/* Key metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">校准后概率</p>
          <p className="text-3xl font-heading text-primary-600">
            {(prediction.calibratedProbability * 100).toFixed(0)}%
          </p>
          <div className="mt-2 w-full bg-background-200 rounded-full h-1.5">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-700"
              style={{ width: `${prediction.calibratedProbability * 100}%` }}
            ></div>
          </div>
        </Card>
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">原始概率</p>
          <p className="text-3xl font-heading text-foreground-900">
            {(prediction.probability * 100).toFixed(0)}%
          </p>
        </Card>
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">模型不确定性</p>
          <p className="text-3xl font-heading text-foreground-900">
            ±{(prediction.uncertainty * 100).toFixed(0)}%
          </p>
          <p className="text-xs text-foreground-400 mt-1">
            {prediction.uncertainty < 0.15 ? '低不确定性' : prediction.uncertainty < 0.25 ? '中等不确定性' : '高不确定性'}
          </p>
        </Card>
        <Card className="text-center py-6">
          <p className="text-xs text-foreground-500 mb-2">风险等级</p>
          <div className="flex justify-center mt-1">
            <RiskBadge level={prediction.riskLevel} size="lg" />
          </div>
        </Card>
      </div>

      {/* Risk description */}
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-3">风险决策解释</h3>
        <div className="bg-background-100 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <i className="ri-information-line text-primary-500 mt-0.5"></i>
            <p className="text-sm text-foreground-700 leading-relaxed">{prediction.riskDescription}</p>
          </div>
        </div>
      </Card>

      {/* Metadata */}
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-3">预测元数据</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <MetadataItem label="预测ID" value={prediction.predictionId} />
          <MetadataItem label="案例ID" value={prediction.caseId} />
          <MetadataItem label="模型" value={`${prediction.modelName} ${prediction.modelVersion}`} />
          <MetadataItem label="区域" value={prediction.regionName} />
          <MetadataItem label="灾种" value={prediction.hazardLabel} />
          <MetadataItem label="目标时间" value={prediction.targetTime.replace('T', ' ').slice(0, 16)} />
          <MetadataItem label="起报时间" value={prediction.initialTime.replace('T', ' ').slice(0, 16)} />
          <MetadataItem label="预报时效" value={`${prediction.leadTimeHours} 小时`} />
          <MetadataItem label="输入数据哈希" value={prediction.inputHash} />
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

function FeaturesTab({ features }: { features: FeatureContribution[] }) {
  const maxContrib = Math.max(...features.map((f) => Math.abs(f.contribution)), 0.01);

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">SHAP 特征贡献</h3>
        <p className="text-xs text-foreground-500 mb-5">模型解释：为什么给出这个概率？以下关键变量的正向贡献推动了概率上升。</p>
        <div className="space-y-3">
          {features.map((feat) => (
            <div key={feat.feature} className="flex items-center gap-4">
              <div className="w-28 flex-shrink-0">
                <p className="text-sm font-medium text-foreground-900">{feat.featureLabel}</p>
                <p className="text-xs text-foreground-400">{feat.feature}</p>
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-foreground-500">
                    实际 {feat.actualValue} {feat.unit} (正常 {feat.normalValue})
                  </span>
                  <span className="text-xs font-medium text-primary-600">
                    +{feat.contribution.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-background-200 rounded-full h-2">
                  <div
                    className="h-full rounded-full bg-primary-500 transition-all duration-700"
                    style={{ width: `${(feat.contribution / maxContrib) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Feature comparison table */}
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-3">指标对比</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-background-200/70">
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">指标</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">正常值</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">实际值</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">偏差</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-foreground-500">贡献</th>
              </tr>
            </thead>
            <tbody>
              {features.map((feat) => {
                const deviation = feat.normalValue !== 0 ? ((feat.actualValue - feat.normalValue) / Math.abs(feat.normalValue) * 100).toFixed(0) : '0';
                const isPositive = Number(deviation) > 0;
                return (
                  <tr key={feat.feature} className="border-b border-background-200/50">
                    <td className="px-4 py-2.5 font-medium text-foreground-900">{feat.featureLabel}</td>
                    <td className="px-4 py-2.5 text-foreground-700">{feat.normalValue} {feat.unit}</td>
                    <td className="px-4 py-2.5 text-foreground-900">{feat.actualValue} {feat.unit}</td>
                    <td className="px-4 py-2.5">
                      <span className={isPositive ? 'text-red-500' : 'text-accent-600'}>
                        {isPositive ? '+' : ''}{deviation}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-primary-600 font-medium">+{feat.contribution.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function RulesTab({ rules }: { rules: RuleHit[] }) {
  const triggered = rules.filter((r) => r.met);
  const notTriggered = rules.filter((r) => !r.met);

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">风险决策规则</h3>
        <p className="text-xs text-foreground-500 mb-5">风险决策解释：为什么发出这个等级？</p>

        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground-500 mb-2">命中的规则 ({triggered.length})</p>
          {triggered.map((rule) => (
            <div key={rule.ruleId} className="bg-accent-50 border border-accent-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <i className="ri-checkbox-circle-fill text-accent-500"></i>
                  <span className="font-medium text-foreground-900 text-sm">{rule.ruleName}</span>
                  <Badge variant="accent" size="sm">权重 {rule.weight}</Badge>
                </div>
              </div>
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-foreground-500">条件: </span>
                  <span className="text-foreground-700 font-mono">{rule.condition}</span>
                </div>
                <div>
                  <span className="text-foreground-500">实际值: </span>
                  <span className="text-foreground-700 font-mono">{rule.actualValue}</span>
                  <span className="text-foreground-500 ml-2">阈值: </span>
                  <span className="text-foreground-700 font-mono">{rule.threshold}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {notTriggered.length > 0 && (
          <div className="mt-5 space-y-2">
            <p className="text-xs font-medium text-foreground-500 mb-2">未命中的规则 ({notTriggered.length})</p>
            {notTriggered.map((rule) => (
              <div key={rule.ruleId} className="bg-background-100 border border-background-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <i className="ri-checkbox-blank-circle-line text-foreground-300"></i>
                  <span className="text-sm text-foreground-600">{rule.ruleName}</span>
                </div>
                <div className="mt-1 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-foreground-500">
                  <span className="font-mono">{rule.condition}</span>
                  <span>实际: {rule.actualValue} / 阈值: {rule.threshold}</span>
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
  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">物理机制相容性</h3>
        <p className="text-xs text-foreground-500 mb-5">当前指标组合与哪些已知气象机制相容？这里不把相容性解释成个例因果。</p>

        <div className="space-y-6">
          {mechanisms.map((mech, mi) => (
            <div key={mech.pathId}>
              <div className="flex items-center gap-3 mb-4">
                <h4 className="font-medium text-foreground-900">{mech.pathName}</h4>
                <Badge variant={mech.confidence === 'high' ? 'success' : mech.confidence === 'medium' ? 'warning' : 'secondary'}>
                  {mech.confidence === 'high' ? '高置信度' : mech.confidence === 'medium' ? '中置信度' : '低置信度'}
                </Badge>
                {mech.supportScore !== undefined && <Badge variant="primary">相容度 {(mech.supportScore * 100).toFixed(0)}%</Badge>}
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
                          <span className="text-foreground-500">指标: {step.indicator}</span>
                          <span className="font-medium text-accent-600">{step.value}</span>
                          {step.compatibility !== undefined && <span className="text-foreground-500">相容 {(step.compatibility * 100).toFixed(0)}%</span>}
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
            <p className="mb-1 font-medium text-foreground-700">说明</p>
            <p>机制相容性来自版本化领域知识和文献目录，不是模型内部推理，也不证明灾害会发生。模型证据请查看特征贡献。</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function HistoryTab({ events }: { events: HistoricalEvent[] }) {
  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-heading text-base text-foreground-900 mb-1">相似历史事件</h3>
        <p className="text-xs text-foreground-500 mb-5">只检索起报时刻之前的案例，并分别比较天气形态、空间背景与季节窗口；低覆盖或代理案例会被降权。</p>

        <div className="space-y-3">
          {events.map((evt) => (
            <div key={evt.eventId} className="bg-background-100 border border-background-200/70 rounded-lg p-4">
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-medium text-foreground-900 text-sm">{evt.date}</span>
                    <Badge variant="secondary">{evt.region}</Badge>
                    <Badge variant="accent">{evt.hazard}</Badge>
                    <Badge variant="primary">相似度 {(evt.similarity * 100).toFixed(0)}%</Badge>
                    {evt.verificationStatus && <Badge variant="secondary">{evt.verificationStatus}</Badge>}
                  </div>
                  <p className="text-sm text-foreground-700 mb-2">{evt.description}</p>
                  <div className="flex flex-wrap gap-3 text-xs text-foreground-500">
                    {evt.maxRainfall != null && <span>最大降水: {evt.maxRainfall}mm</span>}
                    {evt.maxTemp != null && <span>最高温度: {evt.maxTemp}°C</span>}
                    <span className="text-orange-600">影响: {evt.impact}</span>
                    {evt.dataCoverage !== undefined && <span>气象指标覆盖: {(evt.dataCoverage * 100).toFixed(0)}%</span>}
                  </div>
                  {evt.similarityDimensions && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3">
                      {evt.similarityDimensions.map((dimension) => (
                        <div key={dimension.key} className="bg-background-50 rounded p-2 text-xs">
                          <div className="flex justify-between"><span className="text-foreground-600">{dimension.label}</span><span className="font-medium">{(dimension.score * 100).toFixed(0)}%</span></div>
                          <p className="text-foreground-400 mt-1">权重 {(dimension.weight * 100).toFixed(0)}% · {dimension.explanation}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {evt.sourceTitle && <p className="text-[11px] text-foreground-400 mt-3">来源: {evt.sourceTitle}</p>}
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
