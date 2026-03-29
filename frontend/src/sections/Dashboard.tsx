/**
 * Dashboard - System Overview
 */
import { useEffect, useState } from 'react';
import { 
  Car, 
  Key, 
  ClipboardList, 
  CheckCircle, 
  XCircle, 
  Activity,
  ArrowRight,
  Shield,
  Camera
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface DashboardStats {
  total_users: number;
  total_vehicles: number;
  total_tokens_issued: number;
  total_access_logs: number;
  today_attempts: number;
  today_granted: number;
  today_denied: number;
}

interface RecentAccess {
  id: string;
  plate_number: string;
  access_decision: string;
  timestamp: string;
  token_valid: boolean;
  plate_match: boolean;
}

interface DashboardProps {
  onNavigate: (page: 'dashboard' | 'vehicles' | 'tokens' | 'anpr' | 'logs' | 'stats') => void;
}

const API_BASE_URL = 'http://localhost:8000';

export default function Dashboard({ onNavigate }: DashboardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentAccess, setRecentAccess] = useState<RecentAccess[]>([]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const statsRes = await fetch(`${API_BASE_URL}/logs/statistics`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData.statistics);
      }

      const logsRes = await fetch(`${API_BASE_URL}/logs/access?limit=5`);
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setRecentAccess(logsData.logs || []);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast.error('Failed to fetch dashboard data');
    }
  };

  const statCards = [
    {
      title: 'Total Vehicles',
      value: stats?.total_vehicles || 0,
      icon: Car,
      color: 'bg-blue-500',
      description: 'Registered vehicles'
    },
    {
      title: 'Active Tokens',
      value: stats?.total_tokens_issued || 0,
      icon: Key,
      color: 'bg-green-500',
      description: 'Issued tokens'
    },
    {
      title: 'Today\'s Access',
      value: stats?.today_attempts || 0,
      icon: ClipboardList,
      color: 'bg-purple-500',
      description: `${stats?.today_granted || 0} granted, ${stats?.today_denied || 0} denied`
    },
    {
      title: 'Success Rate',
      value: stats?.today_attempts 
        ? Math.round((stats.today_granted / stats.today_attempts) * 100) 
        : 0,
      icon: Activity,
      color: 'bg-orange-500',
      description: 'Access granted %',
      suffix: '%'
    }
  ];

  const quickActions = [
    {
      title: 'Register Vehicle',
      description: 'Add a new vehicle to the system',
      icon: Car,
      action: () => onNavigate('vehicles'),
      color: 'bg-blue-100 text-blue-700'
    },
    {
      title: 'Issue Token',
      description: 'Generate access token for vehicle',
      icon: Key,
      action: () => onNavigate('tokens'),
      color: 'bg-green-100 text-green-700'
    },
    {
      title: 'ANPR Monitor',
      description: 'Live license plate recognition',
      icon: Camera,
      action: () => onNavigate('anpr'),
      color: 'bg-purple-100 text-purple-700'
    },
    {
      title: 'View Logs',
      description: 'Check access history and audit trail',
      icon: ClipboardList,
      action: () => onNavigate('logs'),
      color: 'bg-orange-100 text-orange-700'
    }
  ];

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-xl p-8 text-white">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">
              Welcome to CVT-VACS
            </h1>
            <p className="text-slate-300 max-w-2xl">
              Computer Vision and Token-Based Authentication System for Vehicle Access Control. 
              This system implements Two-Factor Authentication (2FA) combining ANPR and token verification.
            </p>
            <div className="flex items-center gap-4 mt-6">
              <span className="px-3 py-1 bg-green-500/20 text-green-300 text-sm rounded-full flex items-center gap-1">
                <Shield className="w-3 h-3" />
                2FA Active
              </span>
              <span className="px-3 py-1 bg-blue-500/20 text-blue-300 text-sm rounded-full flex items-center gap-1">
                <Camera className="w-3 h-3" />
                ANPR Ready
              </span>
            </div>
          </div>
          <div className="hidden md:block">
            <div className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center">
              <Shield className="w-12 h-12 text-blue-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{stat.title}</p>
                    <p className="text-3xl font-bold mt-1">
                      {stat.value}{stat.suffix || ''}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">{stat.description}</p>
                  </div>
                  <div className={`${stat.color} p-3 rounded-lg`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks and operations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {quickActions.map((action, index) => {
                const Icon = action.icon;
                return (
                  <button
                    key={index}
                    onClick={action.action}
                    className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 
                      hover:border-blue-300 hover:bg-blue-50 transition-all text-left"
                  >
                    <div className={`${action.color} p-2 rounded-lg`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{action.title}</p>
                      <p className="text-sm text-gray-500">{action.description}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Recent Access Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Access Activity</CardTitle>
              <CardDescription>Latest access attempts</CardDescription>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => onNavigate('logs')}
            >
              View All
            </Button>
          </CardHeader>
          <CardContent>
            {recentAccess.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <ClipboardList className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No access logs yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentAccess.map((log) => (
                  <div 
                    key={log.id} 
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      {log.access_decision === 'GRANTED' ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                      <div>
                        <p className="font-medium text-sm">{log.plate_number}</p>
                        <p className="text-xs text-gray-500">{formatTime(log.timestamp)}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full
                      ${log.access_decision === 'GRANTED' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                      }`}>
                      {log.access_decision}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* System Info */}
      <Card className="bg-slate-50 border-slate-200">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-900">System Information</h3>
              <p className="text-sm text-slate-600 mt-1">
                CVT-VACS v1.0.0 | Two-Factor Authentication System
              </p>
            </div>
            <div className="text-right text-sm text-slate-500">
              <p>Backend: <span className="text-green-600 font-medium">Connected</span></p>
              <p>Database: <span className="text-green-600 font-medium">MongoDB</span></p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
