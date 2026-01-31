import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useWorldStore } from '../../stores/worldStore';

export default function StatsPanel() {
  const { t } = useTranslation();
  const { stats, fetchStats } = useWorldStore();

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const items = stats
    ? [
        { label: t('total_ticks'), value: stats.total_ticks.toLocaleString(), color: '#4fc3f7' },
        { label: t('total_born'), value: stats.total_ais_born, color: '#81c784' },
        { label: t('total_alive'), value: stats.total_ais_alive, color: '#81c784' },
        { label: t('concepts'), value: stats.total_concepts, color: '#ce93d8' },
        { label: t('total_interactions'), value: stats.total_interactions, color: '#f48fb1' },
        { label: t('events'), value: stats.total_events, color: '#ff8a65' },
      ]
    : [];

  return (
    <div className="space-y-3 fade-in">
      <h3 className="text-sm font-medium text-glow-cyan">{t('world_stats')}</h3>

      <div className="grid grid-cols-2 gap-2">
        {items.map(({ label, value, color }) => (
          <div key={label} className="p-3 rounded-lg bg-void-lighter text-center">
            <div className="text-xl font-mono font-bold" style={{ color }}>
              {value}
            </div>
            <div className="text-[10px] text-text-dim mt-1">{label}</div>
          </div>
        ))}
      </div>

      {!stats && (
        <div className="text-center py-8">
          <div className="text-text-dim text-xs">Loading...</div>
        </div>
      )}
    </div>
  );
}
