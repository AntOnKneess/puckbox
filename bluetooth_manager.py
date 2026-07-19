import subprocess
import re
import threading
import time

class BluetoothManager:
    def __init__(self):
        self.discovered_devices = []
        self._is_scanning = False
        self._initialize_controller()

    def _initialize_controller(self):
        """Ensures the hardware adapter is powered on and ready to communicate."""
        try:
            # Force target adapter power state and generic pairing agent registration
            subprocess.run(['bluetoothctl', 'power', 'on'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['bluetoothctl', 'agent', 'on'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['bluetoothctl', 'default-agent'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Bluetooth Init Warning] Basic stack provisioning failed: {e}")

    def start_scan(self, duration=10):
        """Runs an interactive scanner worker inside a background process thread."""
        if self._is_scanning:
            return
        
        def scan_worker():
            self._is_scanning = True
            self.discovered_devices = []
            
            # Make sure power is explicitly on before we attempt scanning
            self._initialize_controller()
            
            # Store unique MAC detections to prevent list duplication
            found_registry = {}
            
            try:
                print("[Bluetooth Manager] Launching active discovery pipe...")
                # Run bluetoothctl scan as an interactive long-running stdout subprocess channel
                proc = subprocess.Popen(
                    ['bluetoothctl', 'scan', 'on'], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    bufsize=1
                )
                
                # Listen to incoming stdout lines during the target scanning duration time frame
                start_time = time.time()
                while time.time() - start_time < duration:
                    # Non-blocking check shortcut line read
                    line = proc.stdout.readline()
                    if line:
                        # Inspect live discovery signatures: "[NEW] Device AA:BB:CC:DD:EE:FF HeadphoneName"
                        match = re.search(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', line)
                        if match:
                            mac, name = match.group(1), match.group(2).strip()
                            # Strip raw address formats if name falls back to address hex
                            if name and ":" not in name and "-" not in name:
                                found_registry[mac] = name
                    else:
                        time.sleep(0.1)
                        
                proc.terminate()
                proc.wait()
                
                # --- FALLBACK CHECK: Query the internal stack device registry cache ---
                cache_res = subprocess.run(['bluetoothctl', 'devices'], capture_output=True, text=True)
                cache_matches = re.findall(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', cache_res.stdout)
                for mac, name in cache_matches:
                    name_clean = name.strip()
                    if name_clean and ":" not in name_clean and "-" not in name_clean:
                        found_registry[mac] = name_clean
                        
            except Exception as e:
                print(f"[Bluetooth Error] Thread process loop dropped: {e}")
            finally:
                # Convert our unique tracking registry to standard UI output arrays
                self.discovered_devices = [{"mac": mac, "name": name} for mac, name in found_registry.items()]
                self._is_scanning = False
                print(f"[Bluetooth Manager] Scanning finished. Registered {len(self.discovered_devices)} targets.")

        threading.Thread(target=scan_worker, daemon=True).start()

    def get_scan_status(self):
        return {
            "is_scanning": self._is_scanning,
            "devices": self.discovered_devices
        }

    def connect_device(self, mac_address):
        try:
            print(f"[Bluetooth] Connecting target address: {mac_address}")
            # Ensure agent handling state parameters are initialized
            self._initialize_controller()
            
            subprocess.run(['bluetoothctl', 'pair', mac_address], capture_output=True, timeout=12)
            subprocess.run(['bluetoothctl', 'trust', mac_address], capture_output=True, timeout=8)
            res = subprocess.run(['bluetoothctl', 'connect', mac_address], capture_output=True, text=True, timeout=15)
            
            if "Connection successful" in res.stdout or "Successful" in res.stdout:
                return {"status": "success", "message": "Connected successfully!"}
            
            # Double check active link verification state metrics
            info = subprocess.run(['bluetoothctl', 'info', mac_address], capture_output=True, text=True)
            if "Connected: yes" in info.stdout:
                return {"status": "success", "message": "Connected!"}
                
            return {"status": "error", "message": "Failed establishing link setup. Verify peripheral is in pairing mode."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect_device(self, mac_address):
        try:
            subprocess.run(['bluetoothctl', 'disconnect', mac_address], capture_output=True, timeout=10)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}