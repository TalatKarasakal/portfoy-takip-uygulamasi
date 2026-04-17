import sys
from PySide6.QtWidgets import QApplication
from app.views.main_window import MainWindow
from app.database.engine import init_db

def main():
    # İlk kullanım için veritabanını ilklendir
    init_db()

    app = QApplication(sys.argv)
    
    # Varsayılan temel stili uygula
    app.setStyle("Fusion")
            
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
