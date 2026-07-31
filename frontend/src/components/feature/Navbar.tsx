import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/', label: '仪表盘', icon: 'ri-dashboard-line' },
  { path: '/monitor', label: '监测地图', icon: 'ri-map-2-line' },
  { path: '/workspace', label: '预测工作台', icon: 'ri-tools-line' },
];

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="sticky top-0 z-50 bg-background-50/95 backdrop-blur-sm border-b border-background-200/70">
      <div className="w-full px-6 md:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-8">
            <div
              onClick={() => navigate('/')}
              className="flex items-center gap-2.5 cursor-pointer"
            >
              <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
                <i className="ri-thunderstorms-line text-background-50 text-sm"></i>
              </div>
              <span className="font-heading text-lg text-foreground-900 whitespace-nowrap">
                极端天气预测
              </span>
            </div>

            <div className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium cursor-pointer transition-colors duration-150 whitespace-nowrap ${
                    isActive(item.path)
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-foreground-600 hover:bg-background-100 hover:text-foreground-900'
                  }`}
                >
                  <i className={`${item.icon} text-sm`}></i>
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 text-xs text-foreground-500 bg-background-100 px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-500"></span>
              系统运行中 · 4 个模型在线
            </div>

            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-md text-foreground-600 hover:bg-background-100 cursor-pointer"
            >
              <i className={`${mobileOpen ? 'ri-close-line' : 'ri-menu-line'} text-lg`}></i>
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden py-3 border-t border-background-200/70">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setMobileOpen(false);
                }}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm font-medium cursor-pointer transition-colors duration-150 ${
                  isActive(item.path)
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-foreground-600 hover:bg-background-100'
                }`}
              >
                <i className={`${item.icon} text-sm`}></i>
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}