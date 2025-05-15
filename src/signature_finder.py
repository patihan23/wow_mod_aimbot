import os
import re
import sys
import time
import pymem
import struct
from pymem import Pymem
from pymem.process import module_from_name
from pymem.pattern import pattern_scan_module
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

class SignatureFinder:
    def __init__(self, process_name="WorldOfWarships.exe"):
        self.process_name = process_name
        self.pm = None
        self.module = None
        self.module_name = None
        self.module_size = None
    
    def connect_to_process(self):
        """Connect to the target process"""
        try:
            self.pm = Pymem(self.process_name)
            module_info = module_from_name(self.pm.process_handle, self.process_name)
            self.module = module_info.lpBaseOfDll
            self.module_size = module_info.SizeOfImage
            self.module_name = self.process_name
            return True
        except Exception as e:
            print(f"Error connecting to process: {e}")
            return False
    
    def find_pattern(self, pattern, mask=None):
        """Find a pattern in the game's memory"""
        if not self.pm or not self.module:
            print("Not connected to process")
            return None
        
        try:
            address = pattern_scan_module(self.pm.process_handle, self.module, pattern, mask)
            return address
        except Exception as e:
            print(f"Error finding pattern: {e}")
            return None
    
    def generate_signature(self, address, bytes_before=8, bytes_after=8, min_unique_length=10):
        """Generate a signature based on bytes around an address"""
        if not self.pm or not self.module:
            print("Not connected to process")
            return None
        
        # Check if address is within module bounds
        if not (self.module <= address < self.module + self.module_size):
            print(f"Address {hex(address)} is outside module bounds")
            return None
        
        # Calculate read range while staying within module bounds
        start_addr = max(self.module, address - bytes_before)
        end_addr = min(self.module + self.module_size, address + bytes_after + 1)
        length = end_addr - start_addr
        
        try:
            # Read memory chunk
            buffer = self.pm.read_bytes(start_addr, length)
            
            # Generate initial signature
            signature = ' '.join([f"{b:02X}" for b in buffer])
            
            # Add wildcards for variable bytes (like addresses)
            # This is a simplified approach - a real implementation would be more sophisticated
            
            # Replace the relative address bytes with wildcards if we find them
            # This is specific to common x64 assembly patterns like "48 8B 05 XX XX XX XX"
            # where XX XX XX XX is a 32-bit relative address
            
            # Look for common instruction patterns that include relative addresses
            patterns = [
                (r'(48 8B 05|48 8D 05|48 8D 0D|48 8B 0D|E8|E9) ([0-9A-F]{2} ){4}', 7),  # MOV RAX, [RIP+disp32] or CALL/JMP rel32
                (r'(89 05|8B 05) ([0-9A-F]{2} ){4}', 5)  # MOV/MOV [RIP+disp32], EAX
            ]
            
            mask = ""
            sig_parts = signature.split()
            mask_parts = []
            
            relative_addr_found = False
            
            for pattern, offset in patterns:
                matches = re.finditer(pattern, signature)
                for match in matches:
                    start, end = match.span()
                    start_idx = len(signature[:start].split())
                    # Convert wildcard bytes after the instruction
                    for i in range(start_idx + offset - 1, start_idx + offset + 3):
                        if i < len(sig_parts):
                            sig_parts[i] = "?"
                            relative_addr_found = True
            
            # If we didn't find any relative addresses, look for other byte patterns that might vary
            if not relative_addr_found:
                # Look for potential pointer values (sequences of 4-8 bytes that could be addresses)
                for i in range(len(sig_parts) - 3):
                    # Check if these 4 bytes could represent an address in a common memory region
                    try:
                        value = int(''.join(sig_parts[i:i+4][::-1]), 16)  # Little endian
                        if 0x10000000 <= value <= 0xFFFFFFFF:  # Common memory address range
                            for j in range(i, i+4):
                                sig_parts[j] = "?"
                    except:
                        pass
            
            # Convert modified parts list back to signature string
            final_signature = ' '.join(sig_parts)
            
            # Generate mask (x for fixed bytes, ? for wildcards)
            mask = ''.join(['x' if b != '?' else '?' for b in sig_parts])
            
            return {
                'address': hex(address),
                'offset_from_module': hex(address - self.module),
                'signature': final_signature,
                'mask': mask,
                'byte_pattern': '\\x' + '\\x'.join([b if b != '?' else '00' for b in sig_parts])
            }
            
        except Exception as e:
            print(f"Error generating signature: {e}")
            return None
    
    def scan_pointer_path(self, target_address, max_depth=3, max_offsets=0x1000):
        """Find potential pointer paths to a target address"""
        if not self.pm or not self.module:
            print("Not connected to process")
            return []
        
        results = []
        
        # Helper function for recursive scanning
        def scan_level(base_address, current_path, depth):
            if depth >= max_depth:
                return
            
            # Read memory at this address to see if it's a valid pointer
            try:
                ptr_value = self.pm.read_longlong(base_address)
                
                # Check if pointer points to anything near our target
                if ptr_value:
                    # Calculate offset from pointer to target
                    offset = target_address - ptr_value
                    
                    # If offset is within reasonable range, add to results
                    if -max_offsets <= offset <= max_offsets:
                        results.append({
                            'base': hex(base_address),
                            'points_to': hex(ptr_value),
                            'offset_to_target': hex(offset),
                            'path': current_path + [hex(offset)]
                        })
                    
                    # Continue searching from this pointer
                    scan_level(ptr_value, current_path + [hex(0)], depth + 1)
            except:
                pass
        
        # Start scanning from the module base
        # We'll scan for pointers in the .data section (simplified approach)
        data_section_offset = 0x1000  # Approximate .data section offset (varies by executable)
        data_section_size = 0x100000  # Approximate size to scan
        
        scan_start = self.module + data_section_offset
        scan_end = scan_start + data_section_size
        
        # Scan for potential base pointers
        print(f"Scanning for pointer paths from {hex(scan_start)} to {hex(scan_end)}")
        
        for addr in range(scan_start, scan_end, 8):  # 8 bytes for 64-bit pointers
            scan_level(addr, [hex(addr - self.module)], 0)
            
            # Progress indicator
            if addr % 0x10000 == 0:
                print(f"Scanning: {((addr - scan_start) / data_section_size) * 100:.1f}% complete")
        
        return results

class SignatureFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Memory Signature Finder")
        self.root.geometry("800x600")
        
        self.finder = SignatureFinder()
        self.process_connected = False
        
        self.create_widgets()
    
    def create_widgets(self):
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Process connection frame
        connection_frame = ttk.LabelFrame(main_frame, text="Process Connection")
        connection_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(connection_frame, text="Process Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.process_name_var = tk.StringVar(value="WorldOfWarships.exe")
        ttk.Entry(connection_frame, textvariable=self.process_name_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(connection_frame, text="Connect", command=self.connect_to_process).grid(row=0, column=2, padx=5, pady=5)
        
        self.connection_status_var = tk.StringVar(value="Not Connected")
        ttk.Label(connection_frame, textvariable=self.connection_status_var).grid(row=0, column=3, padx=5, pady=5)
        
        # Notebook for different tools
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Signature generator tab
        sig_frame = ttk.Frame(self.notebook)
        self.notebook.add(sig_frame, text="Signature Generator")
        
        ttk.Label(sig_frame, text="Address (hex):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.address_var = tk.StringVar()
        ttk.Entry(sig_frame, textvariable=self.address_var, width=20).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(sig_frame, text="Bytes Before:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.bytes_before_var = tk.StringVar(value="16")
        ttk.Entry(sig_frame, textvariable=self.bytes_before_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(sig_frame, text="Bytes After:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.bytes_after_var = tk.StringVar(value="16")
        ttk.Entry(sig_frame, textvariable=self.bytes_after_var, width=10).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(sig_frame, text="Generate Signature", command=self.generate_signature).grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        ttk.Label(sig_frame, text="Results:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.sig_result_text = scrolledtext.ScrolledText(sig_frame, width=80, height=15)
        self.sig_result_text.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky=tk.NSEW)
        
        # Pattern search tab
        pattern_frame = ttk.Frame(self.notebook)
        self.notebook.add(pattern_frame, text="Pattern Search")
        
        ttk.Label(pattern_frame, text="Pattern (hex bytes with ? as wildcard):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.pattern_var = tk.StringVar()
        ttk.Entry(pattern_frame, textvariable=self.pattern_var, width=60).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(pattern_frame, text="Search Pattern", command=self.search_pattern).grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        ttk.Label(pattern_frame, text="Results:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.pattern_result_text = scrolledtext.ScrolledText(pattern_frame, width=80, height=15)
        self.pattern_result_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.NSEW)
        
        # Pointer scanner tab
        pointer_frame = ttk.Frame(self.notebook)
        self.notebook.add(pointer_frame, text="Pointer Scanner")
        
        ttk.Label(pointer_frame, text="Target Address (hex):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.target_addr_var = tk.StringVar()
        ttk.Entry(pointer_frame, textvariable=self.target_addr_var, width=20).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(pointer_frame, text="Max Depth:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.max_depth_var = tk.StringVar(value="3")
        ttk.Entry(pointer_frame, textvariable=self.max_depth_var, width=5).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(pointer_frame, text="Max Offset:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.max_offset_var = tk.StringVar(value="0x1000")
        ttk.Entry(pointer_frame, textvariable=self.max_offset_var, width=10).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(pointer_frame, text="Scan for Pointers", command=self.scan_pointers).grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        ttk.Label(pointer_frame, text="Results:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.pointer_result_text = scrolledtext.ScrolledText(pointer_frame, width=80, height=15)
        self.pointer_result_text.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky=tk.NSEW)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Configure grid weights for resizing
        sig_frame.grid_columnconfigure(3, weight=1)
        sig_frame.grid_rowconfigure(5, weight=1)
        pattern_frame.grid_columnconfigure(1, weight=1)
        pattern_frame.grid_rowconfigure(3, weight=1)
        pointer_frame.grid_columnconfigure(1, weight=1)
        pointer_frame.grid_rowconfigure(5, weight=1)
    
    def connect_to_process(self):
        """Connect to the specified process"""
        process_name = self.process_name_var.get()
        self.finder = SignatureFinder(process_name)
        
        self.status_var.set("Connecting to process...")
        self.root.update_idletasks()
        
        if self.finder.connect_to_process():
            self.connection_status_var.set(f"Connected to {process_name}")
            self.process_connected = True
            self.status_var.set(f"Connected to {process_name}, module base: {hex(self.finder.module)}")
        else:
            self.connection_status_var.set("Connection Failed")
            self.process_connected = False
            self.status_var.set("Failed to connect to process")
            messagebox.showerror("Connection Error", f"Failed to connect to {process_name}")
    
    def generate_signature(self):
        """Generate a signature from the specified address"""
        if not self.process_connected:
            messagebox.showwarning("Not Connected", "Please connect to a process first")
            return
        
        try:
            address = int(self.address_var.get(), 16)
            bytes_before = int(self.bytes_before_var.get())
            bytes_after = int(self.bytes_after_var.get())
            
            self.status_var.set(f"Generating signature for address {hex(address)}...")
            self.root.update_idletasks()
            
            signature = self.finder.generate_signature(address, bytes_before, bytes_after)
            
            if signature:
                result = f"Address: {signature['address']}\n"
                result += f"Module Offset: {signature['offset_from_module']}\n"
                result += f"Signature: {signature['signature']}\n"
                result += f"Mask: {signature['mask']}\n"
                result += f"Byte Pattern: {signature['byte_pattern']}\n"
                
                self.sig_result_text.delete(1.0, tk.END)
                self.sig_result_text.insert(tk.END, result)
                self.status_var.set("Signature generated successfully")
            else:
                self.status_var.set("Failed to generate signature")
                messagebox.showerror("Error", "Failed to generate signature")
        
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid hexadecimal address")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.status_var.set(f"Error: {e}")
    
    def search_pattern(self):
        """Search for a pattern in the process memory"""
        if not self.process_connected:
            messagebox.showwarning("Not Connected", "Please connect to a process first")
            return
        
        pattern_str = self.pattern_var.get()
        if not pattern_str:
            messagebox.showwarning("Empty Pattern", "Please enter a pattern to search for")
            return
        
        # Convert pattern string to bytes and mask
        try:
            pattern_bytes = []
            mask = ""
            
            for part in pattern_str.split():
                if part == "?":
                    pattern_bytes.append(0)
                    mask += "?"
                else:
                    pattern_bytes.append(int(part, 16))
                    mask += "x"
            
            pattern = bytes(pattern_bytes)
            
            self.status_var.set("Searching for pattern...")
            self.root.update_idletasks()
            
            address = self.finder.find_pattern(pattern, mask)
            
            if address:
                result = f"Pattern found at: {hex(address)}\n"
                result += f"Module Offset: {hex(address - self.finder.module)}\n"
                
                # Read some bytes at the found address
                try:
                    bytes_at_addr = self.finder.pm.read_bytes(address, 32)
                    bytes_str = ' '.join([f"{b:02X}" for b in bytes_at_addr])
                    result += f"\nBytes at address:\n{bytes_str}"
                except:
                    result += "\nCould not read bytes at address"
                
                self.pattern_result_text.delete(1.0, tk.END)
                self.pattern_result_text.insert(tk.END, result)
                self.status_var.set("Pattern found successfully")
            else:
                self.pattern_result_text.delete(1.0, tk.END)
                self.pattern_result_text.insert(tk.END, "Pattern not found")
                self.status_var.set("Pattern not found")
        
        except ValueError:
            messagebox.showerror("Invalid Pattern", "Please enter a valid pattern (hex bytes with ? as wildcard)")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.status_var.set(f"Error: {e}")
    
    def scan_pointers(self):
        """Scan for pointer paths to a target address"""
        if not self.process_connected:
            messagebox.showwarning("Not Connected", "Please connect to a process first")
            return
        
        try:
            target_addr = int(self.target_addr_var.get(), 16)
            max_depth = int(self.max_depth_var.get())
            max_offset = int(self.max_offset_var.get(), 0)  # Parse as hex if starts with 0x
            
            # Validate inputs
            if max_depth <= 0 or max_depth > 5:
                messagebox.showwarning("Invalid Input", "Max depth should be between 1 and 5")
                return
                
            if max_offset <= 0 or max_offset > 0x10000:
                messagebox.showwarning("Invalid Input", "Max offset should be between 1 and 0x10000")
                return
            
            # Confirm before starting a potentially long scan
            if not messagebox.askyesno("Confirm Scan", "Pointer scanning can take a long time. Continue?"):
                return
            
            self.status_var.set("Scanning for pointers... This may take a while")
            self.root.update_idletasks()
            
            # Ideally this would be in a separate thread to not freeze the UI
            results = self.finder.scan_pointer_path(target_addr, max_depth, max_offset)
            
            if results:
                result_text = f"Found {len(results)} potential pointer paths:\n\n"
                
                for i, result in enumerate(results[:100]):  # Limit display to avoid overwhelming the UI
                    result_text += f"Path {i+1}:\n"
                    result_text += f"  Base: {result['base']} (Offset from module: {hex(int(result['base'], 16) - self.finder.module)})\n"
                    result_text += f"  Points to: {result['points_to']}\n"
                    result_text += f"  Offset to target: {result['offset_to_target']}\n"
                    result_text += f"  Path: {' -> '.join(result['path'])}\n\n"
                
                if len(results) > 100:
                    result_text += f"(Showing 100 of {len(results)} results)\n"
                
                self.pointer_result_text.delete(1.0, tk.END)
                self.pointer_result_text.insert(tk.END, result_text)
                self.status_var.set(f"Found {len(results)} potential pointer paths")
            else:
                self.pointer_result_text.delete(1.0, tk.END)
                self.pointer_result_text.insert(tk.END, "No pointer paths found")
                self.status_var.set("No pointer paths found")
        
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid values for all fields")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.status_var.set(f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SignatureFinderGUI(root)
    root.mainloop()
