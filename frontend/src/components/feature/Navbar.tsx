import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, i18n } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { path: '/', label: t('nav.dashboard'), icon: 'ri-dashboard-line' },
    { path: '/monitor', label: t('nav.monitor'), icon: 'ri-map-2-line' },
    { path: '/workspace', label: t('nav.workspace'), icon: 'ri-tools-line' },
  ];

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const currentLang = i18n.language?.startsWith('zh') ? 'zh' : 'en';
  const toggleLanguage = (lang: 'zh' | 'en') => {
    i18n.changeLanguage(lang);
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
                {t('nav.title')}
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
              {t('nav.systemRunning')}
            </div>

            <div className="flex items-center gap-0.5 bg-background-100 rounded-full p-0.5 text-xs font-medium">
              <button
                onClick={() => toggleLanguage('zh')}
                className={`px-2.5 py-1 rounded-full cursor-pointer transition-colors duration-150 ${
                  currentLang === 'zh'
                    ? 'bg-primary-500 text-background-50'
                    : 'text-foreground-600 hover:text-foreground-900'
                }`}
              >
                {t('lang.zh')}
              </button>
              <button
                onClick={() => toggleLanguage('en')}
                className={`px-2.5 py-1 rounded-full cursor-pointer transition-colors duration-150 ${
                  currentLang === 'en'
                    ? 'bg-primary-500 text-background-50'
                    : 'text-foreground-600 hover:text-foreground-900'
                }`}
              >
                {t('lang.en')}
              </button>
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
