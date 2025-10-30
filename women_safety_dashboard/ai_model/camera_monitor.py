"""
Women Safety Monitoring System - AI Camera Monitor (Enhanced Version)
Detects lone women, dark or unsafe environments, and sends alerts with snapshots
"""

import cv2
from ultralytics import YOLO
import requests
import time
from datetime import datetime
import numpy as np
import os

class SafetyMonitor:
    def __init__(self, backend_url="http://localhost:3000", api_key="secure_key_123"):
        print("🔄 Loading YOLOv8 model...")
        self.model = YOLO('yolov8n.pt')  # lightweight model
        self.backend_url = backend_url
        self.api_key = api_key
        self.last_alert_time = {}
        self.alert_cooldown = 30  # seconds

        # Ensure snippet folder exists
        os.makedirs("snippets", exist_ok=True)

        self.camera_locations = {
            0: {"name": "Park Street Entrance", "lat": 11.1085, "lng": 77.3411},
            1: {"name": "Market Road Junction", "lat": 11.1095, "lng": 77.3421},
            "video": {"name": "Main Street Camera", "lat": 11.1075, "lng": 77.3401}
        }

        print("✅ Enhanced Safety Monitor initialized!")

    def analyze_scene(self, frame, detections):
        """Analyze the frame for potential danger situations."""
        persons = []
        men, women = [], []

        for detection in detections:
            for box in detection.boxes:
                if int(box.cls[0]) == 0:  # class 0 = person
                    confidence = float(box.conf[0])
                    if confidence > 0.5:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        persons.append((x1, y1, x2, y2))

                        # Simple gender guess based on height/width ratio (not perfect)
                        h, w = (y2 - y1), (x2 - x1)
                        aspect = h / (w + 1e-6)
                        if aspect > 2.2:
                            women.append((x1, y1, x2, y2))
                        else:
                            men.append((x1, y1, x2, y2))

        # Lighting check
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        is_dark = brightness < 70  # adjustable threshold

        # Decision logic
        severity, alert_type, description = "LOW", "Normal Activity", f"{len(persons)} person(s) detected"
        if len(women) == 1 and (len(men) == 0 and is_dark):
            severity = "HIGH"
            alert_type = "Lone Woman - Dark Area"
            description = "Single woman detected in poorly lit area. Possible danger."
        elif len(women) == 1 and len(men) >= 2:
            severity = "MAY_RISK"
            alert_type = "Woman Surrounded by Men"
            description = "Single woman among multiple men. Situation may be unsafe."
        elif 1 <= len(women) <= 2 and len(men) >= 3:
            severity = "MAY_RISK"
            alert_type = "Few Women in Male Group"
            description = "Few women surrounded by many men."
        elif len(women) == 1 and not is_dark:
            severity = "MEDIUM"
            alert_type = "Lone Woman"
            description = "Lone woman detected in well-lit area."

        return {
            'men_count': len(men),
            'women_count': len(women),
            'total': len(persons),
            'severity': severity,
            'alert_type': alert_type,
            'description': description,
            'brightness': brightness,
            'is_dark': is_dark
        }

    def send_alert(self, camera_id, analysis, frame):
        """Send alert to the backend with image snippet."""
        now = time.time()
        if camera_id in self.last_alert_time:
            if now - self.last_alert_time[camera_id] < self.alert_cooldown:
                return False

        if analysis['severity'] in ['HIGH', 'MAY_RISK', 'MEDIUM']:
            location = self.camera_locations.get(camera_id, self.camera_locations[0])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            snippet_path = f"snippets/alert_{timestamp}.jpg"
            cv2.imwrite(snippet_path, frame)

            alert_data = {
                'place': location['name'],
                'type': analysis['alert_type'],
                'severity': analysis['severity'],
                'lat': location['lat'],
                'lng': location['lng'],
                'time': datetime.now().isoformat(),
                'description': analysis['description'],
                'cameraId': f"CAM-{str(camera_id).zfill(3)}",
                'menCount': analysis['men_count'],
                'womenCount': analysis['women_count'],
                'lighting': 'Dark' if analysis['is_dark'] else 'Well-lit',
                'image': f"/snippets/{os.path.basename(snippet_path)}"
            }

            try:
                headers = {"x-api-key": self.api_key}
                res = requests.post(f"{self.backend_url}/send-alert", json=alert_data, headers=headers, timeout=5)
                if res.status_code == 200:
                    self.last_alert_time[camera_id] = now
                    print(f"🚨 ALERT SENT: [{analysis['severity']}] {location['name']}")
                else:
                    print(f"❌ Failed to send alert ({res.status_code})")
            except Exception as e:
                print(f"❌ Error sending alert: {e}")

    def monitor_camera(self, source=0):
        print(f"\n📹 Monitoring started on source: {source}")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print("❌ Cannot open camera/video")
            return

        frame_no = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ End of video or camera error")
                break

            frame_no += 1
            if frame_no % 30 == 0:  # process every 30th frame
                results = self.model(frame, verbose=False)
                analysis = self.analyze_scene(frame, results)
                annotated = results[0].plot()

                text = f"W:{analysis['women_count']} M:{analysis['men_count']} | {analysis['severity']}"
                cv2.putText(annotated, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

                self.send_alert(source, analysis, annotated)
                cv2.imshow("Safety Monitor", annotated)
                print(f"Frame {frame_no}: {analysis['alert_type']} | {analysis['severity']}")
            else:
                cv2.imshow("Safety Monitor", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("👋 Exiting monitor...")
                break

        cap.release()
        cv2.destroyAllWindows()

    def test_alert(self):
        print("\n🧪 Sending test alert...")
        dummy = {
            'men_count': 3, 'women_count': 1, 'total': 4,
            'severity': 'MAY_RISK',
            'alert_type': 'Test - Lone Woman Among Men',
            'description': 'This is a test alert to verify dashboard connection.',
            'brightness': 40, 'is_dark': True
        }
        fake_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.send_alert(0, dummy, fake_frame)
        print("✅ Test alert sent successfully!")

def main():
    print("=" * 60)
    print("  WOMEN SAFETY MONITORING SYSTEM - ENHANCED AI MONITOR")
    print("=" * 60)
    monitor = SafetyMonitor()
    while True:
        print("\n1️⃣ Monitor Webcam\n2️⃣ Monitor Video\n3️⃣ Send Test Alert\n4️⃣ Exit")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            monitor.monitor_camera(0)
        elif choice == "2":
            path = input("Enter video path: ").strip()
            monitor.monitor_camera(path)
        elif choice == "3":
            monitor.test_alert()
        elif choice == "4":
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
