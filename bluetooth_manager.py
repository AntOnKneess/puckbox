import subprocess
import re
import threading
import time
import logging
import sys

logger = logging.getLogger("BluetoothManager")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [BluetoothEngine] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BluetoothManager:
    def __init__(self):
        self.discovered_devices = []
        self._is_scanning = False
        self._initialize_controller()

    def _initialize_controller(self):
        """Ensures the hardware adapter is powered on and ready to communicate."""
        try:
            logger.debug("Executing kernel-level rfkill unblock...")
            subprocess.run(['sudo', 'rfkill', 'unblock', 'bluetooth'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            
            logger.debug("Powering up the active adapter and provisioning pairing agents...")
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
        """Runs a timeout-bounded interactive hardware scan to populate the system cache."""
        if self._is_scanning:
            logger.warning("Scan requested, but a discovery thread loop is already running.")
            return
        
        def scan_worker():
            self._is_scanning = True
            self.discovered_devices = []
            found_registry = {}
            
            logger.info(f"Starting timeout-bounded Bluetooth discovery scan ({duration}s)...")
            self._initialize_controller()
            
            try:
                # Use the native --timeout argument to force bluetoothctl to keep the session alive
                # and populate the bluez background daemon device memory map.
                logger.debug(f"Triggering interactive backend scan for {duration} seconds...")
                subprocess.run(
                    ['bluetoothctl', '--timeout', str(duration), 'scan', 'on'],
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                
                # Give the stack a brief moment to settle down after the scan finishes
                time.sleep(0.5)
                
                # Fetch ALL nearby discovered devices directly from the system's memory cache
                # Fetch ALL nearby discovered devices directly from the system's memory cache
                logger.debug("Extracting gathered device tables from system cache...")
                cache_res = subprocess.run(['bluetoothctl', 'devices'], capture_output=True, text=True)
                
                # Parse standard format: "Device AA:BB:CC:DD:EE:FF Device_Name"
                cache_matches = re.findall(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', cache_res.stdout)
                
                for mac, name in cache_matches:
                    name_clean = name.strip()
                    
                    # Check if the name is missing, blank, or just a repeat of the MAC address
                    is_placeholder = (
                        not name_clean or 
                        ":" in name_clean or 
                        "-" in name_clean or 
                        bool(re.match(r'^([0-9A-Fa-f]{2}[:.-]){5}[0-9A-Fa-f]{2}$', name_clean))
                    )
                    
                    # If it's a placeholder, display the MAC address so the user can still click it!
                    display_name = mac if is_placeholder else name_clean
                    
                    logger.info(f"Target identified and captured: '{display_name}' [{mac}]")
                    found_registry[mac] = display_name
                        
            except Exception as e:
                logger.exception("Exception encountered during background scan collection:")
            finally:
                self.discovered_devices = [{"mac": mac, "name": name} for mac, name in found_registry.items()]
                self._is_scanning = False
                logger.info(f"Scan complete. Found a total of {len(self.discovered_devices)} valid audio targets.")

        threading.Thread(target=scan_worker, daemon=True).start()

    def get_scan_status(self):
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