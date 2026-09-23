# main.py - Script principal que integra TODOS los métodos (Frame + Redimension + Generación)
# + Soporte para PsychEngine y V-Slice (con flujo automático completo + Scala.txt + 998)
import os
import sys
import shutil
import re
import threading
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops
from xml.dom import minidom
from math import ceil, sqrt
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ============================================
# CONFIGURACIÓN DE RUTAS (DINÁMICA POR ENGINE)
# ============================================

CARPETA_PRINCIPAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARPETA_SPRITES = None
CARPETA_SPRITES_LISTA = []
CARPETA_FRAMES = None
CARPETA_REDIMENSION = None
CARPETA_SPRITES_OPTIMIZADOS = None
ENGINE_ACTUAL = None


def configurar_paths_psych():
    """Configura los paths para PsychEngine"""
    global CARPETA_SPRITES, CARPETA_SPRITES_LISTA, CARPETA_FRAMES, CARPETA_REDIMENSION, CARPETA_SPRITES_OPTIMIZADOS, ENGINE_ACTUAL
    CARPETA_SPRITES = os.path.join(CARPETA_PRINCIPAL, "Optimizacion-psychEnguine", "Optimizacion_Sprites")
    CARPETA_SPRITES_LISTA = [CARPETA_SPRITES]
    CARPETA_FRAMES = os.path.join(CARPETA_SPRITES, "frames")
    CARPETA_REDIMENSION = os.path.join(CARPETA_SPRITES, "redimensinando")
    CARPETA_SPRITES_OPTIMIZADOS = os.path.join(CARPETA_SPRITES, "sprites_optimizados")
    ENGINE_ACTUAL = "PsychEngine"


def configurar_paths_vslice(mod_name, tipo_ruta):
    """Configura los paths para V-Slice"""
    global CARPETA_SPRITES, CARPETA_SPRITES_LISTA, CARPETA_FRAMES, CARPETA_REDIMENSION, CARPETA_SPRITES_OPTIMIZADOS, ENGINE_ACTUAL
    base_mod = os.path.join(CARPETA_PRINCIPAL, "Optimizacion_V-slice", "Optimizar_Sprites", mod_name)

    p1 = os.path.join(base_mod, "images", "characters")
    p2 = os.path.join(base_mod, "shared", "images", "characters")

    if tipo_ruta == "1":
        paths = [p1]
    elif tipo_ruta == "2":
        paths = [p2]
    elif tipo_ruta == "auto_both":
        paths = [p1, p2]
    else:
        paths = [p1]

    CARPETA_SPRITES = paths[0]
    CARPETA_SPRITES_LISTA = paths
    CARPETA_FRAMES = os.path.join(base_mod, "frames")
    CARPETA_REDIMENSION = os.path.join(base_mod, "redimensinando")
    CARPETA_SPRITES_OPTIMIZADOS = None
    ENGINE_ACTUAL = f"V-Slice ({mod_name})"


# Colores
RESET = "\033[0m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
PURPLE = "\033[95m"
ORANGE = "\033[38;5;208m"

FACTORES_USADOS = {}
FACTORES_LOCK = threading.Lock()


# ============================================
# UTILIDADES DE TERMINAL
# ============================================

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


# ============================================
# MÉTODO 1: FRAME - EXTRACCIÓN
# ============================================

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def extract_frames_mejorado(png_path, xml_path, output_dir, overall_progress, file_progress, task_index, relative_path):
    try:
        image = Image.open(png_path).convert("RGBA")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        png_name = os.path.splitext(os.path.basename(png_path))[0]
        frame_output_dir = os.path.join(output_dir, relative_path, png_name)
        os.makedirs(frame_output_dir, exist_ok=True)
        
        canvas_size_file = os.path.join(frame_output_dir, f"{image.width}x{image.height}.txt")
        with open(canvas_size_file, 'w', encoding="utf-8") as f:
            f.write(f"Original spritesheet: {image.width}x{image.height}\nModo: XML")
        
        subtextures = root.findall(".//SubTexture")
        
        for subtexture in subtextures:
            name = sanitize_filename(subtexture.attrib.get("name", "frame"))
            x = int(float(subtexture.attrib.get("x", 0)))
            y = int(float(subtexture.attrib.get("y", 0)))
            width = int(float(subtexture.attrib.get("width", 0)))
            height = int(float(subtexture.attrib.get("height", 0)))
            
            frameX = int(float(subtexture.attrib.get("frameX", 0)))
            frameY = int(float(subtexture.attrib.get("frameY", 0)))
            frameWidth = int(float(subtexture.attrib.get("frameWidth", width)))
            frameHeight = int(float(subtexture.attrib.get("frameHeight", height)))
            
            rotated = subtexture.attrib.get("rotated", "false").lower() == "true"
            sprite_crop = image.crop((x, y, x + width, y + height))
            
            if rotated:
                sprite_crop = sprite_crop.transpose(Image.ROTATE_90)
                width, height = height, width
            
            paste_x = abs(frameX) if frameX < 0 else 0
            paste_y = abs(frameY) if frameY < 0 else 0
            
            canvas_w = max(frameWidth, width + paste_x)
            canvas_h = max(frameHeight, height + paste_y)
            
            frame_image = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            frame_image.paste(sprite_crop, (paste_x, paste_y))
            
            frame_path = os.path.join(frame_output_dir, f"{name}.png")
            frame_image.save(frame_path, "PNG")
            
            file_progress[task_index].update(1)
            overall_progress.update(1)
        
        print(f"Procesamiento de {png_name}: Completado correctamente.")
    
    except ET.ParseError as e:
        print(f"Error parsing {xml_path}: {e}")
    except Exception as e:
        print(f"Unexpected error processing {png_path} and {xml_path}: {e}")


def collect_tasks(base_dir):
    tasks = []
    skip_dirs = {'frames_output', 'Quegod', 'frames', 'redimensinando', 'sprites_optimizados',
                 '_temp_frames', '_temp_redimensinando'}

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith(".png"):
                png_path = os.path.join(root, file)
                xml_path = os.path.splitext(png_path)[0] + ".xml"
                
                if os.path.exists(xml_path):
                    try:
                        tree = ET.parse(xml_path)
                        root_xml = tree.getroot()
                        frame_count = len(root_xml.findall(".//SubTexture"))
                        relative_path = os.path.relpath(os.path.dirname(png_path), base_dir)
                        tasks.append((png_path, xml_path, relative_path, frame_count))
                    except ET.ParseError:
                        print(f"Error parsing {xml_path}, skipping.")
    return tasks


def process_directory(base_dir):
    bases = [base_dir] if isinstance(base_dir, str) else list(base_dir)
    bases = [b for b in bases if b and os.path.exists(b)]

    if not bases:
        print("No hay rutas de sprites válidas.")
        return

    output_base_dir = CARPETA_FRAMES
    os.makedirs(output_base_dir, exist_ok=True)

    use_prefix = len(bases) > 1
    tasks = []
    for base in bases:
        for task in collect_tasks(base):
            png_path, xml_path, rel_path, frame_count = task
            if use_prefix:
                parts = os.path.normpath(base).replace("\\", "/").split("/")
                prefix = "_".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
                rel_path = prefix if rel_path == "." else os.path.join(prefix, rel_path)
            tasks.append((png_path, xml_path, rel_path, frame_count))

    total_frames = sum(task[3] for task in tasks)

    if total_frames == 0:
        print("No se encontraron spritesheets para procesar.")
        return

    overall_progress = tqdm(total=total_frames, desc="Progreso general", unit="frame", position=0)
    file_progress = [
        tqdm(total=task[3], desc=f"Procesando {os.path.basename(task[0])}", unit="frame", position=i + 1)
        for i, task in enumerate(tasks)
    ]

    with ThreadPoolExecutor() as executor:
        futures = []
        for i, (png_path, xml_path, relative_path, frame_count) in enumerate(tasks):
            futures.append(executor.submit(
                extract_frames_mejorado, png_path, xml_path, output_base_dir,
                overall_progress, file_progress, i, relative_path
            ))
        for future in futures:
            future.result()

    for bar in file_progress:
        bar.close()
    overall_progress.close()


# ============================================
# MÉTODO 2: REDIMENSION
# ============================================

def list_dirs(path):
    return [d for d in sorted(os.listdir(path)) if os.path.isdir(os.path.join(path, d))]


def show_interface(current_path, subfolders, selected_folders):
    clear_screen()
    print(f"{CYAN}Navegando: {current_path}{RESET}")
    print("Carpetas disponibles:")

    for i, folder in enumerate(subfolders):
        full_path = os.path.join(current_path, folder)
        if full_path in selected_folders:
            factor = selected_folders[full_path]
            checked = f"{GREEN}[✓ {factor}]{RESET}"
        else:
            checked = "[ ]"
        print(f"{i + 1}. {checked} {folder}")

    print("\nOpciones:")
    print("1,2,3 - Seleccionar carpetas")
    print("0 - Seleccionar TODAS las carpetas")
    print("999 [n] - Entrar a subcarpeta")
    print("998 - Retroceder")
    print("/xd - Automatizar selección")
    print("x - Ejecutar\n")


