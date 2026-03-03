import { useMemo } from 'react';

// Haversine distance in meters
function haversine(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function useProximity(position, accidents, thresholdMeters = 30) {
    const nearby = useMemo(() => {
        if (!position || !accidents) return [];
        return accidents
            .filter(a => a.active)
            .map(a => ({ ...a, distance: Math.round(haversine(position.lat, position.lng, a.lat, a.lng)) }))
            .filter(a => a.distance <= thresholdMeters)
            .sort((a, b) => a.distance - b.distance);
    }, [position, accidents, thresholdMeters]);

    return { nearby, hasNearby: nearby.length > 0 };
}
