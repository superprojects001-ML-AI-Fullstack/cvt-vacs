/**
 * CameraEntry.tsx
 * Live camera capture → ANPR → Auto token generation → Parking slot allocation
 * Save to: src/sections/CameraEntry.tsx
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Camera, CameraOff, Scan, CheckCircle, XCircle,
  Loader2, RefreshCw, Car, Key, ParkingSquare,
  AlertTriangle, Upload, Keyboard, X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const API_BASE_URL = import.meta.env.VITE_API_URL;

// ── Types ─────────────────────────────────────────────────────────────────────

interface EntryResult {
  success: boolean;
  registered: boolean;
  plate_number: string | null;
  color: string;
  color_hex: string;
  color_confidence: number;
  anpr_confidence: number;
  processing_time_ms: number;
  token: {
    token_id: string;
    token_string: string;
    expiry_time: string;
  } | null;
  parking_slot: string | null;
  parking_zone: string | null;
  message: string;
}

interface ParkingSlot {
  slot_id: string;
  zone: string;
  is_occupied: boolean;
  plate_number: string | null;
  vehicle_color: string | null;
  entry_time: string | null;
}

interface ParkingSummary {
  total: number;
  occupied: number;
  available: number;
  zone_a_available: number;
  zone_b_available: number;
  slots: ParkingSlot[];
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function CameraEntry() {
  // Camera state
  const videoRef  = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraActive,  setCameraActive]  = useState(false);
  const [cameraError,   setCameraError]   = useState<string | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [processing,    setProcessing]    = useState(false);
  const [result,        setResult]        = useState<EntryResult | null>(null);
  const [copied,        setCopied]        = useState(false);

  // Manual fallback state
  const [showManual,    setShowManual]    = useState(false);
  const [manualPlate,   setManualPlate]   = useState('');
  const [manualColor,   setManualColor]   = useState('');

  // Parking grid state
  const [parking,       setParking]       = useState<ParkingSummary | null>(null);
  const [parkingLoading, setParkingLoading] = useState(true);

  // Exit state
  const [exitPlate,     setExitPlate]     = useState('');
  const [exitLoading,   setExitLoading]   = useState(false);

  // ── Parking data ────────────────────────────────────────────────────────────
  const fetchParking = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/camera-entry/slots`);
      if (res.ok) {
        const data = await res.json();
        setParking(data);
      }
    } catch {
      // silent fail — parking grid is supplementary
    } finally {
      setParkingLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchParking();
    const interval = setInterval(fetchParking, 15000); // refresh every 15 s
    return () => clearInterval(interval);
  }, [fetchParking]);

  // ── Camera controls ─────────────────────────────────────────────────────────
  const startCamera = async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',   // rear camera on mobile
          width:  { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActive(true);
      setCapturedImage(null);
      setResult(null);
    } catch (err: any) {
      const msg = err.name === 'NotAllowedError'
        ? 'Camera permission denied. Please allow camera access and try again.'
        : err.name === 'NotFoundError'
        ? 'No camera found on this device.'
        : `Camera error: ${err.message}`;
      setCameraError(msg);
      toast.error(msg);
    }
  };

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraActive(false);
  }, []);

  // Stop camera on unmount
  useEffect(() => () => stopCamera(), [stopCamera]);

  // ── Frame capture ────────────────────────────────────────────────────────────
  const captureFrame = (): string | null => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return null;

    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.92);
  };

  // ── Process capture ──────────────────────────────────────────────────────────
  const handleCapture = async () => {
    const image = captureFrame();
    if (!image) {
      toast.error('Failed to capture frame');
      return;
    }
    stopCamera();
    setCapturedImage(image);
    await processEntry(image);
  };

  const processEntry = async (image: string) => {
    setProcessing(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/camera-entry/process`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ image_base64: image }),
      });
      const data: EntryResult = await res.json();
      setResult(data);
      if (data.success) {
        toast.success(`Entry granted — ${data.parking_slot || 'no slot'}`);
        fetchParking();
      } else {
        toast.warning(data.message);
      }
    } catch {
      toast.error('Network error — please try again');
    } finally {
      setProcessing(false);
    }
  };

  // ── Manual entry ─────────────────────────────────────────────────────────────
  const handleManualEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualPlate.trim()) return;
    setProcessing(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/camera-entry/manual`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          plate_number:  manualPlate.trim().toUpperCase(),
          vehicle_color: manualColor || 'unknown',
        }),
      });
      const data: EntryResult = await res.json();
      setResult(data);
      if (data.success) {
        toast.success(`Entry granted — ${data.parking_slot || 'no slot'}`);
        fetchParking();
        setShowManual(false);
        setManualPlate('');
        setManualColor('');
      } else {
        toast.warning(data.message);
      }
    } catch {
      toast.error('Network error — please try again');
    } finally {
      setProcessing(false);
    }
  };

  // ── Exit ─────────────────────────────────────────────────────────────────────
  const handleExit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exitPlate.trim()) return;
    setExitLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/camera-entry/exit`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ plate_number: exitPlate.trim().toUpperCase() }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        fetchParking();
        setExitPlate('');
      } else {
        toast.warning(data.message);
      }
    } catch {
      toast.error('Network error');
    } finally {
      setExitLoading(false);
    }
  };

  // ── Clipboard ─────────────────────────────────────────────────────────────────
  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    setCopied(true);
    toast.success('Token copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Reset ─────────────────────────────────────────────────────────────────────
  const reset = () => {
    setCapturedImage(null);
    setResult(null);
    stopCamera();
  };

  // ── Helpers ───────────────────────────────────────────────────────────────────
  const getColorStyle = (hex: string) => ({
    backgroundColor: hex,
    border: '2px solid rgba(0,0,0,0.15)',
  });

  const formatExpiry = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Camera Entry</h2>
          <p className="text-gray-500">
            Auto plate detection → token generation → parking allocation
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowManual(v => !v)}
          >
            <Keyboard className="w-4 h-4 mr-2" />
            Manual Entry
          </Button>
        </div>
      </div>

      {/* ── Manual entry panel ──────────────────────────────────────────────── */}
      {showManual && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-yellow-800 text-base">
                Manual Plate Entry (Fallback)
              </CardTitle>
              <button onClick={() => setShowManual(false)}>
                <X className="w-4 h-4 text-yellow-600" />
              </button>
            </div>
            <CardDescription className="text-yellow-700">
              Use when camera cannot read the plate
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleManualEntry} className="flex flex-col sm:flex-row gap-3">
              <Input
                placeholder="Plate number e.g. ABC-123-XY"
                value={manualPlate}
                onChange={e => setManualPlate(e.target.value)}
                className="flex-1 uppercase"
                required
              />
              <Input
                placeholder="Colour (optional)"
                value={manualColor}
                onChange={e => setManualColor(e.target.value)}
                className="w-40"
              />
              <Button type="submit" disabled={processing} className="whitespace-nowrap">
                {processing
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : 'Process Entry'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* ── Main grid ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Left: Camera panel ──────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Vehicle Camera</CardTitle>
            <CardDescription>
              Point the camera at the approaching vehicle
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">

            {/* Camera error */}
            {cameraError && (
              <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-800">Camera unavailable</p>
                  <p className="text-sm text-red-600">{cameraError}</p>
                  <p className="text-xs text-red-500 mt-1">
                    Use Manual Entry as a fallback.
                  </p>
                </div>
              </div>
            )}

            {/* Video / captured image area */}
            <div className="relative bg-gray-900 rounded-xl overflow-hidden aspect-video flex items-center justify-center">
              {/* Live video */}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
              />

              {/* Captured still */}
              {capturedImage && !cameraActive && (
                <img
                  src={capturedImage}
                  alt="Captured vehicle"
                  className="w-full h-full object-cover"
                />
              )}

              {/* Idle placeholder */}
              {!cameraActive && !capturedImage && (
                <div className="text-center text-gray-500 p-8">
                  <Camera className="w-16 h-16 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">Camera inactive</p>
                  <p className="text-xs mt-1 opacity-70">
                    Click "Start Camera" to begin
                  </p>
                </div>
              )}

              {/* Scanning overlay while camera is live */}
              {cameraActive && (
                <div className="absolute inset-0 pointer-events-none">
                  {/* Corner brackets */}
                  <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-green-400" />
                  <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-green-400" />
                  <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-green-400" />
                  <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-green-400" />
                  {/* Scan line animation */}
                  <div
                    className="absolute left-0 right-0 h-0.5 bg-green-400/70"
                    style={{ animation: 'scanLine 2s linear infinite' }}
                  />
                  <style>{`
                    @keyframes scanLine {
                      0%   { top: 10%; }
                      100% { top: 90%; }
                    }
                  `}</style>
                </div>
              )}

              {/* Processing overlay */}
              {processing && (
                <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="w-10 h-10 text-white animate-spin" />
                  <p className="text-white text-sm font-medium">Processing ANPR...</p>
                </div>
              )}
            </div>

            {/* Hidden canvas for frame capture */}
            <canvas ref={canvasRef} className="hidden" />

            {/* Action buttons */}
            <div className="flex gap-3">
              {!cameraActive && !capturedImage && (
                <Button onClick={startCamera} className="flex-1">
                  <Camera className="w-4 h-4 mr-2" />
                  Start Camera
                </Button>
              )}

              {cameraActive && (
                <>
                  <Button
                    variant="outline"
                    onClick={stopCamera}
                    className="flex-1"
                  >
                    <CameraOff className="w-4 h-4 mr-2" />
                    Stop
                  </Button>
                  <Button
                    onClick={handleCapture}
                    disabled={processing}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                  >
                    <Scan className="w-4 h-4 mr-2" />
                    Capture & Process
                  </Button>
                </>
              )}

              {capturedImage && !cameraActive && (
                <>
                  <Button variant="outline" onClick={reset} className="flex-1">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    New Capture
                  </Button>
                  {!processing && !result && (
                    <Button
                      onClick={() => processEntry(capturedImage)}
                      className="flex-1"
                    >
                      <Scan className="w-4 h-4 mr-2" />
                      Re-process
                    </Button>
                  )}
                </>
              )}
            </div>

            {/* Upload fallback */}
            {!cameraActive && !capturedImage && (
              <div className="border-t border-gray-100 pt-3">
                <Label className="text-xs text-gray-500 mb-2 block">
                  Or upload an image
                </Label>
                <label className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-gray-400 hover:bg-gray-50 transition-colors">
                  <Upload className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-500">Choose image file</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={e => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const reader = new FileReader();
                      reader.onload = ev => {
                        const img = ev.target?.result as string;
                        setCapturedImage(img);
                        processEntry(img);
                      };
                      reader.readAsDataURL(file);
                    }}
                  />
                </label>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Right: Results panel ─────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Entry Result</CardTitle>
            <CardDescription>
              Detected plate, colour, token, and assigned slot
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Idle state */}
            {!result && !processing && (
              <div className="text-center py-16 text-gray-400">
                <Car className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="font-medium">Awaiting vehicle capture</p>
                <p className="text-sm mt-1 opacity-70">
                  Start the camera and capture a vehicle to begin
                </p>
              </div>
            )}

            {/* Processing state */}
            {processing && (
              <div className="text-center py-16 text-gray-500">
                <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-blue-500" />
                <p className="font-medium">Running ANPR pipeline...</p>
                <p className="text-sm mt-1 opacity-70">
                  Detecting plate · Detecting colour · Issuing token
                </p>
              </div>
            )}

            {/* Result */}
            {result && !processing && (
              <div className="space-y-4">

                {/* Status banner */}
                <div className={`flex items-center gap-3 p-4 rounded-xl ${
                  result.success
                    ? 'bg-green-50 border border-green-200'
                    : result.registered === false && result.plate_number
                    ? 'bg-yellow-50 border border-yellow-200'
                    : 'bg-red-50 border border-red-200'
                }`}>
                  {result.success
                    ? <CheckCircle className="w-7 h-7 text-green-600 flex-shrink-0" />
                    : result.registered === false && result.plate_number
                    ? <AlertTriangle className="w-7 h-7 text-yellow-500 flex-shrink-0" />
                    : <XCircle className="w-7 h-7 text-red-500 flex-shrink-0" />
                  }
                  <div>
                    <p className={`font-semibold ${
                      result.success ? 'text-green-800'
                      : result.registered === false && result.plate_number
                      ? 'text-yellow-800'
                      : 'text-red-800'
                    }`}>
                      {result.success ? 'Entry Granted'
                        : result.registered === false && result.plate_number
                        ? 'Vehicle Not Registered'
                        : 'Entry Denied'}
                    </p>
                    <p className={`text-sm ${
                      result.success ? 'text-green-600'
                      : result.registered === false && result.plate_number
                      ? 'text-yellow-600'
                      : 'text-red-600'
                    }`}>
                      {result.message}
                    </p>
                  </div>
                </div>

                {/* Plate + colour row */}
                {result.plate_number && (
                  <div className="grid grid-cols-2 gap-3">
                    {/* Plate */}
                    <div className="bg-gray-900 rounded-xl p-4 text-center">
                      <p className="text-xs text-gray-400 mb-1">Detected Plate</p>
                      <p className="text-2xl font-bold font-mono text-white tracking-widest">
                        {result.plate_number}
                      </p>
                      {result.anpr_confidence > 0 && (
                        <p className="text-xs text-gray-400 mt-1">
                          {result.anpr_confidence.toFixed(1)}% confidence
                        </p>
                      )}
                    </div>

                    {/* Colour */}
                    <div className="bg-gray-50 rounded-xl p-4 text-center border border-gray-200">
                      <p className="text-xs text-gray-500 mb-2">Vehicle Colour</p>
                      <div
                        className="w-12 h-12 rounded-full mx-auto mb-2 shadow-md"
                        style={getColorStyle(result.color_hex || '#808080')}
                      />
                      <p className="font-semibold capitalize text-gray-800">
                        {result.color || 'Unknown'}
                      </p>
                      {result.color_confidence > 0 && (
                        <p className="text-xs text-gray-400">
                          {result.color_confidence.toFixed(1)}% confidence
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Token */}
                {result.token && (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Key className="w-4 h-4 text-blue-600" />
                      <span className="font-semibold text-blue-800 text-sm">
                        Auto-Generated Token
                      </span>
                      <Badge className="ml-auto bg-blue-100 text-blue-700 hover:bg-blue-100">
                        JWT
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <input
                        readOnly
                        value={result.token.token_string}
                        className="flex-1 text-xs font-mono bg-white border border-blue-200
                                   rounded-lg px-3 py-2 text-gray-700 truncate"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyToken(result.token!.token_string)}
                        className="border-blue-200 text-blue-600 hover:bg-blue-100"
                      >
                        {copied ? <CheckCircle className="w-4 h-4" /> : 'Copy'}
                      </Button>
                    </div>
                    <p className="text-xs text-blue-500 mt-2">
                      Expires: {formatExpiry(result.token.expiry_time)}
                    </p>
                  </div>
                )}

                {/* Parking slot */}
                {result.success && (
                  <div className={`rounded-xl p-4 border ${
                    result.parking_slot
                      ? 'bg-purple-50 border-purple-200'
                      : 'bg-orange-50 border-orange-200'
                  }`}>
                    <div className="flex items-center gap-2">
                      <ParkingSquare className={`w-5 h-5 ${
                        result.parking_slot ? 'text-purple-600' : 'text-orange-500'
                      }`} />
                      <span className={`font-semibold text-sm ${
                        result.parking_slot ? 'text-purple-800' : 'text-orange-700'
                      }`}>
                        {result.parking_slot ? 'Parking Slot Assigned' : 'Car Park Full'}
                      </span>
                    </div>
                    {result.parking_slot && (
                      <div className="mt-2 flex items-center gap-4">
                        <span className="text-3xl font-bold text-purple-700">
                          {result.parking_slot}
                        </span>
                        <span className="px-2 py-1 bg-purple-100 text-purple-700
                                         text-xs font-medium rounded-full">
                          Zone {result.parking_zone}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Processing time */}
                {result.processing_time_ms > 0 && (
                  <p className="text-xs text-gray-400 text-right">
                    Processed in {result.processing_time_ms.toFixed(0)} ms
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Exit vehicle panel ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Vehicle Exit</CardTitle>
          <CardDescription>
            Release the parking slot when a vehicle leaves
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleExit} className="flex flex-col sm:flex-row gap-3 max-w-lg">
            <Input
              placeholder="Enter plate number to exit e.g. ABC-123-XY"
              value={exitPlate}
              onChange={e => setExitPlate(e.target.value.toUpperCase())}
              className="flex-1"
              required
            />
            <Button
              type="submit"
              disabled={exitLoading}
              variant="outline"
              className="border-red-200 text-red-600 hover:bg-red-50"
            >
              {exitLoading
                ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                : <Car className="w-4 h-4 mr-2" />}
              Record Exit
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* ── Live parking grid ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Live Parking Grid</CardTitle>
              <CardDescription>
                Real-time slot occupancy — refreshes every 15 seconds
              </CardDescription>
            </div>
            {parking && (
              <div className="flex gap-3 text-sm">
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full font-medium">
                  {parking.available} Free
                </span>
                <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full font-medium">
                  {parking.occupied} Occupied
                </span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {parkingLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : !parking ? (
            <p className="text-center text-gray-400 py-8">
              Unable to load parking data
            </p>
          ) : (
            <>
              {/* Zone labels */}
              {['A', 'B'].map(zone => {
                const zoneSlots = parking.slots.filter(s => s.zone === zone);
                return (
                  <div key={zone} className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                      <span className="w-6 h-6 bg-slate-700 text-white rounded flex items-center justify-center text-xs">
                        {zone}
                      </span>
                      Zone {zone}
                    </h4>
                    <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
                      {zoneSlots.map(slot => (
                        <div
                          key={slot.slot_id}
                          title={slot.is_occupied
                            ? `${slot.plate_number} (${slot.vehicle_color || 'unknown colour'})`
                            : 'Available'}
                          className={`relative aspect-square rounded-lg flex flex-col items-center
                            justify-center text-xs font-bold border-2 transition-all cursor-default
                            ${slot.is_occupied
                              ? 'bg-red-100 border-red-300 text-red-700'
                              : 'bg-green-50 border-green-300 text-green-700 hover:bg-green-100'
                            }`}
                        >
                          <span className="text-[10px] font-mono">
                            {slot.slot_id.replace('SLOT-', '')}
                          </span>
                          {slot.is_occupied && slot.vehicle_color && slot.vehicle_color !== 'unknown' && (
                            <div
                              className="w-3 h-3 rounded-full mt-0.5 border border-white/50"
                              style={{ backgroundColor: slot.vehicle_color }}
                              title={slot.vehicle_color}
                            />
                          )}
                          {slot.is_occupied && (
                            <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}

              {/* Legend */}
              <div className="flex items-center gap-6 mt-2 text-xs text-gray-500 border-t border-gray-100 pt-3">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-green-200 border border-green-300 inline-block" />
                  Available
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-red-200 border border-red-300 inline-block" />
                  Occupied
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-gray-400 inline-block" />
                  Colour dot = vehicle colour
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
