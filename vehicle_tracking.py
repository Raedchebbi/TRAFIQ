import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import time
from collections import deque

# ==============================
# PARAMETRES TRAFIQ OPTIMISES
# ==============================
LINE_Y = 400
HISTORY = 12
ACCIDENT_SPEED_THRESHOLD = 8
STOP_DURATION = 3

# Paramètres pour objets statiques (AJUSTES)
STATIC_POSITION_TOLERANCE = 25  # tolérance réduite
STATIC_CHECK_FRAMES = 30  # plus de frames avant décision
STATIC_SPEED_MAX = 4.0  # vitesse max pour être statique
MIN_MOVEMENT_PER_FRAME = 3.0  # mouvement minimum par frame

# ==============================
# INITIALISATION
# ==============================
model = YOLO('path/to/best.pt')
tracker = sv.ByteTrack()
cap = cv2.VideoCapture("videos/traffic2.mp4")

positions = {}
speeds = {}
speed_history = {}
last_positions = {}
counted_ids = set()
vehicle_count = 0
stopped_time = {}
static_objects = set()
first_detection_time = {}
static_frame_counter = {}  # compteur frames statiques consécutives

frame_number = 0


# ==============================
# FONCTIONS UTILITAIRES
# ==============================
def calculate_displacement(positions_list, frames=20):
    """Calcule le déplacement total sur N frames"""
    if len(positions_list) < frames:
        return 0

    recent = list(positions_list)[-frames:]
    total_dist = 0

    for i in range(1, len(recent)):
        x1, y1, _ = recent[i - 1]
        x2, y2, _ = recent[i]
        total_dist += np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    return total_dist


def get_position_variance(positions_list, frames=20):
    """Calcule la variance de position"""
    if len(positions_list) < frames:
        return float('inf')

    recent = list(positions_list)[-frames:]
    x_coords = [p[0] for p in recent]
    y_coords = [p[1] for p in recent]

    return np.var(x_coords) + np.var(y_coords)


