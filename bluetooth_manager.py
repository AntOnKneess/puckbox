import subprocess
import re
import threading
import time
import logging
import sys

# --- CONFIGURING LOGGER OUTPUT CHANNELS ---
# Sets up human-readable timestamps and levels to print clearly to stdout
logger = logging.getLogger("BluetoothManager")
logger.setLevel(logging.DEBUG)

# Prevents duplicating log handlers if the app reloads during debugging
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [BluetoothEngine] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BluetoothManager:
    def __init__(self):
        self.discovered_devices = []
        self._is_scanning = False
        logger.info("Initializing system Bluetooth controller...")
        self._initialize_controller()

    def _initialize_controller(self):
        """Ensures the hardware adapter is powered on and ready to communicate."""
        try:
            logger.debug("Executing kernel-level rfkill unblock...")
            subprocess.run(['sudo', 'rfkill', 'unblock', 'bluetooth'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            
            logger.debug("Powering up the active adapter and provisioning pairing agents...")
            # Capture errors directly from system power commands to catch org.bluez.error states
            power_cmd = subprocess.run(['bluetoothctl', 'power', 'on'], capture_output=True, text=True, timeout=5)
            if power_cmd.returncode != 0:
                logger.error(f"Failed to power on adapter. stderr: {power_cmd.stderr.strip()}")
            else:
                logger.info("Bluetooth adapter successfully powered on.")
                
            subprocess.run(['bluetoothctl', 'agent', 'on'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['bluetoothctl', 'default-agent'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.exception("Unexpected structural failure during controller provisioning:")

    def start_scan(self, duration=10):
        """Runs an interactive scanner worker inside a background process thread."""
        if self._is_scanning:
            logger.warning("Scan requested, but a discovery thread loop is already running.")
            return
        
        def scan_worker():
            self._is_scanning = True
            self.discovered_devices = []
            found_registry = {}
            
            logger.info(f"Starting background Bluetooth discovery scan ({duration}s duration)...")
            self._initialize_controller()
            
            try:
                logger.debug("Opening interactive unbuffered bluetoothctl pipe stream...")
                # Prefix the array command vector with stdbuf -oL 
                proc = subprocess.Popen(
                    ['stdbuf', '-oL', 'bluetoothctl', 'scan', 'on'], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    bufsize=1
                )
                
                start_time = time.time()
                while time.time() - start_time < duration:
                    line = proc.stdout.readline()
                    if line:
                        # Scan live discovery lines out of stdout logs
                        match = re.search(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', line)
                        if match:
                            mac, name = match.group(1), match.group(2).strip()
                            if name and ":" not in name and "-" not in name:
                                if mac not in found_registry:
                                    logger.info(f"Discovered new device in range: '{name}' [{mac}]")
                                found_registry[mac] = name
                    else:
                        time.sleep(0.1)
                        
                logger.debug("Terminating active scanning process...")
                proc.terminate()
                proc.wait()
                
                # Check for standard error lines if the process failed early
                stderr_output = proc.stderr.read()
                if stderr_output.strip():
                    logger.error(f"Subprocess scanner returned errors: {stderr_output.strip()}")
                
                # --- FALLBACK SYSTEM CONTROLLER CACHE CHECK ---
                logger.debug("Querying local bluetoothctl cache for previously paired devices...")
                cache_res = subprocess.run(['bluetoothctl', 'devices'], capture_output=True, text=True)
                cache_matches = re.findall(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', cache_res.stdout)
                for mac, name in cache_matches:
                    name_clean = name.strip()
                    if name_clean and ":" not in name_clean and "-" not in name_clean:
                        if mac not in found_registry:
                            logger.debug(f"Pulled device from cache: '{name_clean}' [{mac}]")
                        found_registry[mac] = name_clean
                        
            except Exception as e:
                logger.exception("Fatal exception encountered during background scan worker loop:")
            finally:
                self.discovered_devices = [{"mac": mac, "name": name} for mac, name in found_registry.items()]
                self._is_scanning = False
                logger.info(f"Scan complete. Found a total of {len(self.discovered_devices)} valid audio targets.")

        threading.Thread(target=scan_worker, daemon=True).start()

    def get_scan_status(self):
        logger.debug(f"Web UI polled status. Scanning={self._is_scanning}, CacheCount={len(self.discovered_devices)}")
        return {
            "is_scanning": self._is_scanning,
            "devices": self.discovered_devices
        }

    def connect_device(self, mac_address):
        try:
            logger.info(f"Attempting connection sequence targeting MAC: {mac_address}")
            self._initialize_controller()
            
            logger.debug(f"Sending pairing request to {mac_address}...")
            pair_res = subprocess.run(['bluetoothctl', 'pair', mac_address], capture_output=True, text=True, timeout=12)
            logger.debug(f"Pairing output: {pair_res.stdout.strip()}")
            
            subprocess.run(['bluetoothctl', 'trust', mac_address], capture_output=True, timeout=8)
            
            logger.debug(f"Sending final connection instruction link payload...")
            res = subprocess.run(['bluetoothctl', 'connect', mac_address], capture_output=True, text=True, timeout=15)
            logger.debug(f"Connection output: {res.stdout.strip()}")
            
            if "Connection successful" in res.stdout or "Successful" in res.stdout:
                logger.info(f"Successfully connected to hardware device: {mac_address}")
                return {"status": "success", "message": "Connected successfully!"}
            
            info = subprocess.run(['bluetoothctl', 'info', mac_address], capture_output=True, text=True)
            if "Connected: yes" in info.stdout:
                logger.info(f"Connection confirmed via stack info review for {mac_address}")
                return {"status": "success", "message": "Connected!"}
                
            logger.error(f"Link profile negotiation failed for device {mac_address}")
            return {"status": "error", "message": "Failed establishing link setup. Verify peripheral is in pairing mode."}
        except subprocess.TimeoutExpired:
            logger.error(f"Connection routine timed out while waiting for hardware target {mac_address}")
            return {"status": "error", "message": "Connection attempt timed out."}
        except Exception as e:
            logger.exception(f"Unhandled exception establishing link interface with {mac_address}:")
            return {"status": "error", "message": str(e)}

    def disconnect_device(self, mac_address):
        try:
            logger.info(f"Disconnecting peripheral profile {mac_address}...")
            subprocess.run(['bluetoothctl', 'disconnect', mac_address], capture_output=True, timeout=10)
            return {"status": "success"}
        except Exception as e:
            logger.exception(f"Error dropping profile link for device {mac_address}:")
            return {"status": "error", "message": str(e)}