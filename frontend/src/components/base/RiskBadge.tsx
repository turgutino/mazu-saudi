import { useTranslation } from 'react-i18next';

interface RiskBadgeProps {
  level: 'green' | 'yellow' | 'orange' | 'red';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const levelConfig: Record<string, { labelKey: string; bg: string; text: string; border: string; dot: string }> = {
  green: { labelKey: 'risk.green', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
  yellow: { labelKey: 'risk.yellow', bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', dot: 'bg-yellow-500' },
  orange: { labelKey: 'risk.orange', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
  red: { labelKey: 'risk.red', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500' },
};

const sizeStyles: Record<string, string> = {
  sm: 'px-2 py-0.5 text-xs gap-1',
  md: 'px-3 py-1 text-sm gap-1.5',
  lg: 'px-4 py-1.5 text-base gap-2',
};

export default function RiskBadge({ level, size = 'md', showLabel = true }: RiskBadgeProps) {
  const { t } = useTranslation();
  const config = levelConfig[level];
  return (
    <span className={`inline-flex items-center rounded-full border whitespace-nowrap font-medium ${config.bg} ${config.text} ${config.border} ${sizeStyles[size]}`}>
      <span className={`w-2 h-2 rounded-full ${config.dot}`}></span>
      {showLabel && t(config.labelKey)}
    </span>
  );
}