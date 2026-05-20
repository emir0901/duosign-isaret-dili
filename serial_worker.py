import time
from PyQt5.QtCore import QThread, pyqtSignal

# Try to import serial for ESP32 COM port reading
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

class SerialWorker(QThread):
    # Signals to communicate with the GUI
    data_received = pyqtSignal(list)      # Emits a list of 22 float sensor values
    status_changed = pyqtSignal(bool, str) # Emits (is_connected, status_message)
    raw_log_emitted = pyqtSignal(str)     # Emits raw serial log string for troubleshooting

    def __init__(self, port=None, baudrate=115200, use_simulation=False):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.use_simulation = False  # Strictly disabled per user request
        self.running = False
        self.serial_conn = None

    def run(self):
        self.running = True
        self.run_serial()

    def stop(self):
        self.running = False
        if self.serial_conn:
            conn = self.serial_conn
            self.serial_conn = None
            try:
                if conn.is_open:
                    conn.close()
            except Exception:
                pass
        self.status_changed.emit(False, "🔴 SİNYAL YOK")

    def run_serial(self):
        if not SERIAL_AVAILABLE:
            self.status_changed.emit(False, "🔴 Pyserial Yüklü Değil")
            return
            
        if not self.port:
            self.status_changed.emit(False, "🔴 Bağlantı Noktası Seçilmedi")
            return

        try:
            self.status_changed.emit(False, f"🟡 Bağlanıyor: {self.port}...")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            time.sleep(1.0) # Wait for ESP32 auto-reset
            self.status_changed.emit(True, "🟢 BAĞLANDI (ESP32)")
            
            while self.running:
                if self.serial_conn.in_waiting > 0:
                    try:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if not line:
                            continue
                            
                        self.raw_log_emitted.emit(line)
                        
                        # Expected format: 10 flex + 6 Left IMU + 6 Right IMU = 22 comma separated values
                        parts = line.split(',')
                        if len(parts) == 22:
                            values = [float(x) for x in parts]
                            self.data_received.emit(values)
                    except ValueError:
                        continue
                    except Exception as e:
                        self.raw_log_emitted.emit(f"Okuma Hatası: {str(e)}")
                time.sleep(0.005) # Lower latency reading (200Hz max)
                
        except Exception as e:
            self.status_changed.emit(False, f"🔴 Bağlantı Hatası: {str(e)}")
        finally:
            self.stop()
