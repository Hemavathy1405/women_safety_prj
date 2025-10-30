"""
Multi-Camera Monitoring System
Monitors multiple camera feeds simultaneously with thread-based processing
"""

import cv2
from ultralytics import YOLO
import requests
import time
from datetime import datetime
import numpy as np
import threading
from queue import Queue
import json

class MultiCameraMonitor:
    def __init__(self, backend_url="http://localhost:3000"):
        """Initialize multi-camera monitoring system"""
        print("🔄 Loading AI model...")
        self.model = YOLO('yolov8n.pt')
        self.backend_url = backend_url
        
        # Thread-safe alert queue
        self.alert_queue = Queue()
        self.running = False
        
        # Camera configurations
        self.cameras = {
            'cam1': {
                'source': 0,  # Webcam
                'name': 'Park Street - North Gate',
                'lat': 11.1085,
                'lng': 77.3411,
                'enabled': True
            },
            'cam2': {
                'source': 'rtsp://your-ip-camera-url',  # IP Camera
                'name': 'Market Road Junction',
                'lat': 11.1095,
                'lng': 77.3421,
                'enabled': False  # Disable if not available
            },
            'cam3': {
                'source': 'video.mp4',  # Video file
                'name': 'Station Road Camera',
                'lat': 11.1075,
                'lng': 77.3401,
                'enabled': False
            }
        }
        
        self.camera_stats = {cam_id: {
            'frames_processed': 0,
            'alerts_sent': 0,
            'last_alert': None,
            'status': 'stopped'
        } for cam_id in self.cameras}
        
        print("✅ Multi-Camera Monitor initialized!")
    
    def analyze_frame(self, frame, cam_id):
        """Analyze a single frame for safety concerns"""
        results = self.model(frame, verbose=False)
        
        persons = []
        for detection in results:
            for box in detection.boxes:
                if int(box.cls[0]) == 0 and float(box.conf[0]) > 0.5:
                    persons.append({
                        'bbox': box.xyxy[0].cpu().numpy(),
                        'confidence': float(box.conf[0])
                    })
        
        # Calculate brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        is_dark = brightness < 80
        
        num_persons = len(persons)
        
        # Risk assessment
        severity = "LOW"
        alert_type = "Normal Activity"
        
        if num_persons == 1 and brightness < 50:
            severity = "CRITICAL"
            alert_type = "Lone Woman - Very Dark Area"
        elif num_persons == 1 and is_dark:
            severity = "HIGH"
            alert_type = "Lone Woman - Dark Area"
        elif num_persons == 2 and is_dark:
            severity = "HIGH"
            alert_type = "Two Persons - Dark Area"
        elif num_persons == 1:
            severity = "MEDIUM"
            alert_type = "Lone Woman Detected"
        elif num_persons >= 3:
            severity = "LOW"
            alert_type = "Multiple Persons"
        
        return {
            'person_count': num_persons,
            'severity': severity,
            'alert_type': alert_type,
            'brightness': brightness,
            'is_dark': is_dark,
            'persons': persons
        }
    
    def camera_worker(self, cam_id, camera_config):
        """Worker thread for processing a single camera"""
        print(f"📹 Starting camera: {cam_id} - {camera_config['name']}")
        
        cap = cv2.VideoCapture(camera_config['source'])
        
        if not cap.isOpened():
            print(f"❌ Failed to open camera: {cam_id}")
            self.camera_stats[cam_id]['status'] = 'error'
            return
        
        self.camera_stats[cam_id]['status'] = 'running'
        frame_count = 0
        last_alert_time = 0
        alert_cooldown = 30  # seconds
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print(f"⚠️ Camera {cam_id} - End of stream")
                    break
                
                frame_count += 1
                self.camera_stats[cam_id]['frames_processed'] = frame_count
                
                # Process every 30 frames
                if frame_count % 30 == 0:
                    analysis = self.analyze_frame(frame, cam_id)
                    
                    # Send alert if needed
                    current_time = time.time()
                    if (analysis['severity'] in ['CRITICAL', 'HIGH', 'MEDIUM'] and 
                        current_time - last_alert_time > alert_cooldown):
                        
                        alert_data = {
                            'place': camera_config['name'],
                            'type': analysis['alert_type'],
                            'severity': analysis['severity'],
                            'lat': camera_config['lat'],
                            'lng': camera_config['lng'],
                            'time': datetime.now().isoformat(),
                            'description': f"{analysis['person_count']} person(s) detected",
                            'cameraId': cam_id.upper(),
                            'personCount': analysis['person_count'],
                            'lighting': 'Dark' if analysis['is_dark'] else 'Well-lit',
                            'brightnessLevel': int(analysis['brightness'])
                        }
                        
                        self.alert_queue.put(alert_data)
                        last_alert_time = current_time
                        self.camera_stats[cam_id]['alerts_sent'] += 1
                        self.camera_stats[cam_id]['last_alert'] = datetime.now().strftime('%H:%M:%S')
                    
                    # Print status
                    print(f"[{cam_id}] Frame {frame_count} | {analysis['alert_type']} | "
                          f"Persons: {analysis['person_count']}")
                
                time.sleep(0.01)  # Small delay to prevent CPU overload
        
        finally:
            cap.release()
            self.camera_stats[cam_id]['status'] = 'stopped'
            print(f"🛑 Camera {cam_id} stopped")
    
    def alert_sender_worker(self):
        """Worker thread for sending alerts to backend"""
        print("📡 Alert sender worker started")
        
        while self.running:
            try:
                # Get alert from queue (blocking with timeout)
                alert_data = self.alert_queue.get(timeout=1)
                
                # Send to backend
                response = requests.post(
                    f"{self.backend_url}/send-alert",
                    json=alert_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    print(f"🚨 ALERT SENT: [{alert_data['severity']}] "
                          f"{alert_data['cameraId']} - {alert_data['place']}")
                else:
                    print(f"❌ Failed to send alert: {response.status_code}")
                
                self.alert_queue.task_done()
                
            except Exception as e:
                if "Empty" not in str(e):
                    print(f"❌ Error in alert sender: {e}")
        
        print("🛑 Alert sender stopped")
    
    def print_status_dashboard(self):
        """Print live status dashboard"""
        while self.running:
            # Clear screen (works on most terminals)
            print("\033[2J\033[H")
            
            print("=" * 70)
            print("  📹 MULTI-CAMERA MONITORING SYSTEM - LIVE STATUS")
            print("=" * 70)
            print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Pending Alerts: {self.alert_queue.qsize()}")
            print("=" * 70)
            
            for cam_id, config in self.cameras.items():
                if config['enabled']:
                    stats = self.camera_stats[cam_id]
                    status_icon = "🟢" if stats['status'] == 'running' else "🔴"
                    
                    print(f"\n{status_icon} {cam_id.upper()} - {config['name']}")
                    print(f"   Status: {stats['status']}")
                    print(f"   Frames: {stats['frames_processed']}")
                    print(f"   Alerts: {stats['alerts_sent']}")
                    print(f"   Last Alert: {stats['last_alert'] or 'None'}")
            
            print("\n" + "=" * 70)
            print("Press Ctrl+C to stop monitoring")
            print("=" * 70)
            
            time.sleep(5)  # Update every 5 seconds
    
    def start_monitoring(self):
        """Start monitoring all enabled cameras"""
        print("\n🚀 Starting Multi-Camera Monitoring System...")
        print("=" * 60)
        
        # Check backend connection
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend server connected")
            else:
                print("⚠️ Backend server returned error")
        except:
            print("❌ Cannot connect to backend server!")
            print(f"   Make sure server is running at {self.backend_url}")
            return
        
        self.running = True
        threads = []
        
        # Start alert sender worker
        alert_thread = threading.Thread(target=self.alert_sender_worker, daemon=True)
        alert_thread.start()
        threads.append(alert_thread)
        
        # Start camera workers
        for cam_id, config in self.cameras.items():
            if config['enabled']:
                thread = threading.Thread(
                    target=self.camera_worker,
                    args=(cam_id, config),
                    daemon=True
                )
                thread.start()
                threads.append(thread)
                time.sleep(0.5)  # Stagger camera starts
        
        print("\n✅ All cameras started!")
        print("=" * 60)
        
        # Start status dashboard
        try:
            self.print_status_dashboard()
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping all cameras...")
            self.running = False
            
            # Wait for threads to finish
            for thread in threads:
                thread.join(timeout=2)
            
            print("✅ All cameras stopped successfully")
    
    def configure_cameras(self):
        """Interactive camera configuration"""
        print("\n" + "=" * 60)
        print("  🎥 CAMERA CONFIGURATION")
        print("=" * 60)
        
        for cam_id, config in self.cameras.items():
            print(f"\n{cam_id.upper()} - {config['name']}")
            print(f"   Source: {config['source']}")
            print(f"   Currently: {'ENABLED' if config['enabled'] else 'DISABLED'}")
            
            response = input(f"   Enable this camera? (y/n, Enter=keep current): ").strip().lower()
            
            if response == 'y':
                config['enabled'] = True
                print("   ✅ Enabled")
            elif response == 'n':
                config['enabled'] = False
                print("   ❌ Disabled")
            
            # Option to change source
            if config['enabled']:
                change_source = input(f"   Change source? (y/n): ").strip().lower()
                if change_source == 'y':
                    new_source = input(f"   Enter new source (0 for webcam, path for video): ").strip()
                    if new_source.isdigit():
                        config['source'] = int(new_source)
                    else:
                        config['source'] = new_source
                    print(f"   ✅ Source updated to: {config['source']}")
        
        enabled_count = sum(1 for c in self.cameras.values() if c['enabled'])
        print(f"\n📊 Total enabled cameras: {enabled_count}")
        
        if enabled_count == 0:
            print("⚠️  WARNING: No cameras enabled!")
    
    def test_alert(self):
        """Send test alert from a specific camera"""
        print("\n🧪 Sending test alert...")
        
        # Use first enabled camera
        test_cam = None
        for cam_id, config in self.cameras.items():
            if config['enabled']:
                test_cam = (cam_id, config)
                break
        
        if not test_cam:
            print("❌ No cameras enabled for testing")
            return
        
        cam_id, config = test_cam
        
        test_alert = {
            'place': config['name'],
            'type': 'TEST ALERT - System Check',
            'severity': 'HIGH',
            'lat': config['lat'],
            'lng': config['lng'],
            'time': datetime.now().isoformat(),
            'description': 'This is a test alert from multi-camera system',
            'cameraId': cam_id.upper(),
            'personCount': 1,
            'lighting': 'Dark',
            'brightnessLevel': 45
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/send-alert",
                json=test_alert,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Test alert sent from {cam_id.upper()}")
            else:
                print(f"❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def save_configuration(self):
        """Save camera configuration to file"""
        config_file = "camera_config.json"
        
        with open(config_file, 'w') as f:
            json.dump(self.cameras, f, indent=2)
        
        print(f"✅ Configuration saved to {config_file}")
    
    def load_configuration(self):
        """Load camera configuration from file"""
        config_file = "camera_config.json"
        
        try:
            with open(config_file, 'r') as f:
                self.cameras = json.load(f)
            print(f"✅ Configuration loaded from {config_file}")
        except FileNotFoundError:
            print(f"⚠️  No saved configuration found")
        except Exception as e:
            print(f"❌ Error loading config: {e}")


def main():
    """Main menu for multi-camera system"""
    print("=" * 60)
    print("  🎥 MULTI-CAMERA WOMEN SAFETY MONITORING SYSTEM")
    print("=" * 60)
    
    monitor = MultiCameraMonitor()
    
    # Try to load saved configuration
    monitor.load_configuration()
    
    while True:
        print("\n" + "=" * 60)
        print("Main Menu:")
        print("1. Configure Cameras")
        print("2. Start Monitoring (All Enabled Cameras)")
        print("3. Send Test Alert")
        print("4. View Current Configuration")
        print("5. Save Configuration")
        print("6. Exit")
        print("=" * 60)
        
        choice = input("Enter choice (1-6): ").strip()
        
        if choice == '1':
            monitor.configure_cameras()
        
        elif choice == '2':
            monitor.start_monitoring()
        
        elif choice == '3':
            monitor.test_alert()
        
        elif choice == '4':
            print("\n📋 Current Camera Configuration:")
            for cam_id, config in monitor.cameras.items():
                status = "✅ ENABLED" if config['enabled'] else "❌ DISABLED"
                print(f"\n{cam_id.upper()} - {status}")
                print(f"   Name: {config['name']}")
                print(f"   Source: {config['source']}")
                print(f"   Location: ({config['lat']}, {config['lng']})")
        
        elif choice == '5':
            monitor.save_configuration()
        
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()