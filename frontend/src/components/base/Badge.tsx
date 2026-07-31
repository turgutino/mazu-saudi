interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'accent' | 'secondary' | 'warning' | 'danger' | 'success';
  size?: 'sm' | 'md';
  className?: string;
}

const variantStyles: Record<string, string> = {
  primary: 'bg-primary-100 text-primary-800 border-primary-200',
  accent: 'bg-accent-100 text-accent-800 border-accent-200',
  secondary: 'bg-secondary-100 text-secondary-800 border-secondary-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger: 'bg-red-50 text-red-700 border-red-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
};

const sizeStyles: Record<string, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
};

export default function Badge({ children, variant = 'primary', size = 'sm', className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full border whitespace-nowrap font-medium ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}>
      {children}
    </span>
  );
}