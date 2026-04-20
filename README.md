# Gift Image Generator

## Описание
Приложение генерирует изображения из вопросов в GIFT-формате и создаёт архив с результатами.

- Читать GIFT-файл `questions.gift`.
- Формировать картинку для каждого вопроса через PIL (текст + варианты ответа).
- Вставлять встроенные вопросы `<img src="@@PLUGINFILE@@/Image/...">`.
- Создавать итоговый файл `main.txt` с обновлёнными блоками.
- Упаковывать результат в `generated.zip` (включает `main.txt` и папку `Image/`).

## Структура проекта
- `generate_images.py` - основной CLI-скрипт
- `gui.py` - GUI-обёртка (Tkinter)
- `Image/` - папка с исходными картинками (не обязательно если используете exe)

## Требования
- Python 3.8+
- Пакеты:
  - Pillow
  - Click

## Используемые библиотеки
- `Pillow` — работа с изображениями и генерация PNG
- `Click` — парсинг командной строки и удобные опции CLI
- `Tkinter` — встроенная в Python библиотека для GUI (используется в `gui.py`)
- `PyInstaller` — не обязательная, но рекомендуемая для сборки `exe`

Установка:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install Pillow click
```

## Быстрый старт GUI
1. Откройте `gui.py` или запустите:
   ```powershell
   python gui.py
   ```
2. Выберите:
   - GIFT-файл
   - Папку с картинками
   - Папку результата
3. Нажмите кнопку "Генерировать изображения"
4. Получите `generated.zip` в выбранной папке

## Быстрый старт CLI
```powershell
python generate_images.py --in questions.gift --outdir Image --out-gift main.txt
```

## Генерация standalone exe
- Убедитесь, что установлен PyInstaller
- Запуск:
```powershell
pyinstaller --onefile --windowed --distpath exe --workpath build --specpath build gui.py
```
- Результат: `exe/gui.exe`

## Что включает `generated.zip`
- `main.txt` (на выходе)
- `Image/q001.png`, `q002.png`, ...

## Контакты
Если нужны изменения или помощь  создайте issue в репозитории или напишите автору.
