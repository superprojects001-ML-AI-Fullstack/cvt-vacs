/**
 * System Statistics and Performance Metrics Page
 */
import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Activity, Clock, Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

// Constants
const API_BASE_URL = import.meta.env.VITE_API_URL;
const REFRESH_INTERVAL_MS = 30000; // 30 seconds
const ANPR_SCORE_THRESHOLD = 90;
const GOOD_SCORE_THRESHOLD = 70;

interface PerformanceMetrics {
  anpr_accuracy: number;
  anpr_precision: number;
  anpr_recall: number;
  anpr_f1_score: number;
  token_verification_latency_ms: number;
  system_response_time_ms: number;
  authentication_success_rate: number;
  throughput_vehicles_per_minute: number;
  false_positive_rate: number;
  false_negative_rate: number;
  sample_size: number;
}

interface SystemStatistics {
  total_users: number;
  total_vehicles: number;
  total_tokens_issued: number;
  total_access_logs: number;
  today_attempts: number;
  today_granted: number;
  today_denied: number;
}

export default function SystemStats() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [stats, setStats] = useState<SystemStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    // Check API URL first
    if (!API_BASE_URL) {
      console.error('❌ VITE_API_URL is not set!');
      setError('API URL is not configured. Check environment variables.');
      setLoading(false);
      return;
    }

    setError(null);
    const perfUrl = `${API_BASE_URL}/logs/performance`;
    const statsUrl = `${API_BASE_URL}/logs/statistics`;
    
    console.log('🔍 Fetching performance from:', perfUrl);
    console.log('🔍 Fetching statistics from:', statsUrl);

    try {
      const [metricsRes, statsRes] = await Promise.all([
        fetch(perfUrl),
        fetch(statsUrl)
      ]);

      console.log('📡 Performance status:', metricsRes.status);
      console.log('📡 Statistics status:', statsRes.status);

      if (metricsRes.ok) {
        const metricsData = await metricsRes.json();
        console.log('✅ Performance data:', metricsData);
        setMetrics(metricsData.metrics || null);
      } else {
        const errorText = await metricsRes.text();
        console.error('❌ Performance error:', errorText);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        console.log('✅ Statistics data:', statsData);
        setStats(statsData.statistics || null);
      } else {
        const errorText = await statsRes.text();
        console.error('❌ Statistics error:', errorText);
      }

      // Show error if both failed
      if (!metricsRes.ok && !statsRes.ok) {
        setError(`Failed to fetch data: ${metricsRes.status}, ${statsRes.status}`);
      }

    } catch (error) {
      console.error('❌ Network error:', error);
      setError('Network error - check console for details');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (value: number) => {
    if (value >= ANPR_SCORE_THRESHOLD) return 'text-green-600';
    if (value >= GOOD_SCORE_THRESHOLD) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Safe fallback values
  const safeMetrics = metrics || {
    anpr_accuracy: 0,
    anpr_precision: 0,
    anpr_recall: 0,
    anpr_f1_score: 0,
    token_verification_latency_ms: 0,
    system_response_time_ms: 0,
    authentication_success_rate: 0,
    throughput_vehicles_per_minute: 0,
    false_positive_rate: 0,
    false_negative_rate: 0,
    sample_size: 0
  };

  const safeStats = stats || {
    total_users: 0,
    total_vehicles: 0,
    total_tokens_issued: 0,
    total_access_logs: 0,
    today_attempts: 0,
    today_granted: 0,
    today_denied: 0
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Failed to Load Statistics</h3>
        <p className="text-gray-500 max-w-md">{error}</p>
        <button 
          onClick={fetchData}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">System Statistics</h2>
          <p className="text-gray-500">Performance metrics and operational analytics</p>
        </div>
        <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full flex items-center gap-1">
          <Activity className="w-3 h-3" />
          Live Metrics
        </span>
      </div>

      {/* Key Performance Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">ANPR Accuracy</p>
                <p className={`text-3xl font-bold ${getScoreColor(safeMetrics.anpr_accuracy)}`}>
                  {safeMetrics.anpr_accuracy.toFixed(1)}%
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <Progress value={safeMetrics.anpr_accuracy} className="mt-4" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Auth Success Rate</p>
                <p className={`text-3xl font-bold ${getScoreColor(safeMetrics.authentication_success_rate)}`}>
                  {safeMetrics.authentication_success_rate.toFixed(1)}%
                </p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <Progress value={safeMetrics.authentication_success_rate} className="mt-4" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Response Time</p>
                <p className="text-3xl font-bold text-purple-600">
                  {safeMetrics.system_response_time_ms.toFixed(0)}ms
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-4">Target: &lt; 500ms</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Throughput</p>
                <p className="text-3xl font-bold text-orange-600">
                  {safeMetrics.throughput_vehicles_per_minute.toFixed(1)}
                </p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-4">Vehicles per minute</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ANPR Performance Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>ANPR Performance</CardTitle>
            <CardDescription>Computer vision recognition metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {[
              { label: 'Accuracy', value: safeMetrics.anpr_accuracy, description: 'Overall recognition accuracy' },
              { label: 'Precision', value: safeMetrics.anpr_precision, description: 'True positives / All positives' },
              { label: 'Recall', value: safeMetrics.anpr_recall, description: 'True positives / Actual positives' },
              { label: 'F1 Score', value: safeMetrics.anpr_f1_score, description: 'Harmonic mean of precision & recall' }
            ].map((metric) => (
              <div key={metric.label}>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-medium text-gray-900">{metric.label}</p>
                    <p className="text-xs text-gray-500">{metric.description}</p>
                  </div>
                  <span className={`font-bold ${getScoreColor(metric.value)}`}>
                    {metric.value.toFixed(1)}%
                  </span>
                </div>
                <Progress value={metric.value} className="h-2" />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Security Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>Security Metrics</CardTitle>
            <CardDescription>Authentication and access control statistics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-red-50 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-5 h-5 text-red-600" />
                  <span className="font-medium text-red-800">False Positive Rate</span>
                </div>
                <p className="text-2xl font-bold text-red-600">
                  {safeMetrics.false_positive_rate.toFixed(2)}%
                </p>
                <p className="text-xs text-red-600 mt-1">Unauthorized access granted</p>
              </div>

              <div className="bg-orange-50 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-5 h-5 text-orange-600" />
                  <span className="font-medium text-orange-800">False Negative Rate</span>
                </div>
                <p className="text-2xl font-bold text-orange-600">
                  {safeMetrics.false_negative_rate.toFixed(2)}%
                </p>
                <p className="text-xs text-orange-600 mt-1">Authorized access denied</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-700">Token Verification Latency</span>
                  <span className="font-medium">{safeMetrics.token_verification_latency_ms.toFixed(1)}ms</span>
                </div>
                <Progress 
                  value={Math.min(safeMetrics.token_verification_latency_ms / 10, 100)} 
                  className="h-2" 
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-700">System Response Time</span>
                  <span className="font-medium">{safeMetrics.system_response_time_ms.toFixed(1)}ms</span>
                </div>
                <Progress 
                  value={Math.min(safeMetrics.system_response_time_ms / 5, 100)} 
                  className="h-2" 
                />
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Sample Size:</strong> {safeMetrics.sample_size} access attempts analyzed
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Overview */}
      <Card>
        <CardHeader>
          <CardTitle>System Overview</CardTitle>
          <CardDescription>Current system state and resource utilization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-3xl font-bold text-gray-900">{safeStats.total_users}</p>
              <p className="text-sm text-gray-500">Registered Users</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-3xl font-bold text-gray-900">{safeStats.total_vehicles}</p>
              <p className="text-sm text-gray-500">Registered Vehicles</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-3xl font-bold text-gray-900">{safeStats.total_tokens_issued}</p>
              <p className="text-sm text-gray-500">Tokens Issued</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-3xl font-bold text-gray-900">{safeStats.total_access_logs}</p>
              <p className="text-sm text-gray-500">Total Access Logs</p>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Today&apos;s Activity</p>
                <p className="text-sm text-gray-500">
                  {safeStats.today_attempts} access attempts
                </p>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-2xl font-bold text-green-600">{safeStats.today_granted}</p>
                  <p className="text-sm text-gray-500">Granted</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-red-600">{safeStats.today_denied}</p>
                  <p className="text-sm text-gray-500">Denied</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2FA Verification Model */}
      <Card className="bg-slate-900 text-white">
        <CardHeader>
          <CardTitle className="text-white">Two-Factor Authentication Model</CardTitle>
          <CardDescription className="text-slate-400">
            Mathematical foundation of the CVT-VACS decision engine
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-800 p-4 rounded-lg">
              <p className="text-sm text-slate-400 mb-2">ANPR Validity (A)</p>
              <p className="text-lg font-mono text-blue-400">
                A = 1 if confidence &ge; T<br />
                A = 0 otherwise
              </p>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg">
              <p className="text-sm text-slate-400 mb-2">Token Validity (T)</p>
              <p className="text-lg font-mono text-green-400">
                T = 1 if valid &amp; not expired<br />
                T = 0 otherwise
              </p>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg">
              <p className="text-sm text-slate-400 mb-2">Plate Match (M)</p>
              <p className="text-lg font-mono text-purple-400">
                M = 1 if P<sub>d</sub> = P<sub>r</sub><br />
                M = 0 otherwise
              </p>
            </div>
          </div>

          <div className="mt-6 bg-slate-800 p-4 rounded-lg text-center">
            <p className="text-sm text-slate-400 mb-2">Final Access Decision</p>
            <p className="text-2xl font-mono text-white">
              Access = A &middot; T &middot; M
            </p>
            <p className="text-sm text-slate-400 mt-2">
              Access is granted only when all three conditions are satisfied (2FA)
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}