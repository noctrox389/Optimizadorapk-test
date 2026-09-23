import os
import shutil
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from math import ceil, sqrt
from PIL import Image, ImageChops
from tqdm import tqdm
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Configuración de colores mejorada
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
PURPLE = "\033[95m"
ORANGE = "\033[38;5;208m"  # Color naranja para sprites

# Diccionario global para almacenar las escalas de todas las imágenes procesadas
# Ahora guarda: {ruta_relativa: escala}
escalas_globales = {}

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def calcular_factor_inverso(escala):
    """Calcula el factor inverso (1/escala)"""
    try:
        if escala == 0:
            return "∞"
        inverso = 1 / float(escala)
        # Redondear a 2 decimales
        return round(inverso, 2)
    except:
        return "Error"

def guardar_escalas_globales(images_root_path):
    """Guarda todas las escalas en un único archivo Scala_General.txt organizado por carpetas"""
    if not escalas_globales:
        return
    
    archivo_escalas = os.path.join(images_root_path, "Scala_General.txt")
    
    try:
        # Organizar escalas por carpeta
        escalas_por_carpeta = {}
        
        for ruta_relativa, escala in escalas_globales.items():
            # Obtener carpeta y nombre de archivo
            carpeta = os.path.dirname(ruta_relativa)
            nombre_archivo = os.path.basename(ruta_relativa)
            
            if carpeta == "":
                carpeta = "."  # Raíz de images
            
            if carpeta not in escalas_por_carpeta:
                escalas_por_carpeta[carpeta] = []
            
            factor_inverso = calcular_factor_inverso(escala)
            escalas_por_carpeta[carpeta].append((nombre_archivo, factor_inverso))
        
        with open(archivo_escalas, 'w', encoding='utf-8') as f:
            f.write("REGISTRO DE ESCALAS DE IMÁGENES (Actualizado automáticamente)\n")
            f.write("=" * 40 + "\n\n")
            
            # Ordenar carpetas alfabéticamente
            carpetas_ordenadas = sorted(escalas_por_carpeta.keys())
            
            for carpeta in carpetas_ordenadas:
                # Escribir nombre de carpeta
                if carpeta == ".":
                    f.write(f"carpeta: images/\n\n")
                else:
                    f.write(f"carpeta: images/{carpeta}/\n\n")
                
                # Ordenar archivos alfabéticamente
                archivos_ordenados = sorted(escalas_por_carpeta[carpeta])
                
                # Escribir todos los archivos de esta carpeta
                for nombre_archivo, factor_inverso in archivos_ordenados:
                    f.write(f"{nombre_archivo} = Escala: {factor_inverso}\n")
                
                # Separador al final de cada sección
                f.write("\n" + "=" * 40 + "\n\n")
        
        print(f"\n{GREEN}📊 Escalas guardadas en: {archivo_escalas}{RESET}")
        print(f"{CYAN}Total de imágenes registradas: {len(escalas_globales)}{RESET}")
        
        # Mostrar resumen organizado en consola también
        print(f"\n{CYAN}📋 RESUMEN ORGANIZADO POR CARPETA:{RESET}")
        for carpeta in sorted(escalas_por_carpeta.keys()):
            if carpeta == ".":
                print(f"\n{GREEN}carpeta: images/{RESET}")
            else:
                print(f"\n{GREEN}carpeta: images/{carpeta}/{RESET}")
            
            for nombre_archivo, factor_inverso in sorted(escalas_por_carpeta[carpeta]):
                print(f"  {nombre_archivo}: {factor_inverso}")
            
            print(f"{BLUE}{'='*30}{RESET}")
            
    except Exception as e:
        print(f"{RED}Error guardando escalas: {e}{RESET}")
        
