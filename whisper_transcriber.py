"""
Модуль для транскрибации аудио с использованием Whisper.
Оптимизирован для работы на компьютерах с ограниченными ресурсами.
"""

import os
import time
import gc
from pydub import AudioSegment
from tqdm import tqdm

# Установка зависимостей
def check_whisper_dependencies():
    """Проверяет и устанавливает зависимости для Whisper"""
    try:
        import whisper
        print("✓ Whisper уже установлен")
        return True
    except ImportError:
        print("Whisper не установлен. Начинаю установку...")
        try:
            import subprocess
            subprocess.check_call(["pip", "install", "openai-whisper"])
            print("✓ Whisper успешно установлен")
            return True
        except Exception as e:
            print(f"❌ Ошибка при установке Whisper: {e}")
            print("Пожалуйста, установите вручную: pip install openai-whisper")
            return False

def prepare_audio_for_whisper(audio_path):
    """Подготавливает аудио для обработки Whisper"""
    try:
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        prepared_path = os.path.join('output', f"{audio_name}_whisper_ready.wav")
        
        # Загружаем аудио
        audio = AudioSegment.from_file(audio_path)
        
        # Нормализуем громкость
        audio = audio.normalize()
        
        # Конвертируем в моно если стерео (Whisper лучше работает с моно)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Устанавливаем частоту дискретизации 16кГц (оптимально для Whisper)
        audio = audio.set_frame_rate(16000)
        
        # Экспортируем в WAV
        audio.export(prepared_path, format="wav")
        
        return prepared_path
    except Exception as e:
        print(f"Ошибка при подготовке аудио для Whisper: {str(e)}")
        return None

def split_audio_for_whisper(audio_path, segment_length_sec=600):
    """Разделяет аудио на сегменты для обработки Whisper"""
    try:
        audio = AudioSegment.from_file(audio_path)
        total_duration_sec = len(audio) / 1000
        
        if total_duration_sec <= segment_length_sec:
            return [audio_path]  # Если файл короткий, не разделяем
        
        # Разделяем на части
        segments = []
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        segments_dir = os.path.join('output', 'whisper_segments')
        os.makedirs(segments_dir, exist_ok=True)
        
        total_segments = int(total_duration_sec / segment_length_sec) + 1
        print(f"Разделяю аудио на {total_segments} сегментов для оптимальной обработки...")
        
        for i in range(total_segments):
            start_ms = i * segment_length_sec * 1000
            end_ms = min((i + 1) * segment_length_sec * 1000, len(audio))
            
            segment = audio[start_ms:end_ms]
            segment_path = os.path.join(segments_dir, f"{base_name}_segment_{i+1}.wav")
            segment.export(segment_path, format="wav")
            segments.append(segment_path)
            
        return segments
    except Exception as e:
        print(f"Ошибка при разделении аудио: {str(e)}")
        return [audio_path]  # В случае ошибки возвращаем исходный файл

def transcribe_with_whisper(audio_path, model_size="base", use_segments=True):
    """
    Преобразует аудио в текст используя Whisper.
    
    Parameters:
    - audio_path: путь к аудиофайлу
    - model_size: размер модели ('tiny', 'base', 'small', 'medium', 'large')
    - use_segments: разделять ли длинные аудио на сегменты
    
    Returns:
    - распознанный текст
    """
    if not check_whisper_dependencies():
        return "Ошибка: Whisper не установлен"

    try:
        # Импортируем whisper только если проверка зависимостей прошла успешно
        import whisper
        
        # Подготавливаем аудио для оптимальной обработки
        prepared_audio = prepare_audio_for_whisper(audio_path)
        if not prepared_audio:
            return "Ошибка при подготовке аудио"
        
        print(f"Загрузка модели Whisper ({model_size})...")
        start_time = time.time()
        
        # Явно указываем использование CPU для слабых компьютеров
        model = whisper.load_model(model_size, device="cpu")
        
        print(f"Модель загружена за {time.time() - start_time:.2f} секунд")
        
        full_text = ""
        
        # Если файл длинный и включено разделение на сегменты
        if use_segments:
            segments = split_audio_for_whisper(prepared_audio)
            
            if len(segments) > 1:
                print(f"Аудио разделено на {len(segments)} сегментов")
                
                for i, segment_path in enumerate(segments):
                    print(f"Обрабатываю сегмент {i+1}/{len(segments)}...")
                    start_time = time.time()
                    
                    # Оптимизированные параметры для слабых компьютеров
                    result = model.transcribe(
                        segment_path, 
                        language="ru",
                        beam_size=3,
                        best_of=1,  # Снижаем для экономии памяти
                        fp16=False,  # Отключаем fp16 для совместимости с CPU
                        verbose=True
                    )
                    
                    segment_text = result["text"]
                    full_text += segment_text + " "
                    
                    print(f"Сегмент {i+1} обработан за {time.time() - start_time:.2f} секунд")
                    print(f"Распознано {len(segment_text)} символов")
                    
                    # Очистка памяти между сегментами
                    gc.collect()
            else:
                # Если сегмент один, обрабатываем напрямую
                start_time = time.time()
                result = model.transcribe(
                    prepared_audio, 
                    language="ru",
                    beam_size=3,
                    best_of=1,
                    fp16=False,
                    verbose=True
                )
                full_text = result["text"]
                print(f"Аудио обработано за {time.time() - start_time:.2f} секунд")
        else:
            # Без разделения на сегменты
            start_time = time.time()
            result = model.transcribe(
                prepared_audio, 
                language="ru",
                beam_size=3,
                best_of=1,
                fp16=False,
                verbose=True
            )
            full_text = result["text"]
            print(f"Аудио обработано за {time.time() - start_time:.2f} секунд")
            
        # Очищаем память
        del model
        gc.collect()
        
        # Удаление временных файлов
        if prepared_audio != audio_path:
            os.remove(prepared_audio)
            
        # Сохраняем результат в файл
        output_text_path = os.path.join('output', f"{os.path.splitext(os.path.basename(audio_path))[0]}_whisper.txt")
        with open(output_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        print(f"Результат сохранен в {output_text_path}")
        
        return full_text
        
    except Exception as e:
        print(f"Ошибка при распознавании с Whisper: {str(e)}")
        return f"Ошибка распознавания: {str(e)}"

def format_whisper_result(text):
    """Форматирует результат распознавания Whisper для лучшей читаемости"""
    # Заменяем множественные пробелы на один
    text = ' '.join(text.split())
    
    # Добавляем заголовок
    formatted_text = "ТРАНСКРИПЦИЯ АУДИО (WHISPER)\n\n"
    
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
    print("Модуль для транскрибации с Whisper")
    print("Этот модуль предназначен для импорта в основной скрипт") 