def get_dimensions_from_txt(folder_path):
    txt_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.txt')]
    for txt_file in txt_files:
        with open(os.path.join(folder_path, txt_file), 'r') as f:
            content = f.read().strip()
            matches = re.findall(r'(\d+)x(\d+)', content)
            if matches:
                return tuple(map(int, matches[0]))
    return None


def calcular_factor(dim):
    if not dim:
        return 1.0
    ancho, alto = dim
    promedio = (ancho + alto) / 2
    if promedio >= 8192:
        return 0.25
    elif 7000 <= promedio < 8192:
        return 0.45
    elif 6000 <= promedio < 7000:
        return 0.55
    elif 5000 <= promedio < 6000:
        return 0.6
    elif 4096 <= promedio < 5000:
        return 0.7
    elif 3000 <= promedio < 4096:
        return 0.8
    return 1.0


def multiply_image(image_path, output_path, factor):
    img = Image.open(image_path)
    new_size = (int(img.width * factor), int(img.height * factor))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    resized.save(output_path)


def redimensionar_lote(archivos, factor, print_lock=None):
    ok = 0
    errores = 0
    
    def procesar_una(tupla):
        input_file, output_file = tupla
        try:
            multiply_image(input_file, output_file, factor)
            return True
        except Exception:
            return False
    
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(procesar_una, t) for t in archivos]
        for future in as_completed(futures):
            try:
                if future.result():
                    ok += 1
                else:
                    errores += 1
            except Exception:
                errores += 1
    
    return ok, errores


def aplicar_redimension_automatica(input_dir, output_dir):
    """Redimensionamiento automático. ❌ NO crea .txt individuales."""
    total_ok = 0
    total_err = 0
    total_copiados = 0
    factores_dict = {}
    
    for root, dirs, files in os.walk(input_dir):
        png_files = [f for f in files if f.endswith('.png')]
        if not png_files:
            continue
        
        rel_path = os.path.relpath(root, input_dir)
        export_path = os.path.join(output_dir, rel_path) if rel_path != '.' else output_dir
        os.makedirs(export_path, exist_ok=True)
        
        dim = get_dimensions_from_txt(root)
        factor = calcular_factor(dim)
        
        nombre_scala = rel_path.replace("\\", "/") if rel_path != '.' else None
        if nombre_scala:
            factores_dict[nombre_scala] = factor
        
        tareas = [
            (os.path.join(root, f), os.path.join(export_path, f))
            for f in png_files
        ]
        
        if factor != 1.0:
            print(f"{CYAN}  📂 {rel_path} → factor: {factor}x ({len(tareas)} imgs){RESET}")
            bar = tqdm(total=len(tareas), desc=f"    {os.path.basename(root)}", unit="img", leave=False)
            ok, err = redimensionar_lote(tareas, factor)
            bar.update(len(tareas))
            bar.close()
            total_ok += ok
            total_err += err
            if err > 0:
                print(f"    {YELLOW}⚠ {err} errores{RESET}")
        else:
            print(f"{CYAN}  📂 {rel_path} → sin cambios (factor 1.0){RESET}")
            for inp, out in tareas:
                try:
                    shutil.copy2(inp, out)
                    total_copiados += 1
                except Exception as e:
                    print(f"    {YELLOW}⚠ Error copiando: {e}{RESET}")
    
    print(f"\n{GREEN}  ✓ Redimensionados: {total_ok} | Copiados: {total_copiados} | Errores: {total_err}{RESET}")
    return total_ok, total_err, factores_dict


def crear_scala_vslice(ruta_destino, factores_dict):
    """Crea Scala.txt en la carpeta destino con formato PsychEngine."""
    if not factores_dict:
        print(f"{YELLOW}  ⚠ No hay factores para escribir en Scala.txt{RESET}")
        return None
    
    scala_path = os.path.join(ruta_destino, "Scala.txt")
    
    try:
        with open(scala_path, 'w', encoding='utf-8') as f:
            f.write("# Archivo de escalas generado automáticamente\n")
            f.write("# Formato: NombreSprite,Scala=1/factor\n")
            f.write("# -------------------------------------------------\n\n")
            
            for nombre, factor in factores_dict.items():
                if factor and factor != 0:
                    scala = round(1 / factor, 4)
                    f.write(f"{nombre},Scala={scala}\n")
        
        print(f"{GREEN}  ✓ Scala.txt creado: {len(factores_dict)} entradas{RESET}")
        return scala_path
    except Exception as e:
        print(f"{RED}  ✗ Error creando Scala.txt: {e}{RESET}")
        return None


def process_folder(input_path, output_path, mode):
    for root, dirs, files in os.walk(input_path):
        rel_path = os.path.relpath(root, input_path)
        export_path = os.path.join(output_path, rel_path)
        os.makedirs(export_path, exist_ok=True)

        if mode == "/xd":
            dim = get_dimensions_from_txt(root)
            factor = calcular_factor(dim)
            if factor != 1.0:
                print(f"{YELLOW}Auto-factor para {rel_path}: {factor}x{RESET}")
        else:
            factor = float(mode)

        images = [f for f in files if f.endswith('.png')]
        if not images:
            continue

        tareas = []
        for img_file in images:
            input_file = os.path.join(root, img_file)
            output_file = os.path.join(export_path, img_file)
            tareas.append((input_file, output_file))

        bar = tqdm(total=len(tareas), desc=f"Procesando {rel_path}", unit="img")
        ok, err = redimensionar_lote(tareas, factor)
        bar.update(len(tareas))
        bar.close()

        if err > 0:
            print(f"{YELLOW}⚠ {err} errores en {rel_path}{RESET}")


def metodo_redimension_interfaz_original():
    current_path = CARPETA_FRAMES
    selected_folders = {}
    
    while True:
        subfolders = list_dirs(current_path)
        show_interface(current_path, subfolders, selected_folders)
        command = input("Ingrese comando: ").strip()
        
        if command == "x":
            if not selected_folders:
                print(f"{RED}No se seleccionaron carpetas{RESET}")
                continue
            output_path = CARPETA_REDIMENSION
            os.makedirs(output_path, exist_ok=True)
            for folder_path, factor in selected_folders.items():
                print(f"{GREEN}Procesando {folder_path} con factor {factor}{RESET}")
                process_folder(folder_path, output_path, str(factor))
            print(f"{GREEN}Proceso completado{RESET}")
            break
        elif command == "/xd":
            selected_folders = {}
            for folder in subfolders:
                full_path = os.path.join(current_path, folder)
                selected_folders[full_path] = "/xd"
            print(f"{GREEN}Seleccionado automático para todas las carpetas{RESET}")
        elif command == "0":
            selected_folders = {}
            for folder in subfolders:
                full_path = os.path.join(current_path, folder)
                selected_folders[full_path] = 1.0
            print(f"{GREEN}Seleccionadas todas las carpetas{RESET}")
        elif command == "998":
            parent = os.path.dirname(current_path)
            if parent:
                current_path = parent
        elif command.startswith("999"):
            parts = command.split()
            if len(parts) > 1:
                index = int(parts[1]) - 1
                if 0 <= index < len(subfolders):
                    current_path = os.path.join(current_path, subfolders[index])
        elif command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(subfolders):
                folder = subfolders[index]
                full_path = os.path.join(current_path, folder)
                if full_path in selected_folders:
                    del selected_folders[full_path]
                    print(f"{YELLOW}Deseleccionado: {folder}{RESET}")
                else:
                    print(f"\n{YELLOW}Seleccione factor para {folder}:{RESET}")
                    print("1. 75% (0.75)")
                    print("2. 50% (0.5)")
                    print("3. 40% (0.4)")
                    print("4. 25% (0.25)")
                    print("5. Personalizado")
                    while True:
                        try:
                            option = input("Opción (1-5): ").strip()
                            if option == "1":
                                factor = 0.75
                                break
                            elif option == "2":
                                factor = 0.5
                                break
                            elif option == "3":
                                factor = 0.4
                                break
                            elif option == "4":
                                factor = 0.25
                                break
                            elif option == "5":
                                factor = float(input("Ingrese factor (ej: 0.33): "))
                                break
                            else:
                                print(f"{RED}Opción no válida{RESET}")
                        except ValueError:
                            print(f"{RED}Valor no válido{RESET}")
                    selected_folders[full_path] = factor
                    print(f"{GREEN}Seleccionado: {folder} con factor {factor}{RESET}")


# ============================================
# MÉTODO 3: GENERACIÓN DE SPRITESHEETS
# ============================================

def trim(image, threshold=5):
    img_rgba = image.convert("RGBA")
    r, g, b, a = img_rgba.split()
    a = a.point(lambda p: p if p >= threshold else 0)
    img_thresh = Image.merge("RGBA", (r, g, b, a))
    bbox = img_thresh.getbbox()
    if bbox:
        return img_rgba.crop(bbox), bbox
    return img_rgba, (0, 0, image.width, image.height)


def find_leaf_folders(folder):
    leaf_folders = []
    for root, dirs, files in os.walk(folder):
        image_files = [f for f in files if f.lower().endswith(('png', 'jpg', 'jpeg'))]
        if image_files:
            leaf_folders.append(root)
    return leaf_folders


