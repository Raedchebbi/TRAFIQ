# TRAFIQ – AI-Powered Traffic Monitoring & Incident Management Platform (Frontend)

<div align="center">

![TRAFIQ Banner](https://img.shields.io/badge/TRAFIQ-Traffic%20Intelligence%20Quotient-0066FF?style=for-the-badge&logo=react)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![Vite](https://img.shields.io/badge/Vite-5.0-646CFF?style=flat-square&logo=vite)
![Leaflet](https://img.shields.io/badge/Leaflet-Maps-199900?style=flat-square&logo=leaflet)
![License](https://img.shields.io/badge/License-Academic-blue?style=flat-square)

**Real-time AI-powered traffic monitoring platform with accident detection, route planning, and proximity alerts.**

</div>

---

## Overview

This project was developed as part of the **PIDEV – 3rd Year Engineering Program** at **Esprit School of Engineering** (Academic Year 2025–2026).

**TRAFIQ** (Traffic Intelligence Quotient) is a full-stack web platform that uses AI computer vision to monitor road traffic in real time, detect accidents automatically, and alert drivers in the vicinity. This repository contains the **React frontend** of the platform.

The frontend is divided into two distinct applications:

- 🚗 **Public App** — for drivers and citizens: real-time traffic map, route planner with alternatives, road status, and GPS-based proximity accident alerts (30-meter radius).
- 🛡️ **Admin Panel** — for traffic operators: live camera monitoring, AI agent pipeline view, accident snapshots gallery, incident management, and analytics dashboard.

---

## Features

### 🚗 Public Application (Drivers)
- ✅ Real-time interactive traffic map (Leaflet.js + OpenStreetMap)
- ✅ Route planner with 3 alternative suggestions (free / slow / blocked)
- ✅ Road status page — blocked, slow, or clear routes
- ✅ **Proximity alert system** — browser notification + in-app toast when an accident is detected within 30 meters of the user's GPS position
- ✅ Vehicle route tracking with animated polylines
- ✅ No login required — fully public access

### 🛡️ Admin Panel (Traffic Operators)
- ✅ Secure login (JWT-based, admin-only)
- ✅ Live camera monitoring grid with bounding box visualization
- ✅ **AI Agent view** — real-time pipeline: YOLO detection → tracking → pair analysis → best.pt validation → auto-correction
- ✅ **Accident snapshots gallery** — annotated canvas views of detected incidents
- ✅ Incident management with score, confidence level (L1/L2/L3), and action buttons
- ✅ Analytics dashboard with charts (Recharts): timeline, score distribution, heatmap, decision levels
- ✅ System settings: camera config, zone setup, notification radius

---

## Tech Stack

### Frontend
| Technology | Usage |
|---|---|
| React 18 + Vite | Core framework & build tool |
| React Router v6 | Client-side routing |
| Leaflet.js + react-leaflet | Interactive maps & GPS overlays |
| Recharts | Analytics charts & graphs |
| Lucide React | Icon library |
| HTML5 Canvas API | Accident snapshot rendering |
| Browser Geolocation API | User GPS tracking |
| Browser Notifications API | Proximity accident alerts |
| Context API | Global state management |
| Google Fonts | Plus Jakarta Sans, DM Sans, IBM Plex Mono |

### Backend (separate repository)
| Technology | Usage |
|---|---|
| Python + OpenCV | AI video processing engine |
| YOLOv8 (Ultralytics) | Vehicle detection model |
| custom best.pt | Specialized accident detection model |
| Node.js + Express | REST API layer |
| PostgreSQL / MongoDB | Data persistence |

---

## Architecture

```
trafiq-frontend/
├── src/
│   ├── apps/
│   │   ├── public/               # Public app (drivers)
│   │   │   ├── pages/
│   │   │   │   ├── Home.jsx       # Main traffic map
│   │   │   │   ├── RoutePlanner.jsx
│   │   │   │   └── RouteStatus.jsx
│   │   │   └── components/
│   │   │       ├── PublicMap.jsx
│   │   │       ├── AccidentAlert.jsx
│   │   │       ├── RouteCard.jsx
│   │   │       └── ProximityAlert.jsx
│   │   │
│   │   └── admin/                # Admin panel (operators)
│   │       ├── pages/
│   │       │   ├── Login.jsx
│   │       │   ├── Dashboard.jsx
│   │       │   ├── LiveMonitoring.jsx
│   │       │   ├── Incidents.jsx
│   │       │   ├── AIAgent.jsx
│   │       │   ├── Snapshots.jsx
│   │       │   └── Analytics.jsx
│   │       └── components/
│   │           ├── AdminMap.jsx
│   │           ├── SnapshotViewer.jsx
│   │           ├── AIAgentLog.jsx
│   │           └── IncidentCard.jsx
│   │
│   ├── shared/
│   │   ├── hooks/
│   │   │   ├── useTrafikData.js    # Polls trafiq_events.json
│   │   │   ├── useGeolocation.js   # GPS tracking
│   │   │   ├── useProximity.js     # 30m accident detection
│   │   │   └── useNotifications.js # Browser alerts
│   │   ├── context/
│   │   │   ├── AuthContext.jsx
│   │   │   └── TrafikContext.jsx
│   │   └── services/
│   │       └── trafiqApi.js
│   │
│   └── App.jsx                    # Root routing (/ public, /admin admin)
```

**Data flow:**
```
Python AI Engine (v9.1)
    ↓ generates
trafiq_events.json + trafiq_memory.json
    ↓ consumed by
Node.js REST API  (/api/events, /api/memory, /api/routes)
    ↓ polled every 3s by
React Frontend (useTrafikData hook)
    ↓ displayed in
Public Map + Admin Dashboard
    ↓ triggers (if accident ≤ 30m)
Browser Notification → Driver Alert
```

---

## Getting Started

### Prerequisites
- Node.js ≥ 18.x
- npm ≥ 9.x

### Installation

```bash
# Clone the repository
git clone https://github.com/esprit-school/Esprit-PIDEV-4TWIN3-2026-TRAFIQ-Frontend.git
cd Esprit-PIDEV-4TWIN3-2026-TRAFIQ-Frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The public app will be available at `http://localhost:5173`
The admin panel is accessible at `http://localhost:5173/admin`

### Admin Credentials (development)
```
Email    : admin@trafiq.ai
Password : trafiq2025
```

### Environment Variables
Create a `.env` file at the root:
```env
VITE_API_URL=http://localhost:3000
VITE_MAP_TILE_URL=https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png
VITE_ACCIDENT_RADIUS_METERS=30
```

---

## Contributors

| Name | Role | GitHub |
|---|---|---|
| Alani Mohamed Khalil | Frontend Developer | [@mohamedkhalil26](https://github.com/username) |

---

## Academic Context

This project was developed as part of the **PIDEV – 3rd Year Engineering Program** at **Esprit School of Engineering – Tunisia**.

| Field | Detail |
|---|---|
| Institution | Esprit School of Engineering – Tunisia |
| Program | PIDEV — Projet Intégré de Développement |
| Year | 3rd Year Engineering |
| Academic Year | 2025–2026 |
| Class | [4TWIN3] |
| Supervisor | [Bouhdid Badiaa] |

---

<div align="center">

Made with ❤️ at **Esprit School of Engineering – Tunisia** · 2025–2026

</div>
