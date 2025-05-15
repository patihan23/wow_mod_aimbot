import ctypes
import struct
import math
import time
import os
import configparser
import json
from pymem import Pymem
from pymem.process import module_from_name

# Windows API for reading memory
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = ctypes.c_bool

# Vector3 class for handling 3D coordinates
class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z
    
    def distance(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)
    
    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

class MemoryReader:
    def __init__(self, config_file=None, process_name=None):
        self.pm = None
        self.game_module = None
        self.offsets = {}
        self.process_name = process_name  # Allow passing process name directly
        
        # If no config file provided, use the absolute path
        if config_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(base_dir, 'config', 'memory_config.json')
        
        self.load_config(config_file)
        self.connect_to_game()
    
    def load_config(self, config_file):
        """Load memory offsets and other configuration data"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Convert string hex values to integers
                self.offsets = {}
                for key, value in config['offsets'].items():
                    if isinstance(value, str) and value.startswith("0x"):
                        self.offsets[key] = int(value, 16)
                    else:
                        self.offsets[key] = value
                        
                # Only set process_name from config if not already set in constructor
                if self.process_name is None and 'process_name' in config:
                    self.process_name = config['process_name']
        except Exception as e:
            print(f"Error loading config: {e}")
            # Default values as a fallback
            if self.process_name is None:
                self.process_name = "WorldOfWarships64.exe"
            self.offsets = {
                "player_base": 0x8ABCD123,  # Placeholder offset
                "player_pos_offset": 0x150,
                "entity_list": 0x9ABCDEF0,  # Placeholder offset
                "entity_size": 0x280,
                "entity_pos_offset": 0x180,
                "entity_velocity_offset": 0x190,
                "max_entities": 32,
                "shell_info_base": 0x8BBCD456  # Placeholder offset
            }
    
    def connect_to_game(self):
        """Connect to the World of Warships process"""
        possible_game_processes = ["WorldOfWarships.exe", "WoWs.exe", "WoWsLauncher.exe", "WorldOfWarships64.exe", "wows.exe"]
        
        # First try the process name from config
        try:
            print(f"Attempting to connect to {self.process_name}...")
            self.pm = Pymem(self.process_name)
            self.game_module = module_from_name(self.pm.process_handle, self.process_name).lpBaseOfDll
            print(f"Successfully connected to {self.process_name}")
            print(f"Base address: {hex(self.game_module)}")
            return
        except Exception as e:
            print(f"Failed to connect to {self.process_name}: {e}")
            
        # Try other possible process names
        print("Trying alternative process names...")
        for process_name in possible_game_processes:
            if process_name == self.process_name:
                continue  # Already tried this one
                
            try:
                print(f"Attempting to connect to {process_name}...")
                self.pm = Pymem(process_name)
                self.game_module = module_from_name(self.pm.process_handle, process_name).lpBaseOfDll
                print(f"Successfully connected to {process_name}")
                print(f"Base address: {hex(self.game_module)}")
                
                # Update process name for future reference
                self.process_name = process_name
                
                # Update the config file with the new process name
                try:
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    config_file = os.path.join(base_dir, 'config', 'memory_config.json')
                    
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    config['process_name'] = process_name
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=4)
                    print(f"Updated configuration with process name: {process_name}")
                except Exception as e:
                    print(f"Warning: Could not update configuration: {e}")
                
                return
            except Exception as e:
                print(f"Failed to connect to {process_name}: {e}")
                
        # If we get here, all attempts failed
        print("ERROR: Could not find any World of Warships process")
        print("Please make sure the game is running. Check these processes:")
        for proc in possible_game_processes:
            print(f"  - {proc}")
        self.pm = None
        self.game_module = None
    
    def read_memory(self, address, data_type):
        """Read memory at specified address with the given data type"""
        if not self.pm:
            print("ERROR: Not connected to game process")
            if data_type == "vector3":
                return Vector3(0, 0, 0)  # Return zero vector to prevent crashes
            return 0  # Return zero for numeric types to prevent crashes

        try:
            if data_type == "float":
                return self.pm.read_float(address)
            elif data_type == "int":
                return self.pm.read_int(address)
            elif data_type == "vector3":
                x = self.pm.read_float(address)
                y = self.pm.read_float(address + 4)
                z = self.pm.read_float(address + 8)
                return Vector3(x, y, z)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
        except Exception as e:
            print(f"Error reading memory at {hex(address)}: {e}")
            return None
    
    def get_player_position(self):
        """Get the player's current position"""
        try:
            player_base = self.game_module + self.offsets["player_base"]
            pos_offset = self.offsets["player_pos_offset"]
            
            # Check if we're dealing with placeholder addresses
            if self.offsets["player_base"] in (0x4, "0x4"):
                print("\nWARNING: Using placeholder memory address for player position!")
                print("The current memory addresses in memory_config.json are examples only.")
                print("You would need to use memory_scanner.py to find the real addresses for your game version.")
                print("Returning a dummy position at center of map for demonstration purposes.\n")
                # Return a dummy position at center of map
                return Vector3(0, 0, 0)
            
            # Read the player position coordinates
            x = self.read_memory(player_base + pos_offset, "float")
            y = self.read_memory(player_base + pos_offset + 4, "float")
            z = self.read_memory(player_base + pos_offset + 8, "float")
            
            position = Vector3(x, y, z)
            
            # If position contains invalid values (could happen if addresses are wrong)
            if math.isnan(x) or math.isnan(y) or math.isnan(z) or abs(x) > 1e10 or abs(y) > 1e10 or abs(z) > 1e10:
                print("\nWARNING: Invalid position values detected!")
                print("This usually means the memory addresses are incorrect or outdated.")
                print("You should run memory_scanner.py to find updated addresses for your game version.")
                return Vector3(0, 0, 0)
            
            return position
        except Exception as e:
            print(f"Error getting player position: {e}")
            print("\nNOTE: This is likely because you're using placeholder memory addresses.")
            print("The current memory addresses in memory_config.json are examples only.")
            print("You would need to use memory_scanner.py to find the real addresses for your game version.")
            # Return a dummy position for demonstration
            return Vector3(0, 0, 0)
    
    def get_enemy_ships(self):
        """Get all enemy ships' positions and velocities"""
        try:
            # Check if we're using obviously placeholder addresses
            if str(self.offsets["entity_list"]).startswith("0x9ABC") or self.offsets["entity_list"] == 0:
                dummy_ships = True
            else:
                entity_list_base = self.game_module + self.offsets["entity_list"]
                dummy_ships = False
                # Try to read first entity to see if addresses are valid
                try:
                    entity_addr = entity_list_base + (0 * self.offsets["entity_size"])
                    test_read = self.pm.read_int(entity_addr)
                except Exception:
                    dummy_ships = True
            
            # If using placeholders, provide detailed feedback
            if dummy_ships:
                print("\nWARNING: Using placeholder memory addresses for enemy ships!")
                print("The current memory addresses in memory_config.json are placeholders.")
                print("You need to use memory_scanner.py to find the actual addresses for your game version.")
                print("Returning dummy enemy ships for demonstration purposes.\n")
            
            entity_list_base = self.game_module + self.offsets["entity_list"]
            enemy_ships = []
            
            # Real implementation - only runs if we have valid memory addresses
            for i in range(self.offsets["max_entities"]):
                entity_addr = entity_list_base + (i * self.offsets["entity_size"])
                
                # Check if entity exists and is enemy ship
                try:
                    is_valid = self.pm.read_int(entity_addr) != 0
                    if not is_valid:
                        continue
                    
                    # Get entity position
                    pos_addr = entity_addr + self.offsets["entity_pos_offset"]
                    position = self.read_memory(pos_addr, "vector3")
                    
                    # Get entity velocity
                    vel_addr = entity_addr + self.offsets["entity_velocity_offset"]
                    velocity = self.read_memory(vel_addr, "vector3")
                    
                    # Skip invalid position/velocity
                    if position is None or velocity is None:
                        continue
                    
                    # Add to enemy ships list
                    enemy_ships.append({
                        "position": position,
                        "velocity": velocity,
                        "address": entity_addr,
                        "name": f"Enemy Ship {i}",  # In a real implementation, you would read the name from memory
                        "team": "enemy",
                        "class": "Unknown"  # In a real implementation, you would read the ship class from memory
                    })
                except Exception as e:
                    # Silent failure for individual entities, just skip them
                    continue
            
            return enemy_ships
        except Exception as e:
            print(f"Error getting enemy ships: {e}")
            print("Returning empty list of enemy ships")
            return []
    
    def get_shell_speed(self):
        """Get the current selected shell speed"""
        try:
            # In a real implementation, this would read the shell speed based on
            # the currently selected weapon/shell type
            shell_info_addr = self.game_module + self.offsets["shell_info_base"]
            
            # Check if using placeholder addresses
            try:
                shell_speed = self.pm.read_float(shell_info_addr)
                return shell_speed
            except Exception as e:
                # If we get here, likely using placeholder addresses
                print(f"\nNotice: Could not read shell speed from memory: {e}")
                print("Using default shell speed value for demonstration purposes.")
                print("This is normal when using placeholder memory addresses.")
                
                # Use different shell types with different speeds for simulation
                import random
                # Shell types from World of Warships with realistic speeds
                shell_types = {
                    "HE_standard": 805.0,
                    "AP_standard": 830.0,
                    "HE_high_velocity": 950.0,
                    "AP_high_velocity": 980.0,
                    "SAP": 900.0,
                    "Torpedo": 65.0
                }
                
                # Get a random shell type for demonstration
                shell_type = random.choice(list(shell_types.keys()))
                shell_speed = shell_types[shell_type]
                
                print(f"Using {shell_type} with speed: {shell_speed} m/s\n")
                return shell_speed
        except Exception as e:
            print(f"Error in get_shell_speed: {e}")
            # Default value if an unexpected error occurs
            return 850.0  # Default shell speed in m/s
    
    def calculate_target_data(self, player_pos, enemy_ship):
        """Calculate distance and angle to target relative to player ship"""
        enemy_pos = enemy_ship["position"]
        distance = player_pos.distance(enemy_pos)
        
        # Calculate angle (simplified for this example)
        dx = enemy_pos.x - player_pos.x
        dy = enemy_pos.y - player_pos.y
        angle = math.atan2(dy, dx) * (180 / math.pi)
        
        return {
            "distance": distance,
            "angle": angle
        }
        
    def calculate_lead_position(self, player_pos, enemy_ship, shell_speed):
        """Calculate the lead position based on enemy velocity and shell travel time"""
        try:
            enemy_pos = enemy_ship["position"]
            enemy_vel = enemy_ship["velocity"]
            
            # Calculate distance
            distance = player_pos.distance(enemy_pos)
            
            # Estimated time for shell to reach target (simplified ballistics)
            time_to_target = distance / shell_speed
            
            # For longer distances, we might want to account for shell drop and air resistance
            # This is a simplified calculation - a real implementation would use more complex ballistics
            
            # Print debug info (useful when using placeholder addresses)
            if "name" in enemy_ship:
                ship_name = enemy_ship["name"]
                print(f"Target: {ship_name}")
                
                if "class" in enemy_ship:
                    print(f"Ship class: {enemy_ship['class']}")
            
            print(f"Distance to target: {distance:.1f} meters")
            print(f"Shell speed: {shell_speed:.1f} m/s")
            print(f"Estimated time to target: {time_to_target:.2f} seconds")
            print(f"Enemy velocity: {enemy_vel}")
            
            # Predict future position
            lead_pos = Vector3(
                enemy_pos.x + (enemy_vel.x * time_to_target),
                enemy_pos.y + (enemy_vel.y * time_to_target),
                enemy_pos.z + (enemy_vel.z * time_to_target)
            )
            
            print(f"Lead position calculated: {lead_pos}")
            
            return lead_pos
        except Exception as e:
            print(f"Error calculating lead position: {e}")
            # In case of an error, just return the current enemy position
            return enemy_ship["position"]
