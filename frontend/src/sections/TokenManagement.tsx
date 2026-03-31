/**
 * Token Management Page
 */
import { useState } from 'react';
import { Key, Plus, Copy, CheckCircle, Clock, XCircle, QrCode, Loader2, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const tokenTypes = [
  { value: 'jwt', label: 'JWT Token' },
  { value: 'qr', label: 'QR Code' },
  { value: 'otp', label: 'One-Time Password (OTP)' }
];

export default function TokenManagement() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isVerifyDialogOpen, setIsVerifyDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  
  const [issueForm, setIssueForm] = useState({
    user_id: 'user_001',
    plate_number: '',
    token_type: 'jwt',
    expiry_hours: '24'
  });

  const [verifyForm, setVerifyForm] = useState({
    token: '',
    plate_number: ''
  });
  const [verifyResult, setVerifyResult] = useState<any>(null);

  const handleIssueToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/tokens/issue?user_id=${issueForm.user_id}&plate_number=${issueForm.plate_number}&token_type=${issueForm.token_type}&expiry_hours=${issueForm.expiry_hours}`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        setGeneratedToken(data.token);
        toast.success('Token issued successfully!');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to issue token');
      }
    } catch (error) {
      toast.error('Network error - please try again');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/tokens/verify-with-plate?token=${encodeURIComponent(verifyForm.token)}&detected_plate=${verifyForm.plate_number}`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        setVerifyResult(data);
        toast.success(data.access_granted ? 'Access granted!' : 'Access denied');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Verification failed');
      }
    } catch (error) {
      toast.error('Network error - please try again');
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Token copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const formatExpiry = (expiryTime: string) => {
    return new Date(expiryTime).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Token Management</h2>
          <p className="text-gray-500">Issue and verify access tokens for vehicles</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => setIsVerifyDialogOpen(true)}>
            <Shield className="w-4 h-4 mr-2" />
            Verify Token
          </Button>
          <Button onClick={() => {
            setGeneratedToken(null);
            setIsDialogOpen(true);
          }}>
            <Plus className="w-4 h-4 mr-2" />
            Issue Token
          </Button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Key className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">JWT Tokens</p>
                <p className="text-lg font-semibold">Secure & Signed</p>
                <p className="text-xs text-gray-400">Cryptographically secure</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <QrCode className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">QR Codes</p>
                <p className="text-lg font-semibold">Scan to Verify</p>
                <p className="text-xs text-gray-400">Mobile-friendly</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Time-Based</p>
                <p className="text-lg font-semibold">Auto-Expiry</p>
                <p className="text-xs text-gray-400">Configurable duration</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* How It Works */}
      <Card>
        <CardHeader>
          <CardTitle>How Token-Based Authentication Works</CardTitle>
          <CardDescription>Understanding the token verification process</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { step: 1, title: 'Token Issued', desc: 'User receives unique token' },
              { step: 2, title: 'Vehicle Arrives', desc: 'ANPR captures plate' },
              { step: 3, title: 'Token Presented', desc: 'Driver provides token' },
              { step: 4, title: '2FA Verification', desc: 'Both factors verified' }
            ].map((item) => (
              <div key={item.step} className="flex flex-col items-center text-center p-4 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold mb-2">
                  {item.step}
                </div>
                <p className="font-medium text-gray-900">{item.title}</p>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Issue Token Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Issue Access Token</DialogTitle>
            <DialogDescription>
              Generate a new authentication token for vehicle access
            </DialogDescription>
          </DialogHeader>

          {!generatedToken ? (
            <form onSubmit={handleIssueToken} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="plate_number">Vehicle Plate Number *</Label>
                <Input
                  id="plate_number"
                  placeholder="e.g., ABC-123-XY"
                  value={issueForm.plate_number}
                  onChange={(e) => setIssueForm({ ...issueForm, plate_number: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="user_id">Owner User ID *</Label>
                <Input
                  id="user_id"
                  value={issueForm.user_id}
                  onChange={(e) => setIssueForm({ ...issueForm, user_id: e.target.value })}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="token_type">Token Type</Label>
                  <Select
                    value={issueForm.token_type}
                    onValueChange={(value) => setIssueForm({ ...issueForm, token_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {tokenTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="expiry_hours">Expiry (Hours)</Label>
                  <Select
                    value={issueForm.expiry_hours}
                    onValueChange={(value) => setIssueForm({ ...issueForm, expiry_hours: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 hour</SelectItem>
                      <SelectItem value="6">6 hours</SelectItem>
                      <SelectItem value="12">12 hours</SelectItem>
                      <SelectItem value="24">24 hours</SelectItem>
                      <SelectItem value="48">48 hours</SelectItem>
                      <SelectItem value="168">1 week</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="flex-1"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Issuing...
                    </>
                  ) : (
                    <>
                      <Key className="w-4 h-4 mr-2" />
                      Issue Token
                    </>
                  )}
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-4 mt-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="font-medium text-green-800">Token Generated Successfully</span>
                </div>
                <p className="text-sm text-green-700">
                  Share this token with the vehicle owner. It will expire at:
                </p>
                <p className="text-sm font-medium text-green-800 mt-1">
                  {formatExpiry(generatedToken.expiry_time)}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Token</Label>
                <div className="flex gap-2">
                  <Input 
                    value={generatedToken.token_string} 
                    readOnly 
                    className="font-mono text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(generatedToken.token_string)}
                  >
                    {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Token ID</Label>
                <Input value={generatedToken.token_id} readOnly className="font-mono text-sm" />
              </div>

              <div className="space-y-2">
                <Label>Plate Number</Label>
                <Input value={generatedToken.plate_number} readOnly />
              </div>

              <Button 
                onClick={() => {
                  setGeneratedToken(null);
                  setIssueForm({
                    user_id: 'user_001',
                    plate_number: '',
                    token_type: 'jwt',
                    expiry_hours: '24'
                  });
                }}
                variant="outline"
                className="w-full"
              >
                Issue Another Token
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Verify Token Dialog */}
      <Dialog open={isVerifyDialogOpen} onOpenChange={setIsVerifyDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Verify Token</DialogTitle>
            <DialogDescription>
              Verify a token against a license plate for 2FA
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleVerifyToken} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="verify_token">Token *</Label>
              <Input
                id="verify_token"
                placeholder="Paste token here..."
                value={verifyForm.token}
                onChange={(e) => setVerifyForm({ ...verifyForm, token: e.target.value })}
                required
                className="font-mono text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="verify_plate">License Plate Number *</Label>
              <Input
                id="verify_plate"
                placeholder="e.g., ABC-123-XY"
                value={verifyForm.plate_number}
                onChange={(e) => setVerifyForm({ ...verifyForm, plate_number: e.target.value })}
                required
              />
            </div>

            {verifyResult && (
              <div className={`p-4 rounded-lg ${verifyResult.access_granted ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {verifyResult.access_granted ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <span className={`font-medium ${verifyResult.access_granted ? 'text-green-800' : 'text-red-800'}`}>
                    {verifyResult.access_granted ? 'Access Granted' : 'Access Denied'}
                  </span>
                </div>
                <div className="space-y-1 text-sm">
                  <p>Token Valid: <span className={verifyResult.token_valid ? 'text-green-600' : 'text-red-600'}>{verifyResult.token_valid ? 'Yes' : 'No'}</span></p>
                  <p>Plate Match: <span className={verifyResult.plate_match ? 'text-green-600' : 'text-red-600'}>{verifyResult.plate_match ? 'Yes' : 'No'}</span></p>
                  <p>Registered Plate: {verifyResult.registered_plate || 'N/A'}</p>
                  <p>Detected Plate: {verifyResult.detected_plate || 'N/A'}</p>
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsVerifyDialogOpen(false);
                  setVerifyResult(null);
                  setVerifyForm({ token: '', plate_number: '' });
                }}
                className="flex-1"
              >
                Close
              </Button>
              <Button 
                type="submit" 
                className="flex-1"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4 mr-2" />
                    Verify
                  </>
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
