import sys
import os
import difflib
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QCheckBox, QFrame, QTextEdit, QProgressBar,
    QInputDialog, QMessageBox, QDialog, QLineEdit, QRadioButton, QButtonGroup,
    QStackedWidget, QGridLayout, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap

# Try to import serial for scanning ports
try:
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

def get_system_ports():
    """Scans and returns available serial ports on the system."""
    ports = []
    if SERIAL_AVAILABLE:
        try:
            port_list = serial.tools.list_ports.comports()
            for p in port_list:
                p_lower = p.device.lower()
                # Exclude virtual / bluetooth / console / system ports on macOS and Linux
                if not sys.platform.startswith('win'):
                    if "bluetooth" in p_lower or "incoming" in p_lower or "debug" in p_lower or "console" in p_lower or "airpods" in p_lower or "bose" in p_lower or "qcy" in p_lower:
                        continue
                    if not ("usb" in p_lower or "modem" in p_lower or "serial" in p_lower or "cp210" in p_lower or "ch340" in p_lower or "wch" in p_lower or "uart" in p_lower or "ttyusb" in p_lower or "ttyacm" in p_lower):
                        continue
                ports.append(p.device)
        except Exception:
            pass
            
    return ports


class SensorGraphWidget(QFrame):
    """
    📈 Anlık Sinyal Görselleştirici (Real-time Signal Graph Oscilloscope)
    Eldivenden gelen sensör verilerini 60 FPS'te anti-aliasing ile akıcı
    şekilde çizdiren, harici kütüphane gerektirmeyen premium QPainter widget'ı.
    """
    def __init__(self, parent=None, graph_title="Sinyal"):
        super().__init__(parent)
        self.graph_title = graph_title
        self.history_size = 100
        # 5 flex sensör verisi için geçmiş veri tutucu
        self.data_history = [[] for _ in range(5)]
        self.colors = [
            QColor(0, 113, 227),    # SF Blue
            QColor(52, 199, 89),    # SF Green
            QColor(175, 82, 222),   # SF Purple
            QColor(255, 149, 0),    # SF Orange
            QColor(255, 59, 48)     # SF Red
        ]
        self.is_dark = False
        self.setMinimumHeight(150)
        self.setObjectName("sensor_graph")
        self.update_styles()

    def update_styles(self):
        if self.is_dark:
            self.setStyleSheet("""
                QFrame#sensor_graph {
                    background-color: #1c1c1e;
                    border: 1px solid #2c2c2e;
                    border-radius: 14px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#sensor_graph {
                    background-color: #f5f5f7;
                    border: 1px solid #e5e5ea;
                    border-radius: 14px;
                }
            """)
        self.update()

    def update_data(self, sensor_values):
        """Yeni sensör verisi geldiğinde çağrılır. İlk 5 flex sensör verisini ekler."""
        if not sensor_values or len(sensor_values) < 5:
            return
            
        for i in range(5):
            val = sensor_values[i]
            # Sensör değerini geçmişe ekle
            self.data_history[i].append(val)
            if len(self.data_history[i]) > self.history_size:
                self.data_history[i].pop(0)
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QFont
        
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        
        # Arka plan ızgara çizgileri (Grid)
        grid_color = QColor(44, 44, 46, 50) if self.is_dark else QColor(229, 229, 234, 180)
        grid_pen = QPen(grid_color, 1, Qt.DashLine)
        painter.setPen(grid_pen)
        
        # Yatay çizgiler
        for y in range(25, h, 25):
            painter.drawLine(10, y, w - 10, y)
            
        # Dikey çizgiler
        for x in range(30, w, 50):
            painter.drawLine(x, 10, x, h - 10)

        # Sinyal eğrilerini çizdir
        for i in range(5):
            history = self.data_history[i]
            if len(history) < 2:
                continue
                
            path = QPainterPath()
            
            # Dinamik ölçekleme için min/max bul
            min_val = min(history)
            max_val = max(history)
            val_range = max_val - min_val
            if val_range == 0:
                val_range = 1.0
                
            # Yumuşak eğri çizgisini oluştur
            for step, val in enumerate(history):
                # X koordinatını hesapla
                x_coord = 10 + (step / (self.history_size - 1)) * (w - 20)
                # Y koordinatını ters çevirerek (0,0 sol üstte olduğu için) hesapla
                y_coord = (h - 15) - ((val - min_val) / val_range) * (h - 30)
                
                if step == 0:
                    path.moveTo(x_coord, y_coord)
                else:
                    path.lineTo(x_coord, y_coord)
                    
            pen_color = self.colors[i]
            alpha = 230 if self.is_dark else 180
            pen = QPen(QColor(pen_color.red(), pen_color.green(), pen_color.blue(), alpha), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)

        # Draw overlay title on graph
        painter.setFont(QFont("Helvetica Neue", 10, QFont.Bold))
        painter.setPen(QColor(142, 142, 147) if self.is_dark else QColor(142, 142, 147))
        painter.drawText(15, 22, self.graph_title)


