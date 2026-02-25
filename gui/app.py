import os
import sys
import time
import random
import math
import psutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QEasingCurve, QPropertyAnimation, pyqtProperty, QThread, pyqtSignal
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QRadialGradient, 
                        QLinearGradient, QFont, QFontDatabase, QPixmap, QPainterPath)

P_BG_DARK = QColor("#0A0E14")
P_BG_DEEP = QColor("#070A0F")
P_PRIMARY = QColor("#A0C4FF")
P_ACCENT = QColor("#BDB2FF")
P_ACCENT2 = QColor("#CDB4DB")
P_HIGHLIGHT = QColor("#FFC6FF")
P_NEUTRAL = QColor("#4A5568")
P_SUCCESS = QColor("#81C784")
P_PROCESSING = QColor("#64B5F6")
P_LISTENING = QColor("#4CAF50")

class BreathingStar:
    """Individual star with physics-based animation properties"""
    def __init__(self, width, height):
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, height)
        self.base_size = random.uniform(0.6, 2.8)
        self.depth = random.uniform(0.1, 1.0)
        self.speed = 0.002 + (0.015 * (1.0 - self.depth))
        self.twinkle_speed = random.uniform(0.8, 1.5)
        self.twinkle_offset = random.uniform(0, math.pi * 2)
        self.hue = random.uniform(200, 280)
        self.saturation = 0.3 + (0.7 * self.depth)
        self.base_brightness = 0.4 + (0.6 * self.depth)
        
    def update(self, time, width, height):
        self.x = (self.x + self.speed * 150) % width
        
        self.y += math.sin(time * self.twinkle_speed + self.twinkle_offset) * 0.15 * self.depth
        
        if self.y < 0:
            self.y = 0
        elif self.y > height:
            self.y = height
            
    def get_color(self, time):
        pulse = (math.sin(time * self.twinkle_speed + self.twinkle_offset) + 1) * 0.5
        brightness = self.base_brightness + (pulse * 0.3 * self.depth)
        
        hue_shift = math.sin(time * 0.3) * 5
        h = (self.hue + hue_shift) % 360
        s = self.saturation
        v = min(1.0, brightness * 1.2)
        
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
            
        return QColor.fromRgbF(r + m, g + m, b + m)

class BreathingStarfield(QWidget):
    """Cinematic starfield with parallax layers and atmospheric depth"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.setUpdatesEnabled(True)
        self.setMinimumWidth(300)
        
        self.stars = []
        self.nexus_clouds = []
        self.time = 0.0
        
        self._generate_nexus_clouds()
        
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._animate)
        self.timer.start()
        
        self._create_background_gradients()
        
    def _generate_nexus_clouds(self):
        """Generate soft cosmic clouds for atmospheric depth"""
        self.nexus_clouds = []
        for _ in range(15):
            self.nexus_clouds.append({
                'pos': QPointF(random.uniform(0, 1), random.uniform(0, 1)),
                'size': random.uniform(80, 200),
                'opacity': random.uniform(0.03, 0.08),
                'color': random.choice([P_PRIMARY, P_ACCENT, P_ACCENT2, P_HIGHLIGHT])
            })
    
    def _create_background_gradients(self):
        """Create multi-stop gradient for cosmic background"""
        self.bg_gradient = QLinearGradient(0, 0, 0, 1)
        self.bg_gradient.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
        self.bg_gradient.setColorAt(0.0, P_BG_DEEP)
        self.bg_gradient.setColorAt(0.4, QColor("#0C1018"))
        self.bg_gradient.setColorAt(1.0, P_BG_DARK)
    
    def _animate(self):
        """Update star positions and animation state"""
        self.time += 0.03
        width = self.width()
        height = self.height()
        
        if not self.stars and width > 0 and height > 0:
            self._initialize_stars(width, height)
        
        for star in self.stars:
            star.update(self.time, width, height)
        
        self.update()
    
    def _initialize_stars(self, width, height):
        """Generate stars with proper distribution and depth layers"""
        self.stars = []
        star_count = max(120, int(width * height / 1200))
        
        for _ in range(star_count):
            self.stars.append(BreathingStar(width, height))
    
    def paintEvent(self, event):
        """Render the starfield with layered depth effects"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        painter.fillRect(self.rect(), self.bg_gradient)
        
        width = self.width()
        height = self.height()
        
        for cloud in self.nexus_clouds:
            x = cloud['pos'].x() * width
            y = cloud['pos'].y() * height
            size = cloud['size'] * (0.8 + math.sin(self.time * 0.2) * 0.2)
            
            radial = QRadialGradient(x, y, size)
            radial.setColorAt(0.0, cloud['color'].lighter(130))
            radial.setColorAt(0.7, cloud['color'].lighter(110))
            radial.setColorAt(1.0, Qt.GlobalColor.transparent)
            
            painter.setBrush(QBrush(radial))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), size, size)
        
        for star in self.stars:
            size = star.base_size * (1.2 + 0.8 * (1.0 - star.depth))
            color = star.get_color(self.time)
            
            if star.depth > 0.7 and size > 1.8:
                glow_size = size * 2.5
                radial = QRadialGradient(star.x, star.y, glow_size)
                radial.setColorAt(0.0, color)
                radial.setColorAt(0.7, QColor(color.red(), color.green(), color.blue(), 80))
                radial.setColorAt(1.0, Qt.GlobalColor.transparent)
                
                painter.setBrush(QBrush(radial))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(star.x, star.y), glow_size, glow_size)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(star.x, star.y), size * 0.5, size * 0.5)
        
        vignette = QRadialGradient(width/2, height/2, max(width, height) * 0.7)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.85, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(5, 8, 12, 200))
        painter.setBrush(QBrush(vignette))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
    
    def resizeEvent(self, event):
        """Reinitialize stars when size changes significantly"""
        super().resizeEvent(event)
        if self.width() > 0 and self.height() > 0:
            if not hasattr(self, '_last_size') or \
               abs(self.width() - self._last_size[0]) > self._last_size[0] * 0.15 or \
               abs(self.height() - self._last_size[1]) > self._last_size[1] * 0.15:
                self._initialize_stars(self.width(), self.height())
                self._last_size = (self.width(), self.height())
    
    def cleanup(self):
        """Stop animation timer for proper cleanup"""
        if self.timer.isActive():
            self.timer.stop()


