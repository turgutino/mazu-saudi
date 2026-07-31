import { type ReactNode } from 'react';

interface ButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'accent' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit';
}

const variantStyles: Record<string, string> = {
  primary: 'bg-primary-500 text-background-50 hover:bg-primary-600 active:bg-primary-700',
  accent: 'bg-accent-500 text-background-50 hover:bg-accent-600 active:bg-accent-700',
  secondary: 'bg-secondary-500 text-background-50 hover:bg-secondary-600 active:bg-secondary-700',
  outline: 'border border-background-300 text-foreground-700 hover:bg-background-100 active:bg-background-200',
  ghost: 'text-foreground-600 hover:bg-background-100 active:bg-background-200',
};

const sizeStyles: Record<string, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5 rounded-md',
  md: 'px-4 py-2 text-sm gap-2 rounded-md',
  lg: 'px-6 py-2.5 text-base gap-2.5 rounded-lg',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  className = '',
  disabled = false,
  onClick,
  type = 'button',
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center whitespace-nowrap font-medium cursor-pointer transition-all duration-150 ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {icon && <i className={`${icon} ${size === 'sm' ? 'text-xs' : 'text-sm'}`}></i>}
      {children}
    </button>
  );
}