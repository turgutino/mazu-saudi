interface StatCardProps {
  label: string;
  value: string | number;
  icon: string;
  trend?: { value: string; positive: boolean };
  variant?: 'default' | 'primary' | 'accent' | 'warning';
}

const variantStyles: Record<string, string> = {
  default: 'bg-background-50 border-background-200/70',
  primary: 'bg-primary-50 border-primary-200',
  accent: 'bg-accent-50 border-accent-200',
  warning: 'bg-orange-50 border-orange-200',
};

const iconStyles: Record<string, string> = {
  default: 'text-foreground-500',
  primary: 'text-primary-600',
  accent: 'text-accent-600',
  warning: 'text-orange-600',
};

export default function StatCard({ label, value, icon, trend, variant = 'default' }: StatCardProps) {
  return (
    <div className={`rounded-lg border p-5 ${variantStyles[variant]}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-foreground-500 font-medium">{label}</p>
          <p className="text-2xl font-heading text-foreground-900 mt-1">{value}</p>
          {trend && (
            <p className={`text-xs mt-2 flex items-center gap-1 ${trend.positive ? 'text-accent-600' : 'text-red-500'}`}>
              <i className={`${trend.positive ? 'ri-arrow-up-line' : 'ri-arrow-down-line'} text-xs`}></i>
              {trend.value}
            </p>
          )}
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconStyles[variant]} bg-background-50`}>
          <i className={`${icon} text-lg`}></i>
        </div>
      </div>
    </div>
  );
}