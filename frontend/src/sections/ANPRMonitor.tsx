/**
 * ANPR Monitor Page - Live License Plate Recognition
 */
import { useState, useRef, useCallback } from 'react';
import { Camera, Upload, Scan, CheckCircle, XCircle, Loader2, RefreshCw, Image as ImageIcon } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const API_BASE_URL = 'http://localhost:8000';

interface ANPRResult {
  success: boolean;
  plate_number?: string;
  confidence?: number;
  message: string;
  processing_time_ms?: number;
  bounding_box?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
}

export default function ANPRMonitor() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [result, setResult] = useState<ANPRResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      setSelectedImage(e.target?.result as string);
      setResult(null);
    };
    reader.readAsDataURL(file);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const processANPR = async () => {
    if (!selectedImage) {
      toast.error('Please select an image first');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/anpr/recognize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: selectedImage })
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
        if (data.success) {
          toast.success(`Plate recognized: ${data.plate_number}`);
        } else {
          toast.warning(data.message);
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || 'ANPR processing failed');
      }
    } catch (error) {
      toast.error('Network error - please try again');
    } finally {
      setLoading(false);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">ANPR Monitor</h2>
          <p className="text-gray-500">Automatic Number Plate Recognition using YOLOv8 + EasyOCR</p>
        </div>
        <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm font-medium rounded-full flex items-center gap-1">
          <Camera className="w-3 h-3" />
          Real-time Processing
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Image Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Vehicle Image</CardTitle>
            <CardDescription>
              Upload or drag & drop an image containing a license plate
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedImage ? (
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
                  transition-all duration-200
                  ${dragActive 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                  }
                `}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileInput}
                  className="hidden"
                />
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-lg font-medium text-gray-700 mb-2">
                  Drop image here or click to browse
                </p>
                <p className="text-sm text-gray-500">
                  Supports JPG, PNG, WEBP (max 10MB)
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative">
                  <img
                    src={selectedImage}
                    alt="Selected vehicle"
                    className="w-full rounded-lg border border-gray-200"
                  />
                  {result?.bounding_box && (
                    <div
                      className="absolute border-2 border-green-500 bg-green-500/20"
                      style={{
                        left: `${(result.bounding_box.x1 / 640) * 100}%`,
                        top: `${(result.bounding_box.y1 / 640) * 100}%`,
                        width: `${((result.bounding_box.x2 - result.bounding_box.x1) / 640) * 100}%`,
                        height: `${((result.bounding_box.y2 - result.bounding_box.y1) / 640) * 100}%`,
                      }}
                    />
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={clearImage}
                    className="flex-1"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Clear
                  </Button>
                  <Button
                    onClick={processANPR}
                    disabled={loading}
                    className="flex-1"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Scan className="w-4 h-4 mr-2" />
                        Recognize Plate
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Section */}
        <Card>
          <CardHeader>
            <CardTitle>Recognition Results</CardTitle>
            <CardDescription>
              ANPR processing output and confidence metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!result ? (
              <div className="text-center py-12 text-gray-500">
                <ImageIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">No results yet</p>
                <p className="text-sm">Upload an image and click &quot;Recognize Plate&quot;</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Status */}
                <div className={`p-4 rounded-lg ${result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                  <div className="flex items-center gap-3">
                    {result.success ? (
                      <CheckCircle className="w-8 h-8 text-green-600" />
                    ) : (
                      <XCircle className="w-8 h-8 text-red-600" />
                    )}
                    <div>
                      <p className={`font-semibold ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                        {result.success ? 'Recognition Successful' : 'Recognition Failed'}
                      </p>
                      <p className={`text-sm ${result.success ? 'text-green-600' : 'text-red-600'}`}>
                        {result.message}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Plate Details */}
                {result.success && (
                  <div className="space-y-4">
                    <div className="bg-gray-50 p-6 rounded-lg text-center">
                      <p className="text-sm text-gray-500 mb-2">Detected License Plate</p>
                      <p className="text-4xl font-bold font-mono text-gray-900 tracking-wider">
                        {result.plate_number}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <p className="text-sm text-blue-600 mb-1">Confidence</p>
                        <p className="text-2xl font-bold text-blue-800">
                          {(result.confidence! * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="bg-purple-50 p-4 rounded-lg">
                        <p className="text-sm text-purple-600 mb-1">Processing Time</p>
                        <p className="text-2xl font-bold text-purple-800">
                          {result.processing_time_ms?.toFixed(0)}ms
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Technical Details */}
                <div className="border-t border-gray-200 pt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">Technical Details</p>
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>Algorithm: YOLOv8 + EasyOCR</p>
                    <p>Input Size: 640x640</p>
                    <p>Model: yolov8n.pt</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ANPR Pipeline Info */}
      <Card className="bg-slate-50 border-slate-200">
        <CardHeader>
          <CardTitle className="text-slate-800">ANPR Processing Pipeline</CardTitle>
          <CardDescription>
            How the Automatic Number Plate Recognition works
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { 
                step: 1, 
                title: 'Image Capture', 
                desc: 'Vehicle image captured via camera or upload',
                icon: Camera
              },
              { 
                step: 2, 
                title: 'Preprocessing', 
                desc: 'Resize to 640x640, normalize pixels',
                icon: ImageIcon
              },
              { 
                step: 3, 
                title: 'YOLO Detection', 
                desc: 'Detect license plate region with bounding box',
                icon: Scan
              },
              { 
                step: 4, 
                title: 'OCR Recognition', 
                desc: 'Extract characters using EasyOCR',
                icon: CheckCircle
              }
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.step} className="flex flex-col items-center text-center p-4 bg-white rounded-lg border border-slate-200">
                  <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold mb-3">
                    <Icon className="w-5 h-5" />
                  </div>
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="text-sm text-slate-500">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
