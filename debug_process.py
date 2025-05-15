import pymem
import psutil

def check_for_game():
    possible_processes = ["WorldOfWarships.exe", "WoWs.exe", "WoWsLauncher.exe", "WorldOfWarships64.exe", "wows.exe"]
    
    print("Checking for running processes...")
    all_processes = [p.name() for p in psutil.process_iter()]
    print(f"Found {len(all_processes)} processes running")
    
    # Check for World of Warships processes
    for process_name in possible_processes:
        if process_name in all_processes:
            print(f"Found {process_name} running!")
            try:
                pm = pymem.Pymem(process_name)
                print(f"Successfully connected to {process_name}")
                return True
            except Exception as e:
                print(f"Error connecting to {process_name}: {e}")
        else:
            print(f"{process_name} not found in running processes")
    
    return False

if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("psutil not installed. Installing now...")
        import subprocess
        subprocess.call(["pip", "install", "psutil"])
        import psutil
    
    if check_for_game():
        print("Game process found and connection successful!")
    else:
        print("Failed to find or connect to World of Warships process")
    
    input("Press Enter to exit...")
