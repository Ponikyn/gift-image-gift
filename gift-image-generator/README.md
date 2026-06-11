# GIFT Image Generator

Небольшая утилита для генерации изображений вопросов из GIFT и упаковки результатов в архив.

Установка зависимостей

Windows (PowerShell):

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

macOS / Linux (bash):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Есть вспомогательные скрипты:

- `install_deps.ps1` — создаёт `.venv` и устанавливает зависимости в Windows PowerShell.
- `install_deps.sh` — аналог для macOS/Linux.

Поддержка drag-and-drop

- В GUI можно перетаскивать GIFT файл на поле "GIFT файл".
- Нажмите на поле "Папка с картинками" и перетащите папку с изображениями или файл из папки.
- Если drag-and-drop не работает, установите зависимость: `pip install tkinterdnd2` или `pip install -r requirements.txt`.

Запуск приложения

После активации виртуального окружения запустите:

```bash
python gui.py
```

Сборка в исполняемый файл (опционально)

```bash
pyinstaller --onedir --windowed --distpath exe --workpath build gui.py
```

Подсказки

- `tkinter` обычно поставляется вместе с CPython — ничего дополнительно устанавливать не нужно.
- Закрепляйте версии в `requirements.txt`, чтобы избегать несовместимостей у пользователей.