class CalibrationDialog(QDialog):
    """
    🧲 Kalibrasyon ve Veri Toplama Merkezi (Apple Light Mode Tasarımı)
    """
    def __init__(self, parent=None, active_sensors=None):
        super().__init__(parent)
        self.active_sensors = active_sensors or [0.0]*22
        self.recording = False
        self.recorded_count = 0
        self.target_count = 800
        self.selected_letter = "A"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Kalibrasyon ve Veri Toplama Merkezi")
        self.setMinimumSize(960, 640)
        
        # Premium macOS Light Mode Dialog Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #1d1d1f;
            }
            QLabel {
                color: #86868b;
                font-size: 13px;
                font-weight: 700;
            }
            QComboBox {
                background-color: #f5f5f7;
                border: 1px solid #d2d2d7;
                border-radius: 10px;
                padding: 8px 12px;
                color: #1d1d1f;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox:focus {
                border-color: #0071e3;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                selection-background-color: #0071e3;
                selection-color: #ffffff;
                color: #1d1d1f;
            }
            
            /* Letter Grid Button Style */
            QPushButton.letter-btn {
                background-color: #f5f5f7;
                color: #1d1d1f;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
                min-width: 44px;
                min-height: 44px;
            }
            QPushButton.letter-btn:hover {
                background-color: #e8e8ed;
                border-color: #0071e3;
            }
            QPushButton.letter-btn:checked {
                background-color: #0071e3;
                color: #ffffff;
                border: none;
            }
            
            /* Primary action button */
            QPushButton#btn_action {
                background-color: #0071e3;
                color: #ffffff;
                border-radius: 12px;
                padding: 12px;
                font-weight: 700;
                font-size: 14px;
                border: none;
            }
            QPushButton#btn_action:hover {
                background-color: #147efb;
            }
            QPushButton#btn_action:pressed {
                background-color: #005bb5;
            }
            
            /* Progress Bar */
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: #e5e5ea;
                color: #1d1d1f;
                height: 12px;
                font-weight: bold;
                font-size: 9px;
            }
            QProgressBar::chunk {
                background-color: #34c759;
                border-radius: 6px;
            }
            
            /* Train button inside dialog */
            QPushButton#btn_train {
                background-color: #af52de;
                color: #ffffff;
                border-radius: 12px;
                padding: 12px;
                font-weight: 700;
                font-size: 14px;
                border: none;
            }
            QPushButton#btn_train:hover {
                background-color: #bf5af2;
            }
            QPushButton#btn_train:pressed {
                background-color: #953fc2;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header Title
        layout.addWidget(QLabel("KALİBRE EDİLECEK HARFİ SEÇİN"))
        
        # Alphabet Grid Layout
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(8)
        
        self.letter_group = QButtonGroup(self)
        self.letter_group.setExclusive(True)
        
        turkish_alphabet = [
            "A", "B", "C", "Ç", "D", "E", "F", "G", "Ğ", "H", "I", "İ", 
            "J", "K", "L", "M", "N", "O", "Ö", "P", "R", "S", "Ş", "T", 
            "U", "Ü", "V", "Y", "Z"
        ]
        
        self.letter_buttons = {}
        for idx, letter in enumerate(turkish_alphabet):
            btn = QPushButton(letter)
            btn.setCheckable(True)
            btn.setProperty("class", "letter-btn")
            btn.setCursor(Qt.PointingHandCursor)
            
            row = idx // 6
            col = idx % 6
            grid_layout.addWidget(btn, row, col)
            
            self.letter_group.addButton(btn)
            self.letter_buttons[letter] = btn
            
            if letter == "A":
                btn.setChecked(True)
            
            btn.clicked.connect(lambda checked, l=letter: self.select_letter(l))
            
        layout.addWidget(grid_widget)

        # Data count setting
        layout.addWidget(QLabel("TOPLANACAK ÖRNEK SAYISI"))
        self.combo_count = QComboBox()
        self.combo_count.addItems(["100", "300", "500", "800", "1000"])
        self.combo_count.setCurrentText("800")
        layout.addWidget(self.combo_count)

        # Status / Sensor Preview
        self.lbl_sensors = QLabel("Anlık Sensör Verileri:\n(Akış bekleniyor...)")
        self.lbl_sensors.setWordWrap(True)
        self.lbl_sensors.setStyleSheet("""
            background-color: #f5f5f7; 
            padding: 12px; 
            border: 1px solid #e5e5ea; 
            border-radius: 12px; 
            font-family: Helvetica Neue, monospace; 
            font-size: 11px; 
            color: #1d1d1f;
        """)
        layout.addWidget(self.lbl_sensors)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Bottom Buttons Layout (Record + Train)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_action = QPushButton("Seçileni Kalibre Et (Veri Topla)")
        self.btn_action.setObjectName("btn_action")
        self.btn_action.clicked.connect(self.toggle_recording)
        self.btn_action.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.btn_action)
        
        self.btn_train = QPushButton("🤖 Modeli Eğit")
        self.btn_train.setObjectName("btn_train")
        self.btn_train.clicked.connect(lambda: self.parent().train_current_model(dialog=self))
        self.btn_train.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.btn_train)
        
        layout.addLayout(btn_layout)

        # Right Panel: İşaret Dili Kılavuzu
        right_panel = QFrame()
        right_panel.setObjectName("right_panel")
        right_panel.setStyleSheet("""
            QFrame#right_panel {
                background-color: #f5f5f7;
                border: 1px solid #d2d2d7;
                border-radius: 14px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        lbl_guide_title = QLabel("TÜRKÇE İŞARET DİLİ KILAVUZU")
        lbl_guide_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #1d1d1f; letter-spacing: 0.5px;")
        lbl_guide_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(lbl_guide_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            /* Custom minimalist scrollbar inside guide */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 4px 0 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #d2d2d7;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #86868b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        lbl_guide_img = QLabel()
        lbl_guide_img.setAlignment(Qt.AlignCenter)

        # Load the guide image from root directory
        workspace_path = self.parent().ml_engine.workspace_path
        img_path = os.path.join(workspace_path, "isaret_rehberi.jpg")
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            # Scale pixmap to fit the width (approx 360px wide) while maintaining aspect ratio
            scaled_pixmap = pixmap.scaledToWidth(360, Qt.SmoothTransformation)
            lbl_guide_img.setPixmap(scaled_pixmap)
        else:
            lbl_guide_img.setText("Kılavuz görseli bulunamadı:\nisaret_rehberi.jpg")
            lbl_guide_img.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 13px;")

        scroll_area.setWidget(lbl_guide_img)
        right_layout.addWidget(scroll_area)

        # Assemble Left and Right inside main QHBoxLayout
        main_layout.addWidget(left_widget, 5)
        main_layout.addWidget(right_panel, 4)

    def select_letter(self, letter):
        self.selected_letter = letter
        self.target_count = int(self.combo_count.currentText())
        self.recorded_count = 0
        self.progress.setValue(0)
        self.recording = True
        self.btn_action.setText("Kalibrasyonu Durdur")
        self.btn_action.setStyleSheet("background-color: #ff3b30;")

    def get_selected_label(self):
        return self.selected_letter.strip().upper()

    def get_selected_filename(self):
        return "harfler.csv"

    def update_sensor_preview(self, sensor_values):
        self.active_sensors = sensor_values
        flex_l = sensor_values[0:5]
        flex_r = sensor_values[5:10]
        acc_l = sensor_values[10:13]
        acc_r = sensor_values[16:19]
        
        preview_text = (
            f"Sol El Flex : {', '.join([str(int(x)) for x in flex_l])}\n"
            f"Sağ El Flex : {', '.join([str(int(x)) for x in flex_r])}\n"
            f"Sol El MPU  : AccX={acc_l[0]:.2f}, AccY={acc_l[1]:.2f}, AccZ={acc_l[2]:.2f}\n"
            f"Sağ El MPU  : AccX={acc_r[0]:.2f}, AccY={acc_r[1]:.2f}, AccZ={acc_r[2]:.2f}"
        )
        self.lbl_sensors.setText(preview_text)

        if self.recording:
            label = self.get_selected_label()
            if not label:
                self.recording = False
                QMessageBox.warning(self, "Hata", "Lütfen geçerli bir harf etiketi seçin!")
                self.btn_action.setText("Seçileni Kalibre Et (Veri Topla)")
                self.btn_action.setStyleSheet("background-color: #0071e3;")
                return

            self.parent().ml_engine.save_sensor_data(
                self.get_selected_filename(),
                self.active_sensors,
                label
            )

            self.recorded_count += 1
            percent = int((self.recorded_count / self.target_count) * 100)
            self.progress.setValue(percent)

            if self.recorded_count >= self.target_count:
                self.recording = False
                self.btn_action.setText("Seçileni Kalibre Et (Veri Topla)")
                self.btn_action.setStyleSheet("background-color: #0071e3;")
                QMessageBox.information(
                    self, "Kalibrasyon Başarılı", 
                    f"'{label}' harf şekli kalibre edildi!\n"
                    f"{self.target_count} adet örnek {self.get_selected_filename()} dosyasına başarıyla kaydedildi!"
                )
                self.recorded_count = 0

    def toggle_recording(self):
        if self.recording:
            self.recording = False
            self.btn_action.setText("Seçileni Kalibre Et (Veri Topla)")
            self.btn_action.setStyleSheet("background-color: #0071e3;")
        else:
            label = self.get_selected_label()
            if not label:
                QMessageBox.warning(self, "Hata", "Lütfen geçerli bir etiket girin!")
                return
            self.target_count = int(self.combo_count.currentText())
            self.recorded_count = 0
            self.progress.setValue(0)
            self.recording = True
            self.btn_action.setText("Kalibrasyonu Durdur")
            self.btn_action.setStyleSheet("background-color: #ff3b30;")


class ModelDrawer(QFrame):
    """
    🧠 Yapay Zeka Model Seçim Çekmecesi (Apple Light Mode Kayan Pencere Tasarımı)
    """
    def __init__(self, parent=None, active_key="MLP"):
        super().__init__(parent)
        self.parent_win = parent
        self.active_key = active_key
        self.drawer_width = 300
        self.is_open = False
        self.init_ui()

    def init_ui(self):
        # Premium macOS Light Mode Slide-out Styling
        self.setObjectName("model_drawer")
        self.setStyleSheet("""
            QFrame#model_drawer {
                background-color: #ffffff;
                border-right: 1px solid #e5e5ea;
            }
            QLabel {
                color: #86868b;
                font-size: 13px;
                font-weight: 700;
            }
            
            /* Model Selection Buttons */
            QPushButton.model-btn {
                background-color: #f5f5f7;
                color: #86868b;
                border: 1px solid #d2d2d7;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 14px 10px;
                text-align: left;
            }
            QPushButton.model-btn:hover {
                background-color: #e8e8ed;
                border-color: #0071e3;
                color: #1d1d1f;
            }
            QPushButton.model-btn:checked {
                background-color: #0071e3;
                color: #ffffff;
                border: none;
                font-weight: 700;
            }
            
            /* Close Drawer Button */
            QPushButton#btn_close_drawer {
                background-color: transparent;
                border: none;
                font-size: 18px;
                color: #86868b;
            }
            QPushButton#btn_close_drawer:hover {
                color: #ff3b30;
            }
        """)

        # Set shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(4, 0)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 24, 20, 24)

        # Header Row: Title & Close Button
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("YAPAY ZEKA MODELLERİ")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #1d1d1f; letter-spacing: -0.5px;")
        
        btn_close = QPushButton("✕")
        btn_close.setObjectName("btn_close_drawer")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.slide_out)
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        
        layout.addLayout(header_layout)
        layout.addSpacing(10)

        # List of models
        self.model_group = QButtonGroup(self)
        self.model_group.setExclusive(True)
        self.model_buttons = {}

        models_data = [
            ("MLP (Ana Model)", "MLP"),
            ("XGBoost Classifier", "XGBoost"),
            ("Random Forest", "Random Forest"),
            ("Support Vector (SVM)", "SVM"),
            ("K-Nearest Neighbors", "KNN"),
            ("Decision Tree", "Decision Tree"),
            ("Naive Bayes (Gaussian)", "Naive Bayes")
        ]

        for idx, (display_name, model_key) in enumerate(models_data):
            btn = QPushButton(f"  {display_name}")
            btn.setCheckable(True)
            btn.setProperty("class", "model-btn")
            btn.setCursor(Qt.PointingHandCursor)
            
            self.model_group.addButton(btn)
            self.model_buttons[model_key] = btn
            
            if model_key == self.active_key:
                btn.setChecked(True)
                
            # Connect model selection slot
            btn.clicked.connect(lambda checked, key=model_key, name=display_name: self.select_model(key, name))
            layout.addWidget(btn)

        layout.addStretch()

        # Set initial size and position
        self.resize(self.drawer_width, self.parent_win.height())
        self.move(-self.drawer_width, 0)
        
        # Setup Animation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    def select_model(self, key, display_name):
        self.active_key = key
        self.parent_win.on_model_selected(key, display_name)
        self.slide_out()

    def slide_in(self):
        self.raise_()
        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(0, 0))
        self.animation.start()
        self.is_open = True

    def slide_out(self):
        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(-self.drawer_width, 0))
        self.animation.start()
        self.is_open = False

    def apply_theme(self, is_dark):
        if is_dark:
            self.setStyleSheet("""
                QFrame#model_drawer {
                    background-color: #2c2c2e;
                    border-right: 1px solid #3a3a3c;
                }
                QLabel {
                    color: #8e8e93;
                    font-size: 13px;
                    font-weight: 700;
                }
                
                /* Model Selection Buttons */
                QPushButton.model-btn {
                    background-color: #3a3a3c;
                    color: #8e8e93;
                    border: 1px solid #48484a;
                    border-radius: 10px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 14px 10px;
                    text-align: left;
                }
                QPushButton.model-btn:hover {
                    background-color: #48484a;
                    border-color: #0a84ff;
                    color: #ffffff;
                }
                QPushButton.model-btn:checked {
                    background-color: #0a84ff;
                    color: #ffffff;
                    border: none;
                    font-weight: 700;
                }
                
                /* Close Drawer Button */
                QPushButton#btn_close_drawer {
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    color: #8e8e93;
                }
                QPushButton#btn_close_drawer:hover {
                    color: #ff453a;
                }
            """)
            if hasattr(self, 'lbl_title'):
                self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;")
        else:
            self.setStyleSheet("""
                QFrame#model_drawer {
                    background-color: #ffffff;
                    border-right: 1px solid #e5e5ea;
                }
                QLabel {
                    color: #86868b;
                    font-size: 13px;
                    font-weight: 700;
                }
                
                /* Model Selection Buttons */
                QPushButton.model-btn {
                    background-color: #f5f5f7;
                    color: #86868b;
                    border: 1px solid #d2d2d7;
                    border-radius: 10px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 14px 10px;
                    text-align: left;
                }
                QPushButton.model-btn:hover {
                    background-color: #e8e8ed;
                    border-color: #0071e3;
                    color: #1d1d1f;
                }
                QPushButton.model-btn:checked {
                    background-color: #0071e3;
                    color: #ffffff;
                    border: none;
                    font-weight: 700;
                }
                
                /* Close Drawer Button */
                QPushButton#btn_close_drawer {
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    color: #86868b;
                }
                QPushButton#btn_close_drawer:hover {
                    color: #ff3b30;
                }
            """)
            if hasattr(self, 'lbl_title'):
                self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #1d1d1f; letter-spacing: -0.5px;")

    def update_layout(self):
        """Update drawer height and position based on parent size changes"""
        h = self.parent_win.height()
        self.setFixedHeight(h)
        if not self.is_open:
            self.move(-self.drawer_width, 0)
        else:
            self.move(0, 0)


class MainAppWindow(QMainWindow):
    def __init__(self, ml_engine, serial_worker):
        super().__init__()
        self.ml_engine = ml_engine
        self.serial_worker = serial_worker
        self.last_predictions = []
        self.voice_feedback = False
        self.is_dark = False
        
        # Initialize default model
        self.active_model_key = "MLP"
        self.active_model_name = "MLP (Ana)"
        
        self.init_ui()
        
        # Initialize sliding drawer for models
        self.model_drawer = ModelDrawer(self, active_key=self.active_model_key)
        self.change_active_model(self.active_model_name)
        
        self.bind_signals()
        
        # Trigger initial auto-connection to the first available port
        self.auto_connect_serial()
        
        # Initialize background scanning loop running every 1 second
        self.port_timer = QTimer(self)
        self.port_timer.timeout.connect(self.auto_scan_ports)
        self.port_timer.start(1000)

    def init_ui(self):
        self.setWindowTitle("DuoSign - Akıllı İşaret Dili Tanıma")
        self.setMinimumSize(1080, 700)
        
        # Premium macOS Light Mode Global Style with Custom Scrollbars & Input styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
            }
            QWidget {
                color: #1d1d1f;
                font-family: Helvetica Neue, Helvetica Neue, Arial, sans-serif;
            }
            
            /* Model Selection Buttons */
            QPushButton.model-btn {
                background-color: #f5f5f7;
                color: #86868b;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 600;
                padding: 8px 4px;
            }
            QPushButton.model-btn:hover {
                background-color: #e8e8ed;
                border-color: #0071e3;
                color: #1d1d1f;
            }
            QPushButton.model-btn:checked {
                background-color: #0071e3;
                color: #ffffff;
                border: none;
                font-weight: 700;
            }
            
            /* Sidebar and Container Cards */
            QFrame#sidebar {
                background-color: #ffffff;
                border: 1px solid #e5e5ea;
                border-radius: 18px;
            }
            QFrame#mid_card, QFrame#right_card {
                background-color: #ffffff;
                border: 1px solid #e5e5ea;
                border-radius: 18px;
            }
            
            /* Modern Input Controls */
            QComboBox {
                background-color: #f5f5f7;
                border: 1px solid #d2d2d7;
                border-radius: 10px;
                padding: 8px 12px;
                color: #1d1d1f;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox:hover {
                border-color: #86868b;
                background-color: #e8e8ed;
            }
            QComboBox:focus {
                border-color: #0071e3;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                selection-background-color: #0071e3;
                selection-color: #ffffff;
                color: #1d1d1f;
                padding: 4px;
            }
            
            /* Checkboxes */
            QCheckBox {
                font-size: 13px;
                font-weight: 500;
                color: #86868b;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #d2d2d7;
                border-radius: 6px;
                background-color: #f5f5f7;
            }
            QCheckBox::indicator:checked {
                background-color: #34c759;
                border-color: #34c759;
            }
            QCheckBox::indicator:hover {
                border-color: #34c759;
            }
            
            /* Elegant scrollbars */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 4px 0 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #d2d2d7;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #86868b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 6px;
                margin: 0 4px 0 4px;
            }
            QScrollBar::handle:horizontal {
                background: #d2d2d7;
                min-width: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #86868b;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # -------------------------------------------------------------
        # LEFT PANEL: ANA KONTROL (Apple Style Sidebar)
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 24, 18, 24)
        sidebar_layout.setSpacing(14)

        # Title
        self.lbl_control_title = QLabel("DuoSign")
        self.lbl_control_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #1d1d1f; letter-spacing: -0.8px;")
        self.lbl_control_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.lbl_control_title)

        # Signal Status Badge
        self.lbl_signal = QLabel("🔴 SİNYAL YOK")
        self.lbl_signal.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 700;
                color: #ff3b30;
                background-color: rgba(255, 59, 48, 0.05);
                border: 1px solid rgba(255, 59, 48, 0.15);
                border-radius: 10px;
                padding: 8px;
            }
        """)
        self.lbl_signal.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.lbl_signal)

        # Hidden Port Selector (automatically scanned and connected in background)
        self.combo_ports = QComboBox(self)
        self.combo_ports.hide()
        self.combo_ports.currentTextChanged.connect(self.on_port_changed)

        # Model Selector group
        self.lbl_model_title = QLabel("YAPAY ZEKA MODELİ")
        self.lbl_model_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px;")
        sidebar_layout.addWidget(self.lbl_model_title)

        # Model selection center button (Apple Purple)
        self.btn_select_model = QPushButton("🧠 Model Seçim Merkezi")
        self.btn_select_model.setCursor(Qt.PointingHandCursor)
        self.btn_select_model.setStyleSheet("""
            QPushButton {
                background-color: #0071e3;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                border-radius: 10px;
                padding: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #147efb;
            }
            QPushButton:pressed {
                background-color: #005bb5;
            }
        """)
        self.btn_select_model.clicked.connect(self.open_model_selection)
        sidebar_layout.addWidget(self.btn_select_model)
        sidebar_layout.addSpacing(4)

        # Calibration button (Apple Blue)
        self.btn_calibrate = QPushButton("🧲 Kalibrasyon Merkezi")
        self.btn_calibrate.setCursor(Qt.PointingHandCursor)
        self.btn_calibrate.setStyleSheet("""
            QPushButton {
                background-color: #0071e3;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                border-radius: 10px;
                padding: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #147efb;
            }
            QPushButton:pressed {
                background-color: #005bb5;
            }
        """)
        self.btn_calibrate.clicked.connect(self.open_calibration)
        sidebar_layout.addWidget(self.btn_calibrate)

        # Voice Feedback Toggle
        self.toggle_voice = QCheckBox("Sesli Geri Bildirim")
        self.toggle_voice.setChecked(False)
        self.toggle_voice.stateChanged.connect(self.on_voice_toggle)
        sidebar_layout.addWidget(self.toggle_voice)

        # Dark Mode Theme Toggle
        self.toggle_dark = QCheckBox("Karanlık Tema (Dark Mode)")
        self.toggle_dark.setChecked(False)
        self.toggle_dark.stateChanged.connect(self.on_theme_toggled)
        sidebar_layout.addWidget(self.toggle_dark)

        # Spacer to push action buttons to bottom left
        sidebar_layout.addStretch()

        # Action Buttons
        self.btn_clear = QPushButton("Ekranı Temizle")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f7;
                color: #1d1d1f;
                font-size: 12px;
                font-weight: 700;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #d2d2d7;
            }
            QPushButton:hover {
                background-color: #e8e8ed;
                border-color: #86868b;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_display)
        sidebar_layout.addWidget(self.btn_clear)

        # Testi Bitir button relocated to right panel

        # Active Model display at bottom
        self.lbl_active_status = QLabel("🟢 MLP (Ana) Aktif")
        self.lbl_active_status.setStyleSheet("font-size: 11px; color: #34c759; font-weight: 600;")
        self.lbl_active_status.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.lbl_active_status)

        main_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # MIDDLE PANEL: ALGILANAN HARF (SF Premium Card)
        # -------------------------------------------------------------
        mid_card = QFrame()
        mid_card.setObjectName("mid_card")
        mid_layout = QVBoxLayout(mid_card)
        mid_layout.setContentsMargins(24, 24, 24, 24)
        mid_layout.setSpacing(15)

        # Title
        self.lbl_mid_title = QLabel("ALGILANAN HARF")
        self.lbl_mid_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #86868b; letter-spacing: 0.5px;")
        self.lbl_mid_title.setAlignment(Qt.AlignCenter)
        mid_layout.addWidget(self.lbl_mid_title)

        mid_layout.addStretch()

        # Display block for letter/word
        self.lbl_letter_display = QLabel("- - -")
        self.lbl_letter_display.setStyleSheet("""
            QLabel {
                font-size: 110px;
                font-weight: 800;
                color: #1d1d1f;
                background-color: #f5f5f7;
                border: 2px solid #e5e5ea;
                border-radius: 20px;
                padding: 30px;
            }
        """)
        self.lbl_letter_display.setAlignment(Qt.AlignCenter)
        mid_layout.addWidget(self.lbl_letter_display)

        mid_layout.addStretch()

        # Confidence bar (Apple System Blue Progress)
        self.progress_confidence = QProgressBar()
        self.progress_confidence.setValue(0)
        self.progress_confidence.setTextVisible(False)
        self.progress_confidence.setFixedHeight(6)
        self.progress_confidence.setStyleSheet("""
            QProgressBar {
                background-color: #f5f5f7;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #0071e3;
                border-radius: 3px;
            }
        """)
        mid_layout.addWidget(self.progress_confidence)

        # Anlık Sinyal Grafik Başlığı
        self.lbl_graph_title = QLabel("ANLIK SİNYAL GÖRSELLEŞTİRİCİ")
        self.lbl_graph_title.setObjectName("lbl_graph_title")
        self.lbl_graph_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b; letter-spacing: 0.5px; margin-top: 10px;")
        self.lbl_graph_title.setAlignment(Qt.AlignCenter)
        mid_layout.addWidget(self.lbl_graph_title)

        # Sensor Graph Widgets (Split for Left and Right Hands)
        graph_layout = QHBoxLayout()
        graph_layout.setSpacing(12)
        
        self.left_sensor_graph = SensorGraphWidget(self, graph_title="SOL EL (Left Hand)")
        self.right_sensor_graph = SensorGraphWidget(self, graph_title="SAĞ EL (Right Hand)")
        
        graph_layout.addWidget(self.left_sensor_graph)
        graph_layout.addWidget(self.right_sensor_graph)
        mid_layout.addLayout(graph_layout)

        main_layout.addWidget(mid_card)

        # -------------------------------------------------------------
        # RIGHT PANEL: HAM KELİME & OTO DÜZELTME
        # -------------------------------------------------------------
        right_card = QFrame()
        right_card.setObjectName("right_card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(12)

        # Ham Kelime Title
        self.lbl_right_title = QLabel("HAM KELİME")
        self.lbl_right_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b; letter-spacing: 0.5px;")
        self.lbl_right_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_right_title)

        # Sentence/sequence field (Apple Blue text inside custom card)
        self.lbl_sentence = QLabel("...")
        self.lbl_sentence.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 700;
                color: #86868b;
                background-color: #f5f5f7;
                border: 1px solid #e5e5ea;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        self.lbl_sentence.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_sentence)

        # Oto Düzeltme Title
        self.lbl_corrected_title = QLabel("OTOMATİK DÜZELTME")
        self.lbl_corrected_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #34c759; letter-spacing: 0.5px;")
        self.lbl_corrected_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_corrected_title)

        # Corrected field (Apple Green text inside glowing card)
        self.lbl_corrected = QLabel("...")
        self.lbl_corrected.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 800;
                color: #ffffff;
                background-color: #34c759;
                border: none;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        self.lbl_corrected.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_corrected)

        # Match label (Apple Green similarity)
        self.lbl_match_title = QLabel("Kelimelerle Eşleşme")
        self.lbl_match_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #34c759;")
        self.lbl_match_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_match_title)

        # Small Apple System Green matching progress bar
        self.progress_match = QProgressBar()
        self.progress_match.setValue(0)
        self.progress_match.setTextVisible(False)
        self.progress_match.setFixedHeight(6)
        self.progress_match.setStyleSheet("""
            QProgressBar {
                background-color: #f5f5f7;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #34c759;
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(self.progress_match)

        right_layout.addSpacing(6)

        # Previous predictions box
        self.lbl_prev_title = QLabel("ÖNCEKİ TAHMİNLER")
        self.lbl_prev_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b;")
        right_layout.addWidget(self.lbl_prev_title)

        self.txt_history = QTextEdit()
        self.txt_history.setReadOnly(True)
        self.txt_history.setText("Hazır...")
        self.txt_history.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f7;
                border: 1px solid #e5e5ea;
                border-radius: 12px;
                padding: 12px;
                color: #1d1d1f;
                font-size: 13px;
            }
        """)
        right_layout.addWidget(self.txt_history)

        # Red button "Testi Bitir" exactly at bottom right (Apple Red)
        self.btn_end = QPushButton("🔴 Testi Bitir")
        self.btn_end.setCursor(Qt.PointingHandCursor)
        self.btn_end.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                border-radius: 10px;
                padding: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff5950;
            }
            QPushButton:pressed {
                background-color: #d12f26;
            }
        """)
        self.btn_end.clicked.connect(self.close)
        right_layout.addWidget(self.btn_end)

        main_layout.addWidget(right_card)

        # Set stretch factors for visual proportion
        main_layout.setStretch(0, 2)
        main_layout.setStretch(1, 4)
        main_layout.setStretch(2, 4)

        # Active calibration dialog instance holder
        self.calibration_dialog = None

    def bind_signals(self):
        self.serial_worker.status_changed.connect(self.update_connection_status)
        self.serial_worker.data_received.connect(self.process_sensor_data)

    def refresh_port_list(self):
        """Scans system for COM ports and repopulates dropdown."""
        self.combo_ports.blockSignals(True)
        self.combo_ports.clear()
        
        ports = get_system_ports()
        if ports:
            self.combo_ports.addItems(ports)
        else:
            self.combo_ports.addItem("Port Yok")
            
        self.combo_ports.blockSignals(False)

    def auto_connect_serial(self):
        """Populates ports, selects first active one, and connects automatically."""
        self.refresh_port_list()
        
        first_port = self.combo_ports.currentText()
        if first_port and first_port != "Port Yok":
            self.on_port_changed(first_port)

    def auto_scan_ports(self):
        """
        Arka planda çalışan ve eldiven takıldığında otomatik bağlanan
        akıllı USB serial port takipçisi (QTimer tarafından her saniye tetiklenir).
        Bluetooth sanal portlarını süzer ve kilitlenmeleri önler.
        """
        if not SERIAL_AVAILABLE:
            return
            
        try:
            port_list = serial.tools.list_ports.comports()
            system_ports = [p.device for p in port_list]
        except Exception:
            system_ports = []
            
        # Fallbacks if empty
        if not system_ports:
            if sys.platform.startswith('win'):
                system_ports = [f"COM{i}" for i in range(1, 10)]
            elif sys.platform.startswith('darwin'):
                system_ports = [f"/dev/cu.usbserial-{i}" for i in range(1, 3)] + [f"/dev/cu.usbmodem-{i}" for i in range(1, 3)]
            else:
                system_ports = [f"/dev/ttyUSB{i}" for i in range(2)] + [f"/dev/ttyACM{i}" for i in range(2)]
                
        # Filtreleme: Bluetooth veya diğer sanal aygıtları hariç tut, USB'leri önceliklendir
        usb_ports = []
        other_ports = []
        for p in system_ports:
            p_lower = p.lower()
            if "bluetooth" in p_lower or "incoming" in p_lower or "airpods" in p_lower or "bose" in p_lower or "debug" in p_lower or "console" in p_lower or "qcy" in p_lower:
                continue
            if "usb" in p_lower or "modem" in p_lower or "serial" in p_lower or "cp210" in p_lower or "ch340" in p_lower or "wch" in p_lower or "uart" in p_lower or "ttyusb" in p_lower or "ttyacm" in p_lower:
                usb_ports.append(p)
            else:
                other_ports.append(p)
                
        # On macOS/Linux, we strictly only allow actual USB-serial port candidates
        if sys.platform.startswith('win'):
            candidate_ports = usb_ports + other_ports
        else:
            candidate_ports = usb_ports
        
        # Mevcut combobox port listesi
        existing_ports = [self.combo_ports.itemText(i) for i in range(self.combo_ports.count())]
        if existing_ports == ["Port Yok"]:
            existing_ports = []
            
        # Eğer liste değiştiyse güncelle
        if set(existing_ports) != set(candidate_ports):
            current_selected = self.combo_ports.currentText()
            self.combo_ports.blockSignals(True)
            self.combo_ports.clear()
            if candidate_ports:
                self.combo_ports.addItems(candidate_ports)
            else:
                self.combo_ports.addItem("Port Yok")
            self.combo_ports.blockSignals(False)
            
            # Bağlantı kararı
            if candidate_ports:
                if current_selected in candidate_ports:
                    self.combo_ports.blockSignals(True)
                    self.combo_ports.setCurrentText(current_selected)
                    self.combo_ports.blockSignals(False)
                else:
                    # Yeni bir eldiven/port takıldı, ilkine otomatik bağlan!
                    new_port = candidate_ports[0]
                    self.combo_ports.blockSignals(True)
                    self.combo_ports.setCurrentText(new_port)
                    self.combo_ports.blockSignals(False)
                    self.on_port_changed(new_port)
            else:
                self.combo_ports.blockSignals(True)
                self.combo_ports.setCurrentText("Port Yok")
                self.combo_ports.blockSignals(False)
                self.on_port_changed("Port Yok")

    def on_port_changed(self, new_port):
        """Gracefully swaps worker connection over to the new port."""
        if not new_port or new_port == "Port Yok":
            self.serial_worker.stop()
            self.serial_worker.wait()
            self.serial_worker.port = None
            return

        self.serial_worker.stop()
        self.serial_worker.wait()
        
        self.serial_worker.port = new_port
        self.serial_worker.start()

    @pyqtSlot(bool, str)
    def update_connection_status(self, is_connected, message):
        if is_connected:
            self.lbl_signal.setText(message)
            self.lbl_signal.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: 700;
                    color: #34c759;
                    background-color: rgba(52, 199, 89, 0.05);
                    border: 1px solid rgba(52, 199, 89, 0.15);
                    border-radius: 10px;
                    padding: 8px;
                }
            """)
        else:
            self.lbl_signal.setText("🔴 SİNYAL YOK")
            self.lbl_signal.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: 700;
                    color: #ff3b30;
                    background-color: rgba(255, 59, 48, 0.05);
                    border: 1px solid rgba(255, 59, 48, 0.15);
                    border-radius: 10px;
                    padding: 8px;
                }
            """)

    @pyqtSlot(list)
    def process_sensor_data(self, sensor_values):
        # Feed the sensor stream to the real-time visualizer graphs (Left Hand: 0-4, Right Hand: 5-9)
        if hasattr(self, 'left_sensor_graph'):
            self.left_sensor_graph.update_data(sensor_values[0:5])
        if hasattr(self, 'right_sensor_graph'):
            self.right_sensor_graph.update_data(sensor_values[5:10])

        if self.calibration_dialog and self.calibration_dialog.isVisible():
            self.calibration_dialog.update_sensor_preview(sensor_values)
            return

        model_key = self.active_model_key

        label, confidence = self.ml_engine.predict(model_key, sensor_values)

        if label and confidence > 0.65:
            self.lbl_letter_display.setText(label)
            if self.is_dark:
                self.lbl_letter_display.setStyleSheet("""
                    QLabel {
                        font-size: 110px;
                        font-weight: 800;
                        color: #0a84ff;
                        background-color: #1c1c1e;
                        border: 2px solid #0a84ff;
                        border-radius: 20px;
                        padding: 30px;
                    }
                """)
            else:
                self.lbl_letter_display.setStyleSheet("""
                    QLabel {
                        font-size: 110px;
                        font-weight: 800;
                        color: #0071e3;
                        background-color: #ffffff;
                        border: 2px solid #0071e3;
                        border-radius: 20px;
                        padding: 30px;
                    }
                """)
            self.progress_confidence.setValue(int(confidence * 100))

            if not self.last_predictions or self.last_predictions[-1] != label:
                self.last_predictions.append(label)
                if len(self.last_predictions) > 12:
                    self.last_predictions.pop(0)

                # Construct raw word
                raw_word = "".join(self.last_predictions).upper().strip()
                self.lbl_sentence.setText(raw_word)

                # Levenshtein/difflib-based Word Auto-correction Engine
                DICTIONARY = []
                words_file = os.path.join(self.ml_engine.workspace_path, "kelimeler.csv")
                if os.path.exists(words_file):
                    try:
                        import csv
                        with open(words_file, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                            if rows:
                                start_idx = 1 if rows[0][0].lower() in ["kelime", "word", "label"] else 0
                                for row in rows[start_idx:]:
                                    if row:
                                        word = row[0].strip().upper()
                                        if word and word not in DICTIONARY:
                                            DICTIONARY.append(word)
                    except Exception as e:
                        print(f"Kelimeler CSV yüklenirken hata: {e}")
                
                # Fallback to default list if file is empty or missing
                if not DICTIONARY:
                    DICTIONARY = [
                        "EMİR", "SERHAT", "NASER", "HARUN", "SELAM", "MERHABA", 
                        "TEŞEKKÜR", "EVET", "HAYIR", "LÜTFEN", "GÖRÜŞÜRÜZ", "TAMAM", 
                        "ELDİVEN", "İŞARET", "DİLİ", "PROJESİ", "NASILSIN", "İYİYİM"
                    ]
                
                best_word = "..."
                best_ratio = 0.0
                
                if raw_word:
                    for word in DICTIONARY:
                        ratio = difflib.SequenceMatcher(None, raw_word, word).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_word = word

                # Update Auto-corrected word and Match progress bar
                if best_ratio >= 0.50:
                    self.lbl_corrected.setText(best_word)
                    self.progress_match.setValue(int(best_ratio * 100))
                else:
                    self.lbl_corrected.setText("...")
                    self.progress_match.setValue(0)

                history_text = "\n".join([f"• Algılandı: {x}" for x in reversed(self.last_predictions)])
                self.txt_history.setText(history_text)

                if self.voice_feedback:
                    self.speak_label(label)
        else:
            self.progress_confidence.setValue(0)
            if self.is_dark:
                self.lbl_letter_display.setStyleSheet("""
                    QLabel {
                        font-size: 110px;
                        font-weight: 800;
                        color: #8e8e93;
                        background-color: #1c1c1e;
                        border: 2px solid #3a3a3c;
                        border-radius: 20px;
                        padding: 30px;
                    }
                """)
            else:
                self.lbl_letter_display.setStyleSheet("""
                    QLabel {
                        font-size: 110px;
                        font-weight: 800;
                        color: #86868b;
                        background-color: #f5f5f7;
                        border: 2px solid #e5e5ea;
                        border-radius: 20px;
                        padding: 30px;
                    }
                """)

    def on_model_selected(self, model_key, display_name):
        self.active_model_key = model_key
        self.active_model_name = display_name
        self.change_active_model(display_name)

    def change_active_model(self, model_name):
        model_key = self.active_model_key
        model_path = os.path.join(self.ml_engine.models_dir, f"{model_key.lower().replace(' ', '_')}_model.pkl")
        if os.path.exists(model_path):
            self.lbl_active_status.setText(f"🟢 {model_name} Aktif")
            self.lbl_active_status.setStyleSheet("font-size: 11px; color: #34c759; font-weight: 600;")
        else:
            self.lbl_active_status.setText(f"🟡 {model_name} (Eğitilmedi)")
            self.lbl_active_status.setStyleSheet("font-size: 11px; color: #ff9500; font-weight: 600;")

    def on_voice_toggle(self, state):
        self.voice_feedback = (state == Qt.Checked)

    def on_theme_toggled(self, state):
        self.apply_theme(state == Qt.Checked)

    def apply_theme(self, is_dark):
        self.is_dark = is_dark
        
        # Update sensor graph widgets theme
        if hasattr(self, 'left_sensor_graph'):
            self.left_sensor_graph.is_dark = is_dark
            self.left_sensor_graph.update_styles()
        if hasattr(self, 'right_sensor_graph'):
            self.right_sensor_graph.is_dark = is_dark
            self.right_sensor_graph.update_styles()
            
        # Update model drawer theme
        if hasattr(self, 'model_drawer'):
            self.model_drawer.apply_theme(is_dark)

        # Update main app stylesheets
        if is_dark:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1c1c1e;
                }
                QWidget {
                    color: #f5f5f7;
                    font-family: Helvetica Neue, Helvetica Neue, Arial, sans-serif;
                }
                
                /* Model Selection Buttons */
                QPushButton.model-btn {
                    background-color: #2c2c2e;
                    color: #8e8e93;
                    border: 1px solid #3a3a3c;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 8px 4px;
                }
                QPushButton.model-btn:hover {
                    background-color: #3a3a3c;
                    border-color: #0a84ff;
                    color: #ffffff;
                }
                QPushButton.model-btn:checked {
                    background-color: #0a84ff;
                    color: #ffffff;
                    border: none;
                    font-weight: 700;
                }
                
                /* Sidebar and Container Cards */
                QFrame#sidebar {
                    background-color: #2c2c2e;
                    border: 1px solid #3a3a3c;
                    border-radius: 18px;
                }
                QFrame#mid_card, QFrame#right_card {
                    background-color: #2c2c2e;
                    border: 1px solid #3a3a3c;
                    border-radius: 18px;
                }
                
                /* Modern Input Controls */
                QComboBox {
                    background-color: #3a3a3c;
                    border: 1px solid #48484a;
                    border-radius: 10px;
                    padding: 8px 12px;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 500;
                }
                QComboBox:hover {
                    border-color: #8e8e93;
                    background-color: #48484a;
                }
                QComboBox:focus {
                    border-color: #0a84ff;
                    background-color: #2c2c2e;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #2c2c2e;
                    border: 1px solid #3a3a3c;
                    border-radius: 8px;
                    selection-background-color: #0a84ff;
                    selection-color: #ffffff;
                    color: #ffffff;
                    padding: 4px;
                }
                
                /* Checkboxes */
                QCheckBox {
                    font-size: 13px;
                    font-weight: 500;
                    color: #8e8e93;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 1px solid #48484a;
                    border-radius: 6px;
                    background-color: #3a3a3c;
                }
                QCheckBox::indicator:checked {
                    background-color: #30d158;
                    border-color: #30d158;
                }
                QCheckBox::indicator:hover {
                    border-color: #30d158;
                }
                
                /* Elegant scrollbars */
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 6px;
                    margin: 4px 0 4px 0;
                }
                QScrollBar::handle:vertical {
                    background: #48484a;
                    min-height: 20px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #8e8e93;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: transparent;
                    height: 6px;
                    margin: 0 4px 0 4px;
                }
                QScrollBar::handle:horizontal {
                    background: #48484a;
                    min-width: 20px;
                    border-radius: 3px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #8e8e93;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
            """)
            
            # Dynamic inline widgets updates
            if hasattr(self, 'lbl_control_title'):
                self.lbl_control_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.8px;")
            if hasattr(self, 'lbl_model_title'):
                self.lbl_model_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8e8e93; text-transform: uppercase; letter-spacing: 0.5px;")
            
            # Select Model & Calibrate buttons
            btn_style = """
                QPushButton {
                    background-color: #0a84ff;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 700;
                    border-radius: 10px;
                    padding: 12px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #3094ff;
                }
                QPushButton:pressed {
                    background-color: #0066cc;
                }
            """
            if hasattr(self, 'btn_select_model'):
                self.btn_select_model.setStyleSheet(btn_style)
            if hasattr(self, 'btn_calibrate'):
                self.btn_calibrate.setStyleSheet(btn_style)
                
            # Clear display button
            if hasattr(self, 'btn_clear'):
                self.btn_clear.setStyleSheet("""
                    QPushButton {
                        background-color: #3a3a3c;
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: 700;
                        border-radius: 10px;
                        padding: 10px;
                        border: 1px solid #48484a;
                    }
                    QPushButton:hover {
                        background-color: #48484a;
                        border-color: #8e8e93;
                    }
                """)
                
            # Middle title
            if hasattr(self, 'lbl_mid_title'):
                self.lbl_mid_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #8e8e93; letter-spacing: 0.5px;")
                
            # Graph title
            if hasattr(self, 'lbl_graph_title'):
                self.lbl_graph_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8e8e93; letter-spacing: 0.5px; margin-top: 10px;")

            # Letter display
            if hasattr(self, 'lbl_letter_display'):
                conf = self.progress_confidence.value()
                if conf > 65:
                    self.lbl_letter_display.setStyleSheet("""
                        QLabel {
                            font-size: 110px;
                            font-weight: 800;
                            color: #0a84ff;
                            background-color: #1c1c1e;
                            border: 2px solid #0a84ff;
                            border-radius: 20px;
                            padding: 30px;
                        }
                    """)
                else:
                    self.lbl_letter_display.setStyleSheet("""
                        QLabel {
                            font-size: 110px;
                            font-weight: 800;
                            color: #8e8e93;
                            background-color: #1c1c1e;
                            border: 2px solid #3a3a3c;
                            border-radius: 20px;
                            padding: 30px;
                        }
                    """)
                    
            # Confidence bar
            if hasattr(self, 'progress_confidence'):
                self.progress_confidence.setStyleSheet("""
                    QProgressBar {
                        background-color: #1c1c1e;
                        border-radius: 3px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background-color: #0a84ff;
                        border-radius: 3px;
                    }
                """)
                
            # Ham Kelime Title & display
            if hasattr(self, 'lbl_right_title'):
                self.lbl_right_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8e8e93; letter-spacing: 0.5px;")
            if hasattr(self, 'lbl_sentence'):
                self.lbl_sentence.setStyleSheet("""
                    QLabel {
                        font-size: 24px;
                        font-weight: 700;
                        color: #8e8e93;
                        background-color: #1c1c1e;
                        border: 1px solid #3a3a3c;
                        border-radius: 12px;
                        padding: 10px;
                    }
                """)
                
            # Oto Düzeltme Title & display
            if hasattr(self, 'lbl_corrected_title'):
                self.lbl_corrected_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #30d158; letter-spacing: 0.5px;")
            if hasattr(self, 'lbl_corrected'):
                self.lbl_corrected.setStyleSheet("""
                    QLabel {
                        font-size: 32px;
                        font-weight: 800;
                        color: #ffffff;
                        background-color: #30d158;
                        border: none;
                        border-radius: 12px;
                        padding: 14px;
                    }
                """)
            if hasattr(self, 'lbl_match_title'):
                self.lbl_match_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #30d158;")
            if hasattr(self, 'progress_match'):
                self.progress_match.setStyleSheet("""
                    QProgressBar {
                        background-color: #1c1c1e;
                        border-radius: 3px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background-color: #30d158;
                        border-radius: 3px;
                    }
                """)
                
            # Previous predictions box
            if hasattr(self, 'lbl_prev_title'):
                self.lbl_prev_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8e8e93;")
            if hasattr(self, 'txt_history'):
                self.txt_history.setStyleSheet("""
                    QTextEdit {
                        background-color: #1c1c1e;
                        border: 1px solid #3a3a3c;
                        border-radius: 12px;
                        padding: 12px;
                        color: #f5f5f7;
                        font-size: 13px;
                    }
                """)
        else:
            # Light Mode
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f7;
                }
                QWidget {
                    color: #1d1d1f;
                    font-family: Helvetica Neue, Helvetica Neue, Arial, sans-serif;
                }
                
                /* Model Selection Buttons */
                QPushButton.model-btn {
                    background-color: #f5f5f7;
                    color: #86868b;
                    border: 1px solid #d2d2d7;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 8px 4px;
                }
                QPushButton.model-btn:hover {
                    background-color: #e8e8ed;
                    border-color: #0071e3;
                    color: #1d1d1f;
                }
                QPushButton.model-btn:checked {
                    background-color: #0071e3;
                    color: #ffffff;
                    border: none;
                    font-weight: 700;
                }
                
                /* Sidebar and Container Cards */
                QFrame#sidebar {
                    background-color: #ffffff;
                    border: 1px solid #e5e5ea;
                    border-radius: 18px;
                }
                QFrame#mid_card, QFrame#right_card {
                    background-color: #ffffff;
                    border: 1px solid #e5e5ea;
                    border-radius: 18px;
                }
                
                /* Modern Input Controls */
                QComboBox {
                    background-color: #f5f5f7;
                    border: 1px solid #d2d2d7;
                    border-radius: 10px;
                    padding: 8px 12px;
                    color: #1d1d1f;
                    font-size: 13px;
                    font-weight: 500;
                }
                QComboBox:hover {
                    border-color: #86868b;
                    background-color: #e8e8ed;
                }
                QComboBox:focus {
                    border-color: #0071e3;
                    background-color: #ffffff;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    border: 1px solid #d2d2d7;
                    border-radius: 8px;
                    selection-background-color: #0071e3;
                    selection-color: #ffffff;
                    color: #1d1d1f;
                    padding: 4px;
                }
                
                /* Checkboxes */
                QCheckBox {
                    font-size: 13px;
                    font-weight: 500;
                    color: #86868b;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 1px solid #d2d2d7;
                    border-radius: 6px;
                    background-color: #f5f5f7;
                }
                QCheckBox::indicator:checked {
                    background-color: #34c759;
                    border-color: #34c759;
                }
                QCheckBox::indicator:hover {
                    border-color: #34c759;
                }
                
                /* Elegant scrollbars */
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 6px;
                    margin: 4px 0 4px 0;
                }
                QScrollBar::handle:vertical {
                    background: #d2d2d7;
                    min-height: 20px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #86868b;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: transparent;
                    height: 6px;
                    margin: 0 4px 0 4px;
                }
                QScrollBar::handle:horizontal {
                    background: #d2d2d7;
                    min-width: 20px;
                    border-radius: 3px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #86868b;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
            """)
            
            # Dynamic inline widgets updates
            if hasattr(self, 'lbl_control_title'):
                self.lbl_control_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #1d1d1f; letter-spacing: -0.8px;")
            if hasattr(self, 'lbl_model_title'):
                self.lbl_model_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px;")
            
            # Select Model & Calibrate buttons
            btn_style = """
                QPushButton {
                    background-color: #0071e3;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 700;
                    border-radius: 10px;
                    padding: 12px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #147efb;
                }
                QPushButton:pressed {
                    background-color: #005bb5;
                }
            """
            if hasattr(self, 'btn_select_model'):
                self.btn_select_model.setStyleSheet(btn_style)
            if hasattr(self, 'btn_calibrate'):
                self.btn_calibrate.setStyleSheet(btn_style)
                
            # Clear display button
            if hasattr(self, 'btn_clear'):
                self.btn_clear.setStyleSheet("""
                    QPushButton {
                        background-color: #f5f5f7;
                        color: #1d1d1f;
                        font-size: 12px;
                        font-weight: 700;
                        border-radius: 10px;
                        padding: 10px;
                        border: 1px solid #d2d2d7;
                    }
                    QPushButton:hover {
                        background-color: #e8e8ed;
                        border-color: #86868b;
                    }
                """)
                
            # Middle title
            if hasattr(self, 'lbl_mid_title'):
                self.lbl_mid_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #86868b; letter-spacing: 0.5px;")
                
            # Graph title
            if hasattr(self, 'lbl_graph_title'):
                self.lbl_graph_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b; letter-spacing: 0.5px; margin-top: 10px;")

            # Letter display
            if hasattr(self, 'lbl_letter_display'):
                conf = self.progress_confidence.value()
                if conf > 65:
                    self.lbl_letter_display.setStyleSheet("""
                        QLabel {
                            font-size: 110px;
                            font-weight: 800;
                            color: #0071e3;
                            background-color: #ffffff;
                            border: 2px solid #0071e3;
                            border-radius: 20px;
                            padding: 30px;
                        }
                    """)
                else:
                    self.lbl_letter_display.setStyleSheet("""
                        QLabel {
                            font-size: 110px;
                            font-weight: 800;
                            color: #86868b;
                            background-color: #f5f5f7;
                            border: 2px solid #e5e5ea;
                            border-radius: 20px;
                            padding: 30px;
                        }
                    """)
                    
            # Confidence bar
            if hasattr(self, 'progress_confidence'):
                self.progress_confidence.setStyleSheet("""
                    QProgressBar {
                        background-color: #f5f5f7;
                        border-radius: 3px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background-color: #0071e3;
                        border-radius: 3px;
                    }
                """)
                
            # Ham Kelime Title & display
            if hasattr(self, 'lbl_right_title'):
                self.lbl_right_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b; letter-spacing: 0.5px;")
            if hasattr(self, 'lbl_sentence'):
                self.lbl_sentence.setStyleSheet("""
                    QLabel {
                        font-size: 24px;
                        font-weight: 700;
                        color: #86868b;
                        background-color: #f5f5f7;
                        border: 1px solid #e5e5ea;
                        border-radius: 12px;
                        padding: 10px;
                    }
                """)
                
            # Oto Düzeltme Title & display
            if hasattr(self, 'lbl_corrected_title'):
                self.lbl_corrected_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #34c759; letter-spacing: 0.5px;")
            if hasattr(self, 'lbl_corrected'):
                self.lbl_corrected.setStyleSheet("""
                    QLabel {
                        font-size: 32px;
                        font-weight: 800;
                        color: #ffffff;
                        background-color: #34c759;
                        border: none;
                        border-radius: 12px;
                        padding: 14px;
                    }
                """)
            if hasattr(self, 'lbl_match_title'):
                self.lbl_match_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #34c759;")
            if hasattr(self, 'progress_match'):
                self.progress_match.setStyleSheet("""
                    QProgressBar {
                        background-color: #f5f5f7;
                        border-radius: 3px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background-color: #34c759;
                        border-radius: 3px;
                    }
                """)
                
            # Previous predictions box
            if hasattr(self, 'lbl_prev_title'):
                self.lbl_prev_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868b;")
            if hasattr(self, 'txt_history'):
                self.txt_history.setStyleSheet("""
                    QTextEdit {
                        background-color: #f5f5f7;
                        border: 1px solid #e5e5ea;
                        border-radius: 12px;
                        padding: 12px;
                        color: #1d1d1f;
                        font-size: 13px;
                    }
                """)

    def speak_label(self, label):
        import threading
        def run_speech():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                for v in voices:
                    if 'tr' in v.id.lower() or 'turkish' in v.name.lower():
                        engine.setProperty('voice', v.id)
                        break
                engine.say(label)
                engine.runAndWait()
            except ImportError:
                pass
            except Exception as e:
                print(f"Ses okuma hatası: {e}")
        
        threading.Thread(target=run_speech, daemon=True).start()

    def open_calibration(self):
        self.calibration_dialog = CalibrationDialog(self)
        self.calibration_dialog.show()

    def open_model_selection(self):
        if self.model_drawer.is_open:
            self.model_drawer.slide_out()
        else:
            self.model_drawer.slide_in()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'model_drawer'):
            self.model_drawer.update_layout()

    def train_current_model(self, dialog=None):
        selected_model = self.active_model_name
        model_key = self.active_model_key
        csv_file = "harfler.csv"
        parent_widget = dialog if dialog is not None else self

        self.lbl_active_status.setText("⏳ Eğitiliyor...")
        
        btn_train_widget = None
        if dialog and hasattr(dialog, 'btn_train'):
            btn_train_widget = dialog.btn_train
        elif hasattr(self, 'btn_train'):
            btn_train_widget = self.btn_train
            
        if btn_train_widget:
            btn_train_widget.setEnabled(False)
            btn_train_widget.setText("⏳ Eğitiliyor...")
        
        from PyQt5.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        success, msg = self.ml_engine.train_model(csv_file, model_key)
        
        if btn_train_widget:
            btn_train_widget.setEnabled(True)
            btn_train_widget.setText("🤖 Modeli Eğit")
            
        self.change_active_model(selected_model)

        if success:
            QMessageBox.information(parent_widget, "Eğitim Başarılı", msg)
        else:
            QMessageBox.warning(parent_widget, "Eğitim Başarısız", msg)

    def clear_display(self):
        self.last_predictions = []
        self.lbl_letter_display.setText("- - -")
        self.lbl_sentence.setText("...")
        self.lbl_corrected.setText("...")
        self.progress_confidence.setValue(0)
        self.progress_match.setValue(0)
        self.txt_history.setText("Hazır...")
        if self.is_dark:
            self.lbl_letter_display.setStyleSheet("""
                QLabel {
                    font-size: 110px;
                    font-weight: 800;
                    color: #8e8e93;
                    background-color: #1c1c1e;
                    border: 2px solid #3a3a3c;
                    border-radius: 20px;
                    padding: 30px;
                }
            """)
        else:
            self.lbl_letter_display.setStyleSheet("""
                QLabel {
                    font-size: 110px;
                    font-weight: 800;
                    color: #86868b;
                    background-color: #f5f5f7;
                    border: 2px solid #e5e5ea;
                    border-radius: 20px;
                    padding: 30px;
                }
            """)
