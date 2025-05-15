# World of Warships Aimbot Mod (Enhanced)

**Educational Purposes Only**

This project demonstrates how external memory reading can be used to create an aimbot for World of Warships. It is intended for educational purposes to understand game memory structures and how external applications can interact with games.

## Features

- External memory reading (no injection)
- Real-time player and enemy ship position tracking
- Movement prediction based on velocity vectors
- Shell ballistics calculation
- Overlay with aim prediction visualization
- Configurable hotkeys and settings
- Memory scanner for finding game data structures
- Signature finder for robust memory patterns
- GUI control panel for easy configuration
- Smart process detection for multiple executable names
- Improved error handling and user feedback

## Installation

1. Ensure you have Python 3.8+ installed
2. Clone or download this repository
3. Open a command prompt as administrator in the project folder
4. Create a virtual environment (recommended):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
5. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running the Project

1. Make sure World of Warships is running
2. Run the launcher as administrator:
   ```
   python launcher_fixed.py
   ```
3. The launcher will automatically detect your game process and update the configuration
4. Click "Launch Aimbot" to start the aimbot module
5. Use the default hotkeys:
   - F5: Toggle aimbot functionality
   - F6: Toggle visual overlay
   - F12: Exit

### Updating Memory Addresses

The default configuration contains placeholder memory addresses that won't work with your game version. To find the correct addresses:

1. From the launcher, click "Launch Memory Scanner"
2. The scanner will automatically connect to your game
3. Select "Scan for player position" to find your position in memory
4. Select "Scan for entity array" to find enemy ship positions
5. Select "Scan for view matrix" if you need 3D to 2D projections
6. Save your configuration when done

### Configuration Files

- `config/memory_config.json`: Contains memory addresses and offsets
- `config/aimbot_config.ini`: Contains aimbot settings and hotkeys
- `config/ship_parameters.json`: Contains ship-specific parameters

## Troubleshooting

### Common Issues

1. **"Could not find any World of Warships process"**
   - Make sure the game is running before starting the mod
   - The mod supports multiple executable names (WorldOfWarships.exe, WoWs.exe, etc.)
   - Run the launcher as administrator

2. **"Using placeholder memory addresses"**
   - This means you need to scan for the correct memory addresses
   - Use the memory scanner as described above

3. **"Error reading memory"**
   - Game version might have changed, requiring new memory addresses
   - Make sure you're running with administrator privileges
   - Anti-cheat may be blocking memory access

### Advanced Debugging

For experienced users, the project includes several diagnostic tools:

- `test_game_connect.py`: Tests basic game process connection
- `test_memory_reader.py`: Tests memory reading functions
- `debug_process.py`: Advanced process debugging

## Disclaimer

This project is for **EDUCATIONAL PURPOSES ONLY**. Using this in online games likely violates terms of service and could result in your account being banned. The authors do not condone cheating in online games.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
