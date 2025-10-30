"""
Quick System Tester for Women Safety Monitoring System
Run this to verify everything is working correctly
"""

import requests
import time
from datetime import datetime

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_backend_health():
    """Check if backend server is running"""
    print_header("STEP 1: Checking Backend Server")
    
    try:
        response = requests.get("http://localhost:3000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend server is RUNNING")
            print(f"   - Uptime: {int(data['uptime'])} seconds")
            print(f"   - Active alerts: {data['alertCount']}")
            print(f"   - Connected dashboards: {data['connectedClients']}")
            return True
        else:
            print("❌ Backend responded with error")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend server is NOT running")
        print("   Please start it with: cd backend && node server.js")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {e}")
        return False

def send_test_alerts():
    """Send multiple test alerts to the backend"""
    print_header("STEP 2: Sending Test Alerts")
    
    test_alerts = [
        {
            "place": "Test Location - Park Street",
            "type": "CRITICAL TEST ALERT",
            "severity": "CRITICAL",
            "lat": 11.1085,
            "lng": 77.3411,
            "time": datetime.now().isoformat(),
            "description": "This is a CRITICAL test alert - Lone woman in dark area",
            "cameraId": "TEST-CAM-001",
            "personCount": 1,
            "lighting": "Dark"
        },
        {
            "place": "Test Location - Market Road",
            "type": "HIGH PRIORITY TEST",
            "severity": "HIGH",
            "lat": 11.1095,
            "lng": 77.3421,
            "time": datetime.now().isoformat(),
            "description": "This is a HIGH priority test alert - Suspicious activity",
            "cameraId": "TEST-CAM-002",
            "personCount": 2,
            "lighting": "Well-lit"
        },
        {
            "place": "Test Location - Station Road",
            "type": "MEDIUM RISK TEST",
            "severity": "MEDIUM",
            "lat": 11.1075,
            "lng": 77.3401,
            "time": datetime.now().isoformat(),
            "description": "This is a MEDIUM risk test alert - Lone woman detected",
            "cameraId": "TEST-CAM-003",
            "personCount": 1,
            "lighting": "Well-lit"
        }
    ]
    
    success_count = 0
    
    for i, alert in enumerate(test_alerts, 1):
        print(f"\n📤 Sending test alert {i}/{len(test_alerts)}...")
        print(f"   Severity: {alert['severity']}")
        print(f"   Location: {alert['place']}")
        
        try:
            response = requests.post(
                "http://localhost:3000/send-alert",
                json=alert,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"   ✅ Alert sent successfully!")
                success_count += 1
            else:
                print(f"   ❌ Failed to send alert: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Wait 1 second between alerts
    
    print(f"\n📊 Results: {success_count}/{len(test_alerts)} alerts sent successfully")
    return success_count == len(test_alerts)

def check_dashboard_access():
    """Check if dashboard is accessible"""
    print_header("STEP 3: Checking Dashboard Access")
    
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard is accessible at http://localhost:3000")
            print("   You can now open it in your browser and login")
            return True
        else:
            print("❌ Dashboard returned error code")
            return False
    except Exception as e:
        print(f"❌ Cannot access dashboard: {e}")
        return False

def get_all_alerts():
    """Retrieve and display all alerts"""
    print_header("STEP 4: Retrieving All Alerts")
    
    try:
        response = requests.get("http://localhost:3000/alerts", timeout=5)
        if response.status_code == 200:
            data = response.json()
            count = data['count']
            print(f"✅ Retrieved {count} alerts from server")
            
            if count > 0:
                print("\n📋 Recent Alerts:")
                for i, alert in enumerate(data['alerts'][:5], 1):
                    print(f"\n   {i}. [{alert['severity']}] {alert['place']}")
                    print(f"      Type: {alert['type']}")
                    print(f"      Camera: {alert['cameraId']}")
            
            return True
        else:
            print("❌ Failed to retrieve alerts")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def clear_test_alerts():
    """Ask user if they want to clear test alerts"""
    print_header("STEP 5: Cleanup")
    
    response = input("\nDo you want to clear all test alerts? (y/n): ").strip().lower()
    
    if response == 'y':
        try:
            result = requests.post("http://localhost:3000/clear-alerts", timeout=5)
            if result.status_code == 200:
                print("✅ All alerts cleared successfully")
                return True
            else:
                print("❌ Failed to clear alerts")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    else:
        print("ℹ️  Alerts kept on dashboard")
        return True

def main():
    """Main test sequence"""
    print("\n" + "=" * 60)
    print("  🧪 WOMEN SAFETY SYSTEM - AUTOMATED TESTER")
    print("=" * 60)
    print("\nThis script will test your entire system setup")
    print("Make sure the backend server is running first!\n")
    
    input("Press Enter to start testing...")
    
    # Run all tests
    results = {
        "Backend Health": check_backend_health(),
        "Send Alerts": False,
        "Dashboard Access": False,
        "Retrieve Alerts": False,
        "Cleanup": False
    }
    
    if results["Backend Health"]:
        results["Send Alerts"] = send_test_alerts()
        results["Dashboard Access"] = check_dashboard_access()
        results["Retrieve Alerts"] = get_all_alerts()
        results["Cleanup"] = clear_test_alerts()
    
    # Final summary
    print_header("FINAL TEST RESULTS")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n📊 Overall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 SUCCESS! Your system is working perfectly!")
        print("\nNext steps:")
        print("1. Open http://localhost:3000 in your browser")
        print("2. Login with: police / 1234")
        print("3. Run camera_monitor.py to start AI detection")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("- Make sure backend is running: cd backend && node server.js")
        print("- Check if port 3000 is available")
        print("- Verify all npm packages are installed")

if __name__ == "__main__":
    main()