class StatusBadge(QFrame):
    """Nexus status indicator with animated glow"""
    
    def __init__(self, status_text="Ready", status_color=P_SUCCESS, parent=None):
        super().__init__(parent)
        self.status_text = status_text
        self.status_color = status_color
        self.glow_intensity = 0.0
        
        self.setObjectName("statusBadge")
        self.setStyleSheet("""
            #statusBadge {
                background: rgba(20, 25, 35, 0.7);
                border-radius: 12px;
                border: 1px solid rgba(100, 130, 180, 0.3);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        self.dot = QWidget()
        self.dot.setFixedSize(12, 12)
        self.dot.setStyleSheet("background: transparent; border-radius: 6px;")
        
        self.label = QLabel(status_text)
        self.label.setFont(QFont("SF Pro Display, Segoe UI, Roboto, Helvetica, Arial", 11, QFont.Weight.Medium))
        self.label.setStyleSheet("color: #E2E8F0;")
        
        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        layout.addStretch()
        
        self.glow_timer = QTimer(self)
        self.glow_timer.setInterval(40)
        self.glow_timer.timeout.connect(self._update_glow)
        self.glow_timer.start()
    
    def _update_glow(self):
        self.glow_intensity = (math.sin(self.glow_timer.interval() / 1000 * 15) + 1) * 0.5
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        glow_radius = 18 + (self.glow_intensity * 6)
        radial = QRadialGradient(18, 14, glow_radius)
        radial.setColorAt(0.0, self.status_color)
        radial.setColorAt(0.7, QColor(self.status_color.red(), self.status_color.green(), self.status_color.blue(), 80))
        radial.setColorAt(1.0, Qt.GlobalColor.transparent)
        
        painter.setBrush(QBrush(radial))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(6 - glow_radius/2, 14 - glow_radius/2, glow_radius, glow_radius))
        
        painter.setBrush(QBrush(self.status_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(12, 10, 8, 8)
    
    def set_status(self, text, color):
        self.status_text = text
        self.status_color = color
        self.label.setText(text)
        self.update()


class NexusMainWindow(QMainWindow):
    """Main application window for the Nexus AI assistant"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus AI • System Monitor")
        self.setMinimumSize(1000, 700)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #05080F;
            }
            QLabel {
                color: #E2E8F0;
            }
            #titleLabel {
                font-size: 28px;
                font-weight: 600;
                color: #A0C4FF;
                letter-spacing: -0.5px;
            }
            #subtitleLabel {
                font-size: 16px;
                color: #A0AEC0;
                margin-top: 4px;
            }
            #metricValue {
                font-size: 32px;
                font-weight: 700;
                margin: 8px 0;
            }
            #metricLabel {
                font-size: 14px;
                color: #A0AEC0;
            }
            #controlPanel {
                background: rgba(20, 28, 40, 0.85);
                border-radius: 20px;
                border: 1px solid rgba(100, 130, 180, 0.2);
            }
            #metricCard {
                background: rgba(30, 38, 55, 0.7);
                border-radius: 16px;
                border: 1px solid rgba(80, 100, 140, 0.2);
            }
        """)
        
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(24)
        
        left_panel = QWidget()
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.starfield = BreathingStarfield()
        self.starfield.setMinimumHeight(500)
        
        overlay_container = QWidget()
        overlay_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(24, 32, 24, 24)
        
        title_label = QLabel("NEXUS AI SYSTEM")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle_label = QLabel("Neural Core Array")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.status_badge = StatusBadge("Operational", P_SUCCESS)
        self.status_badge.setFixedWidth(220)
        
        overlay_layout.addStretch()
        overlay_layout.addWidget(title_label)
        overlay_layout.addWidget(subtitle_label)
        overlay_layout.addSpacing(12)
        overlay_layout.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addStretch()
        
        left_layout.addWidget(self.starfield)
        left_layout.addWidget(overlay_container)
        left_layout.setAlignment(overlay_container, Qt.AlignmentFlag.AlignCenter)
        
        right_panel = QWidget()
        right_panel.setObjectName("controlPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(28, 28, 28, 28)
        right_layout.setSpacing(24)
        
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(20)
        
        self.metric_labels = {}
        for title, key, color in [
            ("CPU Usage", "cpu", P_PRIMARY),
            ("Memory Usage", "ram", P_ACCENT),
            ("Uptime", "uptime", P_SUCCESS)
        ]:
            card = QWidget()
            card.setObjectName("metricCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            
            value_label = QLabel("--")
            value_label.setObjectName("metricValue")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet(f"color: {color.name()};")
            self.metric_labels[key] = value_label
            
            title_label = QLabel(title)
            title_label.setObjectName("metricLabel")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            card_layout.addWidget(value_label)
            card_layout.addWidget(title_label)
            metrics_layout.addWidget(card)
        
        status_details = QWidget()
        status_layout = QVBoxLayout(status_details)
        status_layout.setSpacing(16)
        
        detail_title = QLabel("SYSTEM STATUS")
        detail_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #E2E8F0; margin-bottom: 8px;")
        
        details = [
            ("Core Temperature", "42.3°C", "optimal"),
            ("Memory Allocation", "78.4%", "optimal"),
            ("Network Latency", "18ms", "optimal"),
            ("Security Protocol", "AES-512", "optimal")
        ]
        
        for label, value, status in details:
            row = QHBoxLayout()
            row.setSpacing(12)
            
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("font-size: 14px; color: #A0AEC0;")
            
            val = QLabel(value)
            val.setStyleSheet("font-size: 14px; font-weight: 500; color: #A0C4FF;")
            
            status_dot = QWidget()
            status_dot.setFixedSize(8, 8)
            status_dot.setStyleSheet("background: #38A169; border-radius: 4px;")
            
            row.addWidget(status_dot)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            status_layout.addLayout(row)
        
        status_layout.insertWidget(0, detail_title)
        
        right_layout.addLayout(metrics_layout)
        right_layout.addWidget(status_details)
        right_layout.addStretch()
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        self.setCentralWidget(central_widget)
        
        self._setup_status_simulation()
    
    def _setup_status_simulation(self):
        """Simulate realistic status changes"""
        self.status_sequence = [
            ("Operational", P_SUCCESS),
            ("Processing Data", P_PROCESSING),
            ("Listening for Input", P_LISTENING),
            ("Optimizing Systems", P_ACCENT),
            ("Operational", P_SUCCESS)
        ]
        self.status_index = 0
        
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(4500)
        self.status_timer.timeout.connect(self._cycle_status)
        self.status_timer.start()
    
    def _cycle_status(self):
        self._update_system_metrics()
        
        if hasattr(self, 'status_timer') and not hasattr(self, 'status_changed'):
            self.status_index = (self.status_index + 1) % len(self.status_sequence)
            text, color = self.status_sequence[self.status_index]
            self.status_badge.set_status(text, color)

    def _update_system_metrics(self):
        """Fetch and update actual system metrics"""
        try:
            cpu_percent = psutil.cpu_percent()
            self.metric_labels['cpu'].setText(f"{cpu_percent}%")
            
            ram = psutil.virtual_memory()
            self.metric_labels['ram'].setText(f"{ram.percent}%")
            
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            hours, remainder = divmod(int(uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                uptime_str = f"{hours}h {minutes}m"
            else:
                uptime_str = f"{minutes}m {seconds}s"
            self.metric_labels['uptime'].setText(uptime_str)
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
    
    def closeEvent(self, event):
        """Clean up resources on close"""
        self.starfield.cleanup()
        self.status_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    font = QFont("SF Pro Display, Segoe UI, Roboto, Helvetica, Arial", 10)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)
    
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    
    window = NexusMainWindow()
    window.show()
    
    sys.exit(app.exec())
