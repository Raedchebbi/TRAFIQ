import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './shared/context/AuthContext';
import { TrafikProvider } from './shared/context/TrafikContext';
import PublicApp from './apps/public/PublicApp';
import AdminApp from './apps/admin/AdminApp';
import AdminLogin from './apps/admin/pages/Login';
import RoutePlanner from './apps/public/pages/RoutePlanner';
import RouteStatus from './apps/public/pages/RouteStatus';
import { useAuth } from './shared/context/AuthContext';

function AdminRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/admin/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <TrafikProvider>
          <Routes>
            {/* Public */}
            <Route path="/" element={<PublicApp />} />
            <Route path="/plan" element={<RoutePlanner />} />
            <Route path="/routes" element={<RouteStatus />} />

            {/* Admin */}
            <Route path="/admin" element={<Navigate to="/admin/login" replace />} />
            <Route path="/admin/login" element={<AdminLoginWrapper />} />
            <Route path="/admin/*" element={<AdminRouteWrapper />} />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </TrafikProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

function AdminLoginWrapper() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/admin/dashboard" replace />;
  return <AdminLogin />;
}

function AdminRouteWrapper() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/admin/login" replace />;
  return <AdminApp />;
}
