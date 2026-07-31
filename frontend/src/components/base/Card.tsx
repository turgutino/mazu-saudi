import { type ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export default function Card({ children, className = '', hover = false, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-background-50 border border-background-200/70 rounded-lg p-5 ${
        hover ? 'cursor-pointer transition-all duration-200 hover:border-background-300/80 hover:bg-background-100' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}