from __future__ import annotations

import hashlib
import os
import re
import shutil
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from math import ceil, sqrt
from pathlib import Path
from typing import Callable, Iterable, Optional
from xml.dom import minidom

from PIL import Image

ProgressCallback = Callable[[str, int, int], None]
LogCallback = Callable[[str], None]


@dataclass
class JobResult:
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    output: str = ""


def _log(cb: Optional[LogCallback], text: str) -> None:
    if cb:
        cb(text)


def _progress(cb: Optional[ProgressCallback], label: str, done: int, total: int) -> None:
    if cb:
        cb(label, done, total)


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def _safe_int(value, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _discover_sheets(base_dir: str) -> list[tuple[str, str, str, int]]:
    tasks = []
    skip_dirs = {
        "frames", "resized", "sprites", "optimizer_output",
        "frames_output", "Quegod", "redimensinando", "sprites_optimizados",
        "_temp_frames", "_temp_redimensinando",
    }
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for filename in files:
            if not filename.lower().endswith(".png"):
                continue
            png_path = os.path.join(root, filename)
            xml_path = os.path.splitext(png_path)[0] + ".xml"
            if not os.path.exists(xml_path):
                continue
            try:
                xml_root = ET.parse(xml_path).getroot()
                count = len(xml_root.findall(".//SubTexture"))
            except ET.ParseError:
                count = 0
            rel = os.path.relpath(root, base_dir)
            tasks.append((png_path, xml_path, rel, count))
    return tasks


def _extract_one_sheet(png_path: str, xml_path: str, output_dir: str, relative_path: str) -> int:
    with Image.open(png_path) as opened:
        image = opened.convert("RGBA")

    root = ET.parse(xml_path).getroot()
    png_name = Path(png_path).stem
    frame_dir = os.path.join(output_dir, relative_path, png_name)
    os.makedirs(frame_dir, exist_ok=True)

    with open(os.path.join(frame_dir, f"{image.width}x{image.height}.txt"), "w", encoding="utf-8") as f:
        f.write(f"Original spritesheet: {image.width}x{image.height}\nModo: XML")

    count = 0
    for sub in root.findall(".//SubTexture"):
        name = sanitize_filename(sub.attrib.get("name", "frame"))
        x = _safe_int(sub.attrib.get("x"))
        y = _safe_int(sub.attrib.get("y"))
        width = _safe_int(sub.attrib.get("width"))
        height = _safe_int(sub.attrib.get("height"))
        frame_x = _safe_int(sub.attrib.get("frameX"))
        frame_y = _safe_int(sub.attrib.get("frameY"))
        frame_w = _safe_int(sub.attrib.get("frameWidth"), width)
        frame_h = _safe_int(sub.attrib.get("frameHeight"), height)
        rotated = sub.attrib.get("rotated", "false").lower() == "true"

        sprite = image.crop((x, y, x + width, y + height))
        if rotated:
            sprite = sprite.transpose(Image.Transpose.ROTATE_90)
            width, height = height, width

        paste_x = abs(frame_x) if frame_x < 0 else 0
        paste_y = abs(frame_y) if frame_y < 0 else 0
        canvas_w = max(frame_w, width + paste_x)
        canvas_h = max(frame_h, height + paste_y)

        frame = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        frame.paste(sprite, (paste_x, paste_y))
        frame.save(os.path.join(frame_dir, f"{name}.png"), "PNG")
        sprite.close()
        frame.close()
        count += 1

    image.close()
    return count


def extract_frames(
    input_dir: str,
    output_dir: str,
    workers: int = 4,
    progress: Optional[ProgressCallback] = None,
    log: Optional[LogCallback] = None,
) -> JobResult:
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    tasks = _discover_sheets(input_dir)
    result = JobResult(output=output_dir)
    total = len(tasks)
    if not tasks:
        _log(log, "No se encontraron pares PNG + XML.")
        return result

    _log(log, f"Spritesheets encontrados: {total}")
    done = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_map = {
            pool.submit(_extract_one_sheet, png, xml, output_dir, rel): (png, count)
            for png, xml, rel, count in tasks
        }
        for future in as_completed(future_map):
            png, _ = future_map[future]
            try:
                frames = future.result()
                result.processed += frames
                _log(log, f"✓ {Path(png).name}: {frames} frames")
            except Exception as exc:
                result.errors += 1
                _log(log, f"✗ {Path(png).name}: {exc}")
            with lock:
                done += 1
                _progress(progress, "Extrayendo sprites", done, total)
    return result


def get_dimensions_from_txt(folder: str) -> Optional[tuple[int, int]]:
    try:
        names = os.listdir(folder)
    except OSError:
        return None
    for filename in names:
        if not filename.lower().endswith(".txt"):
            continue
        try:
            content = Path(folder, filename).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        match = re.search(r"(\d+)x(\d+)", content)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def auto_scale(dim: Optional[tuple[int, int]]) -> float:
    if not dim:
        return 1.0
    width, height = dim
    average = (width + height) / 2
    if average >= 8192:
        return 0.25
    if average >= 7000:
        return 0.45
    if average >= 6000:
        return 0.55
    if average >= 5000:
        return 0.60
    if average >= 4096:
        return 0.70
    if average >= 3000:
        return 0.80
    return 1.0


def _resize_one(source: str, destination: str, factor: float) -> None:
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if factor == 1.0:
        shutil.copy2(source, destination)
        return
    with Image.open(source) as image:
        width = max(1, int(image.width * factor))
        height = max(1, int(image.height * factor))
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        resized.save(destination, "PNG")
        resized.close()


def write_scala(path: str, factors: dict[str, float]) -> str:
    scala_path = os.path.join(path, "Scala.txt")
    with open(scala_path, "w", encoding="utf-8") as f:
        f.write("# Archivo de escalas generado automáticamente\n")
        f.write("# Formato: NombreSprite,Scala=1/factor\n")
        f.write("# -------------------------------------------------\n\n")
        for name in sorted(factors):
            factor = factors[name]
            if factor:
                f.write(f"{name},Scala={round(1 / factor, 4)}\n")
    return scala_path


def resize_frames(
    input_dir: str,
    output_dir: str,
    factor: Optional[float] = None,
    workers: int = 4,
    progress: Optional[ProgressCallback] = None,
    log: Optional[LogCallback] = None,
) -> JobResult:
    """Resize PNGs recursively. factor=None uses the original automatic scale rules."""
    if factor is not None and not (0 < factor <= 1):
        raise ValueError("El factor debe ser mayor que 0 y menor o igual a 1.")

    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    tasks: list[tuple[str, str, float]] = []
    factors: dict[str, float] = {}

    for root, _, files in os.walk(input_dir):
        pngs = [name for name in files if name.lower().endswith(".png")]
        if not pngs:
            continue
        rel_root = os.path.relpath(root, input_dir)
        current_factor = factor if factor is not None else auto_scale(get_dimensions_from_txt(root))
        key = rel_root.replace("\\", "/") if rel_root != "." else Path(root).name
        factors[key] = current_factor
        for name in pngs:
            source = os.path.join(root, name)
            destination_root = output_dir if rel_root == "." else os.path.join(output_dir, rel_root)
            tasks.append((source, os.path.join(destination_root, name), current_factor))

    result = JobResult(output=output_dir)
    total = len(tasks)
    if total == 0:
        _log(log, "No se encontraron PNG para redimensionar.")
        return result

    _log(log, f"Imágenes encontradas: {total}")
    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_map = {pool.submit(_resize_one, s, d, f): (s, f) for s, d, f in tasks}
        for future in as_completed(future_map):
            source, used_factor = future_map[future]
            try:
                future.result()
                result.processed += 1
            except Exception as exc:
                result.errors += 1
                _log(log, f"✗ {Path(source).name}: {exc}")
            with lock:
                done += 1
                _progress(progress, f"Redimensionando ({used_factor:g}x)", done, total)

    write_scala(output_dir, factors)
    return result


def trim(image: Image.Image, threshold: int = 5) -> tuple[Image.Image, tuple[int, int, int, int]]:
    rgba = image.convert("RGBA")
    r, g, b, a = rgba.split()
    a = a.point(lambda p: p if p >= threshold else 0)
    thresholded = Image.merge("RGBA", (r, g, b, a))
    bbox = thresholded.getbbox()
    thresholded.close()
    if bbox:
        cropped = rgba.crop(bbox)
        rgba.close()
        return cropped, bbox
    return rgba, (0, 0, image.width, image.height)


def find_leaf_image_folders(folder: str) -> list[str]:
    found = []
    for root, _, files in os.walk(folder):
        if any(name.lower().endswith((".png", ".jpg", ".jpeg")) for name in files):
            found.append(root)
    return found


def _image_digest(image: Image.Image) -> str:
    digest = hashlib.sha1()
    digest.update(str(image.size).encode("ascii"))
    digest.update(image.mode.encode("ascii"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def _pack_folder(folder: str, input_root: str, output_root: str, padding: int = 2) -> tuple[str, str]:
    relative = os.path.relpath(folder, input_root)
    final_dir = os.path.join(output_root, os.path.dirname(relative))
    os.makedirs(final_dir, exist_ok=True)
    sheet_name = os.path.basename(folder)

    image_files = sorted(
        name for name in os.listdir(folder)
        if name.lower().endswith((".png", ".jpg", ".jpeg"))
    )
    processed = []
    for filename in image_files:
        with Image.open(os.path.join(folder, filename)) as opened:
            original_size = opened.size
            trimmed, bbox = trim(opened)
        processed.append((filename, trimmed, bbox, original_size))

    unique = []
    duplicates = []
    digest_map: dict[str, str] = {}
    for filename, image, bbox, original_size in processed:
        digest = _image_digest(image)
        if digest not in digest_map:
            digest_map[digest] = filename
            unique.append((filename, image, bbox, original_size))
        else:
            duplicates.append((filename, digest_map[digest], bbox, original_size))
            image.close()

    unique.sort(key=lambda item: item[1].height, reverse=True)
    total_area = sum((img.width + padding) * (img.height + padding) for _, img, _, _ in unique)
    initial = ceil(sqrt(total_area)) if total_area else 1
    max_width = max((img.width for _, img, _, _ in unique), default=1)
    max_height = max((img.height for _, img, _, _ in unique), default=1)
    sheet_size = max(initial, max_width, max_height)

    while True:
        try:
            sheet = Image.new("RGBA", (sheet_size, sheet_size), (0, 0, 0, 0))
            shelves = []
            max_x = 0
            max_y = 0
            xml_root = ET.Element("TextureAtlas", imagePath=f"{sheet_name}.png")
            sprite_data: dict[str, dict[str, str]] = {}

            for filename, image, bbox, original_size in unique:
                packed = False
                x_pos = y_pos = 0
                for shelf in shelves:
                    if shelf["current_x"] + image.width + padding <= sheet_size and image.height <= shelf["height"]:
                        x_pos = shelf["current_x"]
                        y_pos = shelf["y"]
                        shelf["current_x"] += image.width + padding
                        packed = True
                        break

                if not packed:
                    new_y = 0 if not shelves else shelves[-1]["y"] + shelves[-1]["height"] + padding
                    if new_y + image.height + padding > sheet_size:
                        sheet.close()
                        raise ValueError("increase")
                    x_pos = 0
                    y_pos = new_y
                    shelves.append({"y": new_y, "height": image.height, "current_x": image.width + padding})

                sheet.paste(image, (x_pos, y_pos))
                max_x = max(max_x, x_pos + image.width)
                max_y = max(max_y, y_pos + image.height)

                node = ET.SubElement(xml_root, "SubTexture")
                node.set("name", Path(filename).stem)
                node.set("x", str(x_pos))
                node.set("y", str(y_pos))
                node.set("width", str(image.width))
                node.set("height", str(image.height))
                node.set("frameWidth", str(original_size[0]))
                node.set("frameHeight", str(original_size[1]))
                node.set("frameX", str(-bbox[0]))
                node.set("frameY", str(-bbox[1]))
                sprite_data[filename] = {
                    "x": str(x_pos), "y": str(y_pos),
                    "width": str(image.width), "height": str(image.height),
                }

            for filename, original_filename, bbox, original_size in duplicates:
                original = sprite_data[original_filename]
                node = ET.SubElement(xml_root, "SubTexture")
                node.set("name", Path(filename).stem)
                for key in ("x", "y", "width", "height"):
                    node.set(key, original[key])
                node.set("frameWidth", str(original_size[0]))
                node.set("frameHeight", str(original_size[1]))
                node.set("frameX", str(-bbox[0]))
                node.set("frameY", str(-bbox[1]))

            children = sorted(xml_root.findall("SubTexture"), key=lambda node: node.get("name", ""))
            for child in children:
                xml_root.remove(child)
                xml_root.append(child)

            if max_x and max_y:
                cropped_sheet = sheet.crop((0, 0, max_x, max_y))
                sheet.close()
                sheet = cropped_sheet

            png_out = os.path.join(final_dir, f"{sheet_name}.png")
            xml_out = os.path.join(final_dir, f"{sheet_name}.xml")
            sheet.save(png_out, "PNG")
            sheet.close()

            xml_bytes = ET.tostring(xml_root, encoding="utf-8")
            pretty = minidom.parseString(xml_bytes).toprettyxml(indent="    ")
            body = pretty.split("?>", 1)[1].strip() if "?>" in pretty else pretty
            Path(xml_out).write_text("<?xml version='1.0' encoding='utf-8'?>\n\n" + body, encoding="utf-8")
            break
        except ValueError:
            sheet_size = max(sheet_size + 1, int(sheet_size * 1.15))

    for _, image, _, _ in unique:
        image.close()
    return png_out, xml_out


def generate_spritesheets(
    input_dir: str,
    output_dir: str,
    workers: int = 4,
    progress: Optional[ProgressCallback] = None,
    log: Optional[LogCallback] = None,
) -> JobResult:
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    folders = find_leaf_image_folders(input_dir)
    result = JobResult(output=output_dir)
    total = len(folders)
    if total == 0:
        _log(log, "No se encontraron carpetas con frames.")
        return result

    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_map = {pool.submit(_pack_folder, folder, input_dir, output_dir): folder for folder in folders}
        for future in as_completed(future_map):
            folder = future_map[future]
            try:
                png_out, _ = future.result()
                result.processed += 1
                _log(log, f"✓ Generado: {Path(png_out).name}")
            except Exception as exc:
                result.errors += 1
                _log(log, f"✗ {Path(folder).name}: {exc}")
            with lock:
                done += 1
                _progress(progress, "Generando spritesheets", done, total)
    return result


def clean_directory(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def full_pipeline(
    input_dir: str,
    workspace: str,
    factor: Optional[float] = None,
    workers: int = 4,
    progress: Optional[ProgressCallback] = None,
    log: Optional[LogCallback] = None,
) -> dict[str, JobResult]:
    frames = os.path.join(workspace, "frames")
    resized = os.path.join(workspace, "resized")
    sprites = os.path.join(workspace, "sprites")
    for path in (frames, resized, sprites):
        clean_directory(path)

    _log(log, "=== 1/3 Extracción ===")
    extraction = extract_frames(input_dir, frames, workers, progress, log)
    if extraction.processed == 0:
        return {"extract": extraction}

    _log(log, "=== 2/3 Redimensión ===")
    resize = resize_frames(frames, resized, factor, workers, progress, log)

    _log(log, "=== 3/3 Generación ===")
    generation = generate_spritesheets(resized, sprites, workers, progress, log)
    return {"extract": extraction, "resize": resize, "generate": generation}
