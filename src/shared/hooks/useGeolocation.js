import { useState, useEffect } from 'react';
import { USER_POSITION_MOCK } from './useTrafikData';

export function useGeolocation() {
    const [position, setPosition] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!navigator.geolocation) {
            setPosition(USER_POSITION_MOCK);
            return;
        }

        const watchId = navigator.geolocation.watchPosition(
            (pos) => {
                setPosition({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy });
                setError(null);
            },
            (err) => {
                setError(err.message);
                setPosition(USER_POSITION_MOCK); // Fallback mock
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
        );

        return () => navigator.geolocation.clearWatch(watchId);
    }, []);

    return { position: position || USER_POSITION_MOCK, error };
}
