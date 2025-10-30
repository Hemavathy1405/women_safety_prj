"""
Enhanced Women Safety Monitoring System with Advanced AI Features
Includes: Activity detection, crowd analysis, speed estimation, loitering detection
"""

import cv2
from ultralytics import YOLO
import requests
import time
from datetime import datetime
import numpy as np
from collections import deque, defaultdict
import math

class EnhancedSafetyMonitor:
    def __init__(self, backend_url="http://localhost:3000"):
        """Initialize enhanced safety monitoring system"""
        print("🔄 Loading AI models...")
        
        # Load YOLOv8 models
        self.person_model = YOLO('yolov8n.pt')  # Person detection
        self.pose_model = YOLO('yolov8n-pose.pt')  # Pose estimation for activity
        
        self.backend_url = backend_url
        self.last_alert_time = {}
        self.alert_cooldown = 30  # seconds
        
        # Tracking data structures
        self.person_tracks = defaultdict(lambda: {
            'positions': deque(maxlen=30),
            'timestamps': deque(maxlen=30),
            'first_seen': None,
            'last_alerted': None
        })
        
        # Camera locations with risk zones
        self.camera_locations = {
            0: {
                "name": "Park Street - North Gate", 
                "lat": 11.1085, 
                "lng": 77.3411,
                "risk_zones": [(100, 100, 300, 300)]  # Dark corners
            },
            1: {
                "name": "Market Road Junction", 
                "lat": 11.1095, 
                "lng": 77.3421,
                "risk_zones": []
            },
            "video": {
                "name": "Main Street Camera", 
                "lat": 11.1075, 
                "lng": 77.3401,
                "risk_zones": []
            }
        }
        
        print("✅ Enhanced Safety Monitor initialized!")
        print("📊 Features: Person tracking, activity analysis, crowd detection")
    
    def calculate_speed(self, positions, timestamps):
        """Calculate movement speed from tracked positions"""
        if len(positions) < 2:
            return 0
        
        total_distance = 0
        for i in range(1, len(positions)):
            x1, y1 = positions[i-1]
            x2, y2 = positions[i]
            distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            total_distance += distance
        
        time_diff = timestamps[-1] - timestamps[0]
        if time_diff > 0:
            return total_distance / time_diff  # pixels per second
        return 0
    
    def detect_loitering(self, track_data, current_time):
        """Detect if someone is loitering in an area"""
        if track_data['first_seen'] is None:
            return False
        
        time_in_area = current_time - track_data['first_seen']
        
        # Check if person has been in area for more than 5 minutes
        if time_in_area > 300:  # 5 minutes
            positions = list(track_data['positions'])
            if len(positions) > 10:
                # Calculate if person stayed in small area
                x_coords = [p[0] for p in positions]
                y_coords = [p[1] for p in positions]
                area_radius = max(max(x_coords) - min(x_coords), 
                                 max(y_coords) - min(y_coords))
                
                # If moved less than 100 pixels in 5 minutes = loitering
                if area_radius < 100:
                    return True
        
        return False
    
    def detect_running(self, speed):
        """Detect if someone is running (potential chase or emergency)"""
        # Threshold based on camera distance/resolution
        return speed > 50  # pixels per second
    
    def analyze_crowd_density(self, persons, frame_shape):
        """Analyze crowd density in frame"""
        if len(persons) == 0:
            return "empty", 0
        
        frame_area = frame_shape[0] * frame_shape[1]
        person_area = sum([self.calculate_bbox_area(p['bbox']) for p in persons])
        density_ratio = person_area / frame_area
        
        if density_ratio > 0.6:
            return "very_crowded", density_ratio
        elif density_ratio > 0.3:
            return "crowded", density_ratio
        elif density_ratio > 0.1:
            return "moderate", density_ratio
        else:
            return "sparse", density_ratio
    
    def calculate_bbox_area(self, bbox):
        """Calculate area of bounding box"""
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    
    def is_in_risk_zone(self, bbox, camera_id):
        """Check if person is in a predefined risk zone"""
        location = self.camera_locations.get(camera_id, self.camera_locations[0])
        risk_zones = location.get('risk_zones', [])
        
        person_center_x = (bbox[0] + bbox[2]) / 2
        person_center_y = (bbox[1] + bbox[3]) / 2
        
        for zone in risk_zones:
            if (zone[0] <= person_center_x <= zone[2] and 
                zone[1] <= person_center_y <= zone[3]):
                return True
        
        return False
    
    def analyze_scene_advanced(self, frame, detections, camera_id):
        """Advanced scene analysis with multiple factors"""
        persons = []
        current_time = time.time()
        
        # Extract person detections
        for detection in detections:
            for i, box in enumerate(detection.boxes):
                if int(box.cls[0]) == 0 and float(box.conf[0]) > 0.5:
                    bbox = box.xyxy[0].cpu().numpy()
                    center = ((bbox[0] + bbox[2])/2, (bbox[1] + bbox[3])/2)
                    
                    persons.append({
                        'id': i,
                        'bbox': bbox,
                        'center': center,
                        'confidence': float(box.conf[0])
                    })
                    
                    # Update tracking
                    track_id = f"person_{i}"
                    if self.person_tracks[track_id]['first_seen'] is None:
                        self.person_tracks[track_id]['first_seen'] = current_time
                    
                    self.person_tracks[track_id]['positions'].append(center)
                    self.person_tracks[track_id]['timestamps'].append(current_time)
        
        # Calculate scene brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        is_dark = brightness < 80
        is_very_dark = brightness < 50
        
        # Analyze crowd density
        crowd_level, density = self.analyze_crowd_density(persons, frame.shape)
        
        num_persons = len(persons)
        
        # Initialize risk assessment
        severity = "LOW"
        alert_type = "Normal Activity"
        description = f"{num_persons} person(s) detected"
        risk_factors = []
        
        # CRITICAL SCENARIOS
        if num_persons == 1 and is_very_dark:
            severity = "CRITICAL"
            alert_type = "Lone Woman - Very Dark Area"
            description = "⚠️ URGENT: Single person in very poorly lit area"
            risk_factors.append("Very poor lighting")
            risk_factors.append("Isolated individual")
            
        elif num_persons == 1 and is_dark:
            # Check for loitering
            track_data = self.person_tracks['person_0']
            if self.detect_loitering(track_data, current_time):
                severity = "CRITICAL"
                alert_type = "Loitering Detected - Dark Area"
                description = "Person staying in dark area for extended period"
                risk_factors.append("Loitering behavior")
                risk_factors.append("Poor lighting")
            else:
                severity = "HIGH"
                alert_type = "Lone Woman - Dark Area"
                description = "Single person detected in poorly lit area"
                risk_factors.append("Poor lighting")
                risk_factors.append("Isolated individual")
        
        # HIGH PRIORITY SCENARIOS
        elif num_persons == 2:
            # Check if they're in risk zone
            in_risk_zone = any([self.is_in_risk_zone(p['bbox'], camera_id) for p in persons])
            
            if in_risk_zone and is_dark:
                severity = "CRITICAL"
                alert_type = "Multiple Persons in Risk Zone"
                description = "Two persons detected in high-risk area with poor lighting"
                risk_factors.append("High-risk location")
                risk_factors.append("Poor lighting")
            elif is_dark:
                severity = "HIGH"
                alert_type = "Two Persons - Dark Area"
                description = "Two persons in poorly lit area. Monitoring situation."
                risk_factors.append("Poor lighting")
            else:
                severity = "MEDIUM"
                alert_type = "Two Persons Detected"
                description = "Two persons in frame. Routine monitoring."
        
        # MEDIUM RISK SCENARIOS
        elif num_persons == 1:
            track_data = self.person_tracks['person_0']
            speed = self.calculate_speed(
                list(track_data['positions']), 
                list(track_data['timestamps'])
            )
            
            if self.detect_running(speed):
                severity = "HIGH"
                alert_type = "Running Person Detected"
                description = "Person running - possible emergency or chase situation"
                risk_factors.append("Rapid movement")
            else:
                severity = "MEDIUM"
                alert_type = "Lone Woman Detected"
                description = "Single person walking alone. Monitoring."
        
        # CROWD ANALYSIS
        elif crowd_level == "very_crowded":
            severity = "MEDIUM"
            alert_type = "Very Crowded Area"
            description = f"High crowd density detected ({num_persons} persons)"
            risk_factors.append("Crowd safety concern")
        
        elif num_persons >= 3:
            severity = "LOW"
            alert_type = "Multiple Persons"
            description = f"{num_persons} persons detected. Area appears safe."
        
        return {
            'person_count': num_persons,
            'severity': severity,
            'alert_type': alert_type,
            'description': description,
            'brightness': brightness,
            'is_dark': is_dark,
            'crowd_level': crowd_level,
            'crowd_density': density,
            'risk_factors': risk_factors,
            'persons': persons
        }
    
    def send_alert(self, camera_id, analysis):
        """Send enhanced alert to backend server"""
        current_time = time.time()
        
        # Check cooldown
        if camera_id in self.last_alert_time:
            if current_time - self.last_alert_time[camera_id] < self.alert_cooldown:
                return False
        
        # Send alerts for concerning situations
        if analysis['severity'] in ['CRITICAL', 'HIGH', 'MEDIUM']:
            location = self.camera_locations.get(camera_id, self.camera_locations[0])
            
            alert_data = {
                'place': location['name'],
                'type': analysis['alert_type'],
                'severity': analysis['severity'],
                'lat': location['lat'],
                'lng': location['lng'],
                'time': datetime.now().isoformat(),
                'description': analysis['description'],
                'cameraId': f"CAM-{str(camera_id).zfill(3)}",
                'personCount': analysis['person_count'],
                'lighting': 'Very Dark' if analysis['brightness'] < 50 else ('Dark' if analysis['is_dark'] else 'Well-lit'),
                'crowdLevel': analysis['crowd_level'],
                'riskFactors': ', '.join(analysis['risk_factors']) if analysis['risk_factors'] else 'None',
                'brightnessLevel': int(analysis['brightness'])
            }
            
            try:
                response = requests.post(
                    f"{self.backend_url}/send-alert",
                    json=alert_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.last_alert_time[camera_id] = current_time
                    print(f"🚨 ALERT SENT: [{analysis['severity']}] {location['name']}")
                    print(f"   Risk Factors: {alert_data['riskFactors']}")
                    return True
                else:
                    print(f"❌ Failed to send alert: {response.status_code}")
            except Exception as e:
                print(f"❌ Error sending alert: {e}")
        
        return False
    
    def draw_enhanced_overlay(self, frame, analysis):
        """Draw enhanced information overlay on frame"""
        h, w = frame.shape[:2]
        
        # Create semi-transparent overlay
        overlay = frame.copy()
        
        # Top info bar
        cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Main stats
        y_pos = 30
        cv2.putText(frame, f"Persons: {analysis['person_count']}", 
                    (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Severity with color
        severity_colors = {
            'CRITICAL': (0, 0, 255),
            'HIGH': (0, 165, 255),
            'MEDIUM': (0, 255, 255),
            'LOW': (0, 255, 0)
        }
        color = severity_colors.get(analysis['severity'], (255, 255, 255))
        cv2.putText(frame, f"Severity: {analysis['severity']}", 
                    (10, y_pos + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Lighting condition
        lighting = f"Lighting: {int(analysis['brightness'])}"
        cv2.putText(frame, lighting, 
                    (10, y_pos + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Alert type
        cv2.putText(frame, f"Type: {analysis['alert_type']}", 
                    (10, y_pos + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Draw bounding boxes for persons
        for person in analysis.get('persons', []):
            bbox = person['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Draw box with severity color
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw confidence
            conf_text = f"{person['confidence']:.2f}"
            cv2.putText(frame, conf_text, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def monitor_camera(self, source=0):
        """Monitor camera with enhanced AI analysis"""
        print(f"\n🎥 Starting ENHANCED monitoring on source: {source}")
        print("Press 'q' to quit, 's' to screenshot, 'a' to force alert\n")
        
        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            print("❌ Error: Could not open camera/video")
            return
        
        frame_count = 0
        fps_start_time = time.time()
        fps = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("⚠️ End of video or camera error")
                    break
                
                frame_count += 1
                
                # Calculate FPS
                if frame_count % 30 == 0:
                    fps = 30 / (time.time() - fps_start_time)
                    fps_start_time = time.time()
                
                # Process every 15 frames for better real-time performance
                if frame_count % 15 == 0:
                    # Run detection
                    results = self.person_model(frame, verbose=False)
                    
                    # Advanced analysis
                    analysis = self.analyze_scene_advanced(frame, results, source)
                    
                    # Draw enhanced overlay
                    display_frame = self.draw_enhanced_overlay(frame, analysis)
                    
                    # Add FPS counter
                    cv2.putText(display_frame, f"FPS: {fps:.1f}", 
                               (frame.shape[1] - 150, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Send alert if needed
                    self.send_alert(source, analysis)
                    
                    cv2.imshow('Enhanced Safety Monitor', display_frame)
                    
                    # Status print
                    print(f"Frame {frame_count} | {analysis['alert_type']} | "
                          f"Persons: {analysis['person_count']} | "
                          f"Brightness: {int(analysis['brightness'])}")
                else:
                    cv2.imshow('Enhanced Safety Monitor', frame)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Stopping monitor...")
                    break
                elif key == ord('s'):
                    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"📸 Screenshot saved: {filename}")
                elif key == ord('a'):
                    # Force send current analysis as alert
                    print("⚠️ Forcing alert send...")
                    results = self.person_model(frame, verbose=False)
                    analysis = self.analyze_scene_advanced(frame, results, source)
                    self.last_alert_time[source] = 0  # Reset cooldown
                    self.send_alert(source, analysis)
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("✅ Monitor stopped")
    
    def test_enhanced_alert(self):
        """Send enhanced test alert"""
        print("\n🧪 Sending ENHANCED test alert...")
        
        test_analysis = {
            'person_count': 1,
            'severity': 'CRITICAL',
            'alert_type': 'Enhanced Test - Lone Woman in Dark Risk Zone',
            'description': 'ENHANCED TEST: Critical situation detected with multiple risk factors',
            'brightness': 35,
            'is_dark': True,
            'crowd_level': 'sparse',
            'crowd_density': 0.05,
            'risk_factors': ['Very poor lighting', 'Isolated individual', 'High-risk zone'],
            'persons': []
        }
        
        success = self.send_alert(0, test_analysis)
        if success:
            print("✅ Enhanced test alert sent successfully!")
        else:
            print("❌ Failed to send test alert")


def main():
    """Main function with menu"""
    print("=" * 60)
    print("  ENHANCED WOMEN SAFETY AI MONITORING SYSTEM")
    print("=" * 60)
    print("\n🚀 Features:")
    print("  ✓ Advanced person tracking")
    print("  ✓ Loitering detection")
    print("  ✓ Speed/movement analysis")
    print("  ✓ Crowd density analysis")
    print("  ✓ Risk zone monitoring")
    print("  ✓ Multi-factor risk assessment")
    
    monitor = EnhancedSafetyMonitor()
    
    while True:
        print("\n" + "=" * 60)
        print("Select an option:")
        print("1. Monitor Webcam (Real-time Enhanced AI)")
        print("2. Monitor Video File")
        print("3. Send Enhanced Test Alert")
        print("4. Exit")
        print("=" * 60)
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == '1':
            print("\n🎥 Starting ENHANCED webcam monitoring...")
            time.sleep(1)
            monitor.monitor_camera(0)
        
        elif choice == '2':
            video_path = input("Enter video file path: ").strip()
            if video_path:
                monitor.monitor_camera(video_path)
            else:
                print("❌ Invalid path")
        
        elif choice == '3':
            monitor.test_enhanced_alert()
        
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()