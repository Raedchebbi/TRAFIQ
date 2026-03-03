import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        const stored = sessionStorage.getItem('trafiq_admin');
        return stored ? JSON.parse(stored) : null;
    });

    const login = (email, password) => {
        if (email === 'admin@trafiq.ai' && password === 'trafiq2025') {
            const userData = { email, name: 'Admin TRAFIQ', role: 'admin', avatar: 'AT' };
            sessionStorage.setItem('trafiq_admin', JSON.stringify(userData));
            setUser(userData);
            return true;
        }
        return false;
    };

    const logout = () => {
        sessionStorage.removeItem('trafiq_admin');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
    return ctx;
}
