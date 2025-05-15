import os
import sys

# Add the src directory to the path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.append(src_dir)

# Import the memory reader
from memory_reader import MemoryReader

def main():
    print("=" * 60)
    print("Memory Reader Test")
    print("=" * 60)
    
    try:
        # Initialize memory reader
        print("Initializing memory reader...")
        memory_reader = MemoryReader()
        
        # Try to get player position (this will test if memory reading works)
        print("Attempting to read player position...")
        player_pos = memory_reader.get_player_position()
        
        if player_pos:
            print(f"Player position: {player_pos}")
            print("Memory reading successful!")
        else:
            print("Failed to read player position")
    except Exception as e:
        print(f"Error: {e}")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
