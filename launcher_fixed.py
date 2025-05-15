import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import importlib.util
import ctypes

# Add the src directory to the path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)
config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# Check if running as admin (required for memory reading)
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("World of Warships Aimbot Launcher")
        self.root.geometry("600x400")
        
        # Set application icon (if available)
        try:
            self.root.iconbitmap("data/icon.ico")
        except:
            pass
        
        self.create_widgets()
        self.check_requirements()
    
    def create_widgets(self):
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="World of Warships Aimbot", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        subtitle_label = ttk.Label(main_frame, text="Educational Purposes Only", font=("Arial", 10, "italic"))
        subtitle_label.pack(pady=5)
        
        # Warning frame
        warning_frame = ttk.Frame(main_frame, relief=tk.GROOVE, borderwidth=2)
        warning_frame.pack(fill=tk.X, pady=10, padx=5)
        
        warning_text = "WARNING: This software is for EDUCATIONAL PURPOSES ONLY.\n"
        warning_text += "Using this in online games violates Terms of Service and may result in a ban."
        
        warning_label = ttk.Label(warning_frame, text=warning_text, foreground="red", 
                                 font=("Arial", 9, "bold"), wraplength=550, justify=tk.CENTER)
        warning_label.pack(pady=5)
        
        # Tool selection frame
        tools_frame = ttk.LabelFrame(main_frame, text="Available Tools")
        tools_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Buttons for different tools
        btn_width = 25
        
        # Main aimbot button
        self.aimbot_btn = ttk.Button(tools_frame, text="Start Aimbot", width=btn_width,
                                    command=self.launch_aimbot)
        self.aimbot_btn.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(tools_frame, text="Launch the main aimbot application").grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Control panel button
        self.control_panel_btn = ttk.Button(tools_frame, text="Control Panel UI", width=btn_width,
                                          command=self.launch_control_panel)
        self.control_panel_btn.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(tools_frame, text="Launch the graphical control panel").grid(row=1, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Memory scanner button
        self.scanner_btn = ttk.Button(tools_frame, text="Memory Scanner", width=btn_width,
                                     command=self.launch_memory_scanner)
        self.scanner_btn.grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(tools_frame, text="Scan for memory addresses and offsets").grid(row=2, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Signature finder button
        self.sig_finder_btn = ttk.Button(tools_frame, text="Signature Finder", width=btn_width,
                                        command=self.launch_signature_finder)
        self.sig_finder_btn.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(tools_frame, text="Find memory signatures and patterns").grid(row=3, column=1, padx=5, pady=10, sticky=tk.W)
        
        # System status
        self.status_frame = ttk.LabelFrame(main_frame, text="System Status")
        self.status_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.status_text = tk.StringVar(value="Checking system requirements...")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_text)
        self.status_label.pack(pady=5)
        
        # Exit button
        self.exit_btn = ttk.Button(main_frame, text="Exit", command=self.root.destroy)
        self.exit_btn.pack(pady=10)
    
    def check_requirements(self):
        """Check if all required packages are installed"""
        required_packages = ['pymem', 'keyboard', 'win32api', 'win32con', 'PyQt5']
        missing_packages = []
        
        for package in required_packages:
            if not importlib.util.find_spec(package):
                missing_packages.append(package)
        
        if missing_packages:
            self.status_text.set(f"Missing packages: {', '.join(missing_packages)}")
            messagebox.showwarning("Missing Requirements", 
                                 f"The following packages are missing:\n{', '.join(missing_packages)}\n\n"
                                 f"Please install them using:\npip install {' '.join(missing_packages)}")
        else:
            # Check if game is running
            try:
                import pymem
                game_found = False
                possible_game_processes = ["WorldOfWarships.exe", "WoWs.exe", "WoWsLauncher.exe", "WorldOfWarships64.exe", "wows.exe"]
                
                for process_name in possible_game_processes:
                    try:
                        pymem.Pymem(process_name)
                        self.status_text.set(f"World of Warships is running ({process_name}) - Ready")
                        game_found = True
                        break
                    except:
                        continue
                
                if not game_found:
                    self.status_text.set("World of Warships is not running")
            except Exception as e:
                self.status_text.set(f"Error checking game status: {e}")
        
        # Check if running as admin
        if not is_admin():
            messagebox.showwarning("Administrator Rights Required", 
                                 "This application needs administrator privileges to read game memory.\n\n"
                                 "Please restart the application as administrator.")
    
    def launch_aimbot(self):
        """Launch the main aimbot"""
        try:
            # Check if game is running
            import pymem
            
            game_found = False
            possible_game_processes = ["WorldOfWarships.exe", "WoWs.exe", "WoWsLauncher.exe", "WorldOfWarships64.exe", "wows.exe"]
            
            for process_name in possible_game_processes:
                try:
                    pymem.Pymem(process_name)
                    game_found = True
                    # Update the process name in configuration
                    self.update_process_name(process_name)
                    break
                except:
                    continue
            
            if not game_found:
                messagebox.showwarning("Game Not Running", 
                                     "World of Warships is not running.\n"
                                     "Please start the game first.")
                return            # Launch the aimbot script
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_fixed_final.py')
            subprocess.Popen([sys.executable, script_path])
            
            messagebox.showinfo("Aimbot Started", 
                              "Aimbot has been started.\n\n"
                              "Default hotkeys:\n"
                              "F5: Toggle Aimbot\n"
                              "F6: Toggle Overlay\n"
                              "F12: Exit")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start aimbot: {e}")
    
    def launch_control_panel(self):
        """Launch the control panel UI"""
        try:
            script_path = os.path.join(src_dir, 'control_panel.py')
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start control panel: {e}")
    
    def launch_memory_scanner(self):
        """Launch the memory scanner"""
        try:
            script_path = os.path.join(src_dir, 'memory_scanner.py')
            # Launch in a new console window
            subprocess.Popen([sys.executable, script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start memory scanner: {e}")
    
    def launch_signature_finder(self):
        """Launch the signature finder"""
        try:
            script_path = os.path.join(src_dir, 'signature_finder.py')
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start signature finder: {e}")
            
    def update_process_name(self, process_name):
        """Update the process name in the memory configuration file"""
        try:
            import json
            config_path = os.path.join(config_dir, 'memory_config.json')
            
            # Read current config
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update process name
            config['process_name'] = process_name
            
            # Write updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            print(f"Updated process name to: {process_name}")
        except Exception as e:
            print(f"Error updating process name: {e}")

def main():
    # Check for admin privileges
    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return
    
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