def registrar_escala(ruta_relativa, factor, images_root_path=None):
    """Registra una escala con su ruta relativa a images y guarda automáticamente"""
    escalas_globales[ruta_relativa] = factor
    
    # Si se proporciona la ruta root, guardar inmediatamente
    if images_root_path and os.path.exists(images_root_path):
        try:
            archivo_escalas = os.path.join(images_root_path, "Scala_General.txt")
            
            # Organizar escalas por carpeta
            escalas_por_carpeta = {}
            
            for ruta_rel, esc in escalas_globales.items():
                carpeta = os.path.dirname(ruta_rel)
                nombre_archivo = os.path.basename(ruta_rel)
                
                if carpeta == "":
                    carpeta = "."
                
                if carpeta not in escalas_por_carpeta:
                    escalas_por_carpeta[carpeta] = []
                
                factor_inverso = calcular_factor_inverso(esc)
                escalas_por_carpeta[carpeta].append((nombre_archivo, factor_inverso))
            
            with open(archivo_escalas, 'w', encoding='utf-8') as f:
                f.write("REGISTRO DE ESCALAS DE IMÁGENES (Actualizado automáticamente)\n")
                f.write("=" * 40 + "\n\n")
                
                # Ordenar carpetas alfabéticamente
                carpetas_ordenadas = sorted(escalas_por_carpeta.keys())
                
                for carpeta in carpetas_ordenadas:
                    if carpeta == ".":
                        f.write(f"carpeta: images/\n\n")
                    else:
                        f.write(f"carpeta: images/{carpeta}/\n\n")
                    
                    archivos_ordenados = sorted(escalas_por_carpeta[carpeta])
                    
                    for nombre_archivo, factor_inverso in archivos_ordenados:
                        f.write(f"{nombre_archivo} = Escala: {factor_inverso}\n")
                    
                    f.write("\n" + "=" * 40 + "\n\n")
            
            print(f"{GREEN}📝 Scala_General.txt actualizado{RESET}")
            
        except Exception as e:
            print(f"{RED}Error actualizando Scala_General.txt: {e}{RESET}")

def mostrar_menu_escala():
    """Muestra el menú de selección de escala"""
    print(f"\n{CYAN}🎯 SELECCIONA EL FACTOR DE ESCALA:{RESET}")
    print(f"{GREEN}1. 75% (Factor: {calcular_factor_inverso(0.75)}){RESET}")
    print(f"{GREEN}2. 50% (Factor: {calcular_factor_inverso(0.5)}){RESET}")
    print(f"{GREEN}3. 40% (Factor: {calcular_factor_inverso(0.4)}){RESET}")
    print(f"{YELLOW}4. Personalizar{RESET}")
    print(f"{RED}5. Cancelar{RESET}")
    
    while True:
        try:
            opcion = input(f"{YELLOW}▶ Elige una opción (1-5): {RESET}").strip()
            if opcion in ['1', '2', '3', '4', '5']:
                if opcion == '1':
                    return 0.75
                elif opcion == '2':
                    return 0.5
                elif opcion == '3':
                    return 0.4
                elif opcion == '4':
                    while True:
                        try:
                            personalizada = input(f"{YELLOW}Ingresa el factor (ej: 0.25 para 25%): {RESET}").strip()
                            factor = float(personalizada)
                            
                            # VALIDACIÓN: No permitir más de 1 (100%)
                            if factor > 1:
                                print(f"{RED}❌ ERROR: No puedes redimensionar más allá del 100% (1.0){RESET}")
                                print(f"{YELLOW}Ingresa un valor entre 0.01 y 1.0{RESET}")
                                continue
                            
                            if factor > 0:
                                factor_inverso = calcular_factor_inverso(factor)
                                print(f"{CYAN}Factor inverso: {factor_inverso}{RESET}")
                                return factor
                            print(f"{RED}El factor debe ser mayor que 0{RESET}")
                        except ValueError:
                            print(f"{RED}Debe ingresar un número válido{RESET}")
                elif opcion == '5':
                    return None
            print(f"{RED}Opción no válida. Ingresa 1-5{RESET}")
        except Exception:
            print(f"{RED}Error en la selección{RESET}")

