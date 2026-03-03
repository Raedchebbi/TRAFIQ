import React, { createContext, useContext } from 'react';
import { useTrafikData } from '../hooks/useTrafikData';

const TrafikContext = createContext(null);

export function TrafikProvider({ children }) {
    const data = useTrafikData();
    return <TrafikContext.Provider value={data}>{children}</TrafikContext.Provider>;
}

export function useTrafik() {
    const ctx = useContext(TrafikContext);
    if (!ctx) throw new Error('useTrafik must be used inside TrafikProvider');
    return ctx;
}