# ==============================
# BOUCLE PRINCIPALE
# ==============================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_number += 1

    results = model(frame)[0]
    detections = sv.Detections.from_ultralytics(results)

    # Garder seulement les véhicules
    vehicle_mask = np.isin(detections.class_id, [2, 3, 5, 7])
    detections = detections[vehicle_mask]

    # Tracking
    detections = tracker.update_with_detections(detections)

    current_tracked_ids = set()

    for xyxy, tracker_id in zip(detections.xyxy, detections.tracker_id):
        current_tracked_ids.add(tracker_id)

        x1, y1, x2, y2 = map(int, xyxy)
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        # ==============================
        # INITIALISATION
        # ==============================
        if tracker_id not in positions:
            positions[tracker_id] = deque(maxlen=50)
            first_detection_time[tracker_id] = time.time()
            speed_history[tracker_id] = deque(maxlen=30)
            static_frame_counter[tracker_id] = 0

        positions[tracker_id].append((cx, cy, time.time()))

        # ==============================
        # CALCUL VITESSE
        # ==============================
        if len(positions[tracker_id]) >= HISTORY:
            x_old, y_old, t_old = positions[tracker_id][-HISTORY]
            dist = np.sqrt((cx - x_old) ** 2 + (cy - y_old) ** 2)
            dt = time.time() - t_old

            if dt > 0:
                raw_speed = dist / dt

                # Lissage
                if tracker_id in speeds:
                    speeds[tracker_id] = 0.7 * speeds[tracker_id] + 0.3 * raw_speed
                else:
                    speeds[tracker_id] = raw_speed

                speed_history[tracker_id].append(raw_speed)

        # ==============================
        # DETECTION OBJETS STATIQUES (AMELIOREE)
        # ==============================
        if len(positions[tracker_id]) >= STATIC_CHECK_FRAMES:

            # Calculs sur les 25 dernières frames
            total_displacement = calculate_displacement(positions[tracker_id], frames=25)
            position_variance = get_position_variance(positions[tracker_id], frames=25)
            avg_movement_per_frame = total_displacement / 25 if total_displacement > 0 else 0

            # Vitesse actuelle et moyenne
            current_speed = speeds.get(tracker_id, 0)
            speed_list = list(speed_history[tracker_id])
            avg_speed = np.mean(speed_list[-20:]) if len(speed_list) >= 20 else current_speed
            max_speed = max(speed_list[-20:]) if len(speed_list) >= 20 else current_speed

            # Critères STRICTS pour être statique
            is_currently_static = (
                    avg_movement_per_frame < MIN_MOVEMENT_PER_FRAME and
                    position_variance < STATIC_POSITION_TOLERANCE and
                    avg_speed < STATIC_SPEED_MAX and
                    max_speed < STATIC_SPEED_MAX * 2 and
                    current_speed < STATIC_SPEED_MAX
            )

            # Incrémenter ou réinitialiser compteur
            if is_currently_static:
                static_frame_counter[tracker_id] += 1
            else:
                static_frame_counter[tracker_id] = 0

            # Marquer comme statique seulement après 25 frames consécutives
            if static_frame_counter[tracker_id] >= 25:
                if tracker_id not in static_objects:
                    static_objects.add(tracker_id)

            # Retirer de statique si mouvement détecté
            if tracker_id in static_objects:
                if (avg_movement_per_frame > MIN_MOVEMENT_PER_FRAME * 3 or
                        current_speed > STATIC_SPEED_MAX * 3):
                    static_objects.discard(tracker_id)
                    static_frame_counter[tracker_id] = 0

        # ==============================
        # COMPTEUR (LINE CROSSING)
        # ==============================
        if tracker_id not in static_objects:
            if tracker_id in last_positions:
                prev_cy = last_positions[tracker_id]
            else:
                prev_cy = cy

            last_positions[tracker_id] = cy

            if prev_cy < LINE_Y and cy >= LINE_Y:
                if tracker_id not in counted_ids:
                    counted_ids.add(tracker_id)
                    vehicle_count += 1

        # ==============================
        # DETECTION ACCIDENT
        # ==============================
        accident_flag = False

        if (tracker_id not in static_objects and
                tracker_id in speeds and
                len(speed_history[tracker_id]) >= 10):

            current_speed = speeds[tracker_id]

            # Véhicule doit avoir bougé avant
            speed_list = list(speed_history[tracker_id])
            max_recent_speed = max(speed_list[-20:]) if len(speed_list) >= 20 else 0
            was_moving = max_recent_speed > ACCIDENT_SPEED_THRESHOLD * 3

            if current_speed < ACCIDENT_SPEED_THRESHOLD and was_moving:
                if tracker_id not in stopped_time:
                    stopped_time[tracker_id] = time.time()

                stopped_duration = time.time() - stopped_time[tracker_id]

                if stopped_duration > STOP_DURATION:
                    accident_flag = True
            else:
                stopped_time.pop(tracker_id, None)

        # ==============================
        # AFFICHAGE
        # ==============================
        if tracker_id in static_objects:
            color = (128, 128, 128)
            label = f"STATIC {tracker_id}"
        else:
            color = (0, 255, 0)
            label = f"ID {tracker_id}"

            if tracker_id in speeds:
                label += f" {int(speeds[tracker_id])} px/s"

        if accident_flag:
            color = (0, 0, 255)
            cv2.putText(frame, "ACCIDENT POSSIBLE",
                        (x1, y1 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # ==============================
    # NETTOYAGE
    # ==============================
    lost_ids = set(positions.keys()) - current_tracked_ids
    for lost_id in lost_ids:
        if lost_id in first_detection_time:
            if time.time() - first_detection_time[lost_id] > 5:
                positions.pop(lost_id, None)
                speeds.pop(lost_id, None)
                speed_history.pop(lost_id, None)
                stopped_time.pop(lost_id, None)
                first_detection_time.pop(lost_id, None)
                static_frame_counter.pop(lost_id, None)
                static_objects.discard(lost_id)

    # ==============================
    # UI
    # ==============================
    cv2.line(frame, (0, LINE_Y), (frame.shape[1], LINE_Y), (0, 0, 255), 2)
    cv2.putText(frame, f"Vehicles: {vehicle_count}", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(frame, f"Static objects: {len(static_objects)}", (30, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)

    cv2.imshow("TRAFIQ AI Detection", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()