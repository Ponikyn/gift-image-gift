import os
import re
import shutil
import click
from PIL import Image, ImageDraw, ImageFont, ImageChops

def parse_gift(path: str):
    text = open(path, "r", encoding="utf-8").read()
    items = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gift_dir = os.path.dirname(os.path.abspath(path))
    
    # Разделяем текст на строки, сохраняя категории, комментарии и вопросы
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Проверяем категорию
        if stripped.startswith('$CATEGORY:'):
            items.append({"type": "category", "raw": line})
            i += 1
            continue
        
        # Проверяем комментарий (начинается с //)
        if stripped.startswith('//'):
            items.append({"type": "comment", "raw": line})
            i += 1
            continue
        
        # Проверяем блок вопроса (текст с {...})
        if '{' in line:
            # Собираем полный блок вопроса и ответов
            q_text = line[:line.index('{')].strip()
            ans_start = line.index('{') + 1
            ans_text = line[ans_start:]
            brace_count = 1 + ans_text.count('{') - ans_text.count('}')
            j = i

            while brace_count > 0 and j < len(lines) - 1:
                j += 1
                ans_text += '\n' + lines[j]
                brace_count += lines[j].count('{') - lines[j].count('}')

            # Удаляем закрывающую скобку
            if ans_text.endswith('}'):
                ans_text = ans_text[:-1].rstrip()
            
            # Парсим вопрос и ответы
            start_idx = i
            k = i - 1
            while k >= 0:
                prev_line = lines[k]
                prev_strip = prev_line.strip()
                if prev_strip == '' or prev_strip.startswith('//') or prev_strip.startswith('$CATEGORY:'):
                    break
                if '{' in prev_line or '}' in prev_line:
                    break
                start_idx = k
                k -= 1

            q_raw = '\n'.join(lines[start_idx:i] + [q_text]).strip()
            raw_block = '\n'.join(lines[start_idx:j+1])
            image_path = None
            q_text_norm = q_raw.replace('\\=', '=').replace('\\"', '"').replace("\\'", "'")            # Ищем изображение в тексте вопроса            img_match = re.search(r'<img[^>]*src\s*=\s*(?P<val>"[^"]*"|\'[^\']*\'|[^>\s]+)[^>]*>', q_text_norm, flags=re.I | re.S)
            if img_match:
                raw_val = img_match.group('val').strip()
                if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
                    src = raw_val[1:-1]
                else:
                    src = raw_val
                cleaned = src.replace('@@PLUGINFILE@@/', '').lstrip('/\\')
                candidates = [
                    cleaned,
                    os.path.join(gift_dir, cleaned),
                    os.path.join(script_dir, cleaned),
                    os.path.join(script_dir, 'Image', os.path.basename(cleaned)),
                    os.path.join(gift_dir, 'Image', os.path.basename(cleaned)),
                    os.path.join(script_dir, 'Image', cleaned),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        image_path = os.path.abspath(c)
                        break
                if image_path is None:
                    print(f"Внимание: изображение {src} не найдено; будет пропущено")
                else:
                    print(f"Найдено изображение: {image_path}")
                # Удаляем теги img и br из текста
                q_text = re.sub(r'<img[^>]*>', '', q_text, flags=re.I | re.S)
                q_text = re.sub(r'<\s*/?\s*br\s*/?\s*>', '', q_text, flags=re.I)
            
            q = q_text.strip().replace("\n", " ")
            q = q.replace('\\r\\n', ' ').replace('\\n', ' ').replace('\\r', ' ')
            q = re.sub(r'\\+', '', q)
            
            # Парсим ответы (=правильный, ~дистрактор, #короткий ответ)
            answers = []
            for m in re.finditer(r'([=~#])([^\=~#]+)', ans_text, flags=re.S):
                marker = m.group(1)
                ans = m.group(2).strip()
                weight = None
                content = ans
                wmatch = re.match(r'^\%(-?\d+)\%\s*(.*)', ans, flags=re.S)
                if wmatch:
                    weight = f"%{wmatch.group(1)}%"
                    content = wmatch.group(2).strip()
                lhs = None
                semi = ''
                rhs = content
                arrow_match = re.match(r'^(?P<lhs>.*?->)\s*(?P<rhs>.*?)(?P<semi>;?)\s*$', content)
                if arrow_match:
                    lhs = arrow_match.group('lhs').strip()
                    rhs = arrow_match.group('rhs').strip()
                    semi = arrow_match.group('semi') or ''
                display = rhs
                answers.append({
                    "marker": marker,
                    "text": ans,
                    "display": display,
                    "weight": weight,
                    "lhs": lhs,
                    "semi": semi,
                    "correct": marker in ("=", "#")
                })
            
            if answers:
                # Определяем, нужно ли сохранить ответы в исходном формате
                has_lhs = any(a.get('lhs') for a in answers)
                keep_raw = any(a.get('marker') == '#' for a in answers) or (len(answers) > 1 and all(a.get('correct') for a in answers) and not has_lhs)
                items.append({
                    "type": "question",
                    "question": q,
                    "answers": answers,
                    "image": image_path,
                    "raw": q_raw,
                    "raw_block": raw_block,
                    "raw_answers": ans_text,
                    "keep_answers_raw": keep_raw
                })
            
            i = j + 1
            continue
        
        i += 1
    
    return items

def wrap_text(text, font, draw, max_width):
    """Разбивает текст на строки так, чтобы уместиться в ширину max_width"""
    words = text.split()
    lines = []
    line = ""
    for w in words:
        test = f"{line} {w}".strip()
        # безопасное получение ширины текста: textbbox для новых версий Pillow, fallback к font.getsize
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w_width = bbox[2] - bbox[0]
        except Exception:
            w_width, _ = font.getsize(test)
        if w_width <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def crop_whitespace(im: Image.Image, bg_color=(255,255,255), pad: int = 10):
    """Обрезает единообразный фон со всех сторон. Возвращает обрезанное изображение с добавленным отступом.
    Использует ImageChops.difference для сравнения с фоном того же цвета."""
    try:
        # Создаем фоновое изображение такого же размера и режима
        bg = Image.new(im.mode, im.size, bg_color)
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
        if not bbox:
            return im
        left = max(0, bbox[0] - pad)
        upper = max(0, bbox[1] - pad)
        right = min(im.width, bbox[2] + pad)
        lower = min(im.height, bbox[3] + pad)
        return im.crop((left, upper, right, lower))
    except Exception:
        return im


def render_question(qdata, out_path, img_size=(1200,800), font_path=None, include_answer=False, trim=True, trim_pad=10):
    """Рендирует вопрос с ответами в изображение PNG"""
    W, H = img_size
    margin = 40
    bg_color = "white"
    text_color = "black"
    correct_color = (22, 160, 133)  # зеленый
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # Выбираем шрифты (пробуем несколько стандартных)
    def try_font(name, size):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            return None

    # Если указан шрифт - используем его в первую очередь
    question_font = None
    answer_font = None
    if font_path:
        try:
            question_font = ImageFont.truetype(font_path, 36)
            answer_font = ImageFont.truetype(font_path, 28)
        except Exception:
            question_font = None
            answer_font = None

    for name in ("arial.ttf", "Tahoma.ttf", "DejaVuSans.ttf"):
        if question_font is None:
            question_font = try_font(name, 36)
        if answer_font is None:
            answer_font = try_font(name, 28)

    if question_font is None:
        question_font = ImageFont.load_default()
    if answer_font is None:
        answer_font = ImageFont.load_default()

    # Вспомогательная функция для получения размера текста (совместимо со всеми версиями Pillow)
    def text_size(text, font):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return font.getsize(text)

    # Рендирим текст вопроса
    y = margin
    q_lines = wrap_text(qdata["question"], question_font, draw, W - 2 * margin)
    for line in q_lines:
        draw.text((margin, y), line, font=question_font, fill=text_color)
        _, h = text_size(line, question_font)
        y += h + 8

    y += 12  # Небольшой отступ

    # Если в вопросе есть изображение - вставляем его
    if qdata.get("image"):
        try:
            img_file = qdata.get("image")
            im = Image.open(img_file)
            orig_w, orig_h = im.size
            max_w = W - 2 * margin
            max_h = H // 2  # Разрешаем использовать до половины высоты

            # Масштабируем изображение пропорционально, если оно больше доступного места
            if orig_w > max_w or orig_h > max_h:
                scale_w = max_w / orig_w if orig_w > max_w else 1.0
                scale_h = max_h / orig_h if orig_h > max_h else 1.0
                scale = min(scale_w, scale_h)
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))
                # Совместимая с разными версиями Pillow функция масштабирования
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    try:
                        resample = Image.LANCZOS
                    except Exception:
                        resample = None
                if resample:
                    im = im.resize((new_w, new_h), resample)
                else:
                    im = im.resize((new_w, new_h))
                print(f"Image {img_file} was downscaled to {im.size} to fit the canvas")
            else:
                # Сохраняем оригинальный размер
                pass

            # Выравниваем изображение по левому краю
            x_img = margin
            # Вставляем изображение с поддержкой альфа-канала если необходимо
            if im.mode in ("RGBA", "LA") or (hasattr(im, 'info') and im.info.get('transparency')):
                img.paste(im, (x_img, y), im.convert("RGBA"))
            else:
                img.paste(im.convert("RGB"), (x_img, y))
            y += im.height + 12
        except Exception as e:
            print(f"Warning: cannot open image {qdata.get('image')}: {e}")

    # Рендирим ответы только если это запрошено и это не raw-вопрос
    if include_answer and not qdata.get('keep_answers_raw'):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, a in enumerate(qdata["answers"]):
            display_text = a.get("display") if a.get("display") is not None else a.get("text")
            prefix = f"{letters[i]}) " if i < len(letters) else f"{i+1}) "
            prefix_w, _ = text_size(prefix, answer_font)
            # Разбиваем текст ответа так, чтобы он поместился в ширину
            a_lines = wrap_text(display_text, answer_font, draw, W - 2 * margin - prefix_w)
            for j, ln in enumerate(a_lines):
                x = margin if j == 0 else margin + prefix_w
                text_to_draw = prefix + ln if j == 0 else ln
                draw.text((x, y), text_to_draw, font=answer_font, fill=text_color)
                _, line_h = text_size(ln, answer_font)
                y += line_h + 6
            y += 6

    # Обрезаем белые поля если требуется
    if trim:
        try:
            # Преобразуем цвет в RGB кортеж
            rgb_bg = (255, 255, 255) if isinstance(bg_color, str) else bg_color
            img = crop_whitespace(img, bg_color=rgb_bg, pad=trim_pad)
        except Exception as e:
            print(f"Warning: trimming failed: {e}")
    img.save(out_path, "PNG")


