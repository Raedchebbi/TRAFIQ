import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AdminSidebar from './components/layout/AdminSidebar';
import AdminTopBar from './components/layout/AdminTopBar';
import Dashboard from './pages/Dashboard';
import LiveMonitoring from './pages/LiveMonitoring';
import Incidents from './pages/Incidents';
import AIAgent from './pages/AIAgent';
import Snapshots from './pages/Snapshots';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import './AdminApp.css';

export default function AdminApp() {
    return (
        <div className="admin-app">
            <AdminSidebar />
            <div className="admin-body">
                <AdminTopBar />
                <main className="admin-main">
                    <Routes>
                        <Route path="dashboard" element={<Dashboard />} />
                        <Route path="live" element={<LiveMonitoring />} />
                        <Route path="incidents" element={<Incidents />} />
                        <Route path="ai-agent" element={<AIAgent />} />
                        <Route path="snapshots" element={<Snapshots />} />
                        <Route path="analytics" element={<Analytics />} />
                        <Route path="settings" element={<Settings />} />
                        <Route index element={<Navigate to="dashboard" replace />} />
                        <Route path="*" element={<Navigate to="dashboard" replace />} />
                    </Routes>
                </main>
            </div>
        </div>
    );
}
