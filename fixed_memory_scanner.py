import ctypes
import struct
import re
import time
import json
import os
from pymem import Pymem
from pymem.process import module_from_name
from pymem.pattern import pattern_scan_module

class MemoryScanner:
    def __init__(self, process_name="WorldOfWarships64.exe", config_file=None):
        self.process_name = process_name
        
        # Use absolute path for config file if not provided
        if config_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(base_dir, 'config', 'memory_config.json')
        self.config_file = config_file
        
        self.pm = None
        self.module = None
        self.offsets = {}
        self.signatures = {}
        
        # Load existing configuration if it exists
        self.load_config()
    
    def load_config(self):
        """Load existing configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if 'offsets' in config:
                        self.offsets = config['offsets']
                    if 'signatures' in config:
                        self.signatures = config['signatures']
                    if 'process_name' in config:
                        self.process_name = config['process_name']
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def connect_to_game(self):
        """Connect to the World of Warships process"""
        possible_process_names = ["WorldOfWarships.exe", "WoWs.exe", "WoWsLauncher.exe", "WorldOfWarships64.exe", "wows.exe"]
        
        # First try the process name from config
        try:
            self.pm = Pymem(self.process_name)
            self.module = module_from_name(self.pm.process_handle, self.process_name).lpBaseOfDll
            print(f"Connected to {self.process_name}")
            print(f"Base address: {hex(self.module)}")
            return True
        except Exception as e:
            print(f"Failed to connect to {self.process_name}: {e}")
            
        # Try other possible process names
        for process_name in possible_process_names:
            if process_name == self.process_name:
                continue  # Already tried this one
                
            try:
                self.pm = Pymem(process_name)
                self.module = module_from_name(self.pm.process_handle, process_name).lpBaseOfDll
                print(f"Connected to {process_name}")
                print(f"Base address: {hex(self.module)}")
                
                # Update process name for future reference
                self.process_name = process_name
                return True
            except Exception as e:
                print(f"Failed to connect to {process_name}: {e}")
        
        # If we get here, we couldn't connect to any process
        print("Could not find any World of Warships process")
        return False
    
    def find_pattern(self, pattern, mask=None):
        """Find a pattern in the game's memory"""
        if not self.pm or not self.module:
            print("Not connected to game process")
            return None
        
        try:
            address = pattern_scan_module(self.pm.process_handle, self.module, pattern.encode())
            if address:
                print(f"Found pattern at: {hex(address)}")
            return address
        except Exception as e:
            print(f"Error finding pattern: {e}")
            return None
    
    def find_pointers_from_signature(self, signature, offset_to_address=3, read_offset=False):
        """Find memory address from signature pattern
        
        Args:
            signature: Pattern to scan for
            offset_to_address: Offset from pattern to the relative address bytes
            read_offset: Whether to read the value at the resulting pointer
        
        Returns:
            Found address or None
        """
        if not self.pm or not self.module:
            print("Not connected to game process")
            return None
        
        try:
            # Convert signature from string format to bytes pattern
            if isinstance(signature, str) and "?" in signature:
                pattern_bytes = []
                mask = ""
                
                for part in signature.split():
                    if part == "?":
                        pattern_bytes.append(0)
                        mask += "?"
                    else:
                        pattern_bytes.append(int(part, 16))
                        mask += "x"
                
                pattern = bytes(pattern_bytes)
            else:
                pattern = signature
                mask = None
            
            # Find the pattern
            address = self.find_pattern(pattern, mask)
            if not address:
                return None
            
            # Get the relative offset (32-bit signed integer)
            rel_offset_addr = address + offset_to_address
            rel_offset = self.pm.read_int(rel_offset_addr)
            
            # Calculate the actual address
            # Formula: base_address + rel_offset + offset_bytes + instruction_length
            instruction_length = offset_to_address + 4  # 4 bytes for the offset itself
            abs_address = self.module + rel_offset + instruction_length
            
            print(f"Found absolute address: {hex(abs_address)}")
            
            # Read the value at the address if requested
            if read_offset:
                value = self.pm.read_int(abs_address)
                print(f"Value at address: {hex(value)}")
                return value
            
            return abs_address
            
        except Exception as e:
            print(f"Error in find_pointers_from_signature: {e}")
            return None
    
    def scan_for_floats(self, min_val, max_val, region_size=0x10000000, start_offset=0):
        """Scan memory for float values in a given range
        Useful for finding coordinates and velocities
        """
        if not self.pm or not self.module:
            print("Not connected to game process")
            return []
        
        results = []
        scan_start = self.module + start_offset
        scan_end = scan_start + region_size
        current_addr = scan_start
        
        print(f"Scanning for floats between {min_val} and {max_val}...")
        print(f"Scan range: {hex(scan_start)} - {hex(scan_end)}")
        
        # Calculate step size - we'll read larger chunks for speed
        CHUNK_SIZE = 4096
        
        while current_addr < scan_end:
            try:
                # Read a chunk of memory
                buffer = self.pm.read_bytes(current_addr, min(CHUNK_SIZE, scan_end - current_addr))
                
                # Process chunk in 4-byte segments (size of float)
                for i in range(0, len(buffer) - 3, 4):
                    try:
                        val = struct.unpack('f', buffer[i:i+4])[0]
                        if min_val <= val <= max_val:
                            results.append(current_addr + i)
                    except struct.error:
                        continue
                
                # Move to next chunk
                current_addr += CHUNK_SIZE
                
                # Progress indicator
                if len(results) % 100 == 0 and len(results) > 0:
                    print(f"Found {len(results)} potential matches so far...")
                    if len(results) > 5000:  # Limit results to prevent excessive matches
                        print("Too many matches found, refine search criteria")
                        break
                
            except Exception as e:
                # Skip problematic memory regions
                current_addr += 4
        
        print(f"Scan complete, found {len(results)} matches")
        return results
    
    def find_entity_array(self, known_entity_address=None, max_entities=32, array_size_guess=0x280):
        """Attempt to find the entity array by scanning for known entity patterns
        This is a simplified approach and might need refinement for specific games
        """
        if not self.pm:
            print("Not connected to game process")
            return None
        
        # Check if we're in demonstration mode
        if self.pm == "DUMMY":
            print("\n=== DEMONSTRATION MODE ===")
            print("Generating simulated entity array address for educational purposes...")
            
            import random
            # Create a random but realistic-looking entity array address
            entity_array_addr = self.module + random.randint(0x300000, 0x3FFFFFF)
            print(f"Simulated entity array found at {hex(entity_array_addr)}")
            return entity_array_addr
        
        # If we have a known entity address, use it to try to find the array
        if known_entity_address:
            print(f"Searching for entity array using known entity at {hex(known_entity_address)}")
            # Search backwards in memory to find potential array start
            for i in range(max_entities):
                potential_array_start = known_entity_address - (i * array_size_guess)
                consecutive_entities = 0
                
                # Check if we have consecutive entities
                for j in range(5):  # Check a few consecutive entities
                    check_addr = potential_array_start + (j * array_size_guess)
                    try:
                        # This check would need to be customized for the specific game
                        # to verify it's really an entity
                        entity_value = self.pm.read_int(check_addr)
                        if entity_value != 0:  # Simple validity check
                            consecutive_entities += 1
                    except:
                        break
                
                if consecutive_entities >= 3:  # If we found 3+ consecutive entities
                    print(f"Possible entity array found at {hex(potential_array_start)}")
                    return potential_array_start
        
        # If no known address or the above method failed, try scanning for specific patterns
        print("Attempting pattern-based entity array scan...")
        # This would require game-specific signatures/patterns
        
        print("Could not locate entity array")
        return None
    
    def find_view_matrix(self):
        """Find the view matrix used for 3D to 2D coordinate conversion
        This is a simplified approach and would need game-specific adjustments
        """
        if not self.pm:
            print("Not connected to game process")
            return None
        
        # Check if we're in demonstration mode
        if self.pm == "DUMMY":
            print("\n=== DEMONSTRATION MODE ===")
            print("Generating simulated view matrix address for educational purposes...")
            
            import random
            # Create a random but realistic-looking view matrix address
            view_matrix_addr = self.module + random.randint(0x500000, 0x5FFFFFF)
            print(f"Simulated view matrix found at {hex(view_matrix_addr)}")
            return view_matrix_addr
            
        # Try to find using signature if available
        if 'view_matrix_sig' in self.signatures:
            print("Searching for view matrix using signature...")
            return self.find_pointers_from_signature(
                self.signatures['view_matrix_sig'],
                offset_to_address=3,  # Adjust based on signature
                read_offset=False
            )
        
        # Alternative: scan for typical view matrix values
        # View matrices often have specific patterns, like identity matrix portions
        print("Signature not found. Attempting scan for common view matrix patterns...")
        print("This method is not implemented in this example as it's highly game-specific")
        return None
    
    def scan_for_player_position(self):
        """Scan for player position by looking for coordinates within typical game bounds
        This is a simplified example that would need to be adapted for the specific game
        """
        if not self.pm:
            print("Not connected to game process")
            return []
            
        print("Scanning for potential player position values...")
        
        # Check if we're in demonstration mode
        if self.pm == "DUMMY":
            print("\n=== DEMONSTRATION MODE ===")
            print("Generating simulated player position values for educational purposes...")
            
            import random
            # Generate some realistic-looking simulated player positions
            candidates = []
            for i in range(5):
                # Create some addresses that look like they're in the game's memory space
                base_addr = self.module + random.randint(0x100000, 0x2000000)
                x = random.uniform(-10000.0, 10000.0)
                y = random.uniform(-10000.0, 10000.0)
                z = random.uniform(-100.0, 100.0)
                
                candidates.append({
                    'address': base_addr,
                    'values': (x, y, z)
                })
            
            print(f"Found {len(candidates)} simulated player position candidates")
            return candidates
        
        # In World of Warships, coordinates could be within certain ranges
        # This is a guess and would need adjustment for the actual game
        candidates = self.scan_for_floats(-50000.0, 50000.0)
        
        # Filter candidates for patterns of 3 consecutive floats (X,Y,Z coordinates)
        position_candidates = []
        for addr in candidates:
            try:
                x = self.pm.read_float(addr)
                y = self.pm.read_float(addr + 4)
                z = self.pm.read_float(addr + 8)
                
                # Additional validation could be added here
                position_candidates.append({
                    'address': addr,
                    'values': (x, y, z)
                })
            except:
                continue
                
            if len(position_candidates) >= 20:
                break  # Limit to top candidates
        
        print(f"Found {len(position_candidates)} potential position candidates")
        return position_candidates
    
    def save_config(self):
        """Save the current configuration to file"""
        config = {
            'process_name': self.process_name,
            'offsets': self.offsets,
            'signatures': self.signatures
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def interactive_scan(self):
        """Run an interactive scanning session to find memory addresses"""
        if not self.connect_to_game():
            print("Failed to connect to game. Make sure the game is running.")
            
            # Provide options to proceed with demonstration mode
            demo_choice = input("\nWould you like to run in demonstration mode without a connected game? (y/n): ")
            if demo_choice.lower() == 'y':
                print("\n=== RUNNING IN DEMONSTRATION MODE ===")
                print("This mode will show how the scanner works without an actual game connection.")
                print("Any values found will be simulated for educational purposes.")
                # Set up dummy module address for demonstration
                self.pm = "DUMMY"  # Just a placeholder
                self.module = 0x400000  # Common base address for demonstration
            else:
                return
        
        print("\n===== Memory Scanner for World of Warships =====")
        print("This tool will help you find memory addresses for the aimbot.")
        print("Note: This is an educational example and will need refinement for accurate results.")
        
        while True:
            print("\nSelect a scan option:")
            print("1. Scan for player position")
            print("2. Scan for entity array")
            print("3. Scan for view matrix")
            print("4. Scan for specific pattern")
            print("5. Scan for values in range")
            print("6. Save current configuration")
            print("7. Exit")
            
            choice = input("Enter your choice (1-7): ")
            
            if choice == '1':
                candidates = self.scan_for_player_position()
                print("\nPotential player position addresses:")
                for i, candidate in enumerate(candidates):
                    addr = candidate['address']
                    x, y, z = candidate['values']
                    print(f"{i+1}. Address: {hex(addr)}, Values: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
                
                if candidates:
                    select = input("\nSelect an address to save as player position (number or 'n' to skip): ")
                    if select.isdigit() and 1 <= int(select) <= len(candidates):
                        selected = candidates[int(select) - 1]
                        offset = selected['address'] - self.module
                        self.offsets['player_base'] = hex(offset)
                        print(f"Player position base set to offset: {hex(offset)}")
            
            elif choice == '2':
                known_addr = input("Enter a known entity address (hex) or press Enter to scan: ")
                if known_addr.startswith('0x'):
                    try:
                        addr = int(known_addr, 16)
                        self.find_entity_array(addr)
                    except ValueError:
                        print("Invalid hex address")
                else:
                    self.find_entity_array()
            
            elif choice == '3':
                addr = self.find_view_matrix()
                if addr:
                    offset = addr - self.module
                    self.offsets['view_matrix_base'] = hex(offset)
                    print(f"View matrix base set to offset: {hex(offset)}")
            
            elif choice == '4':
                pattern = input("Enter pattern to search for (format: 48 8B 05 ? ? ? ? 48): ")
                if pattern:
                    addr = self.find_pointers_from_signature(pattern)
                    if addr:
                        offset = addr - self.module
                        key = input("Enter a name for this offset: ")
                        if key:
                            self.offsets[key] = hex(offset)
                            print(f"Offset '{key}' set to: {hex(offset)}")
            
            elif choice == '5':
                try:
                    min_val = float(input("Enter minimum value: "))
                    max_val = float(input("Enter maximum value: "))
                    self.scan_for_floats(min_val, max_val)
                except ValueError:
                    print("Invalid input, please enter numeric values")
            
            elif choice == '6':
                self.save_config()
            
            elif choice == '7':
                print("Exiting scanner")
                break
            
            else:
                print("Invalid choice, please try again")

if __name__ == "__main__":
    scanner = MemoryScanner()
    scanner.interactive_scan()