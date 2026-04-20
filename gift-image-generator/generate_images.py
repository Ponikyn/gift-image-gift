import os
import re
import click
from PIL import Image, ImageDraw, ImageFont, ImageChops

def parse_gift(path: str):
    text = open(path, "r", encoding="utf-8").read()
    pattern = re.compile(r'(?s)(.*?)\{(.*?)\}')
    matches = pattern.findall(text)
    questions = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gift_dir = os.path.dirname(os.path.abspath(path))
    for q_text, ans_block in matches:
        # сохраняем оригинальный текст вопроса (чтобы сохранить литеральные последовательности вроде \r\n в выходном GIFT)
        q_raw = q_text
        # ищем тег <img ... src=...> в тексте вопроса (учитываем экранированные символы вроде \" и \=)
        image_path = None
        # нормализуем экранированные последовательности, чтобы regex мог найти src\="..." и src="..."
        q_text_norm = q_text.replace('\\=', '=').replace('\\"', '"').replace("\\'", "'")
        img_match = re.search(r'<img[^>]*src\s*=\s*(?P<val>"[^"]*"|\'[^\']*\'|[^>\s]+)[^>]*>', q_text_norm, flags=re.I | re.S)
        if img_match:
            raw_val = img_match.group('val').strip()
            # strip surrounding quotes if present
            if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
                src = raw_val[1:-1]
            else:
                src = raw_val
            # remove plugin prefix if present
            cleaned = src.replace('@@PLUGINFILE@@/', '').lstrip('/\\')
            # try candidate locations (prefer current gift dir and script Image folder)
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
                print(f"Warning: image {src} not found for question; image will be skipped")
            else:
                print(f"Found image for question: {image_path}")
            # remove img tag and <br> tags from original question text so they won't be rendered as text
            q_text = re.sub(r'<img[^>]*>', '', q_text, flags=re.I | re.S)
            q_text = re.sub(r'<\s*/?\s*br\s*/?\s*>', '', q_text, flags=re.I)

        # подготовка текста вопроса для рендеринга: удаляем литеральные escape-последовательности вроде \r\n, которые должны остаться в файле, но не на изображении
        q = q_text.strip().replace("\n", " ")
        q = q.replace('\\r\\n', ' ').replace('\\n', ' ').replace('\\r', ' ')
        q = re.sub(r'\\+', '', q)
        answers = []
        for m in re.finditer(r'([=~])([^\=~]+)', ans_block, flags=re.S):
            marker = m.group(1)
            ans = m.group(2).strip()
            # detect weight prefix like %50% or %-100%
            weight = None
            content = ans
            wmatch = re.match(r'^\%(-?\d+)\%\s*(.*)', ans, flags=re.S)
            if wmatch:
                weight = f"%{wmatch.group(1)}%"
                content = wmatch.group(2).strip()
            # detect arrow pattern LHS -> RHS[;]
            lhs = None
            semi = ''
            rhs = content
            arrow_match = re.match(r'^(?P<lhs>.*?->)\s*(?P<rhs>.*?)(?P<semi>;?)\s*$', content)
            if arrow_match:
                lhs = arrow_match.group('lhs').strip()
                rhs = arrow_match.group('rhs').strip()
                semi = arrow_match.group('semi') or ''
            display = rhs
            answers.append({"text": ans, "display": display, "weight": weight, "lhs": lhs, "semi": semi, "correct": marker == "="})
        if answers:
            # determine if this is the special case: multiple '=' answers only -> keep raw answers unchanged in output GIFT and do not render answers on image
            # BUT if any answer uses 'LHS -> RHS' syntax (lhs detected), do NOT treat as raw-answers-only case
            has_lhs = any(a.get('lhs') for a in answers)
            keep_raw = len(answers) > 1 and all(a.get('correct') for a in answers) and not has_lhs
            questions.append({"question": q, "answers": answers, "image": image_path, "raw": q_raw, "raw_answers": ans_block, "keep_answers_raw": keep_raw})
    return questions

def wrap_text(text, font, draw, max_width):
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

