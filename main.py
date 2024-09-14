import os
import re
import unicodedata
import shutil
import time
import sys
from PySide6.QtCore import QThread, Signal
import yt_dlp
import ffmpeg

def get_base_path():
    if getattr(sys, 'frozen', False):
        # Se estiver executando como aplicativo compilado
        return os.path.dirname(sys.executable)
    else:
        # Se estiver executando como script
        return os.path.dirname(os.path.abspath(__file__))

def sanitize_filename(filename):
    filename = unicodedata.normalize('NFD', str(filename)).encode('ASCII', 'ignore').decode()
    filename = filename.replace(' ', '_')
    filename = re.sub(r'[^\w\-_\.]', '_', filename).strip().upper()
    filename = re.sub(r'_+', '_', filename)
    return filename

def set_file_hidden(file_path):
    if os.name == 'nt':  # Windows
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(file_path, 2)
    else:  # Unix-based systems
        new_name = os.path.join(os.path.dirname(file_path), '.' + os.path.basename(file_path))
        os.rename(file_path, new_name)

class DownloadThread(QThread):
    download_progress = Signal(float, str)
    conversion_progress = Signal(float, str)
    finished = Signal(bool, str)
    log = Signal(str)

    def __init__(self, url, output_path, download_mode, sanitize=True):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.download_mode = download_mode
        self.sanitize = sanitize
        base_path = get_base_path()
        self.temp_dir = os.path.join(base_path, 'temp')
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            set_file_hidden(self.temp_dir)
        self.total_fragments = 0
        self.downloaded_fragments = 0
        self.video_title = ""
        self.ydl_opts = {
            'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
        }

        if download_mode == "Baixar MP4":
            self.ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif download_mode == "Baixar WAV":
            self.ydl_opts['format'] = 'bestaudio/best'

    def run(self):
        try:
            self.log.emit(f"Iniciando download no modo: {self.download_mode}")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                filename = ydl.prepare_filename(info)

            self.log.emit(f"Download concluído: {filename}")
            self.download_progress.emit(1.0, "Download concluído")

            if self.sanitize:
                filename = self.sanitize_file(filename)

            if self.download_mode == "Baixar MP4" and not filename.lower().endswith('.mp4'):
                filename = self.convert_to_mp4(filename)
            elif self.download_mode == "Baixar WAV":
                filename = self.convert_to_wav(filename)

            final_filename = self.move_to_output(filename)
            self.finished.emit(True, f"Processo concluído com sucesso! Arquivo salvo como: {final_filename}")
        except Exception as e:
            self.log.emit(f"Erro durante o processo: {str(e)}")
            self.finished.emit(False, f"Erro: {str(e)}")
        finally:
            self.cleanup_temp_files()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            if not self.video_title and 'filename' in d:
                self.video_title = os.path.basename(d['filename'])

            if 'total_fragments' in d:
                self.total_fragments = d['total_fragments']
                self.downloaded_fragments = d['fragment_index']
                fragment_progress = self.downloaded_fragments / self.total_fragments
                overall_progress = (fragment_progress + d['downloaded_bytes'] / d['total_bytes']) / 2
                percentage = overall_progress * 100
                self.download_progress.emit(percentage / 100, f"Baixando: {percentage:.1f}% - {self.video_title}")
            else:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total_bytes > 0:
                    percentage = (d['downloaded_bytes'] / total_bytes) * 100
                    self.download_progress.emit(percentage / 100, f"Baixando: {percentage:.1f}% - {self.video_title}")
                else:
                    self.download_progress.emit(-1, f"Baixando... - {self.video_title}")
        elif d['status'] == 'finished':
            self.download_progress.emit(1.0, f"Download concluído - {self.video_title}")

    def sanitize_file(self, filename):
        directory, old_filename = os.path.split(filename)
        name, ext = os.path.splitext(old_filename)
        new_name = sanitize_filename(name)
        new_filename = f"{new_name}{ext}"
        new_path = os.path.join(directory, new_filename)
        if filename != new_path:
            shutil.move(filename, new_path)
            self.log.emit(f"Arquivo renomeado de {old_filename} para {new_filename}")
        return new_path

    def convert_to_mp4(self, input_file):
        output_file = os.path.splitext(input_file)[0] + '.mp4'
        self.log.emit(f"Convertendo para MP4: {input_file}")
        self.conversion_progress.emit(0.0, "Iniciando conversão para MP4")
        try:
            (
                ffmpeg
                .input(input_file)
                .output(output_file, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            os.remove(input_file)
            self.log.emit(f"Conversão para MP4 concluída: {output_file}")
            self.conversion_progress.emit(1.0, "Conversão para MP4 concluída")
            return output_file
        except ffmpeg.Error as e:
            self.log.emit(f"Erro na conversão para MP4: {str(e)}")
            return input_file

    def convert_to_wav(self, input_file):
        output_file = os.path.splitext(input_file)[0] + '.wav'
        self.log.emit(f"Convertendo para WAV: {input_file}")
        self.conversion_progress.emit(0.0, "Iniciando conversão para WAV")
        try:
            (
                ffmpeg
                .input(input_file)
                .output(output_file, acodec='pcm_s16le', ar=44100)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            os.remove(input_file)
            self.log.emit(f"Conversão para WAV concluída: {output_file}")
            self.conversion_progress.emit(1.0, "Conversão para WAV concluída")
            return output_file
        except ffmpeg.Error as e:
            self.log.emit(f"Erro na conversão para WAV: {str(e)}")
            return input_file

    def move_to_output(self, filename):
        destination = os.path.join(self.output_path, os.path.basename(filename))
        shutil.move(filename, destination)
        return destination

    def cleanup_temp_files(self):
        if not os.path.exists(self.temp_dir):
            return

        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                self.log.emit(f"Erro ao remover {file_path}: {str(e)}")

        retry_count = 0
        while os.path.exists(self.temp_dir) and retry_count < 5:
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.log.emit(f"Tentativa {retry_count + 1} de remover diretório temporário falhou: {str(e)}")
                retry_count += 1
                time.sleep(1)

        if os.path.exists(self.temp_dir):
            self.log.emit(f"Não foi possível remover o diretório temporário {self.temp_dir}. Por favor, remova-o manualmente.")

    def terminate(self):
        super().terminate()
        self.cleanup_temp_files()