/**
 * CVT-VACS Frontend Application
 * Computer Vision and Token-Based Vehicle Access Control System
 *
 * Developed by: Daria Benjamin Francis (AUPG/24/0033)
 * Adeleke University, Ede, Osun State, Nigeria
 */
import { useState } from 'react';
import {
  Shield,
  Car,
  Key,
  Camera,
  ClipboardList,
  BarChart3,
  Menu,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Toaster } from 'sonner';

// ── Page imports ──────────────────────────────────────────────────────────────
import Dashboard          from '@/sections/Dashboard';
import VehicleRegistration from '@/sections/VehicleRegistration';
import TokenManagement    from '@/sections/TokenManagement';
import ANPRMonitor        from '@/sections/ANPRMonitor';
import AccessLogs         from '@/sections/AccessLogs';
import SystemStats        from '@/sections/SystemStats';
import CameraEntry        from '@/sections/CameraEntry';   // ← NEW

import './App.css';

type PageType = 'dashboard' | 'vehicles' | 'tokens' | 'anpr' | 'logs' | 'stats' | 'camera';

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // ── Navigation items ────────────────────────────────────────────────────────
  const navigation: {
    id: PageType;
    label: string;
    icon: React.ElementType;
    description: string;
  }[] = [
    { id: 'dashboard', label: 'Dashboard',     icon: Shield,      description: 'System overview' },
    { id: 'camera',    label: 'Camera Entry',  icon: Camera,      description: 'Auto detect & allocate' },  // ← NEW (placed 2nd for prominence)
    { id: 'vehicles',  label: 'Vehicles',      icon: Car,         description: 'Register & manage vehicles' },
    { id: 'tokens',    label: 'Tokens',        icon: Key,         description: 'Issue & verify tokens' },
    { id: 'anpr',      label: 'ANPR Monitor',  icon: Camera,      description: 'Standalone recognition' },
    { id: 'logs',      label: 'Access Logs',   icon: ClipboardList, description: 'Audit trail' },
    { id: 'stats',     label: 'Statistics',    icon: BarChart3,   description: 'Performance metrics' },
  ];

  // ── Page renderer ────────────────────────────────────────────────────────────
  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard onNavigate={(page: PageType) => setCurrentPage(page)} />;
      case 'camera':
        return <CameraEntry />;
      case 'vehicles':
        return <VehicleRegistration />;
      case 'tokens':
        return <TokenManagement />;
      case 'anpr':
        return <ANPRMonitor />;
      case 'logs':
        return <AccessLogs />;
      case 'stats':
        return <SystemStats />;
      default:
        return <Dashboard onNavigate={(page: PageType) => setCurrentPage(page)} />;
    }
  };

  const currentNav = navigation.find(n => n.id === currentPage);

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 flex">
      <Toaster position="top-right" richColors />

      {/* ── Sidebar ──────────────────────────────────────────────────────────── */}
      <aside
        className={`${sidebarOpen ? 'w-72' : 'w-20'}
          bg-slate-900 text-white transition-all duration-300
          flex flex-col fixed h-full z-50`}
      >
        {/* Logo */}
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <Shield className="w-6 h-6 text-white" />
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="font-bold text-lg leading-tight">CVT-VACS</h1>
                <p className="text-xs text-slate-400">Access Control</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const Icon     = item.icon;
            const isActive = currentPage === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                  ${isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && (
                  <div className="text-left">
                    <p className="font-medium text-sm">{item.label}</p>
                    <p className="text-xs opacity-70">{item.description}</p>
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            {sidebarOpen && (
              <span className="text-xs text-slate-400">System Online</span>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full text-slate-400 hover:text-white hover:bg-slate-800"
          >
            {sidebarOpen
              ? <X    className="w-4 h-4" />
              : <Menu className="w-4 h-4" />}
          </Button>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────────────── */}
      <main
        className={`flex-1 transition-all duration-300 ${
          sidebarOpen ? 'ml-72' : 'ml-20'
        }`}
      >
        {/* Top header */}
        <header className="bg-white border-b border-gray-200 px-8 py-4 sticky top-0 z-40">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-800">
                {currentNav?.label}
              </h2>
              <p className="text-sm text-gray-500">
                {currentNav?.description}
              </p>
            </div>

            <div className="flex items-center gap-4">
              <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm font-medium rounded-full">
                2FA Enabled
              </span>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                Backend Connected
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="p-8">
          {renderPage()}
        </div>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 px-8 py-4 mt-auto">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <p>CVT-VACS 2025 | Developed by Daria Benjamin Francis (AUPG/24/0033)</p>
            <p>Adeleke University, Ede, Osun State, Nigeria</p>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
