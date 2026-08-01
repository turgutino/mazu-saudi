import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '@/components/feature/Navbar';
import StatCard from '@/components/base/StatCard';
import Badge from '@/components/base/Badge';
import RiskBadge from '@/components/base/RiskBadge';
import Button from '@/components/base/Button';
import type { DashboardStats, RecentActivity, WeeklyStat } from '@/mocks/dashboard';
import type { PredictionResult } from '@/mocks/predictions';
import {
  fetchPredictionsList,
  fetchDashboardStats,
  fetchRecentActivities,
  fetchWeeklyStats,
} from '@/services/predictionApi';

const EMPTY_STATS: DashboardStats = {
  totalPredictions: 0,
  activeWarnings: 0,
  modelsOnline: 0,
  regionsMonitored: 0,
  regionRisk: [],
  lastUpdated: null,
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState<PredictionResult[]>([]);
  const [predictionsLoading, setPredictionsLoading] = useState(true);
  const [predictionsError, setPredictionsError] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [weeklyStats, setWeeklyStats] = useState<WeeklyStat[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchPredictionsList()
      .then((data) => {
        if (!cancelled) {
          setPredictions(data);
          setPredictionsError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setPredictionsError(error instanceof Error ? error.message : '预测列表加载失败');
      })
      .finally(() => {
        if (!cancelled) setPredictionsLoading(false);
      });

    Promise.all([fetchDashboardStats(), fetchRecentActivities(), fetchWeeklyStats()])
      .then(([statsData, activitiesData, weeklyData]) => {
        if (cancelled) return;
        setStats(statsData);
        setActivities(activitiesData);
        setWeeklyStats(weeklyData);
      })
      .catch(() => {
        // Non-critical widgets: leave stats/activities/weeklyStats at their
        // empty defaults if this fails; the predictions table above still
        // shows its own error state independently.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const maxWeeklyPredictions = Math.max(1, ...weeklyStats.map((day) => day.predictions));

  return (
    <div className="min-h-screen bg-background-50">
      <Navbar />

      <main className="w-full px-6 md:px-8 py-6">
        <div className="max-w-[1280px] mx-auto">
          {/* Stats */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="累计预测次数"
              value={stats.totalPredictions.toLocaleString()}
              icon="ri-bar-chart-line"
              variant="primary"
            />
            <StatCard
              label="活跃预警"
              value={stats.activeWarnings}
              icon="ri-alert-line"
              variant="warning"
            />
            <StatCard
              label="在线模型"
              value={`${stats.modelsOnline} 个`}
              icon="ri-cpu-line"
              variant="accent"
            />
            <StatCard
              label="监测区域"
              value={`${stats.regionsMonitored} 个`}
              icon="ri-map-pin-line"
            />
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Weekly chart */}
            <section className="lg:col-span-2 bg-background-50 border border-background-200/70 rounded-lg p-5">
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-heading text-base text-foreground-900">本周预测趋势</h3>
                <Badge variant="secondary">近7天</Badge>
              </div>
              <div className="flex items-end gap-3 h-[180px]">
                {weeklyStats.length === 0 ? (
                  <div className="w-full h-full flex items-center justify-center text-sm text-foreground-400">
                    暂无近7天数据
                  </div>
                ) : (
                  weeklyStats.map((day) => (
                    <div key={day.day} className="flex-1 flex flex-col items-center gap-2">
                      <div className="w-full flex flex-col items-center gap-1">
                        <div className="relative w-full flex flex-col items-center">
                          <div
                            className="w-full max-w-[28px] bg-accent-500/80 rounded-t-md transition-all duration-500"
                            style={{ height: `${(day.warnings / maxWeeklyPredictions) * 140}px` }}
                          ></div>
                        </div>
                        <div className="relative w-full flex flex-col items-center">
                          <div
                            className="w-full max-w-[28px] bg-primary-300/60 rounded-t-md transition-all duration-500"
                            style={{ height: `${(day.predictions / maxWeeklyPredictions) * 140}px` }}
                          ></div>
                        </div>
                      </div>
                      <span className="text-xs text-foreground-500">{day.day}</span>
                    </div>
                  ))
                )}
              </div>
              <div className="flex items-center gap-4 mt-4 pt-3 border-t border-background-200/50">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm bg-primary-300/60"></span>
                  <span className="text-xs text-foreground-600">预测次数</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm bg-accent-500/80"></span>
                  <span className="text-xs text-foreground-600">预警数</span>
                </div>
              </div>
            </section>

            {/* Quick actions */}
            <section className="bg-background-50 border border-background-200/70 rounded-lg p-5">
              <h3 className="font-heading text-base text-foreground-900 mb-4">快速操作</h3>
              <div className="space-y-3">
                <Button
                  variant="primary"
                  size="md"
                  icon="ri-add-line"
                  className="w-full justify-start"
                  onClick={() => navigate('/workspace')}
                >
                  发起新预测
                </Button>
                <Button
                  variant="outline"
                  size="md"
                  icon="ri-history-line"
                  className="w-full justify-start"
                  onClick={() => {
                    const latest = predictions[0];
                    if (latest) navigate(`/prediction/${latest.predictionId}`);
                  }}
                >
                  查看最新预测
                </Button>
                <Button
                  variant="outline"
                  size="md"
                  icon="ri-map-2-line"
                  className="w-full justify-start"
                  onClick={() => navigate('/monitor')}
                >
                  监测地图
                </Button>
                <Button
                  variant="outline"
                  size="md"
                  icon="ri-file-chart-line"
                  className="w-full justify-start"
                >
                  生成周报
                </Button>
              </div>

              <div className="mt-5 pt-4 border-t border-background-200/50">
                <p className="text-xs text-foreground-500 mb-3">区域风险概况</p>
                <div className="space-y-2">
                  {stats.regionRisk.length === 0 ? (
                    <p className="text-sm text-foreground-400">暂无预测记录</p>
                  ) : (
                    stats.regionRisk.map((region) => (
                      <div key={region.regionId} className="flex items-center justify-between text-sm">
                        <span className="text-foreground-700">{region.regionName}</span>
                        <RiskBadge level={region.riskLevel} size="sm" />
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>
          </div>

          {/* Recent predictions */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading text-base text-foreground-900">近期预测</h3>
              <Badge variant="secondary">{predictions.length} 条记录</Badge>
            </div>
            {predictionsError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-sm text-red-700">
                <i className="ri-error-warning-line mr-2"></i>{predictionsError}
              </div>
            )}
            {predictionsLoading ? (
              <div className="bg-background-50 border border-background-200/70 rounded-lg p-10 text-center text-foreground-400">
                <i className="ri-loader-4-line animate-spin text-2xl block mb-2"></i>正在加载预测记录…
              </div>
            ) : predictions.length === 0 ? (
              <div className="bg-background-50 border border-background-200/70 rounded-lg p-10 text-center text-foreground-400">
                <i className="ri-inbox-line text-2xl block mb-2"></i>
                <p className="mb-3">暂无预测记录</p>
                <Button variant="primary" size="sm" icon="ri-add-line" onClick={() => navigate('/workspace')}>
                  去发起一个预测
                </Button>
              </div>
            ) : (
            <div className="bg-background-50 border border-background-200/70 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-background-200/70">
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">预测时间</th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">区域</th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">灾种</th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">模型</th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">概率</th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">风险等级</th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-foreground-500 uppercase tracking-wider">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((pred) => (
                      <tr
                        key={pred.predictionId}
                        className="border-b border-background-200/50 hover:bg-background-100/50 transition-colors cursor-pointer"
                        onClick={() => navigate(`/prediction/${pred.predictionId}`)}
                      >
                        <td className="px-5 py-3.5 text-sm text-foreground-700 whitespace-nowrap">
                          {pred.createdAt.replace('T', ' ').slice(0, 16)}
                        </td>
                        <td className="px-5 py-3.5 text-sm text-foreground-900 font-medium whitespace-nowrap">
                          {pred.regionName}
                        </td>
                        <td className="px-5 py-3.5 text-sm text-foreground-700 whitespace-nowrap">
                          {pred.hazardLabel}
                        </td>
                        <td className="px-5 py-3.5">
                          <Badge variant="secondary">{pred.modelName}</Badge>
                        </td>
                        <td className="px-5 py-3.5 text-sm text-foreground-900">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{(pred.calibratedProbability * 100).toFixed(0)}%</span>
                            <span className="text-xs text-foreground-400">±{(pred.uncertainty * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <RiskBadge level={pred.riskLevel} size="sm" />
                        </td>
                        <td className="px-5 py-3.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/prediction/${pred.predictionId}`);
                            }}
                            className="text-primary-600 hover:text-primary-700 text-sm cursor-pointer whitespace-nowrap"
                          >
                            查看详情
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            )}
          </section>

          {/* Recent activity */}
          <section className="mt-8">
            <h3 className="font-heading text-base text-foreground-900 mb-4">最近动态</h3>
            {activities.length === 0 ? (
              <div className="bg-background-50 border border-background-200/70 rounded-lg p-10 text-center text-foreground-400">
                <i className="ri-inbox-line text-2xl block mb-2"></i>暂无近期动态
              </div>
            ) : (
            <div className="bg-background-50 border border-background-200/70 rounded-lg p-1">
              {activities.map((activity, idx) => (
                <div
                  key={activity.id}
                  className={`flex items-start gap-4 px-4 py-3 ${
                    idx < activities.length - 1 ? 'border-b border-background-200/50' : ''
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                    activity.type === 'prediction' ? 'bg-primary-100 text-primary-600' :
                    activity.type === 'warning' ? 'bg-orange-100 text-orange-600' :
                    'bg-accent-100 text-accent-600'
                  }`}>
                    <i className={`${
                      activity.type === 'prediction' ? 'ri-radar-line' :
                      activity.type === 'warning' ? 'ri-alert-line' :
                      'ri-file-text-line'
                    } text-sm`}></i>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-foreground-900">{activity.title}</span>
                      {activity.riskLevel && <RiskBadge level={activity.riskLevel} size="sm" />}
                    </div>
                    <p className="text-xs text-foreground-500 mt-0.5">{activity.description}</p>
                  </div>
                  <span className="text-xs text-foreground-400 whitespace-nowrap">{activity.time.slice(11)}</span>
                </div>
              ))}
            </div>
            )}
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-background-200/70 bg-background-100">
        <div className="max-w-[1280px] mx-auto px-6 md:px-8 py-5">
          <div className="flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-foreground-500">
              <i className="ri-shield-check-line text-accent-600"></i>
              <span>预测结果仅供参考，实际预警以官方发布为准</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