# NUEVO MÉTODO DE EXTRACCIÓN DE FRAMES (versión mejorada de sprite_a_frame_v5)
def extract_frames_mejorado(
    png_path,
    xml_path,
    output_dir,
    overall_progress=None,
    file_progress=None,
    task_index=None,
    relative_path="",
    has_xml=True
):
    """Versión mejorada de extracción de frames con manejo de progreso"""
    try:
        image = Image.open(png_path).convert("RGBA")
        png_name = os.path.splitext(os.path.basename(png_path))[0]

        frame_output_dir = os.path.join(output_dir, relative_path, png_name)
        os.makedirs(frame_output_dir, exist_ok=True)

        with open(os.path.join(frame_output_dir, f"{image.width}x{image.height}.txt"), "w", encoding="utf-8") as f:
            f.write(f"Original spritesheet: {image.width}x{image.height}\nModo: XML")

        # Solo procesar XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
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

            if file_progress and task_index is not None:
                file_progress[task_index].update(1)
            if overall_progress:
                overall_progress.update(1)

        print(f"{GREEN}[OK] {png_name}{RESET}")
        return True

    except Exception as e:
        print(f"{RED}[ERROR] {png_path}\n{e}{RESET}")
        return False

# Función para procesar spritesheets con el nuevo método
def process_sprite_extract(png_path, xml_path, output_dir):
    """Procesa extracción de frames con el método mejorado"""
    try:
        # Configurar progreso simple
        tree = ET.parse(xml_path)
        root = tree.getroot()
        subtextures = root.findall(".//SubTexture")
        total_frames = len(subtextures)
        
        overall_progress = tqdm(
            total=total_frames,
            desc="Extrayendo",
            unit="frame",
            position=0
        )
        
        # Llamar al método mejorado
        result = extract_frames_mejorado(
            png_path,
            xml_path,
            output_dir,
            overall_progress,
            None,
            0,
            "",
            True
        )
        
        overall_progress.close()
        return result
        
    except Exception as e:
        print(f"{RED}Error en procesamiento: {e}{RESET}")
        return False

def extract_frames_antiguo(png_path, xml_path, output_dir):
    """Versión antigua para compatibilidad (mantenida como respaldo)"""
    try:
        image = Image.open(png_path).convert("RGBA")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        png_name = os.path.splitext(os.path.basename(png_path))[0]
        output_dir = os.path.join(output_dir, png_name)
        os.makedirs(output_dir, exist_ok=True)
        
        subtextures = root.findall(".//SubTexture")
        
        with tqdm(subtextures, desc=f"{PURPLE}Extrayendo {png_name}", unit="frame") as pbar:
            for subtexture in pbar:
                name = sanitize_filename(subtexture.attrib['name'])
                x = int(float(subtexture.attrib.get('x', 0)))
                y = int(float(subtexture.attrib.get('y', 0)))
                width = int(float(subtexture.attrib.get('width', 0)))
                height = int(float(subtexture.attrib.get('height', 0)))
                frameX = int(float(subtexture.attrib.get('frameX', 0)))
                frameY = int(float(subtexture.attrib.get('frameY', 0)))
                frameWidth = int(float(subtexture.attrib.get('frameWidth', width)))
                frameHeight = int(float(subtexture.attrib.get('frameHeight', height)))
                rotated = subtexture.attrib.get('rotated', 'false').lower() == 'true'
                
                sprite_crop = image.crop((x, y, x + width, y + height))
                
                if rotated:
                    sprite_crop = sprite_crop.transpose(Image.ROTATE_90)
                    width, height = height, width
                
                frame_image = Image.new("RGBA", (frameWidth, frameHeight), (0, 0, 0, 0))
                paste_x = -frameX if frameX < 0 else 0
                paste_y = -frameY if frameY < 0 else 0
                frame_image.paste(sprite_crop, (paste_x, paste_y))
                
                frame_path = os.path.join(output_dir, f"{name}.png")
                frame_image.save(frame_path, "PNG")
        
        print(f"{GREEN}✅ {png_name} extraído ({len(subtextures)} frames){RESET}")
        return True
    except Exception as e:
        print(f"{RED}Error extrayendo frames: {e}{RESET}")
        return False

# Las siguientes funciones se mantienen igual pero actualizadas para usar el nuevo método

def trim(image, threshold=5):
    """Recorta bordes transparentes de una imagen con umbral configurable"""
    img_rgba = image.convert("RGBA")
    r, g, b, a = img_rgba.split()
    a = a.point(lambda p: p if p >= threshold else 0)
    img_thresh = Image.merge("RGBA", (r, g, b, a))
    
    bbox = img_thresh.getbbox()
    if bbox:
        return img_rgba.crop(bbox), bbox
    return img_rgba, (0, 0, image.width, image.height)

