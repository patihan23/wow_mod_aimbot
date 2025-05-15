import time
import threading
import keyboard
import win32api
import win32con
import configparser
import math
import os
from memory_reader import MemoryReader
from overlay import Overlay

class AimbotController:
    def __init__(self, config_file=None):        # Load configuration
        self.config = configparser.ConfigParser()
        if config_file is None:
            # Use absolute path to config file
            config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'aimbot_config.ini')
        self.config.read(config_file)
        
        # Get process name from memory config to ensure consistent process targeting
        try:
            import json
            memory_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'memory_config.json')
            with open(memory_config_path, 'r') as f:
                memory_config = json.load(f)
                process_name = memory_config.get('process_name', 'WorldOfWarships64.exe')
        except Exception as e:
            print(f"Warning: Could not read memory configuration: {e}")
            process_name = None
            
        # Initialize memory reader with process name
        self.memory_reader = MemoryReader(process_name=process_name)
        
        # Initialize overlay
        self.overlay = Overlay()
        
        # Aimbot state
        self.aimbot_active = False
        self.overlay_active = True
        
        # Hotkeys
        self.hotkey_aimbot_toggle = self.config.get('Hotkeys', 'aimbot_toggle', fallback='F5')
        self.hotkey_overlay_toggle = self.config.get('Hotkeys', 'overlay_toggle', fallback='F6')
        self.hotkey_exit = self.config.get('Hotkeys', 'exit', fallback='F12')
        
        # Register hotkeys
        keyboard.add_hotkey(self.hotkey_aimbot_toggle, self.toggle_aimbot)
        keyboard.add_hotkey(self.hotkey_overlay_toggle, self.toggle_overlay)
        keyboard.add_hotkey(self.hotkey_exit, self.exit_program)
        
        # Aimbot thread
        self.running = True
        self.aimbot_thread = threading.Thread(target=self.aimbot_loop)
        
        # ESP overlay data
        self.predicted_aim_points = []
    
    def toggle_aimbot(self):
        """Toggle aimbot on/off"""
        self.aimbot_active = not self.aimbot_active
        status = "ON" if self.aimbot_active else "OFF"
        print(f"Aimbot: {status}")
    
    def toggle_overlay(self):
        """Toggle overlay on/off"""
        self.overlay_active = not self.overlay_active
        status = "ON" if self.overlay_active else "OFF"
        print(f"Overlay: {status}")
        if not self.overlay_active:
            self.overlay.clear()
    
    def exit_program(self):
        """Exit the program"""
        self.running = False
        self.overlay.destroy()
        print("Exiting...")
    
    def move_mouse_to_position(self, screen_x, screen_y):
        """Move the mouse cursor to the specified screen position"""
        if not self.aimbot_active:
            return
            
        # Get current mouse position to calculate movement
        current_x, current_y = win32api.GetCursorPos()
        
        # Calculate movement needed
        move_x = screen_x - current_x
        move_y = screen_y - current_y
        
        # Move mouse cursor
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)
    
    def world_to_screen(self, world_pos):
        """Convert world position to screen coordinates
        Note: This is a simplified implementation - a real version would use
        the game's view matrix which would need to be read from memory
        """
        # Placeholder implementation - in a real implementation this would
        # use the game's view projection matrix
        # For this example we'll simulate a simple projection
        
        # Get screen size from configuration
        screen_width = int(self.config.get('Display', 'screen_width', fallback='1920'))
        screen_height = int(self.config.get('Display', 'screen_height', fallback='1080'))
        
        # Center of screen
        center_x = screen_width / 2
        center_y = screen_height / 2
        
        # Get player position
        player_pos = self.memory_reader.get_player_position()
        
        # Calculate relative position
        rel_x = world_pos.x - player_pos.x
        rel_y = world_pos.y - player_pos.y
        rel_z = world_pos.z - player_pos.z
        
        # Simple projection (this is highly simplified)
        # A real implementation would use the actual view matrix
        distance = math.sqrt(rel_x**2 + rel_y**2 + rel_z**2)
        scale_factor = 100.0 / max(1.0, distance)  # Adjust scale based on distance
        
        screen_x = center_x + (rel_x * scale_factor)
        screen_y = center_y + (rel_z * scale_factor)  # Using Z for vertical position
        
        return (int(screen_x), int(screen_y))
    
    def aimbot_loop(self):
        """Main aimbot logic loop"""
        while self.running:
            try:
                # Get player position
                player_pos = self.memory_reader.get_player_position()
                if not player_pos:
                    time.sleep(0.1)
                    continue
                
                # Get enemy ships
                enemy_ships = self.memory_reader.get_enemy_ships()
                if not enemy_ships:
                    time.sleep(0.1)
                    continue
                
                # Get shell speed
                shell_speed = self.memory_reader.get_shell_speed()
                
                # Clear previous aim points
                self.predicted_aim_points = []
                
                # Find closest enemy for aiming
                closest_enemy = None
                min_distance = float('inf')
                
                for enemy in enemy_ships:
                    target_data = self.memory_reader.calculate_target_data(player_pos, enemy)
                    distance = target_data["distance"]
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_enemy = enemy
                
                if closest_enemy:
                    # Calculate lead position
                    lead_pos = self.memory_reader.calculate_lead_position(
                        player_pos, closest_enemy, shell_speed)
                    
                    # Convert world position to screen coordinates
                    screen_x, screen_y = self.world_to_screen(lead_pos)
                    
                    # Store for overlay
                    self.predicted_aim_points.append((screen_x, screen_y))
                    
                    # Move mouse to aim position if aimbot is active
                    if self.aimbot_active:
                        self.move_mouse_to_position(screen_x, screen_y)
                
                # Update overlay if active
                if self.overlay_active:
                    self.overlay.update(self.predicted_aim_points)
                
            except Exception as e:
                print(f"Error in aimbot loop: {e}")
            
            # Sleep to prevent high CPU usage
            time.sleep(0.016)  # ~60 updates per second
    
    def start(self):
        """Start the aimbot and overlay"""
        print(f"Starting World of Warships Aimbot")
        print(f"Hotkeys:")
        print(f"  {self.hotkey_aimbot_toggle}: Toggle Aimbot")
        print(f"  {self.hotkey_overlay_toggle}: Toggle Overlay")
        print(f"  {self.hotkey_exit}: Exit")
        
        self.overlay.start()
        self.aimbot_thread.start()
        
        try:
            # Main thread just needs to stay alive
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.exit_program()
        
        # Wait for aimbot thread to finish
        self.aimbot_thread.join()
        print("Application exited")

if __name__ == "__main__":
    import math  # Import math module needed in world_to_screen method
    
    controller = AimbotController()
    controller.start()
