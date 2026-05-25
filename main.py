# -*- coding: utf-8 -*-
# ==============================================================================
# 🧠 DuoSign - Akıllı İşaret Dili Tanıma Arayüzü & Yapay Zeka Altyapısı
# ✍️ Tasarım & Geliştirici: Recep Emirhan Öztürk (emir0901)
# ✉️ İletişim: emrhanozt06@gmail.com
# ==============================================================================

import sys
from PyQt5.QtWidgets import QApplication
from ml_engine import MLEngine
from serial_worker import SerialWorker
from gui import MainAppWindow

def main():
    app = QApplication(sys.argv)
    
    # Apply highly premium dark Fusion style globally
    app.setStyle("Fusion")
    
    # Set workspace path
    workspace_path = "/Users/emir/iki elli işaret dili projesi"
    
    # Initialize Yapay Zeka (ML) Engine
    ml_engine = MLEngine(workspace_path=workspace_path)
    
    # Initialize background serial thread (Defaults to no port, GUI will auto-detect)
    serial_worker = SerialWorker(
        port=None, 
        baudrate=115200, 
        use_simulation=False
    )
    
    # Initialize Main GUI Window (GUI automatically scans, lists, and connects ports on start)
    window = MainAppWindow(ml_engine=ml_engine, serial_worker=serial_worker)
    window.show()
    
    # Execute application
    sys_exit_code = app.exec_()
    
    # Ensure background threads stop cleanly when window closes
    serial_worker.stop()
    serial_worker.wait()
    
    sys.exit(sys_exit_code)

if __name__ == '__main__':
    main()
