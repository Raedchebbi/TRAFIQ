import { useMemo } from 'react';
import { ACCIDENTS_GPS } from './useTrafikData';

const ITINERAIRES_MOCK = [
    {
        id: 1, label: 'RECOMMANDÉ', labelColor: '#2E7D32', labelBg: '#E8F5E9',
        roads: ['A1', 'Blvd Mohamed V'], time: 18, dist: 7.2, status: 'free',
        incidents: 0, extraMin: 0,
        coords: [[36.810, 10.175], [36.808, 10.180], [36.806, 10.183], [36.805, 10.185]],
        color: '#1A73E8', weight: 5, opacity: 0.9, dashArray: null,
    },
    {
        id: 2, label: 'ALTERNATIF  +4 min', labelColor: '#F57C00', labelBg: '#FFF3E0',
        roads: ['Avenue Habib Bourguiba', 'Rue de Marseille'], time: 22, dist: 8.8, status: 'slow',
        incidents: 1, extraMin: 4,
        coords: [[36.810, 10.175], [36.809, 10.177], [36.808, 10.180], [36.807, 10.183], [36.805, 10.185]],
        color: '#1A73E8', weight: 3, opacity: 0.6, dashArray: '8,4',
    },
    {
        id: 3, label: 'DÉCONSEILLÉ  +12 min', labelColor: '#B71C1C', labelBg: '#FFEBEE',
        roads: ['Rue de la Liberté', 'Avenue de la Foire'], time: 30, dist: 6.1, status: 'blocked',
        incidents: 1, isAccident: true, extraMin: 12,
        coords: [[36.810, 10.175], [36.811, 10.178], [36.809, 10.182], [36.807, 10.186], [36.805, 10.185]],
        color: '#E53935', weight: 3, opacity: 0.5, dashArray: '4,4',
    },
];

export function useRoutes(from, to) {
    const routes = useMemo(() => {
        if (!from || !to) return [];
        // Attach accident info
        return ITINERAIRES_MOCK.map(route => ({
            ...route,
            activeAccidents: ACCIDENTS_GPS.filter(a => a.active && route.isAccident),
        }));
    }, [from, to]);

    return { routes };
}

export { ITINERAIRES_MOCK };