def find_leaf_folders(folder):
    """Encuentra todas las carpetas que contienen imágenes"""
    leaf_folders = []
    for root, dirs, files in os.walk(folder):
        image_files = [f for f in files if f.lower().endswith(('png', 'jpg', 'jpeg'))]
        if image_files:
            leaf_folders.append(root)
    return leaf_folders

def generate_spritesheet(image_folder, output_folder):
    """Genera spritesheets a partir de carpetas de imágenes (versión mejorada)"""
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
                with open(xml_file_path, "w", encoding='utf-8') as xml_file:
                    xml_file.write(xml_str)

                txt_path = os.path.join(folder, f"{original_folder_name}.txt")
                if os.path.exists(txt_path):
                    shutil.copy2(txt_path, os.path.join(final_output_dir, f"{original_folder_name}.txt"))

                print(f"{GREEN}✅ Spritesheet generado: {original_folder_name}{RESET}")
                break
                
            except ValueError:
                sheet_size = int(sheet_size * 1.15)
                print(f"{YELLOW}⚠ Aumentando tamaño a {sheet_size}x{sheet_size}{RESET}")

def resize_images(input_dir, output_dir, scale, sprite_name):
    try:
        scale = float(scale)
        if scale <= 0:
            print(f"{RED}La escala debe ser > 0{RESET}")
            return False
        
        # VALIDACIÓN: No permitir más de 1
        if scale > 1:
            print(f"{RED}❌ ERROR: No puedes redimensionar más allá del 100% (1.0){RESET}")
            print(f"{YELLOW}El valor máximo permitido es 1.0{RESET}")
            return False
        
        # Calcular factor inverso para mostrar
        factor_inverso = calcular_factor_inverso(scale)
        
        if scale == 1:
            print(f"{YELLOW}⏭ Saltando redimensionado (escala 1){RESET}")
            # Copiar los frames directamente
            for root, _, files in os.walk(input_dir):
                rel_path = os.path.relpath(root, input_dir)
                out_dir = os.path.join(output_dir, rel_path)
                os.makedirs(out_dir, exist_ok=True)
                for file in files:
                    if file.lower().endswith(('.png','.jpg','.jpeg')):
                        shutil.copy2(os.path.join(root, file), os.path.join(out_dir, file))
            return True

        image_files = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith(('.png','.jpg','.jpeg')):
                    image_files.append((root, file))
        
        if not image_files:
            print(f"{YELLOW}No hay imágenes para redimensionar{RESET}")
            return False

        print(f"{BLUE}🔄 Redimensionando {len(image_files)} imágenes (Factor: {factor_inverso})...{RESET}")
        
        with tqdm(image_files, unit="img") as pbar:
            for root, file in pbar:
                rel_path = os.path.relpath(root, input_dir)
                out_dir = os.path.join(output_dir, rel_path)
                os.makedirs(out_dir, exist_ok=True)
                
                with Image.open(os.path.join(root, file)) as img:
                    new_size = (int(img.width*scale), int(img.height*scale))
                    img.resize(new_size, Image.Resampling.LANCZOS).save(
                        os.path.join(out_dir, file))
        
        print(f"{GREEN}✅ Redimensionado completado (Factor: {factor_inverso}){RESET}")
            
        return True
    except Exception as e:
        print(f"{RED}Error redimensionando: {e}{RESET}")
        return False

def resize_single_image(input_path, output_path, scale, images_root_path, current_path):
    """Redimensiona una sola imagen y registra la escala con ruta relativa"""
    try:
        scale = float(scale)
        if scale <= 0:
            print(f"{RED}La escala debe ser mayor que 0{RESET}")
            return False
        
        # VALIDACIÓN EXTRA: No permitir más de 1
        if scale > 1:
            print(f"{RED}❌ ERROR: No puedes redimensionar más allá del 100% (1.0){RESET}")
            print(f"{YELLOW}El valor máximo permitido es 1.0{RESET}")
            return False
        
        # Obtener ruta relativa a images_root_path
        ruta_relativa = os.path.relpath(input_path, images_root_path)
        
        factor_inverso = calcular_factor_inverso(scale)
        
        with Image.open(input_path) as img:
            original_size = (img.width, img.height)
            new_size = (int(img.width * scale), int(img.height * scale))
            
            img.resize(new_size, Image.Resampling.LANCZOS).save(output_path)
            
            # Registrar la escala con la ruta relativa Y actualizar archivo
            registrar_escala(ruta_relativa, scale, images_root_path)
            
            print(f"{GREEN}✅ {os.path.basename(input_path)} redimensionado")
            print(f"   Tamaño original: {original_size}")
            print(f"   Nuevo tamaño: {new_size}")
            print(f"   Factor: {factor_inverso}{RESET}")
            
            return True
    except Exception as e:
        print(f"{RED}Error al procesar {os.path.basename(input_path)}: {e}{RESET}")
        return False