def generate_spritesheet(image_folder, output_folder):
    """Genera PNG + XML. ❌ NO copia .txt."""
    image_folders = find_leaf_folders(image_folder)

    for folder in tqdm(image_folders, desc="Procesando carpetas"):
        relative_path = os.path.relpath(folder, image_folder)
        final_output_dir = os.path.join(output_folder, os.path.dirname(relative_path))
        os.makedirs(final_output_dir, exist_ok=True)

        original_folder_name = os.path.basename(folder)
        image_files = sorted([file for file in os.listdir(folder) if file.lower().endswith(('png', 'jpg', 'jpeg'))])
        images = [Image.open(os.path.join(folder, file)) for file in image_files]

        processed_data = []
        for img, file_name in zip(images, image_files):
            trimmed_img, bbox = trim(img)
            processed_data.append((file_name, trimmed_img, bbox, img.size))

        unique_trimmed = []
        duplicates = []
        hash_map = {}

        for file_name, trimmed_img, bbox, orig_size in processed_data:
            img_hash = hash(trimmed_img.tobytes())
            if img_hash not in hash_map:
                hash_map[img_hash] = file_name
                unique_trimmed.append((file_name, trimmed_img, bbox, orig_size))
            else:
                orig_file_name = hash_map[img_hash]
                duplicates.append((file_name, orig_file_name, bbox, orig_size))

        unique_trimmed.sort(key=lambda item: item[1].height, reverse=True)

        padding = 2
        total_area = sum((img.width + padding) * (img.height + padding) for _, img, _, _ in unique_trimmed)
        initial_sheet_size = ceil(sqrt(total_area)) if total_area > 0 else 1

        max_width = max((img.width for _, img, _, _ in unique_trimmed), default=1)
        max_height = max((img.height for _, img, _, _ in unique_trimmed), default=1)
        sheet_size = max(initial_sheet_size, max_width, max_height)

        while True:
            try:
                spritesheet = Image.new("RGBA", (sheet_size, sheet_size), (0, 0, 0, 0))
                
                shelves = []
                max_x_used = 0
                max_y_used = 0
                
                root = ET.Element("TextureAtlas", imagePath=f"{original_folder_name}.png")
                sprite_dict = {}

                for file_name, img, bbox, orig_size in unique_trimmed:
                    packed = False
                    x_pos, y_pos = 0, 0
                    
                    for shelf in shelves:
                        if shelf["current_x"] + img.width + padding <= sheet_size:
                            x_pos = shelf["current_x"]
                            y_pos = shelf["y"]
                            shelf["current_x"] += img.width + padding
                            packed = True
                            break
                    
                    if not packed:
                        if not shelves:
                            new_y = 0
                        else:
                            new_y = shelves[-1]["y"] + shelves[-1]["height"] + padding
                        if new_y + img.height + padding > sheet_size:
                            raise ValueError("Increase sheet size")
                        x_pos = 0
                        y_pos = new_y
                        shelves.append({
                            "y": new_y,
                            "height": img.height,
                            "current_x": img.width + padding
                        })
                    
                    spritesheet.paste(img, (x_pos, y_pos))
                    max_x_used = max(max_x_used, x_pos + img.width)
                    max_y_used = max(max_y_used, y_pos + img.height)

                    sprite = ET.SubElement(root, "SubTexture")
                    sprite.set("name", os.path.splitext(file_name)[0])
                    sprite.set("x", str(x_pos))
                    sprite.set("y", str(y_pos))
                    sprite.set("width", str(img.width))
                    sprite.set("height", str(img.height))
                    sprite.set("frameWidth", str(orig_size[0]))
                    sprite.set("frameHeight", str(orig_size[1]))
                    sprite.set("frameX", str(-bbox[0]))
                    sprite.set("frameY", str(-bbox[1]))

                    sprite_dict[file_name] = {
                        "x": str(x_pos), "y": str(y_pos),
                        "width": str(img.width), "height": str(img.height)
                    }

                for file_name, orig_file_name, bbox, orig_size in duplicates:
                    sprite = ET.SubElement(root, "SubTexture")
                    sprite.set("name", os.path.splitext(file_name)[0])
                    orig_data = sprite_dict[orig_file_name]
                    sprite.set("x", orig_data["x"])
                    sprite.set("y", orig_data["y"])
                    sprite.set("width", orig_data["width"])
                    sprite.set("height", orig_data["height"])
                    sprite.set("frameWidth", str(orig_size[0]))
                    sprite.set("frameHeight", str(orig_size[1]))
                    sprite.set("frameX", str(-bbox[0]))
                    sprite.set("frameY", str(-bbox[1]))

                sorted_subelements = sorted(root.findall('SubTexture'), key=lambda x: x.get('name', ''))
                for subelement in sorted_subelements:
                    root.remove(subelement)
                    root.append(subelement)

                if max_x_used > 0 and max_y_used > 0:
                    spritesheet = spritesheet.crop((0, 0, max_x_used, max_y_used))

                spritesheet_path = os.path.join(final_output_dir, f"{original_folder_name}.png")
                spritesheet.save(spritesheet_path)

                xml_str = ET.tostring(root, encoding='utf-8')
                xml_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
                xml_comment = "<?xml version='1.0' encoding='utf-8'?>\n\n"
                xml_str = xml_comment + xml_str.split("?>", 1)[1].strip()

                xml_file_path = os.path.join(final_output_dir, f"{original_folder_name}.xml")
                with open(xml_file_path, "w") as xml_file:
                    xml_file.write(xml_str)

                break
                
            except ValueError:
                sheet_size = int(sheet_size * 1.15)


