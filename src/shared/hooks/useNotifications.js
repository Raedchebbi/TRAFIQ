import { useState, useCallback, useRef } from 'react';

export function useNotifications() {
    const [permission, setPermission] = useState(Notification.permission);
    const notifiedIds = useRef(new Set());

    const requestPermission = useCallback(async () => {
        if (Notification.permission === 'default') {
            const perm = await Notification.requestPermission();
            setPermission(perm);
            return perm;
        }
        return Notification.permission;
    }, []);

    const sendNotification = useCallback((id, title, body) => {
        if (notifiedIds.current.has(id)) return; // Anti-spam
        notifiedIds.current.add(id);

        if (Notification.permission === 'granted') {
            try {
                new Notification(title, { body, icon: '/vite.svg' });
            } catch (e) {
                console.warn('Notification failed:', e);
            }
        }
    }, []);

    return { permission, requestPermission, sendNotification };
}