def process_single_sprite(png_path, output_dir, images_root_path, escala=None):
    """Procesa un solo sprite con limpieza de temporales - AHORA USA EL NUEVO MÉTODO"""
    temp_dir = os.path.join(output_dir, "temp_sprite_process")
    frames_dir = os.path.join(temp_dir, "frames")
    scaled_dir = os.path.join(temp_dir, "scaled")
    
    # Limpieza inicial
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(scaled_dir, exist_ok=True)

    sprite_name = os.path.splitext(os.path.basename(png_path))[0]
    xml_path = os.path.join(output_dir, f"{sprite_name}.xml")
    
    if not os.path.exists(xml_path):
        print(f"{RED}No se encontró el XML correspondiente{RESET}")
        return False

    print(f"\n{ORANGE}🌀 Procesando SPRITE: {sprite_name}{RESET}")
    
    # 1. Extraer frames - AHORA USA EL NUEVO MÉTODO MEJORADO
    if not process_sprite_extract(png_path, xml_path, frames_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
    
    # 2. Obtener escala si no se proporcionó
    if escala is None:
        escala = mostrar_menu_escala()
        if escala is None:
            print(f"{YELLOW}❌ Proceso cancelado{RESET}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
    
    # 3. Redimensionar
    if escala and float(escala) > 0:
        # Crear directorio específico para este sprite en scaled_dir
        sprite_scaled_dir = os.path.join(scaled_dir, sprite_name)
        os.makedirs(sprite_scaled_dir, exist_ok=True)
        
        if not resize_images(os.path.join(frames_dir, sprite_name), sprite_scaled_dir, escala, sprite_name):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
    
    # 4. Preguntar si convertir a sprite
    convertir = input(f"{YELLOW}¿Convertir a sprite? (Y/n): {RESET}").lower() in ('', 'y', 'yes')
    
    if convertir:
        # Usar la nueva función generate_spritesheet mejorada
        generate_spritesheet(os.path.join(scaled_dir, sprite_name), output_dir)
        print(f"{GREEN}✅ Sprite reconstruido{RESET}")
    else:
        print(f"{YELLOW}⚠ Sprite no reconstruido{RESET}")
    
    # Limpieza final
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Registrar la escala del sprite con su ruta relativa
    ruta_relativa = os.path.relpath(png_path, images_root_path)
    registrar_escala(ruta_relativa, escala, images_root_path)
    
    print(f"{GREEN}✨ {sprite_name} procesado exitosamente{RESET}")
    
    return True

def modify_images(selected_images, current_path, images_root_path, escala=None):
    """Proceso completo de modificación de imágenes normales"""
    if not selected_images:
        print(f"{YELLOW}No se seleccionaron imágenes{RESET}")
        return False

    # Obtener escala si no se proporcionó
    if escala is None:
        print(f"\n{CYAN}📸 IMÁGENES SELECCIONADAS ({len(selected_images)}):{RESET}")
        for i, img in enumerate(selected_images, 1):
            print(f"  {i}. {img}")
        
        escala = mostrar_menu_escala()
        if escala is None:
            print(f"{YELLOW}❌ Proceso cancelado{RESET}")
            return False

    # Calcular factor inverso para mostrar
    factor_inverso = calcular_factor_inverso(escala)
    
    # Procesar todas las imágenes con la misma escala
    print(f"\n{BLUE}🔧 Aplicando factor {factor_inverso} a {len(selected_images)} imágenes...{RESET}")
    
    for image_name in selected_images:
        image_path = os.path.join(current_path, image_name)
        base_name = os.path.splitext(image_name)[0]
        
        # Verificar si es un sprite (tiene XML)
        is_sprite = os.path.exists(os.path.join(current_path, f"{base_name}.xml"))
        
        if is_sprite:
            print(f"{ORANGE}⚠ Sprite detectado (usar modo sprite): {image_name}{RESET}")
        else:
            resize_single_image(image_path, image_path, escala, images_root_path, current_path)

    return True

def list_directory(directory, selected_items=None):
    """Lista directorios con mejor formato y manejo de errores"""
    try:
        items = os.listdir(directory)
        folders = [item for item in items if os.path.isdir(os.path.join(directory, item))]
        files = [item for item in items if os.path.isfile(os.path.join(directory, item))]

        # Listar carpetas con emoji y numeración
        for i, folder in enumerate(folders, 1):
            print(f"{BLUE}📁 {i}: {folder}{RESET}")

        # Identificar sprites (png+xml) y archivos normales
        sprite_files = []
        normal_files = []
        
        for file in files:
            base, ext = os.path.splitext(file)
            if ext.lower() == '.png' and f"{base}.xml" in files:
                sprite_files.append(file)
            elif ext.lower() == '.xml':
                continue  # Omitir archivos XML
            elif ext.lower() in ('.png', '.jpg', '.jpeg'):
                normal_files.append(file)

        # Listar sprites (en ORANGE como solicitaste)
        counter = len(folders) + 1
        all_items = folders.copy()
        
        for sprite in sprite_files:
            color = ORANGE if selected_items and sprite in selected_items else ORANGE
            prefix = "✔ " if sprite in selected_items else ""
            print(f"{color}{prefix}🎬 {counter}: {sprite} (sprite){RESET}")
            all_items.append(sprite)
            counter += 1
        
        # Listar imágenes normales
        for file in normal_files:
            color = GREEN if selected_items and file in selected_items else RESET
            prefix = "✔ " if file in selected_items else ""
            print(f"{color}{prefix}📷 {counter}: {file}{RESET}")
            all_items.append(file)
            counter += 1

        print(f"\n{YELLOW}📤 0: Retroceder{RESET}")
        print(f"{RED}🚪 00: Finalizar script{RESET}")
        return folders, all_items

    except Exception as e:
        print(f"{RED}Error al listar directorio: {e}{RESET}")
        return [], []

def choose_multiple(items):
    """Selección mejorada con validación robusta"""
    while True:
        try:
            choice = input(f"{YELLOW}▶ Selecciona números (ej: 1,3 o 2-5): {RESET}").strip()
            if choice == "0":
                return "back"
            if choice == "00":
                return "exit"
            
            selected_indices = []
            for part in choice.replace(" ", "").split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    selected_indices.extend(range(start-1, end))
                else:
                    selected_indices.append(int(part)-1)
            
            if all(0 <= idx < len(items) for idx in selected_indices):
                return [items[idx] for idx in sorted(set(selected_indices))]
            print(f"{RED}¡Algunos números están fuera de rango! (Máximo: {len(items)}){RESET}")
        except ValueError:
            print(f"{RED}Entrada inválida. Usa números como '1,3' o '2-5'{RESET}")

def navigate_directory(images_root_path):
    """Navegación mejorada entre directorios"""
    current_path = images_root_path
    selected_items = []

    while True:
        folders, all_items = list_directory(current_path, selected_items)
        
        selection = choose_multiple(all_items)
        
        if selection == "back":
            if current_path == images_root_path:
                print(f"{YELLOW}🏠 Ya estás en el directorio images{RESET}")
                # Guardar escalas globales al salir
                guardar_escalas_globales(images_root_path)
                break
            current_path = os.path.dirname(current_path)
            selected_items = []
        elif selection == "exit":
            print(f"\n{YELLOW}🚪 Finalizando script...{RESET}")
            # Guardar escalas globales antes de salir
            guardar_escalas_globales(images_root_path)
            return "exit"
        elif isinstance(selection, list):
            for item in selection:
                item_path = os.path.join(current_path, item)
                
                if os.path.isdir(item_path):
                    current_path = item_path
                    selected_items = []
                    break
                else:
                    # Verificar si es un sprite
                    base_name = os.path.splitext(item)[0]
                    xml_exists = os.path.exists(os.path.join(current_path, f"{base_name}.xml"))
                    
                    if item.lower().endswith('.png') and xml_exists:
                        # Es un sprite - procesar con modo sprite
                        print(f"{ORANGE}🎬 Procesando sprite: {item}{RESET}")
                        process_single_sprite(item_path, current_path, images_root_path)
                    else:
                        # Es imagen normal - agregar a selección
                        if item not in selected_items:
                            selected_items.append(item)
                            print(f"{GREEN}✔ Seleccionado: {item}{RESET}")

            # Si hay imágenes normales seleccionadas, procesarlas
            if selected_items:
                if modify_images(selected_items, current_path, images_root_path):
                    selected_items = []

def navigate_mods(base_path):
    """Navegación por mods con mejor presentación"""
    mods_path = os.path.join(base_path, "Bgs_stage_scale")
    
    if not os.path.exists(mods_path):
        print(f"{RED}❌ Carpeta 'mods' no encontrada{RESET}")
        return

    print(f"\n{CYAN}🎮 MODS DISPONIBLES{RESET}")
    mods, _ = list_directory(mods_path)

    if not mods:
        print(f"{YELLOW}No hay mods disponibles{RESET}")
        return

    selected = choose_multiple(mods)
    if isinstance(selected, list) and len(selected) == 1:
        mod_name = selected[0]
        images_path = os.path.join(mods_path, mod_name, "images")
        
        if os.path.exists(images_path):
            print(f"\n{BLUE}🌌 Entrando en MOD: {mod_name}{RESET}")
            # Limpiar diccionario global antes de entrar a un nuevo mod
            escalas_globales.clear()
            resultado = navigate_directory(images_path)
            if resultado == "exit":
                return "exit"
        else:
            print(f"{RED}❌ No se encontró 'images' en {mod_name}{RESET}")
    elif selected == "exit":
        return "exit"

def main():
    """Función principal con manejo de errores"""
    print(f"\n{GREEN}✨=== SPRITE SCALA EDITOR PRO ===✨{RESET}")
    print(f"{CYAN}Nueva función: Scala_General.txt con registro de todas las escalas{RESET}")
    print(f"{CYAN}Nota: Se muestra el FACTOR INVERSO (1/escala) en el archivo{RESET}")
    print(f"{YELLOW}⚠  IMPORTANTE: El redimensionado está limitado a máximo 100% (1.0){RESET}")
    print(f"{YELLOW}   ¡No puedes redimensionar más allá del tamaño original!{RESET}")
    print(f"{CYAN}🔧 NUEVO: Método mejorado de extracción de frames{RESET}")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_path = os.path.join(BASE_DIR, "Optimizacion-psychEnguine/")
    
    try:
        if not os.path.exists(base_path):
            print(f"{RED}❌ Directorio base no existe: {base_path}{RESET}")
            return
        
        while True:
            resultado = navigate_mods(base_path)
            if resultado == "exit":
                print(f"\n{YELLOW}👋 Saliendo del programa...{RESET}")
                break
            
            continuar = input(f"\n{YELLOW}¿Deseas procesar otro mod? (Y/n): {RESET}").lower()
            if continuar not in ('', 'y', 'yes'):
                print(f"\n{YELLOW}👋 Saliendo del programa...{RESET}")
                break
                
    except KeyboardInterrupt:
        print(f"\n{RED}🚫 Proceso cancelado por el usuario{RESET}")
        # Guardar escalas antes de salir si hay algún mod abierto
        if escalas_globales:
            # Intentar encontrar la ruta images actual
            mods_path = os.path.join(base_path, "Bgs_stage_scale")
            if os.path.exists(mods_path):
                mods = os.listdir(mods_path)
                for mod in mods:
                    images_path = os.path.join(mods_path, mod, "images")
                    if os.path.exists(images_path):
                        guardar_escalas_globales(images_path)
                        break
    except Exception as e:
        print(f"\n{RED}💥 Error crítico: {e}{RESET}")
    finally:
        print(f"\n{GREEN}🏁 Programa terminado{RESET}")

if __name__ == "__main__":
    main()