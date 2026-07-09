import { Link } from 'react-router-dom';
import { Activity } from 'lucide-react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  linkTo?: string;
  className?: string;
}

export default function Logo({ size = 'md', linkTo, className = '' }: LogoProps) {
  const sizeClasses = {
    sm: {
      text: 'text-lg',
      container: 'w-10 h-10 rounded-lg',
      icon: 'w-5 h-5',
      gap: 'gap-2',
    },
    md: {
      text: 'text-xl',
      container: 'w-12 h-12 rounded-xl',
      icon: 'w-7 h-7',
      gap: 'gap-2',
    },
    lg: {
      text: 'text-2xl',
      container: 'w-12 h-12 rounded-xl',
      icon: 'w-7 h-7',
      gap: 'gap-3',
    },
  };

  const currentSize = sizeClasses[size];

  const content = (
    <div className={`flex items-center ${currentSize.gap} ${className}`}>
      <div className={`${currentSize.container} bg-white flex items-center justify-center`}>
        <Activity className={`${currentSize.icon} text-black`} />
      </div>
      <span className={`${currentSize.text} font-semibold text-gradient`}>HealthAI</span>
    </div>
  );

  if (linkTo) {
    return (
      <Link to={linkTo} className="group flex items-center">
        {content}
      </Link>
    );
  }

  return content;
}