def metodo_generacion():
    if not CARPETA_SPRITES_OPTIMIZADOS:
        print(f"\n{RED}❌ Este método no está disponible en el modo actual.{RESET}")
        print(f"{YELLOW}💡 En V-Slice usa el modo Automatizar (999) para generar directo en characters.{RESET}")
        return False
    
    print(f"\n{CYAN}╔════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║   MÉTODO 3: GENERACIÓN DE SPRITESHEETS  ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════╝{RESET}")
    
    print(f"\n{YELLOW}Ruta de entrada:{RESET} {CARPETA_REDIMENSION}/")
    print(f"{YELLOW}Ruta de salida:{RESET} {CARPETA_SPRITES_OPTIMIZADOS}/\n")
    
    if not os.path.exists(CARPETA_REDIMENSION):
        print(f"{RED}❌ La carpeta 'redimensinando/' no existe.{RESET}")
        if os.path.exists(CARPETA_FRAMES):
            usar_frames = input(f"¿Usar frames sin redimensionar? (s/n): ").lower()
            if usar_frames == 's':
                carpeta_entrada = CARPETA_FRAMES
            else:
                return False
        else:
            return False
    else:
        carpeta_entrada = CARPETA_REDIMENSION
    
    num_archivos = sum(1 for _, _, files in os.walk(carpeta_entrada) for f in files if f.endswith('.png'))
    if num_archivos == 0:
        print(f"{RED}❌ No hay archivos para procesar.{RESET}")
        return False
    
    print(f"{GREEN}📊 Archivos encontrados: {num_archivos}{RESET}")
    
    carpetas_con_imagenes = []
    for root, dirs, files in os.walk(carpeta_entrada):
        png_files = [f for f in files if f.endswith('.png')]
        if png_files:
            rel_path = os.path.relpath(root, carpeta_entrada)
            if rel_path != '.':
                carpetas_con_imagenes.append((rel_path, len(png_files)))
    
    if carpetas_con_imagenes:
        print(f"{GREEN}📁 Carpetas encontradas: {len(carpetas_con_imagenes)}{RESET}")
        print(f"\n{YELLOW}📂 Carpetas detectadas:{RESET}")
        for i, (carpeta, cantidad) in enumerate(carpetas_con_imagenes, 1):
            print(f"{CYAN}{i:2}. {carpeta:<30} → {cantidad:>3} imágenes{RESET}")
    
    if os.path.exists(CARPETA_SPRITES_OPTIMIZADOS):
        shutil.rmtree(CARPETA_SPRITES_OPTIMIZADOS)
    os.makedirs(CARPETA_SPRITES_OPTIMIZADOS)
    
    print(f"\n{GREEN}▶ Generando spritesheets optimizados...{RESET}")
    
    try:
        generate_spritesheet(carpeta_entrada, CARPETA_SPRITES_OPTIMIZADOS)
        print(f"\n{GREEN}✅ ¡Generación completada!{RESET}")
        print(f"{BLUE}📁 Spritesheets guardados en: {CARPETA_SPRITES_OPTIMIZADOS}{RESET}")
        
        num_png = sum(1 for _, _, files in os.walk(CARPETA_SPRITES_OPTIMIZADOS) for f in files if f.endswith('.png'))
        num_xml = sum(1 for _, _, files in os.walk(CARPETA_SPRITES_OPTIMIZADOS) for f in files if f.endswith('.xml'))
        num_txt = sum(1 for _, _, files in os.walk(CARPETA_SPRITES_OPTIMIZADOS) for f in files if f.endswith('.txt'))
        print(f"{GREEN}📊 Resumen: {num_png} PNG + {num_xml} XML + {num_txt} TXT{RESET}")
        
        crear_archivo_scala()
        return True
    except Exception as e:
        print(f"{RED}❌ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# AUXILIARES
# ============================================

def crear_estructura_carpetas():
    carpetas = [c for c in [
        CARPETA_SPRITES,
        CARPETA_FRAMES,
        CARPETA_REDIMENSION,
        CARPETA_SPRITES_OPTIMIZADOS
    ] if c]
    
    for carpeta in carpetas:
        if not os.path.exists(carpeta):
            os.makedirs(carpeta, exist_ok=True)
            try:
                rel = os.path.relpath(carpeta, CARPETA_PRINCIPAL)
            except ValueError:
                rel = carpeta
            print(f"{GREEN}📁 Creada carpeta: {rel}{RESET}")
    return True


def verificar_sprites_originales():
    bases = CARPETA_SPRITES_LISTA if CARPETA_SPRITES_LISTA else ([CARPETA_SPRITES] if CARPETA_SPRITES else [])
    if not bases:
        return False
    for base in bases:
        if not base or not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            if any(folder in root for folder in ['frames', 'redimensinando', 'sprites_optimizados',
                                                  '_temp_frames', '_temp_redimensinando']):
                continue
            for file in files:
                if file.endswith('.png'):
                    return True
    return False


def mostrar_estructura():
    if not CARPETA_SPRITES:
        return
    
    print(f"\n{CYAN}📂 Estructura actual ({ENGINE_ACTUAL}):{RESET}")
    
    try:
        rel_frames = os.path.relpath(CARPETA_FRAMES, CARPETA_PRINCIPAL) if CARPETA_FRAMES else None
        rel_redim = os.path.relpath(CARPETA_REDIMENSION, CARPETA_PRINCIPAL) if CARPETA_REDIMENSION else None
        rel_opt = os.path.relpath(CARPETA_SPRITES_OPTIMIZADOS, CARPETA_PRINCIPAL) if CARPETA_SPRITES_OPTIMIZADOS else None
    except ValueError:
        rel_frames = CARPETA_FRAMES
        rel_redim = CARPETA_REDIMENSION
        rel_opt = CARPETA_SPRITES_OPTIMIZADOS
    
    print(f"{BLUE}└── {os.path.basename(CARPETA_PRINCIPAL)}/{RESET}")
    
    bases = CARPETA_SPRITES_LISTA if CARPETA_SPRITES_LISTA else ([CARPETA_SPRITES] if CARPETA_SPRITES else [])
    for base in bases:
        try:
            rel_sprites = os.path.relpath(base, CARPETA_PRINCIPAL)
        except ValueError:
            rel_sprites = base
        if os.path.exists(base):
            num_orig = 0
            for root, dirs, files in os.walk(base):
                if any(x in root for x in ['frames', 'redimensinando', 'sprites_optimizados',
                                            '_temp_frames', '_temp_redimensinando']):
                    continue
                num_orig += sum(1 for f in files if f.endswith('.png'))
            print(f"{BLUE}    ├── {rel_sprites}/  {GREEN}({num_orig} sprites){RESET}")
        else:
            print(f"{BLUE}    ├── {rel_sprites}/  {YELLOW}(no existe){RESET}")
    
    if CARPETA_FRAMES:
        if os.path.exists(CARPETA_FRAMES):
            num_frames = sum(1 for _, _, files in os.walk(CARPETA_FRAMES) for f in files if f.endswith('.png'))
            print(f"{BLUE}    ├── {rel_frames}/  {GREEN}({num_frames} frames){RESET}")
        else:
            print(f"{BLUE}    ├── {rel_frames}/  {YELLOW}(se generará){RESET}")
    
    if CARPETA_REDIMENSION:
        if os.path.exists(CARPETA_REDIMENSION):
            num_redim = sum(1 for _, _, files in os.walk(CARPETA_REDIMENSION) for f in files if f.endswith('.png'))
            print(f"{BLUE}    ├── {rel_redim}/  {GREEN}({num_redim} redimensionados){RESET}")
        else:
            print(f"{BLUE}    ├── {rel_redim}/  {YELLOW}(se generará){RESET}")
    
    if CARPETA_SPRITES_OPTIMIZADOS:
        if os.path.exists(CARPETA_SPRITES_OPTIMIZADOS):
            num_opt = sum(1 for _, _, files in os.walk(CARPETA_SPRITES_OPTIMIZADOS) for f in files if f.endswith(('.png', '.xml', '.txt')))
            print(f"{BLUE}    └── {rel_opt}/  {GREEN}({num_opt} optimizados){RESET}")
        else:
            print(f"{BLUE}    └── {rel_opt}/  {YELLOW}(se generará){RESET}")


def mostrar_banner():
    engine_display = ENGINE_ACTUAL if ENGINE_ACTUAL else "SIN ENGINE"
    print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║{MAGENTA}     SISTEMA DE OPTIMIZACIÓN DE SPRITESHEETS      {CYAN}║{RESET}")
    print(f"{CYAN}║{BLUE}        ENGINE ACTUAL: {engine_display:<29}{CYAN}║{RESET}")
    print(f"{CYAN}║{GREEN}       VERSIÓN MEJORADA - V5 + V-SLICE           {CYAN}║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")


# ============================================
# MÉTODO 1: EXTRACCIÓN
# ============================================

def metodo_frame():
    print(f"\n{CYAN}╔════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║     MÉTODO 1: EXTRACCIÓN DE FRAMES     ║{RESET}")
    print(f"{CYAN}║        VERSIÓN MEJORADA V5             ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════╝{RESET}")
    
    print(f"\n{YELLOW}Ruta de entrada:{RESET}")
    for p in CARPETA_SPRITES_LISTA:
        print(f"   • {p}/")
    print(f"{YELLOW}Ruta de salida:{RESET} {CARPETA_FRAMES}/\n")
    
    if not verificar_sprites_originales():
        print(f"{RED}❌ No se encontraron archivos .png{RESET}")
        for p in CARPETA_SPRITES_LISTA:
            print(f"{YELLOW}💡 Verifica: {p}/{RESET}")
        return False
    
    crear_estructura_carpetas()
    
    if os.path.exists(CARPETA_FRAMES) and any(os.listdir(CARPETA_FRAMES)):
        print(f"{YELLOW}⚠ La carpeta 'frames/' ya contiene archivos{RESET}")
        opcion = input(f"¿Limpiar carpeta antes de extraer? (s/n): ").lower()
        if opcion == 's':
            shutil.rmtree(CARPETA_FRAMES)
            os.makedirs(CARPETA_FRAMES)
            print(f"{GREEN}✓ Carpeta 'frames/' limpiada{RESET}")
    
    print(f"\n{GREEN}▶ Iniciando extracción...{RESET}")
    try:
        process_directory(CARPETA_SPRITES_LISTA)
        print(f"\n{GREEN}✅ ¡Extracción completada!{RESET}")
        print(f"{BLUE}📁 Frames guardados en: {CARPETA_FRAMES}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}❌ Error: {e}{RESET}")
        return False


# ============================================
# MÉTODO 2: REDIMENSIONAMIENTO
# ============================================

def metodo_redimension():
    global FACTORES_USADOS
    
    print(f"\n{CYAN}╔════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║     MÉTODO 2: REDIMENSIONAMIENTO       ║{RESET}")
    print(f"{CYAN}║           MODO MULTIHILO 🚀            ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════╝{RESET}")
    
    print(f"\n{YELLOW}Ruta de entrada:{RESET} {CARPETA_FRAMES}/")
    print(f"{YELLOW}Ruta de salida:{RESET} {CARPETA_REDIMENSION}/\n")
    
    if not os.path.exists(CARPETA_FRAMES):
        print(f"{RED}❌ La carpeta 'frames/' no existe.{RESET}")
        if verificar_sprites_originales():
            usar_sprites = input(f"¿Usar sprites sin extraer frames? (s/n): ").lower()
            if usar_sprites == 's':
                return redimensionar_directamente_desde_sprites()
        return False
    
    carpetas_con_imagenes = []
    for root, dirs, files in os.walk(CARPETA_FRAMES):
        png_files = [f for f in files if f.endswith('.png')]
        if png_files:
            rel_path = os.path.relpath(root, CARPETA_FRAMES)
            if rel_path != '.':
                carpetas_con_imagenes.append((rel_path, len(png_files)))
    
    num_frames = sum(count for _, count in carpetas_con_imagenes)
    if num_frames == 0:
        print(f"{RED}❌ No hay frames{RESET}")
        if verificar_sprites_originales():
            usar_sprites = input(f"¿Usar sprites sin extraer frames? (s/n): ").lower()
            if usar_sprites == 's':
                return redimensionar_directamente_desde_sprites()
        return False
    
    print(f"{GREEN}📊 Frames encontrados: {num_frames}{RESET}")
    print(f"{GREEN}📁 Carpetas encontradas: {len(carpetas_con_imagenes)}{RESET}")
    
    if carpetas_con_imagenes:
        print(f"\n{YELLOW}📂 Carpetas detectadas:{RESET}")
        for i, (carpeta, cantidad) in enumerate(carpetas_con_imagenes, 1):
            print(f"{CYAN}{i:2}. {carpeta:<30} → {cantidad:>3} imágenes{RESET}")
    
    if num_frames > 0:
        print(f"\n{YELLOW}❓ ¿Deseas saltar el redimensionamiento?{RESET}")
        saltar = input(f"¿Saltar? (s/n): ").lower()
        if saltar == 's':
            if os.path.exists(CARPETA_REDIMENSION):
                shutil.rmtree(CARPETA_REDIMENSION)
            shutil.copytree(CARPETA_FRAMES, CARPETA_REDIMENSION)
            print(f"{GREEN}✓ Frames copiados{RESET}")
            with FACTORES_LOCK:
                FACTORES_USADOS = {}
                for carpeta, _ in carpetas_con_imagenes:
                    FACTORES_USADOS[carpeta] = 1.0
            return True
    
    print(f"\n{YELLOW}Seleccione modo:{RESET}")
    print(f"{GREEN}1.{RESET} Automático")
    print(f"{GREEN}2.{RESET} Manual por carpeta")
    print(f"{GREEN}3.{RESET} Manual único")
    print(f"{GREEN}4.{RESET} Interfaz original")
    
    modo = input(f"\n{CYAN}Opción (1-4): {RESET}").strip()
    
    if os.path.exists(CARPETA_REDIMENSION):
        shutil.rmtree(CARPETA_REDIMENSION)
    os.makedirs(CARPETA_REDIMENSION)
    
    if modo == "1":
        print(f"\n{GREEN}⚙ Modo automático (multihilo)...{RESET}")
        try:
            with FACTORES_LOCK:
                FACTORES_USADOS = {}
            for root, dirs, files in os.walk(CARPETA_FRAMES):
                if any(f.endswith('.png') for f in files):
                    rel_path = os.path.relpath(root, CARPETA_FRAMES)
                    export_path = os.path.join(CARPETA_REDIMENSION, rel_path)
                    os.makedirs(export_path, exist_ok=True)
                    dim = get_dimensions_from_txt(root)
                    factor = calcular_factor(dim)
                    with FACTORES_LOCK:
                        if rel_path != '.':
                            FACTORES_USADOS[rel_path] = factor
                    png_files = [f for f in files if f.endswith('.png')]
                    tareas = [(os.path.join(root, f), os.path.join(export_path, f)) for f in png_files]
                    if factor != 1.0:
                        print(f"{CYAN}📂 {rel_path} → factor: {factor}x ({len(tareas)} imgs){RESET}")
                        bar = tqdm(total=len(tareas), desc=f"  {rel_path}", unit="img", leave=False)
                        ok, err = redimensionar_lote(tareas, factor)
                        bar.update(len(tareas))
                        bar.close()
                    else:
                        print(f"{CYAN}📂 {rel_path} → sin cambios (factor 1.0){RESET}")
                        for input_file, output_file in tareas:
                            try:
                                shutil.copy2(input_file, output_file)
                            except Exception as e:
                                print(f"{YELLOW}⚠ {e}{RESET}")
            print(f"\n{GREEN}✅ ¡Redimensionamiento completado!{RESET}")
            print(f"{BLUE}📁 Resultados en: {CARPETA_REDIMENSION}{RESET}")
            return True
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False

    elif modo == "2":
        print(f"\n{YELLOW}📏 MODO MANUAL POR CARPETA{RESET}")
        with FACTORES_LOCK:
            FACTORES_USADOS = {}
        factores = {}
        for carpeta, cantidad in carpetas_con_imagenes:
            print(f"\n{CYAN}┌─ Carpeta: {carpeta}{RESET}")
            print(f"{GREEN}1.{RESET} 75% | {GREEN}2.{RESET} 50% | {GREEN}3.{RESET} 40% | {GREEN}4.{RESET} 25% | {GREEN}5.{RESET} Personalizar")
            while True:
                try:
                    opcion = input(f"{CYAN}Opción (1-5): {RESET}").strip()
                    if opcion == "1":
                        factor = 0.75; break
                    elif opcion == "2":
                        factor = 0.5; break
                    elif opcion == "3":
                        factor = 0.4; break
                    elif opcion == "4":
                        factor = 0.25; break
                    elif opcion == "5":
                        porcentaje = float(input(f"Ingrese porcentaje (ej: 33): ").strip())
                        if porcentaje <= 0 or porcentaje > 100:
                            print(f"{RED}❌ Entre 0 y 100{RESET}"); continue
                        factor = porcentaje / 100.0; break
                    else:
                        print(f"{RED}❌ Opción no válida{RESET}")
                except ValueError:
                    print(f"{RED}❌ Valor inválido{RESET}")
            factores[carpeta] = factor
            with FACTORES_LOCK:
                FACTORES_USADOS[carpeta] = factor
            print(f"{GREEN}✓ {int(factor*100)}% (factor: {factor:.2f}){RESET}")
        
        print(f"\n{YELLOW}📋 RESUMEN:{RESET}")
        for carpeta, factor in factores.items():
            print(f"{CYAN}[{factor:.2f}] {carpeta} ({int(factor*100)}%){RESET}")
        
        if input(f"\n{CYAN}¿Continuar? (s/n): {RESET}").lower() != 's':
            return False
        
        try:
            total_ok = 0; total_err = 0
            for carpeta, factor in factores.items():
                input_path = os.path.join(CARPETA_FRAMES, carpeta)
                output_path = os.path.join(CARPETA_REDIMENSION, carpeta)
                os.makedirs(output_path, exist_ok=True)
                png_files = [f for f in os.listdir(input_path) if f.endswith('.png')]
                tareas = [(os.path.join(input_path, f), os.path.join(output_path, f)) for f in png_files]
                print(f"{CYAN}📂 {carpeta} → {len(tareas)} × {factor:.2f}x{RESET}")
                ok, err = redimensionar_lote(tareas, factor)
                total_ok += ok; total_err += err
            print(f"\n{GREEN}✅ Completado: {total_ok} OK | {total_err} err{RESET}")
            return True
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False

    elif modo == "3":
        print(f"\n{YELLOW}📏 MODO MANUAL ÚNICO{RESET}")
        with FACTORES_LOCK:
            FACTORES_USADOS = {}
        print(f"{GREEN}1.{RESET} 75% | {GREEN}2.{RESET} 50% | {GREEN}3.{RESET} 40% | {GREEN}4.{RESET} 25% | {GREEN}5.{RESET} Personalizar")
        while True:
            try:
                opcion = input(f"{CYAN}Opción (1-5): {RESET}").strip()
                if opcion == "1":
                    factor = 0.75; break
                elif opcion == "2":
                    factor = 0.5; break
                elif opcion == "3":
                    factor = 0.4; break
                elif opcion == "4":
                    factor = 0.25; break
                elif opcion == "5":
                    porcentaje = float(input("Porcentaje: ").strip())
                    if porcentaje <= 0 or porcentaje > 100:
                        print(f"{RED}❌ Entre 0 y 100{RESET}"); continue
                    factor = porcentaje / 100.0; break
                else:
                    print(f"{RED}❌ Opción no válida{RESET}")
            except ValueError:
                print(f"{RED}❌ Valor inválido{RESET}")
        
        with FACTORES_LOCK:
            for carpeta, _ in carpetas_con_imagenes:
                FACTORES_USADOS[carpeta] = factor
        
        if input(f"\n{CYAN}¿Continuar con {int(factor*100)}%? (s/n): {RESET}").lower() != 's':
            return False
        
        try:
            total_ok = 0; total_err = 0
            for root, dirs, files in os.walk(CARPETA_FRAMES):
                if any(f.endswith('.png') for f in files):
                    rel_path = os.path.relpath(root, CARPETA_FRAMES)
                    if rel_path == '.': continue
                    export_path = os.path.join(CARPETA_REDIMENSION, rel_path)
                    os.makedirs(export_path, exist_ok=True)
                    png_files = [f for f in files if f.endswith('.png')]
                    tareas = [(os.path.join(root, f), os.path.join(export_path, f)) for f in png_files]
                    print(f"{CYAN}📂 {rel_path} → {len(tareas)} × {factor:.2f}x{RESET}")
                    ok, err = redimensionar_lote(tareas, factor)
                    total_ok += ok; total_err += err
            print(f"\n{GREEN}✅ Completado: {total_ok} OK | {total_err} err{RESET}")
            return True
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False

    elif modo == "4":
        print(f"\n{YELLOW}⚠ Interfaz original...{RESET}")
        input("Presione Enter para continuar...")
        try:
            metodo_redimension_interfaz_original()
            with FACTORES_LOCK:
                for carpeta, _ in carpetas_con_imagenes:
                    while True:
                        try:
                            factor_str = input(f"Factor para '{carpeta}' (ej: 0.5): ").strip()
                            factor = float(factor_str)
                            if factor <= 0:
                                print(f"{RED}❌ > 0{RESET}"); continue
                            FACTORES_USADOS[carpeta] = factor
                            break
                        except ValueError:
                            print(f"{RED}❌ Valor inválido{RESET}")
            return True
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False
    else:
        print(f"{RED}❌ Opción no válida{RESET}")
        return False


def redimensionar_directamente_desde_sprites():
    global FACTORES_USADOS
    
    print(f"\n{YELLOW}🔄 Redimensionando desde sprites{RESET}")
    
    if os.path.exists(CARPETA_FRAMES):
        shutil.rmtree(CARPETA_FRAMES)
    os.makedirs(CARPETA_FRAMES)
    if os.path.exists(CARPETA_REDIMENSION):
        shutil.rmtree(CARPETA_REDIMENSION)
    os.makedirs(CARPETA_REDIMENSION)
    
    spritesheets = []
    bases = CARPETA_SPRITES_LISTA if CARPETA_SPRITES_LISTA else ([CARPETA_SPRITES] if CARPETA_SPRITES else [])
    for base in bases:
        if not base or not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            if any(folder in root for folder in ['frames', 'redimensinando', 'sprites_optimizados',
                                                  '_temp_frames', '_temp_redimensinando']):
                continue
            for file in files:
                if file.endswith('.png'):
                    base_name = os.path.splitext(file)[0]
                    xml_file = base_name + '.xml'
                    if os.path.exists(os.path.join(root, xml_file)):
                        spritesheets.append((os.path.join(root, file), os.path.join(root, xml_file)))
                    else:
                        spritesheets.append((os.path.join(root, file), None))
    
    if not spritesheets:
        print(f"{RED}❌ No hay spritesheets{RESET}")
        return False
    
    print(f"{GREEN}📊 Spritesheets: {len(spritesheets)}{RESET}")
    print(f"\n{GREEN}1.{RESET} Extraer frames y redimensionar")
    print(f"{GREEN}2.{RESET} Redimensionar directamente")
    opcion = input(f"{CYAN}Opción (1-2): {RESET}").strip()
    
    if opcion == "1":
        try:
            process_directory(CARPETA_SPRITES_LISTA)
            return metodo_redimension()
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False
    
    elif opcion == "2":
        print(f"\n{GREEN}1.{RESET} 75% | {GREEN}2.{RESET} 50% | {GREEN}3.{RESET} 40% | {GREEN}4.{RESET} 25% | {GREEN}5.{RESET} Personalizar")
        while True:
            try:
                op = input(f"{CYAN}Opción (1-5): {RESET}").strip()
                if op == "1":
                    factor = 0.75; break
                elif op == "2":
                    factor = 0.5; break
                elif op == "3":
                    factor = 0.4; break
                elif op == "4":
                    factor = 0.25; break
                elif op == "5":
                    p = float(input("Porcentaje: ").strip())
                    if p <= 0 or p > 100:
                        print(f"{RED}❌ Entre 0 y 100{RESET}"); continue
                    factor = p / 100.0; break
                else:
                    print(f"{RED}❌ Opción no válida{RESET}")
            except ValueError:
                print(f"{RED}❌ Valor inválido{RESET}")
        
        with FACTORES_LOCK:
            FACTORES_USADOS = {}
            for png_file, _ in spritesheets:
                nombre_base = os.path.splitext(os.path.basename(png_file))[0]
                FACTORES_USADOS[nombre_base] = factor
        
        try:
            tareas_png = []
            for png_file, xml_file in spritesheets:
                nombre_base = os.path.splitext(os.path.basename(png_file))[0]
                output_png = os.path.join(CARPETA_REDIMENSION, f"{nombre_base}_optimizado.png")
                tareas_png.append((png_file, output_png))
            print(f"{CYAN}🖼 Redimensionando {len(tareas_png)} spritesheets...{RESET}")
            ok, err = redimensionar_lote(tareas_png, factor)
            for png_file, xml_file in spritesheets:
                if xml_file and os.path.exists(xml_file):
                    nombre_base = os.path.splitext(os.path.basename(png_file))[0]
                    output_xml = os.path.join(CARPETA_REDIMENSION, f"{nombre_base}_optimizado.xml")
                    shutil.copy2(xml_file, output_xml)
            print(f"\n{GREEN}✅ OK: {ok} | Errores: {err}{RESET}")
            return True
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False
    else:
        print(f"{RED}❌ Opción no válida{RESET}")
        return False


# ============================================
# FLUJO AUTOMÁTICO V-SLICE (individual)
# ============================================

def flujo_automatico_vslice(mod_name):
    """
    Flujo automático completo para V-Slice (un mod).
    Genera: PNG + XML + Scala.txt (sin .txt individuales).
    """
    global CARPETA_FRAMES, CARPETA_REDIMENSION
    
    base_mod = os.path.join(CARPETA_PRINCIPAL, "Optimizacion_V-slice", "Optimizar_Sprites", mod_name)
    orig_frames = CARPETA_FRAMES
    orig_redim = CARPETA_REDIMENSION
    
    temp_frames = os.path.join(base_mod, "_temp_frames")
    temp_redim = os.path.join(base_mod, "_temp_redimensinando")
    
    print(f"\n{CYAN}{'═'*62}{RESET}")
    print(f"{MAGENTA}  🚀 FLUJO AUTOMÁTICO V-SLICE - {mod_name}{RESET}")
    print(f"{CYAN}{'═'*62}{RESET}")
    
    rutas_validas = []
    for ruta in CARPETA_SPRITES_LISTA:
        if not os.path.exists(ruta):
            continue
        tiene_png = any(f.endswith('.png') for _, _, fs in os.walk(ruta) for f in fs)
        if tiene_png:
            rutas_validas.append(ruta)
    
    if not rutas_validas:
        print(f"\n{RED}❌ No se encontraron sprites (.png) en ninguna ruta.{RESET}")
        return False
    
    print(f"\n{CYAN}📥 Rutas a procesar ({len(rutas_validas)}):{RESET}")
    for r in rutas_validas:
        try:
            print(f"   • {os.path.relpath(r, base_mod)}")
        except ValueError:
            print(f"   • {r}")
    
    try:
        for idx, ruta_original in enumerate(rutas_validas, 1):
            try:
                ruta_rel = os.path.relpath(ruta_original, base_mod)
            except ValueError:
                ruta_rel = ruta_original
            
            print(f"\n{CYAN}{'─'*62}{RESET}")
            print(f"{MAGENTA}  [{idx}/{len(rutas_validas)}] {ruta_rel}{RESET}")
            print(f"{CYAN}{'─'*62}{RESET}")
            
            for temp in [temp_frames, temp_redim]:
                if os.path.exists(temp):
                    shutil.rmtree(temp)
            os.makedirs(temp_frames, exist_ok=True)
            os.makedirs(temp_redim, exist_ok=True)
            
            CARPETA_FRAMES = temp_frames
            CARPETA_REDIMENSION = temp_redim
            
            # PASO 1: Extraer frames
            print(f"\n{GREEN}▶ [1/4] Extrayendo frames...{RESET}")
            process_directory(ruta_original)
            
            # PASO 2: Redimensionar (auto)
            print(f"\n{GREEN}▶ [2/4] Redimensionando automáticamente...{RESET}")
            _, _, factores_dict = aplicar_redimension_automatica(temp_frames, temp_redim)
            
            # PASO 3: Generar spritesheets
            print(f"\n{GREEN}▶ [3/4] Generando spritesheets en:{RESET}")
            print(f"   {ruta_original}")
            generate_spritesheet(temp_redim, ruta_original)
            
            # PASO 4: Scala.txt
            print(f"\n{GREEN}▶ [4/4] Generando Scala.txt...{RESET}")
            if factores_dict:
                scala_path = crear_scala_vslice(ruta_original, factores_dict)
                if scala_path:
                    try:
                        print(f"   {CYAN}→ {os.path.relpath(scala_path, base_mod)}{RESET}")
                    except ValueError:
                        print(f"   {CYAN}→ {scala_path}{RESET}")
                    print(f"   {YELLOW}Contenido:{RESET}")
                    for nombre, factor in factores_dict.items():
                        if factor and factor != 0:
                            print(f"     {CYAN}{nombre},Scala={round(1/factor, 4)}{RESET}")
            else:
                print(f"   {YELLOW}⚠ No hay factores registrados.{RESET}")
            
            print(f"\n{GREEN}✅ Completado:{RESET} {ruta_rel}")
    
    finally:
        CARPETA_FRAMES = orig_frames
        CARPETA_REDIMENSION = orig_redim
        
        print(f"\n{YELLOW}🧹 Limpiando temporales...{RESET}")
        for temp in [temp_frames, temp_redim]:
            if os.path.exists(temp):
                try:
                    shutil.rmtree(temp)
                    print(f"{GREEN}✓ Eliminada: {os.path.basename(temp)}{RESET}")
                except Exception as e:
                    print(f"{YELLOW}⚠ {e}{RESET}")
    
    print(f"\n{GREEN}{'═'*62}{RESET}")
    print(f"{GREEN}  🎉 ¡FLUJO AUTOMÁTICO COMPLETADO!{RESET}")
    print(f"{GREEN}{'═'*62}{RESET}")
    return True


# ============================================
# FLUJO AUTOMÁTICO V-SLICE — TODOS LOS MODS (998)
# ============================================

def detectar_tipo_ruta_mod(mod_name, ruta_base):
    """Detecta automáticamente el tipo de ruta de un mod (auto)"""
    base_mod = os.path.join(ruta_base, mod_name)
    p1 = os.path.join(base_mod, "images", "characters")
    p2 = os.path.join(base_mod, "shared", "images", "characters")
    
    exist1 = os.path.exists(p1)
    exist2 = os.path.exists(p2)
    
    if exist1 and exist2:
        return "auto_both"
    elif exist1:
        return "1"
    elif exist2:
        return "2"
    return "1"


def mostrar_estado_mods(mods, estados):
    """Muestra el estado de todos los mods (pendiente / procesando / completado / error)"""
    clear_screen()
    print(f"\n{CYAN}{'═'*62}{RESET}")
    print(f"{MAGENTA}  🚀 AUTOMATIZAR TODOS LOS MODS - V-SLICE{RESET}")
    print(f"{CYAN}{'═'*62}{RESET}\n")
    
    for i, mod in enumerate(mods, 1):
        estado = estados.get(mod, "pendiente")
        
        if estado == "pendiente":
            color = YELLOW
            icono = "⏳"
        elif estado == "procesando":
            color = CYAN
            icono = "⚙️"
        elif estado == "completado":
            color = GREEN
            icono = "✅"
        else:
            color = RED
            icono = "❌"
        
        print(f"{color}{i:>3} : {mod:<30} ({estado}) {icono}{RESET}")
    
    print()


def procesar_todos_mods_vslice(ruta_base, mods):
    """Procesa TODOS los mods en orden mostrando estado individual"""
    estados = {mod: "pendiente" for mod in mods}
    resultados = {}
    
    for mod in mods:
        # Marcar como procesando
        estados[mod] = "procesando"
        mostrar_estado_mods(mods, estados)
        
        # Detectar tipo de ruta automáticamente
        tipo_ruta = detectar_tipo_ruta_mod(mod, ruta_base)
        configurar_paths_vslice(mod, tipo_ruta)
        
        # Procesar
        try:
            exito = flujo_automatico_vslice(mod)
            if exito:
                estados[mod] = "completado"
                resultados[mod] = "OK"
            else:
                estados[mod] = "error"
                resultados[mod] = "Sin sprites o error"
        except Exception as e:
            estados[mod] = "error"
            resultados[mod] = f"Excepción: {e}"
        
        # Mostrar estado actualizado antes de pasar al siguiente
        mostrar_estado_mods(mods, estados)
        input(f"{YELLOW}⏎ Presione Enter para continuar con el siguiente mod...{RESET}")
    
    # Resumen final
    clear_screen()
    print(f"\n{CYAN}{'═'*62}{RESET}")
    print(f"{MAGENTA}  📊 RESUMEN FINAL{RESET}")
    print(f"{CYAN}{'═'*62}{RESET}\n")
    
    ok_count = sum(1 for v in resultados.values() if v == "OK")
    err_count = len(resultados) - ok_count
    
    for i, mod in enumerate(mods, 1):
        estado = estados[mod]
        if estado == "completado":
            print(f"{GREEN}{i:>3} : {mod:<30} ✅ Completado{RESET}")
        else:
            print(f"{RED}{i:>3} : {mod:<30} ❌ {resultados[mod]}{RESET}")
    
    print(f"\n{CYAN}{'─'*62}{RESET}")
    print(f"{GREEN}✓ Completados: {ok_count}{RESET}")
    print(f"{RED}✗ Errores:     {err_count}{RESET}")
    print(f"{CYAN}{'─'*62}{RESET}")
    
    return True


# ============================================
# FUNCIONES ADICIONALES
# ============================================

def crear_archivo_scala():
    """Crea Scala.txt en CARPETA_SPRITES_OPTIMIZADOS (PsychEngine)."""
    global FACTORES_USADOS
    
    if not CARPETA_SPRITES_OPTIMIZADOS:
        print(f"\n{YELLOW}⚠ No hay carpeta destino.{RESET}")
        return False
    
    print(f"\n{YELLOW}📝 Creando Scala.txt...{RESET}")
    
    if not FACTORES_USADOS:
        print(f"{RED}❌ No hay factores.{RESET}")
        return False
    
    scala_path = os.path.join(CARPETA_SPRITES_OPTIMIZADOS, "Scala.txt")
    
    with open(scala_path, 'w', encoding='utf-8') as f:
        f.write("# Archivo de escalas generado automáticamente\n")
        f.write("# Formato: NombreSprite,Scala=1/factor\n")
        f.write("# -------------------------------------------------\n\n")
        for nombre, factor in FACTORES_USADOS.items():
            if factor != 0:
                scala = round(1 / factor, 4)
                f.write(f"{nombre},Scala={scala}\n")
    
    print(f"{GREEN}✓ Scala.txt creado: {scala_path}{RESET}")
    return True


def flujo_completo():
    print(f"\n{CYAN}╔════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║        FLUJO COMPLETO (1→2→3)          ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════╝{RESET}")
    
    print(f"\n{YELLOW}Ejecutará:{RESET}")
    print(f"{GREEN}1.{RESET} Extracción → {CARPETA_FRAMES}/")
    print(f"{GREEN}2.{RESET} Redimensión → {CARPETA_REDIMENSION}/")
    if CARPETA_SPRITES_OPTIMIZADOS:
        print(f"{GREEN}3.{RESET} Generación → {CARPETA_SPRITES_OPTIMIZADOS}/")
    
    mostrar_estructura()
    
    if input(f"\n{CYAN}¿Continuar? (s/n): {RESET}").lower() != 's':
        return False
    
    crear_estructura_carpetas()
    
    print(f"\n{CYAN}═══ PASO 1: EXTRACCIÓN ═══{RESET}")
    if not metodo_frame():
        print(f"{RED}❌ Interrumpido en Paso 1{RESET}")
        return False
    
    print(f"\n{CYAN}═══ PASO 2: REDIMENSIÓN ═══{RESET}")
    if not metodo_redimension():
        print(f"{RED}❌ Interrumpido en Paso 2{RESET}")
        return False
    
    if CARPETA_SPRITES_OPTIMIZADOS:
        print(f"\n{CYAN}═══ PASO 3: GENERACIÓN ═══{RESET}")
        if not metodo_generacion():
            print(f"{RED}❌ Interrumpido en Paso 3{RESET}")
            return False
    
    print(f"\n{GREEN}🎉 ¡FLUJO COMPLETO EXITOSO! 🎉{RESET}")
    mostrar_estructura()
    return True


def limpiar_carpetas():
    print(f"\n{CYAN}╔════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║        LIMPIEZA DE CARPETAS           ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════╝{RESET}")
    
    carpetas_a_limpiar = [c for c in [
        CARPETA_FRAMES,
        CARPETA_REDIMENSION,
        CARPETA_SPRITES_OPTIMIZADOS
    ] if c]
    
    print(f"\n{YELLOW}⚠ Se eliminará todo en:{RESET}")
    for carpeta in carpetas_a_limpiar:
        if os.path.exists(carpeta):
            num_archivos = sum(len(files) for _, _, files in os.walk(carpeta))
            print(f"   {os.path.basename(carpeta)}/ ({num_archivos} archivos)")
    
    if input(f"\n{CYAN}¿Seguro? (s/n): {RESET}").lower() != 's':
        return False
    
    for carpeta in carpetas_a_limpiar:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            os.makedirs(carpeta)
            print(f"{GREEN}✓ Limpiada: {os.path.basename(carpeta)}/{RESET}")
    
    print(f"\n{GREEN}✅ Limpieza completada{RESET}")
    return True


# ============================================
# SELECCIÓN DE ENGINE
# ============================================

def seleccionar_engine():
    while True:
        clear_screen()
        print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║{MAGENTA}     SISTEMA DE OPTIMIZACIÓN DE SPRITESHEETS      {CYAN}║{RESET}")
        print(f"{CYAN}║{BLUE}              SELECCIÓN DE ENGINE                    {CYAN}║{RESET}")
        print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{GREEN}Seleccione engine:{RESET}")
        print(f"{CYAN}1.{RESET} 🎮 PsychEngine")
        print(f"{CYAN}2.{RESET} 🎵 V-Slice (nuevo)")
        print(f"{CYAN}0.{RESET} ❌ Salir")
        
        opcion = input(f"\n{CYAN}👉 Opción (0-2): {RESET}").strip()
        
        if opcion == "0":
            return False
        elif opcion == "1":
            configurar_paths_psych()
            print(f"\n{GREEN}✓ Engine: PsychEngine{RESET}")
            print(f"{CYAN}  Sprites: {CARPETA_SPRITES}{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
            return True
        elif opcion == "2":
            if seleccionar_vslice():
                return True
        else:
            print(f"{RED}❌ Opción no válida{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")


def seleccionar_vslice():
    ruta_base = os.path.join(CARPETA_PRINCIPAL, "Optimizacion_V-slice", "Optimizar_Sprites")

    if not os.path.exists(ruta_base):
        os.makedirs(ruta_base, exist_ok=True)
        clear_screen()
        print(f"{YELLOW}📁 Se creó:{RESET} {ruta_base}")
        input(f"\n{YELLOW}⏎ Enter...{RESET}")
        return False

    mods = [d for d in sorted(os.listdir(ruta_base)) if os.path.isdir(os.path.join(ruta_base, d))]

    if not mods:
        clear_screen()
        print(f"{RED}❌ No hay mods en:{RESET} {ruta_base}")
        input(f"\n{YELLOW}⏎ Enter...{RESET}")
        return False

    auto_mode = False
    mod_elegido = None

    # ─── Loop de selección de mod ───
    while True:
        clear_screen()
        print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║{MAGENTA}            V-SLICE - SELECCIÓN DE MOD            {CYAN}║{RESET}")
        print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"\n{YELLOW}📂 Mods en:{RESET} {ruta_base}\n")

        auto_label = f"{GREEN}true{RESET}" if auto_mode else f"{RED}false{RESET}"
        print(f"{YELLOW}999.{RESET} ⚙  Automatizar ({auto_label})")
        print(f"{YELLOW}998.{RESET} 🚀 Ejecutar automatización en TODOS los mods")
        for i, mod in enumerate(mods, 1):
            print(f"{GREEN}{i}.{RESET} {mod}")
        print(f"{YELLOW}0.{RESET}   ↩  Volver")

        opcion = input(f"\n{CYAN}👉 Mod (1-{len(mods)}) | 998 | 999 Auto: {RESET}").strip()

        if opcion == "0":
            return False

        # ─── 999: Toggle auto ───
        if opcion == "999":
            clear_screen()
            print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
            print(f"{CYAN}║{MAGENTA}              ¿AUTOMATIZAR?                        {CYAN}║{RESET}")
            print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
            print(f"\n{GREEN}1.{RESET} true   {CYAN}(detecta y procesa todo){RESET}")
            print(f"{GREEN}2.{RESET} false  {CYAN}(preguntar manual){RESET}")
            sub = input(f"\n{CYAN}👉 (1-2): {RESET}").strip()
            if sub == "1":
                auto_mode = True
                print(f"{GREEN}✓ Automatizar = true{RESET}")
            elif sub == "2":
                auto_mode = False
                print(f"{GREEN}✓ Automatizar = false{RESET}")
            else:
                print(f"{RED}❌ Mantiene: {auto_mode}{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
            continue

        # ─── 998: Automatizar TODOS ───
        if opcion == "998":
            if not auto_mode:
                clear_screen()
                print(f"\n{RED}❌ La función 999 está en false, actívala para true{RESET}")
                print(f"{YELLOW}💡 Ve a la opción 999 y actívala.{RESET}")
                input(f"\n{YELLOW}⏎ Enter...{RESET}")
                continue
            
            clear_screen()
            print(f"{GREEN}✓ La función true está activada{RESET}")
            print(f"\n{CYAN}¿Continuar con la automatización de TODOS los mods?{RESET}")
            print(f"{GREEN}1.{RESET} Sí")
            print(f"{RED}2.{RESET} No")
            sub = input(f"\n{CYAN}👉 (1-2): {RESET}").strip()
            
            if sub == "1":
                clear_screen()
                print(f"{CYAN}📦 Mods a procesar: {len(mods)}{RESET}\n")
                for i, mod in enumerate(mods, 1):
                    print(f"  {i}. {mod}")
                input(f"\n{YELLOW}⏎ Presione Enter para iniciar...{RESET}")
                
                procesar_todos_mods_vslice(ruta_base, mods)
                input(f"\n{YELLOW}⏎ Presione Enter para volver al menú...{RESET}")
            continue

        # ─── Selección de mod individual ───
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(mods):
                mod_elegido = mods[idx]
                break
            print(f"{RED}❌ Opción no válida{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        except ValueError:
            print(f"{RED}❌ Número válido{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")

    # ─── Configurar paths del mod elegido ───
    base_mod = os.path.join(ruta_base, mod_elegido)
    p1 = os.path.join(base_mod, "images", "characters")
    p2 = os.path.join(base_mod, "shared", "images", "characters")

    if auto_mode:
        clear_screen()
        print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║{MAGENTA}          🔍 DETECCIÓN AUTOMÁTICA                 {CYAN}║{RESET}")
        print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"\n{CYAN}Mod:{RESET} {mod_elegido}")
        print(f"{CYAN}Escaneando:{RESET}\n  → {p1}\n  → {p2}\n")

        exist1 = os.path.exists(p1)
        exist2 = os.path.exists(p2)

        if exist1 and exist2:
            tipo_ruta = "auto_both"
            print(f"{GREEN}✓ AMBAS rutas:{RESET}")
            print(f"  • {p1}")
            print(f"  • {p2}")
        elif exist1:
            tipo_ruta = "1"
            print(f"{GREEN}✓ {p1}{RESET}")
        elif exist2:
            tipo_ruta = "2"
            print(f"{GREEN}✓ {p2}{RESET}")
        else:
            tipo_ruta = "1"
            print(f"{YELLOW}⚠ Ninguna existe. Default: {p1}{RESET}")

        input(f"\n{YELLOW}⏎ Enter...{RESET}")
    else:
        clear_screen()
        print(f"{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║{MAGENTA}        ¿Ruta de characters?                      {CYAN}║{RESET}")
        print(f"{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"\n{GREEN}1.{RESET} {mod_elegido}/images/characters/")
        print(f"{GREEN}2.{RESET} {mod_elegido}/shared/images/characters/")
        while True:
            opcion = input(f"\n{CYAN}👉 (1-2): {RESET}").strip()
            if opcion in ("1", "2"):
                tipo_ruta = opcion
                break
            print(f"{RED}❌ Opción no válida{RESET}")

    configurar_paths_vslice(mod_elegido, tipo_ruta)

    if auto_mode:
        flujo_automatico_vslice(mod_elegido)
        input(f"\n{YELLOW}⏎ Enter para volver...{RESET}")
        return False

    for carpeta in [CARPETA_FRAMES, CARPETA_REDIMENSION]:
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

    clear_screen()
    print(f"{GREEN}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{GREEN}║              ✓ CONFIGURACIÓN APLICADA              ║{RESET}")
    print(f"{GREEN}╚══════════════════════════════════════════════════════╝{RESET}")
    print(f"\n{CYAN}🎵 Engine:{RESET} V-Slice ({mod_elegido})")
    print(f"{CYAN}⚙ Automatizar:{RESET} false (manual)")
    print(f"{CYAN}📥 Sprites:{RESET}")
    for p in CARPETA_SPRITES_LISTA:
        print(f"     • {p}/")
    print(f"{CYAN}📁 Frames:{RESET} {CARPETA_FRAMES}/")
    print(f"{CYAN}📁 Redimensión:{RESET} {CARPETA_REDIMENSION}/")

    input(f"\n{YELLOW}⏎ Enter...{RESET}")
    return True


# ============================================
# MENÚ PRINCIPAL
# ============================================

def menu_principal():
    crear_estructura_carpetas()
    
    while True:
        mostrar_banner()
        mostrar_estructura()
        
        print(f"\n{GREEN}Seleccione opción:{RESET}")
        print(f"{CYAN}1.{RESET} 🎞  Método 1: Extracción de frames")
        print(f"{CYAN}2.{RESET} 📏 Método 2: Redimensionamiento (MULTIHILO 🚀)")
        if CARPETA_SPRITES_OPTIMIZADOS:
            print(f"{CYAN}3.{RESET} 🖼  Método 3: Generación de spritesheets")
        else:
            print(f"{YELLOW}3.{RESET} 🖼  Método 3: (no disponible en V-Slice)")
        print(f"{CYAN}4.{RESET} 🚀 Flujo completo (1→2→3)")
        print(f"{CYAN}5.{RESET} 🧹 Limpiar carpetas")
        print(f"{CYAN}6.{RESET} 🔄 Cambiar de Engine")
        print(f"{CYAN}0.{RESET} ❌ Salir")
        
        opcion = input(f"\n{CYAN}👉 Opción (0-6): {RESET}").strip()
        
        if opcion == "1":
            metodo_frame()
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        elif opcion == "2":
            metodo_redimension()
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        elif opcion == "3":
            metodo_generacion()
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        elif opcion == "4":
            flujo_completo()
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        elif opcion == "5":
            limpiar_carpetas()
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        elif opcion == "6":
            if seleccionar_engine():
                print(f"{GREEN}✓ Engine: {ENGINE_ACTUAL}{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")
        elif opcion == "0":
            print(f"\n{MAGENTA}👋 ¡Hasta luego!{RESET}")
            break
        else:
            print(f"{RED}❌ Opción no válida{RESET}")
            input(f"\n{YELLOW}⏎ Enter...{RESET}")


# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================

if __name__ == "__main__":
    try:
        if not seleccionar_engine():
            print(f"\n{MAGENTA}👋 ¡Hasta luego!{RESET}")
            sys.exit(0)
        menu_principal()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠ Interrumpido.{RESET}")
    except Exception as e:
        print(f"\n{RED}💥 Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        input(f"\n{YELLOW}⏎ Enter...{RESET}")