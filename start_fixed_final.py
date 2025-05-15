import os
import sys
import time

# Add the src directory to the path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.append(src_dir)

# Import the aimbot controller
from aimbot import AimbotController
from memory_reader import MemoryReader

def main():
    print("=" * 60)
    print("World of Warships Aimbot Mod")
    print("=" * 60)
    print("Educational purposes only - Use at your own risk")
    print("=" * 60)
    
    # Check if game is running
    import pymem
    game_running = False
    possible_process_names = ["WorldOfWarships.exe", "WoWs.exe", "WoWsLauncher.exe", "WorldOfWarships64.exe", "wows.exe"]
    found_process = None
    
    for process_name in possible_process_names:
        try:
            pymem.Pymem(process_name)
            print(f"World of Warships detected as {process_name}!")
            game_running = True
            found_process = process_name
            
            # Update the process name in configuration
            try:
                config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
                config_path = os.path.join(config_dir, 'memory_config.json')
                
                import json
                # Read current config
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                except:
                    config = {}
                    
                # Update process name
                config['process_name'] = process_name
                
                # Write updated config
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=4)
                    
                print(f"Updated configuration with process name: {process_name}")
            except Exception as e:
                print(f"Warning: Could not update configuration: {e}")
                
            break
        except:
            continue
    
    if not game_running:
        print("World of Warships is not running!")
        print("Please start the game first.")
        input("Press Enter to exit...")
        return
    
    # Check for required Python packages
    try:
        import win32api
        import win32con
        import keyboard
        from PyQt5.QtWidgets import QApplication
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install the required packages:")
        print("pip install pywin32 keyboard pymem PyQt5")
        input("Press Enter to exit...")
        return
    
    # Initialize the aimbot
    print("Initializing aimbot...")
    try:
        # First initialize memory reader to ensure it can connect
        memory_reader = MemoryReader(process_name=found_process)
        
        if memory_reader.pm is None:
            print("Failed to connect to game memory!")
            print("Make sure you're running as administrator and the game is running.")
            input("Press Enter to exit...")
            return
            
        print("Successfully connected to game memory")
        
        # Initialize aimbot controller
        aimbot = AimbotController()
        
        # Start the aimbot in a loop
        print("\nAimbot is now running!")
        print("Press F5 to toggle aimbot functionality")
        print("Press F6 to toggle visual overlay")
        print("Press F12 to exit")
        
        # Enter the aimbot main loop
        aimbot.start()
        
    except Exception as e:
        print(f"Error starting aimbot: {e}")
        input("Press Enter to exit...")
        return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")