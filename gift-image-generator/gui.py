import os
import zipfile
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKDND_AVAILABLE = True
except ImportError:
    try:
        from TkinterDnD2 import DND_FILES, TkinterDnD
        TKDND_AVAILABLE = True
    except ImportError:
        DND_FILES = None
        TkinterDnD = None
        TKDND_AVAILABLE = False

from generate_images import parse_gift, render_question, render_answer_image


def create_root():
    if TKDND_AVAILABLE:
        return TkinterDnD.Tk()
    return tk.Tk()

class GiftImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GIFT Image Generator")
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        width = max(500, min(900, int(screen_width * 0.6)))
        height = max(300, min(650, int(screen_height * 0.45)))
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(500, 300)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=0)
        self.root.grid_rowconfigure(5, weight=1)

        # Переменные для путей
        self.gift_file = tk.StringVar()
        self.image_folder = tk.StringVar()
        # output_folder: пустое по умолчанию — пользователь должен выбрать папку вручную
        self.output_folder = tk.StringVar()
        # Флаг: запускать без использования внешних картинок
        self.no_images_var = tk.BooleanVar(value=False)

        # Элементы интерфейса
        tk.Label(root, text="GIFT файл:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.gift_entry = tk.Entry(root, textvariable=self.gift_file, width=40)
        self.gift_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        tk.Button(root, text="Выбрать", command=self.select_gift_file).grid(row=0, column=2, padx=10, pady=5)

        tk.Label(root, text="Папка с картинками:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.image_entry = tk.Entry(root, textvariable=self.image_folder, width=40)
        self.image_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        tk.Button(root, text="Выбрать", command=self.select_image_folder).grid(row=1, column=2, padx=10, pady=5)

        tk.Label(root, text="Выходная папка:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.output_entry = tk.Entry(root, textvariable=self.output_folder, width=40)
        self.output_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        tk.Button(root, text="Выбрать", command=self.select_output_folder).grid(row=2, column=2, padx=10, pady=5)

        # Чекбокс: запуск без картинок
        self.no_images_checkbox = tk.Checkbutton(root, text="Прогон без картинок (не требовать папку с изображениями)", variable=self.no_images_var)
        self.no_images_checkbox.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        # Кнопка генерации
        self.generate_button = tk.Button(root, text="Генерировать изображения", command=self.generate_images, bg="green", fg="white")
        self.generate_button.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=20)

        # Статус
        self.status_label = tk.Label(root, text="")
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

        if TKDND_AVAILABLE:
            self.gift_entry.drop_target_register(DND_FILES)
            self.gift_entry.dnd_bind('<<Drop>>', self.on_gift_drop)
            self.image_entry.drop_target_register(DND_FILES)
            self.image_entry.dnd_bind('<<Drop>>', self.on_image_drop)
            self.output_entry.drop_target_register(DND_FILES)
            self.output_entry.dnd_bind('<<Drop>>', self.on_output_drop)
            self.status_label.config(text="Можно перетаскивать GIFT файл, папку с картинками и выходную папку.")
        else:
            self.status_label.config(text="Drag-and-drop отключён: установите tkinterdnd2 через pip.")

    def select_gift_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("GIFT files", "*.gift"), ("All files", "*.*")])
        if file_path:
            self.gift_file.set(file_path)

    def select_image_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.image_folder.set(folder_path)

    def select_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_folder.set(folder_path)

    def generate_images(self):
        gift_path = self.gift_file.get()
        image_folder = self.image_folder.get()
        output_dir = self.output_folder.get()

        if not gift_path or not os.path.exists(gift_path):
            messagebox.showerror("Ошибка", "Выберите корректный GIFT файл.")
            return
        # если флажок "без картинок" не установлен — проверяем папку с картинками
        if not self.no_images_var.get():
            if not image_folder or not os.path.exists(image_folder):
                messagebox.showerror("Ошибка", "Выберите корректную папку с картинками.")
                return

        # Проверяем, что пользователь выбрал выходную папку
        if not output_dir:
            messagebox.showerror("Ошибка", "Выберите выходную папку для архива.")
            return
        # Пытаемся создать выходную папку, если её ещё нет
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать выходную папку: {e}")
            return

        # Создаем временную папку для промежуточных файлов
        temp_dir = tempfile.mkdtemp()

        try:
            # Парсим GIFT
            self.status_label.config(text="Парсинг GIFT файла...")
            self.root.update()
            qs = parse_gift(gift_path)
            if not qs:
                messagebox.showerror("Ошибка", "Вопросы не найдены в GIFT файле.")
                return

            # Генерируем изображения во временную папку
            self.status_label.config(text="Генерация изображений...")
            self.root.update()
            generated_images = []
            generated_answer_images = []
            question_items = [item for item in qs if item.get('type') == 'question']
            # Если пользователь выбрал прогон без картинок — убираем ссылки на внешние изображения
            if self.no_images_var.get():
                for q in question_items:
                    q['image'] = None
            for idx, q in enumerate(question_items, start=1):
                if q.get('keep_answers_raw'):
                    generated_images.append(None)
                    generated_answer_images.append([])
                    continue

                question_path = os.path.join(temp_dir, f"q{idx:03d}.png")
                render_question(q, question_path, img_size=(1200, 800), font_path=None, include_answer=False, trim=True, trim_pad=10)
                generated_images.append(question_path)

                # Копируем встроенное изображение из вопроса если оно есть
                q_image = q.get('image')
                if q_image and os.path.exists(q_image):
                    img_basename = os.path.basename(q_image)
                    dest_img = os.path.join(temp_dir, img_basename)
                    # Останавливаем перезапись если несколько вопросов используют одно изображение
                    if not os.path.exists(dest_img):
                        shutil.copy2(q_image, dest_img)

                answer_paths = []
                for a_idx, a in enumerate(q['answers'], start=1):
                    answer_path = os.path.join(temp_dir, f"q{idx:03d}_ans{a_idx:02d}.png")
                    answer_text = f"{a.get('lhs') or ''}{a.get('display') or a.get('text') or ''}"
                    render_answer_image(answer_text, answer_path, img_size=(1000, 120), font_path=None, trim=True, trim_pad=10)
                    answer_paths.append(answer_path)
                generated_answer_images.append(answer_paths)

            # Создаем выходной файл main.txt во временную папку (кодировка UTF-8)
            out_gift_path = os.path.join(temp_dir, "main.txt")
            with open(out_gift_path, 'w', encoding='utf-8') as f:
                question_idx = 0
                for item in qs:
                    if item.get('type') == 'category':
                        f.write(item.get('raw', '').rstrip() + "\n\n")
                        continue
                    if item.get('type') == 'comment':
                        f.write(item.get('raw', '').rstrip() + "\n")
                        continue

                    question_idx += 1
                    if item.get('keep_answers_raw'):
                        raw_block = item.get('raw_block')
                        if raw_block is not None:
                            f.write(raw_block.rstrip() + "\n\n")
                        continue

                    # Получаем параметры генерированных изображений
                    img_path = generated_images[question_idx-1]
                    answer_paths = generated_answer_images[question_idx-1]
                    try:
                        with open(img_path, 'rb') as im_file:
                            pass  # Проверяем, что файл существует
                        basename = os.path.basename(img_path)
                        img_tag = f"\\r\\n</br>\n<img src\\=\"@@PLUGINFILE@@/Image/{basename}\">"
                        f.write(img_tag + "{\n")
                        for a_idx, a in enumerate(item['answers'], start=1):
                            answer_name = os.path.basename(answer_paths[a_idx-1])
                            prefix = '=' if a.get('correct') else '~'
                            weight = a.get('weight') or ''
                            semi = a.get('semi') or ''
                            answer_img = f"<img src\\=\"@@PLUGINFILE@@/Image/{answer_name}\">"
                            f.write(f"{prefix}{weight}{answer_img}{semi}\n")
                        f.write("}\n\n")
                    except Exception as e:
                        print(f"Ошибка при обработке вопроса {question_idx}: {e}")

            # Создаем ZIP-архив только с файлами из временной папки
            self.status_label.config(text="Создание архива...")
            self.root.update()
            zip_path = os.path.join(output_dir, "generated.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Добавляем новый GIFT файл
                zipf.write(out_gift_path, os.path.basename(out_gift_path))
                # Добавляем все изображения в подпапку "Image"
                for img in generated_images:
                    if img and os.path.exists(img):
                        zipf.write(img, os.path.join("Image", os.path.basename(img)))
                for answer_paths in generated_answer_images:
                    for answer_path in answer_paths:
                        if answer_path and os.path.exists(answer_path):
                            zipf.write(answer_path, os.path.join("Image", os.path.basename(answer_path)))
                # Добавляем все остальные файлы из temp_dir (в т.ч. картинки из вопросов)
                for fname in os.listdir(temp_dir):
                    fpath = os.path.join(temp_dir, fname)
                    if os.path.isfile(fpath) and fname not in ('main.txt', os.path.basename(out_gift_path)):
                # Останавливаем передублирование если файл уже добавлен как вопрос или ответ
                        if not any(fname == os.path.basename(img) for img in generated_images if img) and \
                           not any(fname == os.path.basename(ap) for answer_paths in generated_answer_images for ap in answer_paths):
                            zipf.write(fpath, os.path.join("Image", fname))

            self.status_label.config(text=f"Готово! Архив создан: {zip_path}")
            messagebox.showinfo("Успех", f"Изображения сгенерированы и упакованы в архив: {zip_path}")

            # Открываем папку с архивом
            os.startfile(output_dir)
        
        finally:
            # Очищаем временную папку со всеми файлами
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _normalize_drop_path(self, data):
        data = data.strip()
        paths = []
        current = []
        in_braces = False
        for ch in data:
            if ch == '{':
                in_braces = True
                current = []
                continue
            if ch == '}':
                in_braces = False
                paths.append(''.join(current).strip())
                current = []
                continue
            if in_braces:
                current.append(ch)
            elif not ch.isspace():
                current.append(ch)
            elif current:
                paths.append(''.join(current).strip())
                current = []
        if current:
            paths.append(''.join(current).strip())
        if paths:
            return paths[0].strip('"')
        return data.strip('"')

    def on_gift_drop(self, event):
        path = self._normalize_drop_path(event.data)
        if os.path.isfile(path):
            self.gift_file.set(path)
        else:
            messagebox.showerror("Ошибка", "Перетащите корректный GIFT файл.")

    def on_image_drop(self, event):
        path = self._normalize_drop_path(event.data)
        if os.path.isdir(path):
            self.image_folder.set(path)
        elif os.path.isfile(path):
            self.image_folder.set(os.path.dirname(path))
        else:
            messagebox.showerror("Ошибка", "Перетащите папку с изображениями или файл внутри неё.")

    def on_output_drop(self, event):
        path = self._normalize_drop_path(event.data)
        if os.path.isdir(path):
            self.output_folder.set(path)
        elif os.path.isfile(path):
            self.output_folder.set(os.path.dirname(path))
        else:
            messagebox.showerror("Ошибка", "Перетащите выходную папку или файл внутри неё.")

if __name__ == "__main__":
    root = create_root()
    app = GiftImageGeneratorApp(root)
    root.mainloop()