def render_answer_image(text, out_path, img_size=(1000,140), font_path=None, bg_color="white", text_color="black", trim=True, trim_pad=10):
    W, H = img_size
    margin = 20
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    def try_font(name, size):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            return None

    answer_font = None
    if font_path:
        try:
            answer_font = ImageFont.truetype(font_path, 30)
        except Exception:
            answer_font = None

    for name in ("arial.ttf", "Tahoma.ttf", "DejaVuSans.ttf"):
        if answer_font is None:
            answer_font = try_font(name, 30)

    if answer_font is None:
        answer_font = ImageFont.load_default()

    def text_size(text, font):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return font.getsize(text)

    lines = wrap_text(text, answer_font, draw, W - 2 * margin)
    y = margin
    for line in lines:
        w, h = text_size(line, answer_font)
        x = max(margin, (W - w) // 2)
        draw.text((x, y), line, font=answer_font, fill=text_color)
        y += h + 8

    if trim:
        try:
            rgb_bg = (255, 255, 255) if isinstance(bg_color, str) else bg_color
            img = crop_whitespace(img, bg_color=rgb_bg, pad=trim_pad)
        except Exception:
            pass
    img.save(out_path, "PNG")


def crop_whitespace(im: Image.Image, bg_color=(255,255,255), pad: int = 10):
    """Crop uniform background from all sides. Returns cropped image with `pad` added back.
    Uses ImageChops.difference against a solid background of same color."""
    try:
        # Create background image same mode and size
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
    W, H = img_size
    margin = 40
    bg_color = "white"
    text_color = "black"
    correct_color = (22, 160, 133)  # зеленый
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # fonts (попробуем несколько стандартных шрифтов)
    def try_font(name, size):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            return None

    # если указан font_path - попробуем его сначала
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

    # вспомогательная функция для получения размера текста (совместимость между версиями Pillow)
    def text_size(text, font):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return font.getsize(text)

    # render question
    y = margin
    q_lines = wrap_text(qdata["question"], question_font, draw, W - 2 * margin)
    for line in q_lines:
        draw.text((margin, y), line, font=question_font, fill=text_color)
        _, h = text_size(line, question_font)
        y += h + 8

    y += 12  # небольшая пауза

    # если у вопроса есть изображение, пытаемся открыть и вставить его
    if qdata.get("image"):
        try:
            img_file = qdata.get("image")
            im = Image.open(img_file)
            orig_w, orig_h = im.size
            max_w = W - 2 * margin
            max_h = H // 2  # разрешаем использовать до половины высоты, но не масштабируем, если не нужно

            # Если изображение больше доступного места — уменьшим пропорционально, иначе сохраним исходный размер
            if orig_w > max_w or orig_h > max_h:
                scale_w = max_w / orig_w if orig_w > max_w else 1.0
                scale_h = max_h / orig_h if orig_h > max_h else 1.0
                scale = min(scale_w, scale_h)
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))
                # compatible resampling for different Pillow versions
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
                # сохраняем оригинальный размер
                pass

            # left-align image (start at left margin)
            x_img = margin
            # paste with alpha support if needed
            if im.mode in ("RGBA", "LA") or (hasattr(im, 'info') and im.info.get('transparency')):
                img.paste(im, (x_img, y), im.convert("RGBA"))
            else:
                img.paste(im.convert("RGB"), (x_img, y))
            y += im.height + 12
        except Exception as e:
            print(f"Warning: cannot open image {qdata.get('image')}: {e}")

    # отображаем варианты ответов только если включено рендерить ответы на изображении
    if include_answer and not qdata.get('keep_answers_raw'):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, a in enumerate(qdata["answers"]):
            display_text = a.get("display") if a.get("display") is not None else a.get("text")
            prefix = f"{letters[i]}) " if i < len(letters) else f"{i+1}) "
            prefix_w, _ = text_size(prefix, answer_font)
            # wrap answer text to remain within width
            a_lines = wrap_text(display_text, answer_font, draw, W - 2 * margin - prefix_w)
            for j, ln in enumerate(a_lines):
                x = margin if j == 0 else margin + prefix_w
                text_to_draw = prefix + ln if j == 0 else ln
                draw.text((x, y), text_to_draw, font=answer_font, fill=text_color)
                _, line_h = text_size(ln, answer_font)
                y += line_h + 6
            y += 6
    else:
        # специальные вопросы: ответы остаются в исходном GIFT и не рисуются на изображении
        pass

    # optionally trim whitespace margins
    if trim:
        try:
            # bg_color is "white" but crop expects RGB tuple
            rgb_bg = (255, 255, 255) if isinstance(bg_color, str) else bg_color
            img = crop_whitespace(img, bg_color=rgb_bg, pad=trim_pad)
        except Exception as e:
            print(f"Warning: trimming failed: {e}")
    img.save(out_path, "PNG")

