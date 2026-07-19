import subprocess
import re
import threading
import time

class BluetoothManager:
    def __init__(self):
        self.discovered_devices = []
        self._is_scanning = False

    def start_scan(self, duration=8):
        """Runs a Bluetooth scan in a background thread to prevent blocking Flask."""
        if self._is_scanning:
            return
        
        def scan_worker():
            self._is_scanning = True
            self.discovered_devices = []
            try:
                # Trigger bluetoothctl scan engine
                proc = subprocess.Popen(['bluetoothctl', 'scan', 'on'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                time.sleep(duration)
                proc.terminate()
                
                # Fetch all known/discovered devices from the controller cache
                result = subprocess.run(['bluetoothctl', 'devices'], capture_output=True, text=True)
                devices = []
                # Match format: "Device AA:BB:CC:DD:EE:FF Device_Name"
                matches = re.findall(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', result.stdout)
                
                for mac, name in matches:
                    if name.strip() and not name.startswith("AA-BB-"): # filter out un-named devices
                        devices.append({"mac": mac, "name": name.strip()})
                
                self.discovered_devices = devices
            except Exception as e:
                print(f"[Bluetooth Error] Scanning failure: {e}")
            finally:
                self._is_scanning = False

        threading.Thread(target=scan_worker, daemon=True).start()

    def get_scan_status(self):
        return {
            "is_scanning": self._is_scanning,
            "devices": self.discovered_devices
        }

    def connect_device(self, mac_address):
        """Pairs, trusts, and connects to a specific target MAC address."""
        try:
            print(f"[Bluetooth] Initiating connection targeting: {mac_address}")
            # Pair -> Trust -> Connect flow sequence
            subprocess.run(['bluetoothctl', 'pair', mac_address], capture_output=True, timeout=10)
            subprocess.run(['bluetoothctl', 'trust', mac_address], capture_output=True, timeout=5)
            res = subprocess.run(['bluetoothctl', 'connect', mac_address], capture_output=True, text=True, timeout=15)
            
            if "Connection successful" in res.stdout or "Successful" in res.stdout:
                return {"status": "success", "message": "Connected successfully!"}
            
            # Double check via devices inquiry if it registered anyway
            info = subprocess.run(['bluetoothctl', 'info', mac_address], capture_output=True, text=True)
            if "Connected: yes" in info.stdout:
                return {"status": "success", "message": "Connected!"}
                
            return {"status": "error", "message": "Failed establishing link."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect_device(self, mac_address):
        """Disconnects a targeting bluetooth accessory profile safely."""
        try:
            subprocess.run(['bluetoothctl', 'disconnect', mac_address], capture_output=True, timeout=10)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}