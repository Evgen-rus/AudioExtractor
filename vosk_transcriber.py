"""
Модуль для транскрибации аудио с использованием Vosk.
Оптимизирован для работы на компьютерах с очень ограниченными ресурсами.
"""

import os
import json
import time
import wave
import subprocess
from pydub import AudioSegment
from tqdm import tqdm

# Настройки
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
VOSK_MODEL_PATH = "vosk-model-small-ru-0.22"

def check_vosk_dependencies():
    """Проверяет и устанавливает зависимости для Vosk"""
    try:
        from vosk import Model, KaldiRecognizer
        print("✓ Vosk уже установлен")
        
        # Проверка наличия модели
        if not os.path.exists(VOSK_MODEL_PATH) and not os.path.exists(f"{VOSK_MODEL_PATH}.zip"):
            print(f"Модель Vosk не найдена. Требуется скачать модель: {VOSK_MODEL_URL}")
            print("Для установки модели выполните следующие команды:")
            print(f"wget {VOSK_MODEL_URL}")
            print(f"unzip {os.path.basename(VOSK_MODEL_URL)}")
            return False
        
        return True
    except ImportError:
        print("Vosk не установлен. Начинаю установку...")
        try:
            import subprocess
            subprocess.check_call(["pip", "install", "vosk"])
            print("✓ Vosk успешно установлен")
            
            # Проверка наличия модели
            if not os.path.exists(VOSK_MODEL_PATH) and not os.path.exists(f"{VOSK_MODEL_PATH}.zip"):
                print(f"Требуется скачать модель: {VOSK_MODEL_URL}")
                print("Для установки модели выполните следующие команды:")
                print(f"wget {VOSK_MODEL_URL}")
                print(f"unzip {os.path.basename(VOSK_MODEL_URL)}")
                return False
            
            return True
        except Exception as e:
            print(f"❌ Ошибка при установке Vosk: {e}")
            print("Пожалуйста, установите вручную: pip install vosk")
            return False

