import sys
try:
    from moviepy.editor import VideoFileClip
    import tkinter as tk
    from tkinter import filedialog
    import speech_recognition as sr
    from pydub import AudioSegment
    from tqdm import tqdm
    import time
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Путь Python:", sys.executable)
    sys.exit(1)
import os

def check_dependencies():
    """Проверяет наличие всех необходимых зависимостей"""
    try:
        import moviepy
        print("✓ moviepy установлен")
        
        import speech_recognition
        print("✓ speech_recognition установлен")
        
        import pyaudio
        print("✓ pyaudio установлен")
        
        import pydub
        print("✓ pydub установлен")
        
        # Проверка FFmpeg
        from moviepy.config import get_setting
        if get_setting("FFMPEG_BINARY"):
            print("✓ FFmpeg найден")
        else:
            print("❌ FFmpeg не найден")
            
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def create_directories():
    """Создаём необходимые директории, если они не существуют"""
    os.makedirs('input', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    os.makedirs('output/chunks', exist_ok=True)  # Добавляем папку для чанков

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

def convert_audio_to_wav(audio_path):
    """Конвертирует аудио файл в формат WAV"""
    try:
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        wav_path = os.path.join('output', f"{audio_name}_temp.wav")
        
        # Загружаем аудио и конвертируем в WAV
        audio = AudioSegment.from_file(audio_path)
        
        # Нормализуем громкость
        audio = audio.normalize()
        
        # Конвертируем в моно если стерео
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Устанавливаем частоту дискретизации
        audio = audio.set_frame_rate(16000)
        
        # Экспортируем в WAV
        audio.export(wav_path, format="wav")
        
        return wav_path
    except Exception as e:
        print(f"Ошибка при конвертации в WAV: {str(e)}")
        return None

def format_text(text):
    """Форматирует текст для лучшей читаемости в формате документа"""
    # Заменяем множественные пробелы на один
    text = ' '.join(text.split())
    
    # Добавляем заголовок
    formatted_text = "ТРАНСКРИПЦИЯ АУДИО\n"
    
    # Настройки форматирования
    max_line_length = 120 # максимальная длина строки
    words = text.split()
    current_line = []
    current_length = 0
    paragraphs = []
    current_paragraph = []
    
    # Разбиваем на строки
    for word in words:
        word_length = len(word)
        
        # Проверяем, поместится ли слово в текущую строку
        if current_length + word_length + 1 <= max_line_length:
            current_line.append(word)
            current_length += word_length + 1
        else:
            # Добавляем готовую строку в текущий параграф
            if current_line:
                current_paragraph.append(' '.join(current_line))
            
            # Начинаем новую строку
            current_line = [word]
            current_length = word_length
            
            # Если параграф достаточно большой, начинаем новый
            if len(current_paragraph) >= 5:  # количество строк в параграфе
                paragraphs.append('\n'.join(current_paragraph))
                current_paragraph = []
    
    # Добавляем последнюю строку и параграф
    if current_line:
        current_paragraph.append(' '.join(current_line))
    if current_paragraph:
        paragraphs.append('\n'.join(current_paragraph))
    
    # Собираем финальный текст
    formatted_text += '\n\n'.join(paragraphs)
    
    # Добавляем статистику
    formatted_text += f"Количество строк: {sum(len(p.split('\n')) for p in paragraphs)}\n"
    formatted_text += f"Количество слов: {len(words)}\n"
    formatted_text += f"Количество символов: {len(text)}\n"
    formatted_text += f"Количество параграфов: {len(paragraphs)}\n"
    
    return formatted_text

def save_audio_chunk(audio_segment, chunk_number, original_filename):
    """Сохраняет часть аудио в отдельный файл"""
    try:
        chunk_name = f"{os.path.splitext(original_filename)[0]}_chunk_{chunk_number}.wav"
        chunk_path = os.path.join('output', 'chunks', chunk_name)
        audio_segment.export(chunk_path, format="wav")
        return chunk_path
    except Exception as e:
        print(f"Ошибка при сохранении чанка: {str(e)}")
        return None

def audio_to_text(audio_path):
    """Преобразует аудио в текст"""
    try:
        print("\nПодготовка к обработке аудио...")
        
        # Конвертируем в WAV если файл не в этом формате
        if not audio_path.lower().endswith('.wav'):
            print("Конвертация в WAV формат...")
            audio_path = convert_audio_to_wav(audio_path)
            if not audio_path:
                return False

        # Загружаем полное аудио для разделения на чанки
        full_audio = AudioSegment.from_wav(audio_path)
        
        # Инициализируем распознаватель
        print("Инициализация распознавателя речи...")
        recognizer = sr.Recognizer()
        max_retries = 5
        
        # Читаем аудио файл
        with sr.AudioFile(audio_path) as source:
            duration = source.DURATION
            total_chunks = int(duration // 30) + 1
            
            print(f"\nОбщая длительность аудио: {int(duration)} секунд")
            print(f"Количество частей для обработки: {total_chunks}")
            
            chunk_duration = 30 * 1000  # в миллисекундах для pydub
            offset = 0
            full_text = []
            
            with tqdm(total=total_chunks, desc="Прогресс обработки") as pbar:
                while offset < duration * 1000:  # переводим в миллисекунды
                    current_chunk = offset//(chunk_duration) + 1
                    print(f"\nОбработка части {current_chunk}/{total_chunks}")
                    
                    # Вырезаем и сохраняем чанк
                    chunk_audio = full_audio[offset:offset + chunk_duration]
                    chunk_path = save_audio_chunk(chunk_audio, current_chunk, 
                                                os.path.basename(audio_path))
                    print(f"Сохранен чанк: {chunk_path}")
                    
                    # Распознаем текст из сохраненного чанка
                    with sr.AudioFile(chunk_path) as chunk_source:
                        audio = recognizer.record(chunk_source)
                        
                        # Пытаемся распознать текст несколько раз
                        success = False
                        for attempt in range(max_retries):
                            try:
                                print(f"Попытка распознавания {attempt + 1}/{max_retries}...")
                                chunk_text = recognizer.recognize_google(audio, language='ru-RU')
                                print(f"✅ Успешно распознано {len(chunk_text)} символов")
                                full_text.append(chunk_text)
                                success = True
                                break
                            except sr.UnknownValueError:
                                print(f"⚠️ Попытка {attempt + 1}: Не удалось распознать речь")
                                if attempt < max_retries - 1:
                                    print("Повторная попытка через 2 секунды...")
                                    time.sleep(5)
                            except sr.RequestError as e:
                                print(f"❌ Ошибка сервиса распознавания речи: {str(e)}")
                                if attempt < max_retries - 1:
                                    print("Повторная попытка через 5 секунд...")
                                    time.sleep(5)
                        
                        if not success:
                            print(f"❌ Не удалось распознать часть {current_chunk} после {max_retries} попыток")
                            full_text.append(f"[Не удалось распознать часть {current_chunk}]")
                    
                    offset += chunk_duration
                    pbar.update(1)
                    time.sleep(0.1)
        
        # Объединяем весь текст
        text = ' '.join(full_text)
        
        # Форматируем текст
        formatted_text = format_text(text)
        
        # Сохраняем текст в файл
        output_text_path = os.path.join('output', f"{os.path.splitext(os.path.basename(audio_path))[0]}.txt")
        with open(output_text_path, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
        
        print(f"\n✅ Текст успешно сохранен в файл: {output_text_path}")
        print(f"Размер текста: {len(text)} символов")
        print(f"Чанки аудио сохранены в папке: {os.path.join('output', 'chunks')}")
        
        # Удаляем временный WAV файл если он был создан
        if audio_path.endswith('_temp.wav'):
            os.remove(audio_path)
            print("🧹 Временные файлы удалены (кроме чанков)")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {str(e)}")
        return False

def extract_audio(video_path):
    """Извлекает аудио из видео файла"""
    try:
        video_name = os.path.basename(video_path)
        audio_name = os.path.splitext(video_name)[0] + '.mp3'
        audio_path = os.path.join('output', audio_name)
        
        if not os.path.exists(video_path):
            print(f"Ошибка: Файл {video_path} не найден!")
            return None
        
        print(f"Начинаю обработку файла {video_name}...")
        video = VideoFileClip(video_path)
        audio = video.audio
        
        audio.write_audiofile(audio_path)
        
        video.close()
        audio.close()
        
        print(f"Аудио сохранено как {audio_path}")
        return audio_path
        
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        return None

def process_file(file_path):
    """Обрабатывает файл в зависимости от его типа"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    print("\n📂 Начало обработки файла...")
    print(f"📍 Путь к файлу: {file_path}")
    print(f"📝 Тип файла: {file_ext}")
    print(f"📊 Размер файла: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
    
    # Видео форматы
    if file_ext in ['.mp4', '.avi', '.mkv', '.mov']:
        print("\n🎥 1. Обнаружен видео файл. Извлекаю аудио...")
        audio_path = extract_audio(file_path)
        if audio_path:
            print("\n🎵 2. Преобразую аудио в текст...")
            audio_to_text(audio_path)
    
    # Аудио форматы
    elif file_ext in ['.mp3', '.wav', '.ogg', '.m4a', '.wma']:
        print("\n🎵 1. Обнаружен аудио файл. Преобразую в текст...")
        audio_to_text(file_path)
    
    else:
        print("\n❌ Ошибка: Неподдерживаемый формат файла")

def main():
    if not check_dependencies():
        print("Пожалуйста, установите все необходимые зависимости")
        sys.exit(1)
    
    create_directories()
    
    file_path = select_file()
    
    if file_path:
        process_file(file_path)
    else:
        print("Выбор файла отменён")

if __name__ == "__main__":
    main()