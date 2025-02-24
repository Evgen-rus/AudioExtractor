import os
from datetime import datetime
from yt_dlp import YoutubeDL
from moviepy.editor import AudioFileClip
from typing import Optional, Tuple
import time
import logging

class YouTubeDownloader:
    def __init__(self, output_dir: str = "output", cookies_file: Optional[str] = None):
        """Инициализация загрузчика"""
        self.logger = logging.getLogger('YouTubeDownloader')
        self.logger.setLevel(logging.DEBUG)
        
        # Настройка вывода логов в файл
        file_handler = logging.FileHandler('youtube_downloader.log', encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Базовые настройки для yt-dlp
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                }
            }
        }
        
        if cookies_file:
            self.ydl_opts['cookiefile'] = cookies_file
            print(f"🍪 Используем cookies из файла: {cookies_file}")
    
    def sanitize_filename(self, filename: str) -> str:
        """Очищает имя файла от недопустимых символов"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    
    def get_video_info(self, url: str) -> Tuple[str, str, int]:
        """Получает информацию о видео"""
        self.logger.debug(f"Попытка получить информацию для URL: {url}")
        try:
            self.logger.info("🔄 Получение информации о видео...")
            with YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    self.logger.info("✅ Успешно получена информация о видео")
                    return (
                        self.sanitize_filename(info['title']),
                        info.get('uploader', 'Unknown'),
                        info.get('duration', 0)
                    )
                self.logger.error("❌ Не удалось получить информацию о видео")
                raise Exception("Не удалось получить информацию о видео")
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации: {str(e)}", exc_info=True)
            print(f"❌ Ошибка при получении информации о видео: {str(e)}")
            return None
    
    def download_audio(self, 
                      url: str, 
                      filename: Optional[str] = None,
                      quality: str = "high") -> Optional[str]:
        """Скачивает аудио с YouTube"""
        self.logger.debug(f"Начало загрузки аудио для URL: {url}")
        try:
            # Генерируем имя файла если не указано
            if not filename:
                info = self.get_video_info(url)
                if info:
                    title, _, _ = info
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{title}.mp3"
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_video.mp3"
            
            output_path = os.path.join(self.output_dir, filename)
            
            # Настройки для загрузки
            download_opts = {
                **self.ydl_opts,
                'outtmpl': output_path[:-4],
                'quiet': False,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192' if quality == 'high' else '128',
                }],
            }
            
            print("📥 Загрузка и конвертация аудио...")
            with YoutubeDL(download_opts) as ydl:
                error_code = ydl.download([url])
                if error_code != 0:
                    raise Exception("Ошибка при скачивании")
            
            if os.path.exists(output_path):
                print(f"✅ Аудио успешно сохранено: {output_path}")
                return output_path
            else:
                raise Exception("Файл не был создан")
                
        except Exception as e:
            self.logger.error(f"Ошибка при скачивании: {str(e)}", exc_info=True)
            print(f"❌ Ошибка при скачивании: {str(e)}")
            return None

def main():
    print("=== YouTube Audio Downloader ===")
    print("Если видео требует авторизации, выполните:")
    print("1. Экспортируйте cookies из браузера (см. https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)")
    print("2. Укажите путь к файлу cookies.txt")
    print("3. Или просто нажмите Enter для продолжения без cookies\n")
    
    cookies_path = input("Путь к файлу cookies (Enter для пропуска): ").strip()
    downloader = YouTubeDownloader(cookies_file=cookies_path if cookies_path else None)
    
    while True:
        print("\n=== Основное меню ===")
        url = input("Введите ссылку на YouTube видео (или 'q' для выхода): ").strip()
        
        if url.lower() == 'q':
            break
        
        # Проверяем формат URL
        if not url.startswith(('https://www.youtube.com/', 'https://youtu.be/')):
            print("❌ Неверный формат ссылки. Используйте ссылки вида:")
            print("   https://www.youtube.com/watch?v=XXXXXXXXXXX")
            print("   https://youtu.be/XXXXXXXXXXX")
            continue
        
        # Обработка видео
        try:
            info = downloader.get_video_info(url)
            if not info:
                print("❌ Не удалось получить информацию о видео")
                continue
            
            title, author, duration = info
            minutes = duration // 60
            seconds = duration % 60
            
            print(f"\nНайдено видео:")
            print(f"Название: {title}")
            print(f"Автор: {author}")
            print(f"Длительность: {minutes}:{seconds:02d}")
            
            # Выбор качества
            while True:
                quality = input("\nВыберите качество (h - высокое, l - низкое): ").strip().lower()
                if quality in ['h', 'l']:
                    break
                print("❌ Пожалуйста, введите 'h' для высокого или 'l' для низкого качества")
            
            # Скачивание
            result = downloader.download_audio(url, quality='high' if quality == 'h' else 'low')
            if result:
                print("\nХотите преобразовать аудио в текст? (y/n)")
                if input().strip().lower() == 'y':
                    # Здесь можно добавить вызов функции для преобразования в текст
                    pass
        
        except Exception as e:
            print(f"\n❌ Ошибка: {str(e)}")
            print("Попробуйте еще раз")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма завершена пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}") 