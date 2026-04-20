import os
import zipfile
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from generate_images import parse_gift, render_question, render_answer_image

class GiftImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GIFT Image Generator")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        self.root.minsize(500, 300)
        self.root.maxsize(500, 300)

        # Переменные для путей
        self.gift_file = tk.StringVar()
        self.image_folder = tk.StringVar()
        self.output_folder = tk.StringVar(value=os.path.join(os.getcwd(), "output"))

        # Элементы интерфейса
        tk.Label(root, text="GIFT файл:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        tk.Entry(root, textvariable=self.gift_file, width=40).grid(row=0, column=1, padx=10, pady=5)
        tk.Button(root, text="Выбрать", command=self.select_gift_file).grid(row=0, column=2, padx=10, pady=5)

        tk.Label(root, text="Папка с картинками:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        tk.Entry(root, textvariable=self.image_folder, width=40).grid(row=1, column=1, padx=10, pady=5)
        tk.Button(root, text="Выбрать", command=self.select_image_folder).grid(row=1, column=2, padx=10, pady=5)

        tk.Label(root, text="Выходная папка:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        tk.Entry(root, textvariable=self.output_folder, width=40).grid(row=2, column=1, padx=10, pady=5)
        tk.Button(root, text="Выбрать", command=self.select_output_folder).grid(row=2, column=2, padx=10, pady=5)

        # Кнопка генерации
        self.generate_button = tk.Button(root, text="Генерировать изображения", command=self.generate_images, bg="green", fg="white")
        self.generate_button.grid(row=3, column=0, columnspan=3, pady=20)

        # Статус
        self.status_label = tk.Label(root, text="")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=5)

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
        if not image_folder or not os.path.exists(image_folder):
            messagebox.showerror("Ошибка", "Выберите корректную папку с картинками.")
            return

        os.makedirs(output_dir, exist_ok=True)

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
            for idx, q in enumerate(qs, start=1):
                question_path = os.path.join(temp_dir, f"q{idx:03d}.png")
                render_question(q, question_path, img_size=(1200, 800), font_path=None, include_answer=False, trim=True, trim_pad=10)
                generated_images.append(question_path)

                answer_paths = []
                if not q.get('keep_answers_raw'):
                    for a_idx, a in enumerate(q['answers'], start=1):
                        answer_path = os.path.join(temp_dir, f"q{idx:03d}_ans{a_idx:02d}.png")
                        render_answer_image(a.get('display'), answer_path, img_size=(1000, 120), font_path=None, trim=True, trim_pad=10)
                        answer_paths.append(answer_path)
                generated_answer_images.append(answer_paths)

            # Создаем выходной файл main.txt во временную папку (кодировка UTF-8)
            out_gift_path = os.path.join(temp_dir, "main.txt")
            with open(out_gift_path, 'w', encoding='utf-8') as f:
                for idx, q in enumerate(qs, start=1):
                    img_path = generated_images[idx-1]
                    answer_paths = generated_answer_images[idx-1]
                    try:
                        with open(img_path, 'rb') as im_file:
                            pass  # Проверяем, что файл существует
                        basename = os.path.basename(img_path)
                        img_tag = f"\\r\\n</br>\n<img src\\=\"@@PLUGINFILE@@/Image/{basename}\">"
                        f.write(img_tag + "{\n")
                        if q.get('keep_answers_raw'):
                            raw_ans = q.get('raw_answers', '').rstrip()
                            f.write(raw_ans + "\n")
                        else:
                            for a_idx, a in enumerate(q['answers'], start=1):
                                answer_name = os.path.basename(answer_paths[a_idx-1])
                                prefix = '=' if a.get('correct') else '~'
                                weight = a.get('weight') or ''
                                lhs = a.get('lhs')
                                semi = a.get('semi') or ''
                                answer_img = f"<img src\\=\"@@PLUGINFILE@@/Image/{answer_name}\">"
                                if lhs:
                                    f.write(f"{prefix}{weight}{lhs}{answer_img}{semi}\n")
                                else:
                                    if weight:
                                        f.write(f"{prefix}{weight}{answer_img}\n")
                                    else:
                                        f.write(f"{prefix}{answer_img}\n")
                        f.write("}\n\n")
                    except Exception as e:
                        print(f"Ошибка при обработке вопроса {idx}: {e}")

            # Создаем ZIP-архив только с файлами из временной папки
            self.status_label.config(text="Создание архива...")
            self.root.update()
            zip_path = os.path.join(output_dir, "generated.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Добавляем новый GIFT файл
                zipf.write(out_gift_path, os.path.basename(out_gift_path))
                # Добавляем все изображения в подпапку "Image"
                for img in generated_images:
                    zipf.write(img, os.path.join("Image", os.path.basename(img)))
                for answer_paths in generated_answer_images:
                    for answer_path in answer_paths:
                        zipf.write(answer_path, os.path.join("Image", os.path.basename(answer_path)))

            self.status_label.config(text=f"Готово! Архив создан: {zip_path}")
            messagebox.showinfo("Успех", f"Изображения сгенерированы и упакованы в архив: {zip_path}")

            # Открываем папку с архивом
            os.startfile(output_dir)
        
        finally:
            # Удаляем временную папку со всеми файлами
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = GiftImageGeneratorApp(root)
    root.mainloop()