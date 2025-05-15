import sys
import os
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QVBoxLayout, QHBoxLayout, QWidget, QCheckBox, 
                             QTabWidget, QLineEdit, QGroupBox, QGridLayout,
                             QComboBox, QSlider, QTextEdit, QSpinBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon
import sip

# Add the src directory to the path
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Import our modules
from aimbot import AimbotController
from memory_reader import MemoryReader, Vector3

class StatusThread(QThread):
    update_signal = pyqtSignal(dict)
    
    def __init__(self, memory_reader):
        super().__init__()
        self.memory_reader = memory_reader
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Get player position
                player_pos = self.memory_reader.get_player_position()
                
                # Get enemy ships
                enemy_ships = self.memory_reader.get_enemy_ships()
                
                # Get shell speed
                shell_speed = self.memory_reader.get_shell_speed()
                
                # Build status object
                status = {
                    "player_position": player_pos,
                    "enemy_count": len(enemy_ships),
                    "shell_speed": shell_speed,
                    "enemy_ships": enemy_ships[:5]  # Limit to 5 enemies to avoid UI overload
                }
                
                # Emit signal with status
                self.update_signal.emit(status)
                
            except Exception as e:
                # Emit error status
                self.update_signal.emit({"error": str(e)})
            
            # Sleep to prevent high CPU usage
            time.sleep(0.5)  # Update twice per second
    
    def stop(self):
        self.running = False
        self.wait()

class AimbotControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize aimbot controller
        self.aimbot = None
        self.memory_reader = None
        self.status_thread = None
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        # Main window setup
        self.setWindowTitle("World of Warships Aimbot Controller")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Add status area at top
        self.create_status_area()
        
        # Add tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Create tab contents
        self.create_control_tab()
        self.create_config_tab()
        self.create_scanner_tab()
        self.create_log_tab()
        
        # Add buttons at bottom
        self.create_action_buttons()
        
        # Setup auto-refreshing status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_manually)
        self.status_timer.start(1000)  # Update every second until we connect
    
    def create_status_area(self):
        # Status group box
        self.status_group = QGroupBox("Status")
        self.status_layout = QGridLayout()
        self.status_group.setLayout(self.status_layout)
        
        # Status labels
        self.status_labels = {
            "connection": QLabel("Not Connected"),
            "player_pos": QLabel("Player Position: Unknown"),
            "enemy_count": QLabel("Enemy Ships: 0"),
            "shell_speed": QLabel("Shell Speed: Unknown"),
            "aimbot_status": QLabel("Aimbot: OFF"),
            "overlay_status": QLabel("Overlay: OFF")
        }
        
        # Add labels to layout
        row = 0
        for key, label in self.status_labels.items():
            self.status_layout.addWidget(label, row // 2, row % 2)
            if key == "connection":
                # Make connection status more prominent
                font = label.font()
                font.setBold(True)
                label.setFont(font)
            row += 1
        
        # Add status group to main layout
        self.main_layout.addWidget(self.status_group)
    
    def create_control_tab(self):
        # Control tab
        control_tab = QWidget()
        control_layout = QVBoxLayout(control_tab)
        
        # Aimbot controls
        aimbot_group = QGroupBox("Aimbot Controls")
        aimbot_layout = QGridLayout()
        
        # Toggle buttons
        self.aimbot_toggle_btn = QPushButton("Toggle Aimbot (F5)")
        self.aimbot_toggle_btn.clicked.connect(self.toggle_aimbot)
        
        self.overlay_toggle_btn = QPushButton("Toggle Overlay (F6)")
        self.overlay_toggle_btn.clicked.connect(self.toggle_overlay)
        
        # Add buttons to layout
        aimbot_layout.addWidget(self.aimbot_toggle_btn, 0, 0)
        aimbot_layout.addWidget(self.overlay_toggle_btn, 0, 1)
        
        # Add options
        self.aim_speed_slider = QSlider(Qt.Horizontal)
        self.aim_speed_slider.setMinimum(1)
        self.aim_speed_slider.setMaximum(10)
        self.aim_speed_slider.setValue(5)  # Default 0.5
        self.aim_speed_slider.setTickPosition(QSlider.TicksBelow)
        
        aimbot_layout.addWidget(QLabel("Aim Speed:"), 1, 0)
        aimbot_layout.addWidget(self.aim_speed_slider, 1, 1)
        
        # Target selection dropdown
        self.target_selection = QComboBox()
        self.target_selection.addItems([
            "Closest Target", 
            "Largest Target", 
            "Most Dangerous", 
            "Lowest Health"
        ])
        
        aimbot_layout.addWidget(QLabel("Target Priority:"), 2, 0)
        aimbot_layout.addWidget(self.target_selection, 2, 1)
        
        # Finish aimbot group
        aimbot_group.setLayout(aimbot_layout)
        control_layout.addWidget(aimbot_group)
        
        # Enemy list
        enemies_group = QGroupBox("Detected Enemies")
        enemies_layout = QVBoxLayout()
        
        self.enemy_text = QTextEdit()
        self.enemy_text.setReadOnly(True)
        enemies_layout.addWidget(self.enemy_text)
        
        enemies_group.setLayout(enemies_layout)
        control_layout.addWidget(enemies_group)
        
        # Add control tab to tabs
        self.tabs.addTab(control_tab, "Control")
    
    def create_config_tab(self):
        # Config tab
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        # Hotkeys group
        hotkeys_group = QGroupBox("Hotkeys")
        hotkeys_layout = QGridLayout()
        
        hotkeys_layout.addWidget(QLabel("Aimbot Toggle:"), 0, 0)
        self.hotkey_aimbot = QLineEdit("F5")
        hotkeys_layout.addWidget(self.hotkey_aimbot, 0, 1)
        
        hotkeys_layout.addWidget(QLabel("Overlay Toggle:"), 1, 0)
        self.hotkey_overlay = QLineEdit("F6")
        hotkeys_layout.addWidget(self.hotkey_overlay, 1, 1)
        
        hotkeys_layout.addWidget(QLabel("Exit Program:"), 2, 0)
        self.hotkey_exit = QLineEdit("F12")
        hotkeys_layout.addWidget(self.hotkey_exit, 2, 1)
        
        hotkeys_group.setLayout(hotkeys_layout)
        config_layout.addWidget(hotkeys_group)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QGridLayout()
        
        display_layout.addWidget(QLabel("Screen Width:"), 0, 0)
        self.screen_width = QSpinBox()
        self.screen_width.setMinimum(800)
        self.screen_width.setMaximum(7680)
        self.screen_width.setValue(1920)
        display_layout.addWidget(self.screen_width, 0, 1)
        
        display_layout.addWidget(QLabel("Screen Height:"), 1, 0)
        self.screen_height = QSpinBox()
        self.screen_height.setMinimum(600)
        self.screen_height.setMaximum(4320)
        self.screen_height.setValue(1080)
        display_layout.addWidget(self.screen_height, 1, 1)
        
        display_layout.addWidget(QLabel("Overlay Opacity:"), 2, 0)
        self.overlay_opacity = QSlider(Qt.Horizontal)
        self.overlay_opacity.setMinimum(1)
        self.overlay_opacity.setMaximum(10)
        self.overlay_opacity.setValue(7)  # 0.7 opacity
        display_layout.addWidget(self.overlay_opacity, 2, 1)
        
        # ESP options
        display_layout.addWidget(QLabel("Draw Trajectories:"), 3, 0)
        self.draw_trajectories = QCheckBox()
        self.draw_trajectories.setChecked(True)
        display_layout.addWidget(self.draw_trajectories, 3, 1)
        
        display_layout.addWidget(QLabel("Show Distance:"), 4, 0)
        self.show_distance = QCheckBox()
        self.show_distance.setChecked(True)
        display_layout.addWidget(self.show_distance, 4, 1)
        
        display_group.setLayout(display_layout)
        config_layout.addWidget(display_group)
        
        # Add save button
        self.save_config_btn = QPushButton("Save Configuration")
        self.save_config_btn.clicked.connect(self.save_config)
        config_layout.addWidget(self.save_config_btn)
        
        # Add config tab to tabs
        self.tabs.addTab(config_tab, "Configuration")
    
    def create_scanner_tab(self):
        # Memory scanner tab
        scanner_tab = QWidget()
        scanner_layout = QVBoxLayout(scanner_tab)
        
        # Scanner controls
        scanner_group = QGroupBox("Memory Scanner")
        scanner_control_layout = QGridLayout()
        
        scanner_control_layout.addWidget(QLabel("Process Name:"), 0, 0)
        self.process_name = QLineEdit("WorldOfWarships.exe")
        scanner_control_layout.addWidget(self.process_name, 0, 1)
        
        # Scan buttons
        self.scan_player_btn = QPushButton("Scan for Player Position")
        self.scan_player_btn.clicked.connect(self.scan_for_player_position)
        scanner_control_layout.addWidget(self.scan_player_btn, 1, 0)
        
        self.scan_entities_btn = QPushButton("Scan for Entity List")
        self.scan_entities_btn.clicked.connect(self.scan_for_entity_list)
        scanner_control_layout.addWidget(self.scan_entities_btn, 1, 1)
        
        self.scan_view_matrix_btn = QPushButton("Scan for View Matrix")
        self.scan_view_matrix_btn.clicked.connect(self.scan_for_view_matrix)
        scanner_control_layout.addWidget(self.scan_view_matrix_btn, 2, 0)
        
        self.launch_scanner_btn = QPushButton("Launch Interactive Scanner")
        self.launch_scanner_btn.clicked.connect(self.launch_interactive_scanner)
        scanner_control_layout.addWidget(self.launch_scanner_btn, 2, 1)
        
        scanner_group.setLayout(scanner_control_layout)
        scanner_layout.addWidget(scanner_group)
        
        # Scanner output
        scanner_output_group = QGroupBox("Scanner Output")
        scanner_output_layout = QVBoxLayout()
        
        self.scanner_output = QTextEdit()
        self.scanner_output.setReadOnly(True)
        scanner_output_layout.addWidget(self.scanner_output)
        
        scanner_output_group.setLayout(scanner_output_layout)
        scanner_layout.addWidget(scanner_output_group)
        
        # Add scanner tab to tabs
        self.tabs.addTab(scanner_tab, "Memory Scanner")
    
    def create_log_tab(self):
        # Log tab
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # Clear button
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(self.clear_log_btn)
        
        # Add log tab to tabs
        self.tabs.addTab(log_tab, "Log")
    
    def create_action_buttons(self):
        # Action buttons at the bottom
        button_layout = QHBoxLayout()
        
        # Connect button
        self.connect_btn = QPushButton("Connect to Game")
        self.connect_btn.clicked.connect(self.connect_to_game)
        button_layout.addWidget(self.connect_btn)
        
        # Start aimbot button
        self.start_btn = QPushButton("Start Aimbot")
        self.start_btn.clicked.connect(self.start_aimbot)
        self.start_btn.setEnabled(False)  # Disabled until connected
        button_layout.addWidget(self.start_btn)
        
        # Exit button
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close_application)
        button_layout.addWidget(self.exit_btn)
        
        # Add button layout to main layout
        self.main_layout.addLayout(button_layout)
    
    def log(self, message):
        """Add a message to the log tab"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def clear_log(self):
        """Clear the log display"""
        self.log_text.clear()
    
    def connect_to_game(self):
        """Connect to the World of Warships process"""
        try:
            self.log("Connecting to game...")
            self.memory_reader = MemoryReader()
            
            # Update UI elements based on connection status
            self.status_labels["connection"].setText("Connected")
            self.status_labels["connection"].setStyleSheet("color: green")
            
            self.connect_btn.setEnabled(False)
            self.start_btn.setEnabled(True)
            
            # Start the status thread
            self.status_thread = StatusThread(self.memory_reader)
            self.status_thread.update_signal.connect(self.update_status)
            self.status_thread.start()
            
            self.log("Successfully connected to World of Warships")
            
        except Exception as e:
            self.log(f"Error connecting to game: {e}")
            self.status_labels["connection"].setText("Connection Failed")
            self.status_labels["connection"].setStyleSheet("color: red")
    
    def start_aimbot(self):
        """Start the aimbot controller"""
        try:
            if not self.aimbot:
                self.log("Starting aimbot controller...")
                
                # Create aimbot controller
                self.aimbot = AimbotController()
                
                # Update UI
                self.start_btn.setText("Stop Aimbot")
                
                # Start the aimbot
                threading.Thread(target=self.aimbot.start, daemon=True).start()
                
                self.log("Aimbot controller started")
            else:
                # Stop the aimbot
                self.log("Stopping aimbot controller...")
                self.aimbot.exit_program()
                self.aimbot = None
                
                # Update UI
                self.start_btn.setText("Start Aimbot")
                
                self.log("Aimbot controller stopped")
        except Exception as e:
            self.log(f"Error controlling aimbot: {e}")
    
    def update_status(self, status):
        """Update UI with status information from the status thread"""
        if "error" in status:
            self.log(f"Status update error: {status['error']}")
            return
            
        # Update player position
        if "player_position" in status and status["player_position"]:
            pos = status["player_position"]
            self.status_labels["player_pos"].setText(f"Player Position: {pos}")
        
        # Update enemy count
        if "enemy_count" in status:
            self.status_labels["enemy_count"].setText(f"Enemy Ships: {status['enemy_count']}")
        
        # Update shell speed
        if "shell_speed" in status:
            self.status_labels["shell_speed"].setText(f"Shell Speed: {status['shell_speed']} m/s")
        
        # Update enemy list display
        if "enemy_ships" in status:
            enemies = status["enemy_ships"]
            enemy_text = ""
            
            for i, enemy in enumerate(enemies):
                pos = enemy["position"]
                vel = enemy["velocity"]
                distance = pos.distance(status["player_position"]) if status["player_position"] else 0
                
                enemy_text += f"Enemy #{i+1}:\n"
                enemy_text += f"  Position: {pos}\n"
                enemy_text += f"  Velocity: {vel}\n"
                enemy_text += f"  Distance: {distance:.1f}m\n\n"
            
            self.enemy_text.setText(enemy_text)
    
    def update_status_manually(self):
        """Called by the timer to update status before we connect"""
        if self.status_thread is None:
            # We're not connected yet, update status manually
            from pymem import Pymem
            try:
                Pymem("WorldOfWarships.exe")
                self.status_labels["connection"].setText("Game Found (Not Connected)")
                self.status_labels["connection"].setStyleSheet("color: orange")
            except:
                self.status_labels["connection"].setText("Game Not Running")
                self.status_labels["connection"].setStyleSheet("color: red")
    
    def toggle_aimbot(self):
        """Toggle aimbot on/off"""
        if self.aimbot:
            self.aimbot.toggle_aimbot()
            is_active = self.aimbot.aimbot_active
            status = "ON" if is_active else "OFF"
            self.status_labels["aimbot_status"].setText(f"Aimbot: {status}")
            if is_active:
                self.status_labels["aimbot_status"].setStyleSheet("color: green")
            else:
                self.status_labels["aimbot_status"].setStyleSheet("")
                
            self.log(f"Aimbot toggled: {status}")
    
    def toggle_overlay(self):
        """Toggle overlay on/off"""
        if self.aimbot:
            self.aimbot.toggle_overlay()
            is_active = self.aimbot.overlay_active
            status = "ON" if is_active else "OFF"
            self.status_labels["overlay_status"].setText(f"Overlay: {status}")
            if is_active:
                self.status_labels["overlay_status"].setStyleSheet("color: green")
            else:
                self.status_labels["overlay_status"].setStyleSheet("")
                
            self.log(f"Overlay toggled: {status}")
    
    def save_config(self):
        """Save configuration"""
        # In a real implementation, this would update the config files
        self.log("Saving configuration...")
        # TODO: Implement actual config saving
        self.log("Configuration saved")
    
    def scan_for_player_position(self):
        """Start a scan for player position"""
        if not self.memory_reader:
            self.log("Please connect to the game first")
            return
            
        self.log("Scanning for player position...")
        self.scanner_output.append("Starting player position scan...\n")
        
        # This would normally be threaded to prevent UI freezing
        try:
            # Import and use scanner
            import memory_scanner
            scanner = memory_scanner.MemoryScanner()
            if scanner.connect_to_game():
                candidates = scanner.scan_for_player_position()
                
                output = "Potential player position addresses:\n"
                for i, candidate in enumerate(candidates):
                    addr = candidate['address']
                    x, y, z = candidate['values']
                    output += f"{i+1}. Address: {hex(addr)}, Values: X={x:.2f}, Y={y:.2f}, Z={z:.2f}\n"
                
                self.scanner_output.append(output)
                self.log(f"Found {len(candidates)} potential player positions")
            else:
                self.scanner_output.append("Failed to connect to game process")
        except Exception as e:
            self.scanner_output.append(f"Error during scan: {e}")
            self.log(f"Scan error: {e}")
    
    def scan_for_entity_list(self):
        """Start a scan for entity list"""
        self.log("Scanning for entity list...")
        self.scanner_output.append("Entity list scan not implemented in this demo")
    
    def scan_for_view_matrix(self):
        """Start a scan for view matrix"""
        self.log("Scanning for view matrix...")
        self.scanner_output.append("View matrix scan not implemented in this demo")
    
    def launch_interactive_scanner(self):
        """Launch the interactive scanner in a terminal"""
        self.log("Launching interactive scanner...")
        
        try:
            # Run the scanner in a separate process
            import subprocess
            import sys
            
            # Get the path to the memory scanner
            scanner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_scanner.py")
            
            # Launch in a new terminal
            subprocess.Popen([sys.executable, scanner_path], 
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
                
            self.log("Interactive scanner launched in new window")
            
            # Update scanner output with instructions
            self.scanner_output.append(
                "Memory scanner launched in a separate window.\n"
                "Use the scanner to find memory addresses for:\n"
                "- Player position\n"
                "- Enemy ships\n"
                "- View matrix\n"
                "- Weapon data\n\n"
                "Once found, addresses can be saved to memory_config.json"
            )
        except Exception as e:
            self.log(f"Error launching scanner: {e}")
            self.scanner_output.append(f"Error: {e}\n"
                                    "Please make sure memory_scanner.py exists in the src directory.")
    
    def close_application(self):
        """Clean up resources and exit"""
        try:
            # Stop threads
            if self.status_thread:
                self.status_thread.stop()
            
            # Stop aimbot
            if self.aimbot:
                self.aimbot.exit_program()
        except:
            pass
            
        self.close()
        
    def launch_memory_scanner(self):
        """Launch the memory scanner - alias for launch_interactive_scanner for compatibility"""
        return self.launch_interactive_scanner()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AimbotControlPanel()
    window.show()
    sys.exit(app.exec_())
