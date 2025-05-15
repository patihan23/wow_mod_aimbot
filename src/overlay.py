import sys
import threading
import time
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

class Overlay(QWidget):
    def __init__(self):
        # Initialize app in a separate thread
        self.app = None
        self.aim_points = []
        self.running = True
        self.overlay_thread = threading.Thread(target=self.run_overlay)
    
    def run_overlay(self):
        """Run the overlay in a separate thread"""
        self.app = QApplication([])
        super().__init__()
        
        # Set up the overlay window
        self.setWindowTitle("WoWS Overlay")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # Prevents showing in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # Clicks pass through
        
        # Set window to cover entire screen
        screen_rect = self.app.desktop().screenGeometry()
        self.setGeometry(screen_rect)
        
        # Set up timer for regular repainting
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.repaint)
        self.timer.start(16)  # ~60 FPS
        
        # Show the overlay
        self.show()
        
        # Start Qt event loop
        self.app.exec_()
    
    def start(self):
        """Start the overlay thread"""
        self.overlay_thread.start()
    
    def update(self, aim_points):
        """Update the aim points to display"""
        self.aim_points = aim_points
    
    def clear(self):
        """Clear all displayed aim points"""
        self.aim_points = []
        self.repaint()
    
    def destroy(self):
        """Destroy the overlay"""
        self.running = False
        if self.app:
            self.app.quit()
    
    def paintEvent(self, event):
        """Draw the overlay elements"""
        if not self.running:
            return
            
        painter = QPainter(self)
        
        # Set up the painter for anti-aliasing
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw aim points
        for x, y in self.aim_points:
            # Draw outer circle
            painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
            painter.drawEllipse(x - 15, y - 15, 30, 30)
            
            # Draw inner circle
            painter.setPen(QPen(QColor(255, 255, 0, 200), 1))
            painter.drawEllipse(x - 5, y - 5, 10, 10)
            
            # Draw crosshair lines
            painter.setPen(QPen(QColor(0, 255, 0, 200), 1))
            painter.drawLine(x - 20, y, x + 20, y)
            painter.drawLine(x, y - 20, x, y + 20)
            
            # Add some text
            painter.setPen(QColor(255, 255, 255, 200))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x + 20, y - 10, "Predicted")
            painter.drawText(x + 20, y + 5, "Aim Point")

# For standalone testing
if __name__ == "__main__":
    overlay = Overlay()
    overlay.start()
    
    # Simulate some aim points for testing
    test_points = [(500, 500), (800, 600)]
    
    try:
        while True:
            overlay.update(test_points)
            # Move test points around to test updating
            test_points = [(p[0] + 1, p[1]) for p in test_points]
            time.sleep(0.05)
    except KeyboardInterrupt:
        overlay.destroy()
