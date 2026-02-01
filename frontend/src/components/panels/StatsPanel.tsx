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
        { label: t('total_ticks'), value: stats.total_ticks.toLocaleString(), color: 'text-cyan' },
        { label: t('total_born'), value: stats.total_ais_born, color: 'text-green' },
        { label: t('total_alive'), value: stats.total_ais_alive, color: 'text-green' },
        { label: t('concepts'), value: stats.total_concepts, color: 'text-accent' },
        { label: t('total_interactions'), value: stats.total_interactions, color: 'text-rose' },
        { label: t('events'), value: stats.total_events, color: 'text-orange' },
      ]
    : [];

  return (
    <div className="space-y-3 fade-in">
      <h3 className="text-xs font-medium text-text">{t('world_stats')}</h3>

      {stats ? (
        <div className="grid grid-cols-2 gap-2">
          {items.map(({ label, value, color }) => (
            <div
              key={label}
              className="p-3 rounded-lg bg-surface-2 border border-border"
            >
              <div className={`text-lg mono font-medium ${color}`}>{value}</div>
              <div className="text-[10px] text-text-3 mt-1 tracking-wide">{label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-text-3 text-[11px]">Loading...</div>
        </div>
      )}
    </div>
  );
}
