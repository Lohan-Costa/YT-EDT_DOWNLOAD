import sys
import os
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QProgressBar, QLabel, QFileDialog, QCheckBox,
                               QComboBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from main import DownloadThread, get_base_path

class VideoDownloader(QWidget):
    def __init__(self):
        super().__init__()
        base_path = get_base_path()
        self.output_path = os.path.join(base_path, 'Downloads')
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        self.sanitize_filename = True
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Ciclo Media Downloader')
        self.setWindowIcon(QIcon('icon.svg'))
        self.setFixedWidth(400)  # Define uma largura fixa
        
        layout = QVBoxLayout()

        # URL input
        self.url_input = QLineEdit(placeholderText="Cole o link do vídeo aqui")
        layout.addWidget(self.url_input)

        # Download options and buttons
        options_layout = QHBoxLayout()
        
        self.download_mode = QComboBox()
        self.download_mode.addItems(["Baixar MP4", "Baixar WAV", "Baixar Sem Converter"])
        self.download_mode.setFixedHeight(32)
        options_layout.addWidget(self.download_mode)

        self.download_btn = QPushButton("Baixar", clicked=self.start_download)
        self.download_btn.setFixedWidth(100)
        options_layout.addWidget(self.download_btn)

        self.settings_btn = QPushButton(clicked=self.toggle_settings)
        self.settings_btn.setIcon(QIcon('gear.svg'))
        self.settings_btn.setFixedSize(QSize(32, 32))
        self.settings_btn.setIconSize(QSize(24, 24))
        options_layout.addWidget(self.settings_btn)

        layout.addLayout(options_layout)

        # Settings area
        self.settings_widget = QWidget()
        settings_layout = QHBoxLayout(self.settings_widget)
        self.location_btn = QPushButton("Local", clicked=self.change_output_location)
        self.sanitize_checkbox = QCheckBox("Adequar nome para rede", checked=True, stateChanged=self.toggle_sanitize)
        settings_layout.addWidget(self.location_btn)
        settings_layout.addWidget(self.sanitize_checkbox)
        self.settings_widget.hide()
        layout.addWidget(self.settings_widget)

        # Progress bars
        self.download_progress_bar = QProgressBar(visible=False)
        self.download_progress_bar.setTextVisible(False)
        layout.addWidget(self.download_progress_bar)

        self.conversion_progress_bar = QProgressBar(visible=False)
        self.conversion_progress_bar.setTextVisible(False)
        layout.addWidget(self.conversion_progress_bar)

        # Cancel button
        self.cancel_btn = QPushButton("Cancelar", clicked=self.cancel_download, visible=False)
        layout.addWidget(self.cancel_btn)

        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)  # Permite quebra de linha
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Developer signature
        signature_label = QLabel('Desenvolvido por: <a href="https://www.linkedin.com/in/lohan-costa/">Lohan Costa, edt.</a>')
        signature_label.setOpenExternalLinks(True)
        signature_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(signature_label)

        self.setLayout(layout)
        self.setStyleSheet(self.get_stylesheet())

    def get_stylesheet(self):
        return """
            QWidget {
                font-family: Arial, sans-serif;
                background-color: #f0f0f0;
            }
            QLineEdit, QPushButton, QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
            }
            QComboBox {
                background-color: #F0F0F0;
                color: #787878;
                border-radius: 4px;
            }
            QPushButton:hover{
                background-color: #566ab1;
            }
            QComboBox:hover {
                background-color: #ececec;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 40px;
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            QComboBox::down-arrow {
                image: url('down.svg');
                width: 20px;
                height: 20px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid gray;
                background-color: white;
                selection-background-color: lightgray;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 10px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 10px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #ddd;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #3498db;
                background-color: #3498db;
            }
        """

    def toggle_settings(self):
        self.settings_widget.setVisible(not self.settings_widget.isVisible())

    def toggle_sanitize(self, state):
        self.sanitize_filename = state == Qt.Checked

    def start_download(self):
        url = self.url_input.text()
        if not url:
            self.status_label.setText("Por favor, insira um link válido.")
            return

        self.download_btn.setEnabled(False)
        self.settings_btn.setEnabled(False)
        self.download_progress_bar.show()
        self.download_progress_bar.setValue(0)
        self.conversion_progress_bar.hide()
        self.conversion_progress_bar.setValue(0)
        self.cancel_btn.show()
        self.status_label.setText("Iniciando download...")

        download_mode = self.download_mode.currentText()
        self.download_thread = DownloadThread(url, self.output_path, download_mode, self.sanitize_filename)
        self.download_thread.download_progress.connect(self.update_download_progress)
        self.download_thread.conversion_progress.connect(self.update_conversion_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.log.connect(self.log_message)
        self.download_thread.start()

    def update_download_progress(self, progress, status):
        self.download_progress_bar.setValue(int(progress * 100))
        self.status_label.setText(status)
        QApplication.processEvents()
        
    def reset_ui(self):
        self.download_btn.setEnabled(True)
        self.settings_btn.setEnabled(True)
        self.download_progress_bar.hide()
        self.conversion_progress_bar.hide()
        self.cancel_btn.hide()
        self.url_input.clear()
        self.status_label.clear()

    def update_conversion_progress(self, progress, status):
        self.conversion_progress_bar.show()
        self.conversion_progress_bar.setValue(int(progress * 100))
        self.status_label.setText(status)

    def download_finished(self, success, message):
        self.status_label.setText(message)
        self.reset_ui()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
            self.download_thread.cleanup_temp_files()
        self.status_label.setText("Download cancelado.")
        self.reset_ui()

    def change_output_location(self):
        new_path = QFileDialog.getExistingDirectory(self, "Selecione o local para salvar os vídeos")
        if new_path:
            self.output_path = new_path
            self.status_label.setText(f"Local de salvamento alterado para: {self.output_path}")

    def log_message(self, message):
        print(f"Log: {message}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Ciclo Media Downloader")
    ex = VideoDownloader()
    ex.show()
    sys.exit(app.exec())