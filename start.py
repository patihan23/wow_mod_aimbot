import os
import sys
import time

# Add the src directory to the path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.append(src_dir)

# Import the aimbot controller
from aimbot import AimbotController

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
    
    for process_name in possible_process_names:
        try:
            pymem.Pymem(process_name)
            print(f"World of Warships detected as {process_name}!")
            game_running = True
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
        from PyQt5.QtWidgets import QApplication    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install the required packages:")
        print("pip install pywin32 keyboard pymem PyQt5")
        input("Press Enter to exit...")
        return
    
    # Check for configuration files
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    required_configs = [
        os.path.join(config_dir, 'aimbot_config.ini'),
        os.path.join(config_dir, 'memory_config.json'),
        os.path.join(config_dir, 'ship_parameters.json')
    ]
    
    missing_configs = [cfg for cfg in required_configs if not os.path.exists(cfg)]
    if missing_configs:
        print("Missing configuration files:")
        for cfg in missing_configs:
            print(f"  - {os.path.basename(cfg)}")
        input("Press Enter to exit...")
        return
    
    # Start the aimbot
    try:
        controller = AimbotController()
        controller.start()
    except Exception as e:
        print(f"Error starting aimbot: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