def render_answer_image(text, out_path, img_size=(1000,120), font_path=None, trim=True, trim_pad=10):
    """Рендирует текст ответа в горизонтальное изображение и сохраняет как PNG"""
    W, H = img_size
    margin = 20
    bg_color = "white"
    text_color = "black"
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # Пробуем несколько стандартных шрифтов
    def try_font(name, size):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            return None

    answer_font = None
    if font_path:
        try:
            answer_font = ImageFont.truetype(font_path, 28)
        except Exception:
            answer_font = None

    for name in ("arial.ttf", "Tahoma.ttf", "DejaVuSans.ttf"):
        if answer_font is None:
            answer_font = try_font(name, 28)

    if answer_font is None:
        answer_font = ImageFont.load_default()

    def text_size_local(t, font):
        try:
            bbox = draw.textbbox((0, 0), t, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return font.getsize(t)

    max_width = W - 2 * margin
    lines = wrap_text(text, answer_font, draw, max_width)
    y = margin
    # Рендирим каждую строку ответа
    for ln in lines:
        draw.text((margin, y), ln, font=answer_font, fill=text_color)
        _, h = text_size_local(ln, answer_font)
        y += h + 6

    if trim:
        try:
            rgb_bg = (255, 255, 255)
            img = crop_whitespace(img, bg_color=rgb_bg, pad=trim_pad)
        except Exception as e:
            print(f"Warning: trimming answer image failed: {e}")
    img.save(out_path, "PNG")

@click.command()
@click.option("--in", "infile", default="questions.gift", help="GIFT файл (кодировка UTF-8)")
@click.option("--outdir", default="Image", help="Выходная папка (относительно скрипта, если не абсолютный путь)")
@click.option("--width", type=int, default=1200)
@click.option("--height", type=int, default=800)
@click.option("--font", default=None, help="Путь к TTF шрифту (опционально)")
@click.option("--show-answer", is_flag=True, default=False, help="Выделить правильный ответ")
@click.option("--out-gift", "out_gift", default="questions_images.gift", help="Выходной GIFT файл со ссылками на генерированные изображения")
@click.option("--no-trim", "no_trim", is_flag=True, default=False, help="Отключить обрезку белых полей на генерированных изображениях")
@click.option("--trim-pad", "trim_pad", type=int, default=10, help="Отступ (px) при обрезке полей")
def main(infile, outdir, width, height, font, show_answer, out_gift, no_trim, trim_pad):
    # Интерактивный запрос имени GIFT файла
    prompt_default = infile or "questions.gift"
    try:
        infile = click.prompt('Введите имя GIFT файла (с расширением)', default=prompt_default, show_default=True)
    except Exception:
        # Если не работает интерактивный режим, используем значение по умолчанию
        infile = prompt_default

    # Сделаем пути относительными к каталогу с скриптом, если не заданы абсолютные
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(infile):
        candidate = os.path.join(script_dir, infile)
        if os.path.exists(candidate):
            infile = candidate
    if not os.path.isabs(outdir):
        outdir = os.path.join(script_dir, outdir)

    os.makedirs(outdir, exist_ok=True)
    qs = parse_gift(infile)
    if not qs:
        print(f"Вопросы не найдены в {infile}")
        return

    # Генерируем изображения для вопросов
    question_items = [item for item in qs if item.get('type') == 'question']
    generated = []
    for idx, q in enumerate(question_items, start=1):
        if q.get('keep_answers_raw'):
            generated.append(None)
            continue
        out = os.path.join(outdir, f"q{idx:03d}.png")
        render_question(q, out, img_size=(width, height), font_path=font, include_answer=show_answer, trim=not no_trim, trim_pad=trim_pad)
        generated.append(out)
        
        # Copy embedded image from question if present
        q_image = q.get('image')
        if q_image and os.path.exists(q_image):
            img_basename = os.path.basename(q_image)
            dest_img = os.path.join(outdir, img_basename)
            shutil.copy2(q_image, dest_img)
            print(f"Copied embedded image: {q_image} -> {dest_img}")

    print(f"Saved {sum(1 for q in question_items if not q.get('keep_answers_raw'))} images to {outdir}")

    # Создаем GIFT файл со ссылками на генерированные изображения
    if not os.path.isabs(out_gift):
        out_gift = os.path.join(script_dir, out_gift)
    try:
        with open(out_gift, 'w', encoding='utf-8') as f:
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            question_idx = 0  # Счетчик обработанных вопросов
            for item in qs:
                if item.get('type') == 'category':
                    f.write(item.get('raw', '').rstrip() + "\n\n")
                    continue
                if item.get('type') == 'comment':
                    f.write(item.get('raw', '').rstrip() + "\n")
                    continue

                if item.get('keep_answers_raw'):
                    raw_block = item.get('raw_block')
                    if raw_block is not None:
                        f.write(raw_block.rstrip() + "\n\n")
                    question_idx += 1
                    continue

                question_idx += 1
                img_path = generated[question_idx-1]
                # Получаем размер изображения (после масштабирования)
                try:
                    with Image.open(img_path) as im:
                        w, h = im.size
                except Exception:
                    w, h = None, None
                basename = os.path.basename(img_path) if img_path else None
                # Строим тег изображения с префиксом \r\n (сохраняем экранированные последовательности)
                if w and h and basename:
                    img_tag = f"\\r\\n</br>\n<img height\\=\"{h}px\" width\\=\"{w}px\" src\\=\"@@PLUGINFILE@@/Image/{basename}\">"
                else:
                    img_tag = f"\\r\\n</br>\n<img src\\=\"@@PLUGINFILE@@/Image/{basename}\">" if basename else ""
                f.write(img_tag + "{\n")
                # Записываем ответы буквами, соответствующими меткам на изображении (с весами и левой частью если есть)
                for i, a in enumerate(item['answers']):
                    letter = letters[i] if i < len(letters) else str(i+1)
                    prefix = '=' if a.get('correct') else '~'
                    weight = a.get('weight') or ''
                    lhs = a.get('lhs')
                    semi = a.get('semi') or ''
                    if lhs:
                        f.write(f"{prefix}{weight}{lhs}{letter}{semi}\n")
                    else:
                        if weight:
                            f.write(f"{prefix}{weight}{letter}\n")
                        else:
                            f.write(f"{prefix}{letter}\n")
                f.write("}\n\n")
        print(f"GIFT файл со ссылками на изображения сохранен: {out_gift}")
    except Exception as e:
        print(f"Ошибка при записи GIFT файла {out_gift}: {e})")

if __name__ == "__main__":
    main()