@click.command()
@click.option("--in", "infile", default="questions.gift", help="GIFT file (utf-8)")
@click.option("--outdir", default="Image", help="Output folder (relative to script if not absolute)")
@click.option("--width", type=int, default=1200)
@click.option("--height", type=int, default=800)
@click.option("--font", default=None, help="Path to TTF font (optional)")
@click.option("--show-answer", is_flag=True, default=False, help="(compat) Highlight correct answer")
@click.option("--out-gift", "out_gift", default="questions_images.gift", help="Output GIFT file that will contain links to generated images")
@click.option("--no-trim", "no_trim", is_flag=True, default=False, help="Disable automatic trimming of white margins on generated images")
@click.option("--trim-pad", "trim_pad", type=int, default=10, help="Padding (px) to keep when trimming margins")
def main(infile, outdir, width, height, font, show_answer, out_gift, no_trim, trim_pad):
    # Interactive prompt for GIFT filename (по требованию)
    prompt_default = infile or "questions.gift"
    try:
        infile = click.prompt('Введите имя GIFT файла (с расширением)', default=prompt_default, show_default=True)
    except Exception:
        # fallback in non-interactive environments
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
        print(f"No questions found in {infile}")
        return

    # render images
    question_images = []
    answer_images_per_question = []
    for idx, q in enumerate(qs, start=1):
        question_path = os.path.join(outdir, f"q{idx:03d}.png")
        render_question(q, question_path, img_size=(width, height), font_path=font, include_answer=False, trim=not no_trim, trim_pad=trim_pad)
        question_images.append(question_path)

        answer_paths = []
        if not q.get('keep_answers_raw'):
            for a_idx, a in enumerate(q['answers'], start=1):
                answer_path = os.path.join(outdir, f"q{idx:03d}_ans{a_idx:02d}.png")
                render_answer_image(a.get('display'), answer_path, img_size=(1000, 120), font_path=font, trim=True, trim_pad=trim_pad)
                answer_paths.append(answer_path)
        answer_images_per_question.append(answer_paths)

    print(f"Saved {len(question_images)} images to {outdir}")

    # create a GIFT file where each question is replaced by a link to the generated image
    if not os.path.isabs(out_gift):
        out_gift = os.path.join(script_dir, out_gift)
    try:
        with open(out_gift, 'w', encoding='utf-8') as f:
            for idx, q in enumerate(qs, start=1):
                img_path = question_images[idx-1]
                answer_paths = answer_images_per_question[idx-1]
                # get actual image size (after any resizing)
                try:
                    with Image.open(img_path) as im:
                        w, h = im.size
                except Exception:
                    w, h = None, None
                basename = os.path.basename(img_path)
                # build the image tag with literal "\\r\\n" prefix (so file keeps backslash sequences)
                if w and h:
                    img_tag = f"\\r\\n</br>\n<img height\\=\"{h}px\" width\\=\"{w}px\" src\\=\"@@PLUGINFILE@@/Image/{basename}\">"
                else:
                    img_tag = f"\\r\\n</br>\n<img src\\=\"@@PLUGINFILE@@/Image/{basename}\">"
                if answer_paths:
                    for answer_path in answer_paths:
                        answer_name = os.path.basename(answer_path)
                        img_tag += f"\\r\\n</br>\n<img src\\=\"@@PLUGINFILE@@/Image/{answer_name}\">"
                f.write(img_tag + "{\n")
                # If this question keeps answers raw, write the original answer block unchanged
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
        print(f"Wrote GIFT with image tags to {out_gift}")
    except Exception as e:
        print(f"Failed to write GIFT file {out_gift}: {e})")

if __name__ == "__main__":
    main()