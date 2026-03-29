# CVT-VACS: Computer Vision and Token-Based Vehicle Access Control System

## Developed by
**Daria Benjamin Francis**  
Matric No: AUPG/24/0033  
Adeleke University, Ede, Osun State, Nigeria  
Supervisor: Dr Onamade, A.A  
Co-supervisor: Dr Oduwole, O. A.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [Installation & Setup](#installation--setup)
6. [API Documentation](#api-documentation)
7. [Two-Factor Authentication Model](#two-factor-authentication-model)
8. [Performance Metrics](#performance-metrics)
9. [Directory Structure](#directory-structure)
10. [Usage Guide](#usage-guide)

---

## Project Overview

CVT-VACS (Computer Vision and Token-Based Vehicle Access Control System) is a sophisticated two-factor authentication system designed for secure vehicle access control. The system combines:

1. **Automatic Number Plate Recognition (ANPR)** - Computer vision-based vehicle identification using YOLOv8 and EasyOCR
2. **Token-based Authentication** - Secure JWT/QR/OTP tokens for credential verification

This hybrid approach addresses the limitations of traditional single-factor systems (RFID, manual verification) by implementing a robust 2FA mechanism that significantly reduces unauthorized access.

### Problem Statement
Traditional vehicle access control systems suffer from:
- Single-factor vulnerabilities (RFID cloning, token sharing)
- Operational inefficiencies (manual verification delays)
- Weak audit capabilities
- Poor performance under challenging conditions

### Solution
CVT-VACS provides:
- **Two-Factor Authentication**: Combines something you have (token) + something you are (vehicle identity)
- **Real-time ANPR**: Deep learning-based license plate recognition
- **Secure Token Framework**: JWT-based tokens with cryptographic signatures
- **Comprehensive Audit Trail**: Complete logging of all access attempts

---

## System Architecture

### Three-Tier Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│              React + Tailwind CSS Frontend                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Dashboard│ │ Vehicles │ │  Tokens  │ │  ANPR    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│              FastAPI (Python) Backend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    ANPR      │  │Token Service │  │   Decision   │      │
│  │   Service    │  │              │  │   Engine     │      │
│  │ (YOLO+OCR)   │  │   (JWT)      │  │    (2FA)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│              MongoDB Atlas (NoSQL Database)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Users   │ │ Vehicles │ │  Tokens  │ │  Logs    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Features
1. **Vehicle Registration**: Register vehicles with plate numbers, types, and owner information
2. **Token Issuance**: Generate JWT, QR, or OTP tokens with configurable expiry
3. **ANPR Processing**: Real-time license plate recognition from images
4. **2FA Verification**: Combined token + ANPR verification
5. **Access Logging**: Complete audit trail with performance metrics
6. **Statistics Dashboard**: Real-time system performance monitoring

### Security Features
- JWT tokens with cryptographic signatures
- Token expiration and revocation
- Plate matching verification
- Comprehensive access logging
- False positive/negative tracking

### Performance Features
- YOLOv8 for fast object detection
- EasyOCR for accurate text recognition
- Async database operations
- Real-time metrics calculation

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database**: MongoDB Atlas (Motor async driver)
- **ANPR**: YOLOv8 (Ultralytics) + EasyOCR
- **Authentication**: JWT (python-jose)
- **Server**: Uvicorn (ASGI)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Icons**: Lucide React

### Computer Vision
- **Object Detection**: YOLOv8n (nano) - 640x640 input
- **OCR**: EasyOCR (English)
- **Image Processing**: OpenCV

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB (local or Atlas)
- Git

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables (optional):
Create `.env` file:
```env
MONGODB_URL=mongodb://localhost:27017
SECRET_KEY=your-secret-key
```

5. Start the backend server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd app
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

4. Build for production:
```bash
npm run build
```

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### API Endpoints

#### Vehicles
- `POST /vehicles/register` - Register a new vehicle
- `GET /vehicles/plate/{plate_number}` - Get vehicle by plate
- `GET /vehicles/user/{user_id}` - Get vehicles by user
- `GET /vehicles/all` - Get all vehicles
- `PATCH /vehicles/status/{plate_number}` - Update vehicle status

#### Tokens
- `POST /tokens/issue` - Issue a new token
- `POST /tokens/verify` - Verify token validity
- `POST /tokens/verify-with-plate` - Verify token with plate matching
- `POST /tokens/revoke/{token_id}` - Revoke a token
- `GET /tokens/active/{plate_number}` - Get active tokens for vehicle
- `GET /tokens/{token_id}` - Get token details

#### ANPR
- `POST /anpr/recognize` - Recognize plate from base64 image
- `POST /anpr/recognize-file` - Recognize plate from uploaded file
- `POST /anpr/validate` - Validate plate format
- `GET /anpr/status` - Get ANPR service status

#### Access Control
- `POST /access/verify` - Two-factor authentication verification
- `POST /access/verify-manual` - Manual verification (for testing)
- `GET /access/status` - Get access system status

#### Logs & Statistics
- `GET /logs/access` - Get access logs
- `GET /logs/access/today` - Get today's logs
- `GET /logs/statistics` - Get system statistics
- `GET /logs/performance` - Get performance metrics
- `GET /logs/plate/{plate_number}/history` - Get vehicle access history

### Interactive API Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Two-Factor Authentication Model

### Mathematical Formulation

The CVT-VACS decision engine implements the following mathematical model:

#### Variables
- **A** = ANPR output validity (1 if confidence ≥ threshold, 0 otherwise)
- **T** = Token validity (1 if valid and not expired, 0 otherwise)
- **M** = Plate matching condition (1 if detected plate = registered plate, 0 otherwise)

#### Decision Function
```
Access = A · T · M
```

Access is granted only when all three conditions are satisfied (A = 1, T = 1, M = 1).

### Verification Flow
1. Vehicle approaches access point
2. Camera captures vehicle image
3. ANPR extracts license plate (computes A)
4. Driver presents authentication token
5. System verifies token signature and expiry (computes T)
6. System compares detected plate with registered plate (computes M)
7. Decision engine evaluates Access = A · T · M
8. Access granted if all conditions met, denied otherwise
9. Event logged with all metrics

---

## Performance Metrics

The system tracks the following performance metrics:

### ANPR Metrics
- **Accuracy**: (TP + TN) / Total
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1 Score**: 2 · (Precision · Recall) / (Precision + Recall)

### System Metrics
- **Token Verification Latency**: Average time to verify token (ms)
- **System Response Time**: Total 2FA verification time (ms)
- **Authentication Success Rate**: Percentage of successful authentications
- **Throughput**: Vehicles processed per minute
- **False Positive Rate**: FP / (FP + TN)
- **False Negative Rate**: FN / (FN + TP)

### Target Performance
- ANPR Accuracy: > 90%
- System Response Time: < 500ms
- Authentication Success Rate: > 95%
- Throughput: > 10 vehicles/minute

---

## Directory Structure

```
CVT-VACS/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py        # MongoDB connection
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── vehicles.py    # Vehicle API routes
│   │   │   ├── tokens.py      # Token API routes
│   │   │   ├── anpr.py        # ANPR API routes
│   │   │   ├── access.py      # Access control routes
│   │   │   └── logs.py        # Logs & statistics routes
│   │   └── services/
│   │       ├── token_service.py    # JWT token logic
│   │       ├── anpr_service.py     # ANPR processing
│   │       └── decision_engine.py  # 2FA decision logic
│   ├── main.py                # Application entry point
│   └── requirements.txt       # Python dependencies
│
├── app/                       # React Frontend
│   ├── src/
│   │   ├── sections/          # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── VehicleRegistration.tsx
│   │   │   ├── TokenManagement.tsx
│   │   │   ├── ANPRMonitor.tsx
│   │   │   ├── AccessLogs.tsx
│   │   │   └── SystemStats.tsx
│   │   ├── components/ui/     # shadcn/ui components
│   │   ├── App.tsx           # Main application
│   │   ├── App.css           # Custom styles
│   │   └── main.tsx          # Entry point
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
└── README.md                  # This file
```

---

## Usage Guide

### 1. Register a Vehicle
1. Navigate to "Vehicles" page
2. Click "Register Vehicle"
3. Enter plate number, type, make, model, color
4. Submit the form

### 2. Issue a Token
1. Navigate to "Tokens" page
2. Click "Issue Token"
3. Enter vehicle plate number
4. Select token type (JWT/QR/OTP)
5. Set expiry duration
6. Copy the generated token

### 3. Test ANPR
1. Navigate to "ANPR Monitor" page
2. Upload a vehicle image with visible license plate
3. Click "Recognize Plate"
4. View recognition results and confidence score

### 4. Verify Access (2FA)
1. Navigate to "Tokens" page
2. Click "Verify Token"
3. Paste the token
4. Enter the license plate number
5. Click "Verify" to see 2FA result

### 5. View Access Logs
1. Navigate to "Access Logs" page
2. View all access attempts with decisions
3. Filter by plate number or decision type
4. Export logs to CSV if needed

### 6. Monitor Statistics
1. Navigate to "Statistics" page
2. View real-time performance metrics
3. Check ANPR accuracy and system response times
4. Monitor authentication success rates

---

## Research Contributions

This project contributes to the field of intelligent vehicle access control by:

1. **Hybrid 2FA Model**: Novel integration of ANPR and token-based authentication
2. **Performance Evaluation**: Comprehensive metrics for real-world deployment
3. **Scalable Architecture**: Cloud-ready design with MongoDB Atlas
4. **Open Implementation**: Fully documented codebase for academic replication

---

## Future Enhancements

- Mobile app for token management
- SMS integration for OTP delivery (Twilio)
- Blockchain-based token validation
- Edge deployment on Raspberry Pi
- Multi-language plate recognition
- Real-time video stream processing

---

## License

This project is developed as part of academic research at Adeleke University, Ede, Osun State, Nigeria.

---

## Acknowledgments

- Supervisor: Dr Onamade, A.A
- Co-supervisor: Dr Oduwole, O. A.
- Department of Computer Science, Faculty of Science, Adeleke University

---

**CVT-VACS v1.0.0** | 2025