def download_vosk_model():
    """Скачивает модель Vosk для русского языка"""
    try:
        if not os.path.exists(VOSK_MODEL_PATH) and not os.path.exists(f"{VOSK_MODEL_PATH}.zip"):
            print(f"Скачиваю модель Vosk для русского языка...")
            
            # Проверяем наличие wget
            try:
                subprocess.run(["wget", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                has_wget = True
            except:
                has_wget = False
            
            # Скачиваем модель
            if has_wget:
                subprocess.run(["wget", VOSK_MODEL_URL])
                print("Модель скачана. Распаковываю...")
                
                # Проверяем наличие unzip
                try:
                    subprocess.run(["unzip", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    has_unzip = True
                except:
                    has_unzip = False
                
                if has_unzip:
                    subprocess.run(["unzip", os.path.basename(VOSK_MODEL_URL)])
                    print("Модель распакована и готова к использованию")
                    return True
                else:
                    print("❌ Утилита unzip не найдена. Распакуйте файл вручную")
                    return False
            else:
                print("❌ Утилита wget не найдена.")
                print(f"Пожалуйста, скачайте модель вручную: {VOSK_MODEL_URL}")
                print("После скачивания распакуйте архив в текущую директорию")
                return False
        else:
            print("✓ Модель Vosk уже скачана")
            return True
    except Exception as e:
        print(f"❌ Ошибка при скачивании модели: {e}")
        return False

def prepare_audio_for_vosk(audio_path):
    """Подготавливает аудио для обработки Vosk (16кГц, 16бит, моно WAV)"""
    try:
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        prepared_path = os.path.join('output', f"{audio_name}_vosk_ready.wav")
        
        # Загружаем аудио
        audio = AudioSegment.from_file(audio_path)
        
        # Нормализуем громкость
        audio = audio.normalize()
        
        # Конвертируем в моно если стерео
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Устанавливаем частоту дискретизации 16кГц (обязательно для Vosk)
        audio = audio.set_frame_rate(16000)
        
        # Экспортируем в WAV 16бит PCM
        audio.export(prepared_path, format="wav", parameters=["-acodec", "pcm_s16le"])
        
        return prepared_path
    except Exception as e:
        print(f"Ошибка при подготовке аудио для Vosk: {str(e)}")
        return None

def split_audio_for_vosk(audio_path, segment_length_sec=300):
    """Разделяет аудио на сегменты для обработки Vosk"""
    try:
        audio = AudioSegment.from_file(audio_path)
        total_duration_sec = len(audio) / 1000
        
        if total_duration_sec <= segment_length_sec:
            return [audio_path]  # Если файл короткий, не разделяем
        
        # Разделяем на части
        segments = []
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        segments_dir = os.path.join('output', 'vosk_segments')
        os.makedirs(segments_dir, exist_ok=True)
        
        total_segments = int(total_duration_sec / segment_length_sec) + 1
        print(f"Разделяю аудио на {total_segments} сегментов для оптимальной обработки...")
        
        for i in range(total_segments):
            start_ms = i * segment_length_sec * 1000
            end_ms = min((i + 1) * segment_length_sec * 1000, len(audio))
            
            segment = audio[start_ms:end_ms]
            segment_path = os.path.join(segments_dir, f"{base_name}_segment_{i+1}.wav")
            segment.export(segment_path, format="wav", parameters=["-acodec", "pcm_s16le"])
            segments.append(segment_path)
            
        return segments
    except Exception as e:
        print(f"Ошибка при разделении аудио: {str(e)}")
        return [audio_path]  # В случае ошибки возвращаем исходный файл

def transcribe_with_vosk(audio_path, use_segments=True):
    """
    Преобразует аудио в текст, используя Vosk.
    
    Parameters:
    - audio_path: путь к аудиофайлу
    - use_segments: разделять ли длинные аудио на сегменты
    
    Returns:
    - распознанный текст
    """
    if not check_vosk_dependencies():
        return "Ошибка: Vosk не установлен или модель не найдена"
    
    # Проверка наличия модели и попытка скачать
    if not os.path.exists(VOSK_MODEL_PATH):
        if not download_vosk_model():
            return "Ошибка: Не удалось найти или скачать модель Vosk"
    
    try:
        # Импортируем Vosk только если проверка зависимостей прошла успешно
        from vosk import Model, KaldiRecognizer
        
        # Подготавливаем аудио для оптимальной обработки
        prepared_audio = prepare_audio_for_vosk(audio_path)
        if not prepared_audio:
            return "Ошибка при подготовке аудио"
        
        print("Загрузка модели Vosk...")
        start_time = time.time()
        
        # Загружаем модель Vosk
        model = Model(VOSK_MODEL_PATH)
        
        print(f"Модель загружена за {time.time() - start_time:.2f} секунд")
        
        full_text = ""
        
        # Если файл длинный и включено разделение на сегменты
        if use_segments:
            segments = split_audio_for_vosk(prepared_audio)
            
            if len(segments) > 1:
                print(f"Аудио разделено на {len(segments)} сегментов")
                
                for i, segment_path in enumerate(segments):
                    print(f"Обрабатываю сегмент {i+1}/{len(segments)}...")
                    start_time = time.time()
                    
                    # Открываем аудиофайл
                    wf = wave.open(segment_path, "rb")
                    
                    # Проверяем формат
                    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                        print(f"⚠️ Некорректный формат WAV: {segment_path}")
                        print("Должен быть: моно PCM")
                        continue
                    
                    # Создаем распознаватель
                    rec = KaldiRecognizer(model, wf.getframerate())
                    rec.SetWords(True)  # Включаем информацию о словах
                    
                    # Буфер для результата
                    segment_text = ""
                    
                    # Чтение небольшими порциями для экономии памяти
                    chunk_size = 4000  # размер порции в сэмплах
                    
                    # Общее количество порций для прогресс-бара
                    total_chunks = int(wf.getnframes() / chunk_size) + 1
                    
                    with tqdm(total=total_chunks, desc=f"Сегмент {i+1}") as pbar:
                        while True:
                            data = wf.readframes(chunk_size)
                            if len(data) == 0:
                                break
                                
                            if rec.AcceptWaveform(data):
                                part_result = json.loads(rec.Result())
                                segment_text += part_result.get("text", "") + " "
                            
                            pbar.update(1)
                    
                    # Получаем финальный результат сегмента
                    part_result = json.loads(rec.FinalResult())
                    segment_text += part_result.get("text", "")
                    
                    # Добавляем текст сегмента к общему результату
                    full_text += segment_text + " "
                    
                    print(f"Сегмент {i+1} обработан за {time.time() - start_time:.2f} секунд")
                    print(f"Распознано {len(segment_text)} символов")
                    
                    # Закрываем файл
                    wf.close()
            else:
                # Если сегмент один, обрабатываем напрямую
                start_time = time.time()
                
                # Открываем аудиофайл
                wf = wave.open(prepared_audio, "rb")
                
                # Проверяем формат
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                    print(f"⚠️ Некорректный формат WAV: {prepared_audio}")
                    print("Должен быть: моно PCM")
                    return "Ошибка: Некорректный формат аудио"
                
                # Создаем распознаватель
                rec = KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)
                
                # Буфер для результата
                full_text = ""
                
                # Чтение небольшими порциями для экономии памяти
                chunk_size = 4000
                
                # Общее количество порций для прогресс-бара
                total_chunks = int(wf.getnframes() / chunk_size) + 1
                
                with tqdm(total=total_chunks, desc="Распознавание") as pbar:
                    while True:
                        data = wf.readframes(chunk_size)
                        if len(data) == 0:
                            break
                            
                        if rec.AcceptWaveform(data):
                            part_result = json.loads(rec.Result())
                            full_text += part_result.get("text", "") + " "
                        
                        pbar.update(1)
                
                # Получаем финальный результат
                part_result = json.loads(rec.FinalResult())
                full_text += part_result.get("text", "")
                
                # Закрываем файл
                wf.close()
                
                print(f"Аудио обработано за {time.time() - start_time:.2f} секунд")
        else:
            # Без разделения на сегменты (то же самое, что и обработка одного сегмента)
            start_time = time.time()
            
            # Открываем аудиофайл
            wf = wave.open(prepared_audio, "rb")
            
            # Проверяем формат
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                print(f"⚠️ Некорректный формат WAV: {prepared_audio}")
                print("Должен быть: моно PCM")
                return "Ошибка: Некорректный формат аудио"
            
            # Создаем распознаватель
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)
            
            # Буфер для результата
            full_text = ""
            
            # Чтение небольшими порциями для экономии памяти
            chunk_size = 4000
            
            # Общее количество порций для прогресс-бара
            total_chunks = int(wf.getnframes() / chunk_size) + 1
            
            with tqdm(total=total_chunks, desc="Распознавание") as pbar:
                while True:
                    data = wf.readframes(chunk_size)
                    if len(data) == 0:
                        break
                        
                    if rec.AcceptWaveform(data):
                        part_result = json.loads(rec.Result())
                        full_text += part_result.get("text", "") + " "
                    
                    pbar.update(1)
            
            # Получаем финальный результат
            part_result = json.loads(rec.FinalResult())
            full_text += part_result.get("text", "")
            
            # Закрываем файл
            wf.close()
            
            print(f"Аудио обработано за {time.time() - start_time:.2f} секунд")
            
        # Удаление временных файлов
        if prepared_audio != audio_path:
            os.remove(prepared_audio)
            
        # Сохраняем результат в файл
        output_text_path = os.path.join('output', f"{os.path.splitext(os.path.basename(audio_path))[0]}_vosk.txt")
        with open(output_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        print(f"Результат сохранен в {output_text_path}")
        
        return full_text
        
    except Exception as e:
        print(f"Ошибка при распознавании с Vosk: {str(e)}")
        return f"Ошибка распознавания: {str(e)}"

def format_vosk_result(text):
    """Форматирует результат распознавания Vosk для лучшей читаемости"""
    # Заменяем множественные пробелы на один
    text = ' '.join(text.split())
    
    # Добавляем заголовок
    formatted_text = "ТРАНСКРИПЦИЯ АУДИО (VOSK)\n\n"
    
    # Настройки форматирования
    max_line_length = 80
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
            if len(current_paragraph) >= 4:  # количество строк в параграфе
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
    formatted_text += f"\n\nСтатистика:\n"
    formatted_text += f"Количество слов: {len(words)}\n"
    formatted_text += f"Количество символов: {len(text)}\n"
    
    return formatted_text

if __name__ == "__main__":
    # Если файл запущен напрямую, а не импортирован
    print("Модуль для транскрибации с Vosk")
    print("Этот модуль предназначен для импорта в основной скрипт") 