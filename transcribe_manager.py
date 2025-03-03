"""
Модуль для управления различными методами транскрибации аудио в текст.
Поддерживает Google Speech Recognition, Whisper и Vosk.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import messagebox
import threading

# Проверка наличия зависимостей
try:
    from pydub import AudioSegment
    from tqdm import tqdm
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Некоторые зависимости не установлены.")
    print("Установите необходимые зависимости: pip install pydub tqdm")
    sys.exit(1)

# Импортируем модули для разных методов распознавания
# Они будут загружены по требованию для экономии ресурсов
whisper_module = None
vosk_module = None

def load_whisper_module():
    """Загружает модуль Whisper при необходимости"""
    global whisper_module
    if whisper_module is None:
        try:
            import whisper_transcriber
            whisper_module = whisper_transcriber
            return True
        except ImportError:
            print("Модуль Whisper не найден")
            return False
    return True

def load_vosk_module():
    """Загружает модуль Vosk при необходимости"""
    global vosk_module
    if vosk_module is None:
        try:
            import vosk_transcriber
            vosk_module = vosk_transcriber
            return True
        except ImportError:
            print("Модуль Vosk не найден")
            return False
    return True

def transcribe_with_google(audio_path):
    """Преобразует аудио в текст, используя Google Speech Recognition из main.py"""
    # Это обертка для функции audio_to_text из main.py
    import main
    result = main.audio_to_text(audio_path)
    return result

def transcribe_with_vosk(audio_path):
    """Преобразует аудио в текст, используя Vosk"""
    if not load_vosk_module():
        return False, "Ошибка: Модуль Vosk не найден"
    
    try:
        result_text = vosk_module.transcribe_with_vosk(audio_path)
        formatted_text = vosk_module.format_vosk_result(result_text)
        
        # Сохраняем форматированный текст
        output_path = os.path.join('output', f"{os.path.splitext(os.path.basename(audio_path))[0]}_vosk_formatted.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
            
        return True, result_text
    except Exception as e:
        return False, f"Ошибка Vosk: {str(e)}"

def transcribe_with_whisper(audio_path, model_size="base"):
    """Преобразует аудио в текст, используя Whisper"""
    if not load_whisper_module():
        return False, "Ошибка: Модуль Whisper не найден"
    
    try:
        result_text = whisper_module.transcribe_with_whisper(audio_path, model_size=model_size)
        formatted_text = whisper_module.format_whisper_result(result_text)
        
        # Сохраняем форматированный текст
        output_path = os.path.join('output', f"{os.path.splitext(os.path.basename(audio_path))[0]}_whisper_formatted.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
            
        return True, result_text
    except Exception as e:
        return False, f"Ошибка Whisper: {str(e)}"

def create_directories():
    """Создаём необходимые директории, если они не существуют"""
    os.makedirs('input', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    os.makedirs('output/chunks', exist_ok=True)
    os.makedirs('output/whisper_segments', exist_ok=True)
    os.makedirs('output/vosk_segments', exist_ok=True)

def select_file():
    """Открывает диалоговое окно для выбора файла"""
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Выберите файл",
        filetypes=[
            ("Все поддерживаемые форматы", "*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.ogg *.m4a *.wma"),
            ("Видео файлы", "*.mp4 *.avi *.mkv *.mov"),
            ("Аудио файлы", "*.mp3 *.wav *.ogg *.m4a *.wma"),
            ("Все файлы", "*.*")
        ]
    )
    return file_path

class TranscriptionApp:
    """Графический интерфейс для выбора методов транскрибации"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Транскрибация аудио в текст")
        self.root.geometry("600x450")
        self.root.resizable(True, True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Верхняя рамка для выбора файла
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(file_frame, text="Файл:").pack(side=tk.LEFT)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(file_frame, text="Выбрать", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # Рамка выбора метода
        method_frame = ttk.LabelFrame(self.root, text="Метод распознавания", padding="10")
        method_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.method_var = tk.StringVar(value="google")
        
        ttk.Radiobutton(method_frame, text="Google Speech Recognition (онлайн)", 
                        variable=self.method_var, value="google").pack(anchor=tk.W)
        ttk.Radiobutton(method_frame, text="Whisper (офлайн, качественный)", 
                        variable=self.method_var, value="whisper").pack(anchor=tk.W)
        ttk.Radiobutton(method_frame, text="Vosk (офлайн, быстрый)", 
                        variable=self.method_var, value="vosk").pack(anchor=tk.W)
        
        # Параметры для Whisper
        whisper_frame = ttk.LabelFrame(self.root, text="Параметры Whisper", padding="10")
        whisper_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(whisper_frame, text="Размер модели:").pack(side=tk.LEFT)
        
        self.whisper_model_var = tk.StringVar(value="base")
        whisper_model_combo = ttk.Combobox(whisper_frame, textvariable=self.whisper_model_var, width=15)
        whisper_model_combo['values'] = ('tiny', 'base', 'small', 'medium', 'large')
        whisper_model_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(whisper_frame, text="*tiny и base для слабых компьютеров").pack(side=tk.LEFT, padx=5)
        
        # Кнопки действий
        action_frame = ttk.Frame(self.root, padding="10")
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(action_frame, text="Проверить зависимости", 
                   command=self.check_dependencies).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Начать распознавание", 
                   command=self.start_transcription).pack(side=tk.RIGHT, padx=5)
        
        # Лог выполнения
        log_frame = ttk.LabelFrame(self.root, text="Лог выполнения", padding="10")
        log_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Полоса прокрутки для лога
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов к работе")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=10, pady=5)
    
    def browse_file(self):
        """Открывает диалог выбора файла"""
        file_path = select_file()
        if file_path:
            self.file_path_var.set(file_path)
            self.log(f"Выбран файл: {file_path}")
            
            # Проверяем наличие расширения в списке поддерживаемых
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.mp4', '.avi', '.mkv', '.mov', '.mp3', '.wav', '.ogg', '.m4a', '.wma']:
                self.log("⚠️ Предупреждение: Выбран файл с неподдерживаемым расширением")
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Прокручивает лог до конца
    
    def check_dependencies(self):
        """Проверяет наличие всех необходимых зависимостей"""
        self.log("Проверка зависимостей...")
        
        # Базовые зависимости
        try:
            import pydub
            self.log("✓ pydub установлен")
            
            import tqdm
            self.log("✓ tqdm установлен")
            
            # Проверяем для выбранного метода
            method = self.method_var.get()
            
            if method == "google":
                import speech_recognition
                self.log("✓ speech_recognition установлен")
            
            elif method == "whisper":
                if load_whisper_module():
                    self.log("✓ whisper_transcriber доступен")
                    whisper_module.check_whisper_dependencies()
                else:
                    self.log("❌ whisper_transcriber не найден")
            
            elif method == "vosk":
                if load_vosk_module():
                    self.log("✓ vosk_transcriber доступен")
                    vosk_module.check_vosk_dependencies()
                else:
                    self.log("❌ vosk_transcriber не найден")
            
            # Проверка FFmpeg
            try:
                from moviepy.config import get_setting
                if get_setting("FFMPEG_BINARY"):
                    self.log("✓ FFmpeg найден")
                else:
                    self.log("❌ FFmpeg не найден")
            except:
                self.log("⚠️ Не удалось проверить FFmpeg")
            
            self.log("Проверка зависимостей завершена")
            
        except ImportError as e:
            self.log(f"❌ Ошибка импорта: {e}")
    
    def start_transcription(self):
        """Запускает процесс транскрибации в отдельном потоке"""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showerror("Ошибка", "Выберите файл для обработки")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Ошибка", f"Файл не найден: {file_path}")
            return
        
        # Запускаем обработку в отдельном потоке
        self.status_var.set("Выполняется распознавание...")
        
        # Отключаем кнопки на время выполнения
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.configure(state='disabled')
        
        # Запускаем обработку в отдельном потоке
        threading.Thread(target=self.process_file, args=(file_path,), daemon=True).start()
    
    def process_file(self, file_path):
        """Обрабатывает файл в зависимости от выбранного метода"""
        try:
            create_directories()
            
            # Проверяем расширение файла
            file_ext = os.path.splitext(file_path)[1].lower()
            method = self.method_var.get()
            
            self.log("\n📂 Начало обработки файла...")
            self.log(f"📍 Путь к файлу: {file_path}")
            self.log(f"📝 Тип файла: {file_ext}")
            self.log(f"📊 Размер файла: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
            self.log(f"🔍 Выбранный метод: {method}")
            
            # Для видео сначала извлекаем аудио
            if file_ext in ['.mp4', '.avi', '.mkv', '.mov']:
                self.log("\n🎥 1. Обнаружен видео файл. Извлекаю аудио...")
                import main  # Используем функцию из main.py
                audio_path = main.extract_audio(file_path)
                if not audio_path:
                    raise Exception("Не удалось извлечь аудио из видео")
                self.log(f"✅ Аудио извлечено: {audio_path}")
            else:
                audio_path = file_path
            
            # Выполняем транскрибацию в зависимости от метода
            self.log(f"\n🎵 2. Преобразую аудио в текст с помощью {method}...")
            
            if method == "google":
                result = transcribe_with_google(audio_path)
                if result:
                    self.log("✅ Транскрибация успешно завершена")
                else:
                    self.log("❌ Произошла ошибка при транскрибации")
            
            elif method == "whisper":
                model_size = self.whisper_model_var.get()
                self.log(f"Используется модель Whisper: {model_size}")
                success, result = transcribe_with_whisper(audio_path, model_size)
                if success:
                    self.log("✅ Транскрибация с Whisper успешно завершена")
                else:
                    self.log(f"❌ Ошибка Whisper: {result}")
            
            elif method == "vosk":
                success, result = transcribe_with_vosk(audio_path)
                if success:
                    self.log("✅ Транскрибация с Vosk успешно завершена")
                else:
                    self.log(f"❌ Ошибка Vosk: {result}")
            
            else:
                self.log(f"❌ Неизвестный метод: {method}")
            
            self.log("\n✅ Обработка файла завершена")
            self.status_var.set("Готов к работе")
            
            # Показываем сообщение об успешном завершении
            messagebox.showinfo("Готово", "Транскрибация успешно завершена!")
            
        except Exception as e:
            self.log(f"\n❌ Произошла ошибка: {str(e)}")
            self.status_var.set("Ошибка обработки")
            messagebox.showerror("Ошибка", str(e))
        finally:
            # Включаем кнопки обратно
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Button):
                            child.configure(state='normal')

def main():
    """Главная функция программы"""
    create_directories()
    app = TranscriptionApp()
    app.root.mainloop()

if __name__ == "__main__":
    main() 