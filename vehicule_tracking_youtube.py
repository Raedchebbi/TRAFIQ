import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import time
from collections import deque
import yt_dlp

# ==============================
# CONFIGURATION
# ==============================
YOUTUBE_URL = "https://www.youtube.com/watch?v=1xl0hX-nF2E"


def get_youtube_stream_url(youtube_url):
    print("Recherche du stream YouTube...")
    ydl_opts = {
        'format': 'best[height<=720]',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            print(f"Stream trouve: {info.get('title', 'Sans titre')}")
            return info['url']
    except Exception as e:
        print(f"Erreur: {e}")
        return None


# ==============================
# PARAMETRES SIMPLIFIES
# ==============================
# Une seule ligne au milieu pour détecter les deux sens
LINE_Y_CENTER = 370  # Ligne centrale

# Zone de détection autour de la ligne (pour éviter faux positifs)
DETECTION_MARGIN = 50

HISTORY = 8
ACCIDENT_SPEED_THRESHOLD = 8
STOP_DURATION = 3

# Paramètres objets statiques
STATIC_POSITION_TOLERANCE = 20
STATIC_CHECK_FRAMES = 40
STATIC_SPEED_MAX = 2.5
MIN_MOVEMENT_PER_FRAME = 2.0

# ==============================
# INITIALISATION
# ==============================
print("Initialisation YOLO...")
model = YOLO("yolov8n.pt")
tracker = sv.ByteTrack()

stream_url = get_youtube_stream_url(YOUTUBE_URL)
if not stream_url:
    print("Erreur stream")
    exit()

print("Connexion au stream...")
cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("Impossible d'ouvrir le stream")
    exit()

print("Stream OK! Demarrage...")

# Variables de tracking
positions = {}
speeds = {}
speed_history = {}
first_y_position = {}  # NOUVEAU: premiere position Y detectee

# Compteurs
counted_ids_down = set()
counted_ids_up = set()
vehicle_count_down = 0
vehicle_count_up = 0

# Autres
stopped_time = {}
static_objects = set()
first_detection_time = {}
static_frame_counter = {}

frame_number = 0
fps_counter = deque(maxlen=30)
last_time = time.time()


# ==============================
# FONCTIONS
# ==============================
def calculate_displacement(positions_list, frames=20):
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
    if len(positions_list) < frames:
        return float('inf')
    recent = list(positions_list)[-frames:]
    x_coords = [p[0] for p in recent]
    y_coords = [p[1] for p in recent]
    return np.var(x_coords) + np.var(y_coords)


def get_simple_direction(current_y, first_y):
    """
    METHODE SIMPLE: Compare position actuelle avec position initiale
    Si Y augmente -> DOWN (vers le bas de l'image)
    Si Y diminue -> UP (vers le haut de l'image)
    """
    diff = current_y - first_y

    # Seuil minimum pour éviter bruit
    if abs(diff) > 20:
        if diff > 0:
            return "DOWN"
        else:
            return "UP"

    return None


# ==============================
# BOUCLE PRINCIPALE
# ==============================
reconnect_attempts = 0
max_reconnect_attempts = 5

while True:
    ret, frame = cap.read()

    if not ret:
        print(f"Reconnexion... ({reconnect_attempts + 1}/{max_reconnect_attempts})")
        reconnect_attempts += 1

        if reconnect_attempts >= max_reconnect_attempts:
            print("Arret.")
            break

        time.sleep(2)
        cap.release()

        stream_url = get_youtube_stream_url(YOUTUBE_URL)
        if stream_url:
            cap = cv2.VideoCapture(stream_url)
            if cap.isOpened():
                print("Reconnexion OK!")
                reconnect_attempts = 0
                continue
        continue

    reconnect_attempts = 0
    frame_number += 1

    # FPS
    current_time = time.time()
    fps = 1.0 / (current_time - last_time) if (current_time - last_time) > 0 else 0
    fps_counter.append(fps)
    last_time = current_time
    avg_fps = np.mean(fps_counter)

    # Detection
    results = model(frame)[0]
    detections = sv.Detections.from_ultralytics(results)

    # Vehicules uniquement
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
            # IMPORTANT: Sauvegarder la premiere position Y
            first_y_position[tracker_id] = cy

        positions[tracker_id].append((cx, cy, time.time()))

        # ==============================
        # VITESSE
        # ==============================
        if len(positions[tracker_id]) >= HISTORY:
            x_old, y_old, t_old = positions[tracker_id][-HISTORY]
            dist = np.sqrt((cx - x_old) ** 2 + (cy - y_old) ** 2)
            dt = time.time() - t_old

            if dt > 0:
                raw_speed = dist / dt
                if tracker_id in speeds:
                    speeds[tracker_id] = 0.7 * speeds[tracker_id] + 0.3 * raw_speed
                else:
                    speeds[tracker_id] = raw_speed
                speed_history[tracker_id].append(raw_speed)

        # ==============================
        # OBJETS STATIQUES
        # ==============================
        if len(positions[tracker_id]) >= STATIC_CHECK_FRAMES:
            total_displacement = calculate_displacement(positions[tracker_id], frames=30)
            position_variance = get_position_variance(positions[tracker_id], frames=30)
            avg_movement_per_frame = total_displacement / 30 if total_displacement > 0 else 0

            current_speed = speeds.get(tracker_id, 0)
            speed_list = list(speed_history[tracker_id])
            avg_speed = np.mean(speed_list[-25:]) if len(speed_list) >= 25 else current_speed
            max_speed = max(speed_list[-25:]) if len(speed_list) >= 25 else current_speed

            is_currently_static = (
                    avg_movement_per_frame < MIN_MOVEMENT_PER_FRAME and
                    position_variance < STATIC_POSITION_TOLERANCE and
                    avg_speed < STATIC_SPEED_MAX and
                    max_speed < STATIC_SPEED_MAX * 1.5 and
                    current_speed < STATIC_SPEED_MAX
            )

            if is_currently_static:
                static_frame_counter[tracker_id] += 1
            else:
                static_frame_counter[tracker_id] = 0

            if static_frame_counter[tracker_id] >= 35:
                if tracker_id not in static_objects:
                    static_objects.add(tracker_id)

            if tracker_id in static_objects:
                if (avg_movement_per_frame > MIN_MOVEMENT_PER_FRAME * 4 or
                        current_speed > STATIC_SPEED_MAX * 4):
                    static_objects.discard(tracker_id)
                    static_frame_counter[tracker_id] = 0

        # ==============================
        # DETERMINATION DIRECTION (SIMPLIFIEE)
        # ==============================
        direction = None
        if tracker_id not in static_objects and tracker_id in first_y_position:
            direction = get_simple_direction(cy, first_y_position[tracker_id])

        # ==============================
        # COMPTAGE BIDIRECTIONNEL
        # ==============================
        if tracker_id not in static_objects and direction is not None:
            # Zone de détection autour de la ligne centrale
            in_detection_zone = abs(cy - LINE_Y_CENTER) < DETECTION_MARGIN

            if in_detection_zone:
                # Véhicule allant vers le BAS
                if direction == "DOWN" and tracker_id not in counted_ids_down:
                    # Vérifier qu'il a bien franchi la ligne
                    if cy > LINE_Y_CENTER:
                        counted_ids_down.add(tracker_id)
                        vehicle_count_down += 1
                        print(f"[v DOWN] Vehicule {tracker_id} - Total DOWN: {vehicle_count_down}")

                # Véhicule allant vers le HAUT
                elif direction == "UP" and tracker_id not in counted_ids_up:
                    # Vérifier qu'il a bien franchi la ligne
                    if cy < LINE_Y_CENTER:
                        counted_ids_up.add(tracker_id)
                        vehicle_count_up += 1
                        print(f"[^ UP] Vehicule {tracker_id} - Total UP: {vehicle_count_up}")

        # ==============================
        # ACCIDENT
        # ==============================
        accident_flag = False
        if (tracker_id not in static_objects and
                tracker_id in speeds and
                len(speed_history[tracker_id]) >= 10):

            current_speed = speeds[tracker_id]
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
            color = (80, 80, 80)
            label = f"STATIC {tracker_id}"
        else:
            if direction == "DOWN":
                color = (0, 69, 255)  # Orange
                arrow = "v"
            elif direction == "UP":
                color = (0, 255, 0)  # Vert
                arrow = "^"
            else:
                color = (0, 200, 200)  # Jaune
                arrow = "-"

            label = f"ID{tracker_id} {arrow}"
            if tracker_id in speeds:
                label += f" {int(speeds[tracker_id])}"

        if accident_flag:
            color = (0, 0, 255)
            cv2.putText(frame, "ACCIDENT!", (x1, y1 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

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
                first_y_position.pop(lost_id, None)
                static_objects.discard(lost_id)

    # ==============================
    # UI
    # ==============================
    # Zone de détection (rectangle semi-transparent)
    overlay = frame.copy()
    detection_y1 = LINE_Y_CENTER - DETECTION_MARGIN
    detection_y2 = LINE_Y_CENTER + DETECTION_MARGIN
    cv2.rectangle(overlay, (0, detection_y1), (frame.shape[1], detection_y2),
                  (100, 100, 100), -1)
    cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

    # Ligne centrale
    cv2.line(frame, (0, LINE_Y_CENTER), (frame.shape[1], LINE_Y_CENTER),
             (255, 255, 0), 2)
    cv2.putText(frame, "DETECTION LINE", (frame.shape[1] // 2 - 100, LINE_Y_CENTER - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # Panneau compteurs
    overlay = frame.copy()
    cv2.rectangle(overlay, (15, 25), (350, 230), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    cv2.putText(frame, f"v DOWN: {vehicle_count_down}", (25, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 69, 255), 2)
    cv2.putText(frame, f"^ UP: {vehicle_count_up}", (25, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 0), 2)

    cv2.line(frame, (25, 110), (335, 110), (255, 255, 255), 2)

    cv2.putText(frame, f"TOTAL: {vehicle_count_down + vehicle_count_up}", (25, 145),
                cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 2)

    cv2.putText(frame, f"Static: {len(static_objects)}", (25, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 2)

    cv2.putText(frame, f"FPS: {int(avg_fps)}", (25, 210),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

    # LIVE
    cv2.putText(frame, "LIVE", (frame.shape[1] - 100, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 3)

    cv2.imshow("Traffic Detection - Bidirectional", frame)

    if cv2.waitKey(1) == 27:
        print("\nArret...")
        print(f"\nSTATISTIQUES:")
        print(f"  v DOWN: {vehicle_count_down}")
        print(f"  ^ UP: {vehicle_count_up}")
        print(f"  TOTAL: {vehicle_count_down + vehicle_count_up}")
        break

cap.release()
cv2.destroyAllWindows()
print("Termine")
