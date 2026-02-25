🚦 TRAFIQ – AI Traffic Accident Detection System

Overview:

TRAFIQ is an AI-powered traffic monitoring system designed to automatically detect vehicle collisions from video footage.

The system uses computer vision and deep learning to:

Detect vehicles

Identify collisions

Capture accident snapshots

Generate structured accident reports (JSON)



🎯 Features

✅ Vehicle detection using YOLO
✅ Collision detection using bounding-box overlap (IoU)
✅ Accident classification with trained crash model
✅ Automatic accident snapshot capture
✅ JSON accident report generation


🧠 AI Models
Vehicle Detection Model

Detects vehicles in the video.

Model:

vehicle-model.pt

Detects:

Cars

Trucks

Buses

Motorcycles

Crash Detection Model

Detects accidents.

Model:

crash-model.pt

Classes:

['0', '1', '2']

Only "crash" class is considered a valid accident.

⚙️ Technologies Used

Python

OpenCV

YOLOv8 (Ultralytics)

NumPy

JSON

VSCode

📁 Project Structure
backend/
 └── ai-engine/
      detect_video.py
      └── dateset/
      └──models/
         best_vehicle.pt
         best_crash.pt
      accident_log.json
      snapshots.jpg


▶️ How to Run
1️⃣ Install Dependencies
pip install ultralytics opencv-python numpy
2️⃣ Run Detection (backend/ai-engine/)
python detect_video.py
🎥 Input Video

Place video file inside:

backend/ai-engine/

Example:

accident0.mp4

Recommended resolution:

1280x720
📸 Output
Accident Snapshot

When an accident is detected:

snapshots/accident_YYYYMMDD_HHMMSS.jpg

Example:

snapshots/accident_20260225_184233.jpg
JSON Report

File created automatically:

accident_log.json

Example:

[
  {
    "timestamp": "2026-02-25 18:42:33",
    "snapshot": "snapshots/accident_20260225_184233.jpg",
    "confidence": 0.91
  }
]
🧪 Detection Logic

An accident is confirmed when:

1️⃣ Two vehicles overlap (IoU ≥ threshold)

AND

2️⃣ Crash model detects class:

2

AND

3️⃣ Detection is stable across multiple frames

This reduces false detections.



Sprint 1 includes:

✔ Vehicle detection

✔ Collision detection

✔ Crash classification

✔ Snapshot capture

✔ JSON logging

✔ Video processing