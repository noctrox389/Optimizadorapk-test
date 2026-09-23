import os
import json
from pathlib import Path
import re
import shutil

def mostrar_logo():
    logo = """
    ╔══════════════════════════════════════════╗
    ║    🎮 SCALE JSON PSYCHENGINE            ║
    ║    Versión 5.0 - SCALE Y RENOMBRAR      ║
    ╚══════════════════════════════════════════╝
    """
    print(logo)

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def normalizar_nombre(nombre):
    """Convierte a minúsculas y limpia el nombre"""
    if not nombre:
        return ""
    return nombre.strip().lower()

def extraer_nombre_spritesheet(ruta_imagen):
    """Extrae el nombre del spritesheet ignorando mayúsculas"""
    if not ruta_imagen:
        return ""
    
    # Limpiar y normalizar
    ruta = ruta_imagen.strip().lower()
    
    # Quitar "characters/" si está
    if ruta.startswith("characters/"):
        ruta = ruta[11:]
    
    # Quitar cualquier carpeta antes
    nombre = Path(ruta).name
    
    # Quitar extensión si la tiene
    if '.' in nombre:
        nombre = nombre.split('.')[0]
    
    return nombre

# ============================================================================
# FUNCIÓN: MANUAL SCALA
# ============================================================================

def manual_scala(carpeta_json):
    """
    Modo manual para aplicar Scala y opcionalmente renombrar con "1"
    """
    print("\n" + "═" * 60)
    print("🎮 MANUAL SCALA - ESCALA Y RENOMBRAR PERSONALIZADO")
    print("═" * 60)
    
    # Listar todos los archivos JSON
    archivos_json = list(sorted(carpeta_json.glob("*.json")))
    
    if not archivos_json:
        print("❌ No hay archivos JSON en la carpeta")
        input("Enter para continuar...")
        return
    
    # Crear carpeta de resultados
    resultados_dir = carpeta_json / "resultados_manual_scala"
    resultados_dir.mkdir(exist_ok=True)
    
    # Mostrar lista de archivos
    print(f"\n📂 Archivos disponibles ({len(archivos_json)}):")
    print("─" * 60)
    
    for idx, json_path in enumerate(archivos_json, 1):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            ruta_imagen = datos.get("image", "")
            nombre_spritesheet = extraer_nombre_spritesheet(ruta_imagen) or "SIN NOMBRE"
            escala_actual = datos.get("scale", 1.0)
            
            print(f"{idx:2}. {json_path.name:25}")
            print(f"    Sprite: {nombre_spritesheet:20} | Scale actual: {escala_actual}")
            
        except Exception as e:
            print(f"{idx:2}. {json_path.name:25} ❌ Error: {e}")
    
    print("─" * 60)
    
    # Seleccionar archivo
    try:
        seleccion = input(f"\nSelecciona un archivo (1-{len(archivos_json)}), 't' para todos, '0' para cancelar: ").strip()
        
        if seleccion == '0':
            print("\n🚫 Operación cancelada")
            input("Enter para continuar...")
            return
        
        if seleccion.lower() == 't':
            procesar_todos_manual_scala(archivos_json, resultados_dir)
            return
        
        seleccion_idx = int(seleccion) - 1
        
        if seleccion_idx < 0 or seleccion_idx >= len(archivos_json):
            print("❌ Selección inválida")
            input("Enter para continuar...")
            return
        
        json_path = archivos_json[seleccion_idx]
        
        # Procesar archivo individual
        procesar_individual_manual_scala(json_path, resultados_dir)
        
    except ValueError:
        print("❌ Selección inválida")
        input("Enter para continuar...")
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Enter para continuar...")

def procesar_individual_manual_scala(json_path, resultados_dir):
    """Procesa un archivo individual en modo Manual Scala"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        ruta_imagen = datos.get("image", "")
        nombre_spritesheet = extraer_nombre_spritesheet(ruta_imagen) or "SIN NOMBRE"
        escala_actual = datos.get("scale", 1.0)
        
        print(f"\n📄 Archivo seleccionado: {json_path.name}")
        print(f"   Sprite: {nombre_spritesheet}")
        print(f"   Scale actual: {escala_actual}")
        print("─" * 50)
        
        # Solicitar factor de Scala
        factor_input = input("¿Cuánto de Scala? (ej: 1.5, 2.0, 0.75): ").strip()
        
        try:
            factor = float(factor_input)
            
            if factor <= 0:
                print("❌ El factor debe ser mayor que 0")
                input("Enter para continuar...")
                return
            
            # Si factor=1, solo mostrar mensaje y no crear archivo
            if factor == 1.0:
                print(f"\nℹ️  Factor=1.0, no se requiere cambio en {json_path.name}")
                print("   No se generará archivo en resultados (skip)")
                input("Enter para continuar...")
                return
            
            # Preguntar si agregar "1"
            agregar_uno = input("\n¿Añadir un '1' al final del nombre? (s/n): ").strip().lower()
            
            nueva_escala = escala_actual * factor
            porcentaje_img = 100 / factor if factor != 0 else 100
            
            print(f"\n📊 RESUMEN DE CAMBIOS:")
            print(f"   Archivo: {json_path.name}")
            print(f"   Sprite: {nombre_spritesheet}")
            print(f"   Scale actual: {escala_actual}")
            print(f"   Scala aplicada: {factor}")
            print(f"   Nueva escala: {nueva_escala:.4f}")
            print(f"   Tamaño imagen: {porcentaje_img:.1f}%")
            print(f"   ¿Agregar '1'? {'SÍ' if agregar_uno == 's' else 'NO'}")
            
            confirmar = input("\n¿Confirmar cambios? (s/n): ").strip().lower()
            
            if confirmar != 's':
                print("\n🚫 Cambios cancelados")
                input("Enter para continuar...")
                return
            
            # Aplicar cambios
            print(f"\n⚙️  Procesando {json_path.name}...")
            
            # 1. Actualizar escala
            datos["scale"] = round(nueva_escala, 4)
            
            # 2. Si se eligió agregar "1", renombrar sprite en el JSON
            nuevo_nombre_archivo = json_path.name
            nuevo_nombre_sprite = None
            
            if agregar_uno == 's' and ruta_imagen:
                # Extraer nombre base del sprite (sin characters/ y sin extensión)
                if '/' in ruta_imagen:
                    # Separar por "/" y tomar el último elemento
                    partes_ruta = ruta_imagen.split('/')
                    nombre_con_extension = partes_ruta[-1]
                    nombre_base = nombre_con_extension.split('.')[0] if '.' in nombre_con_extension else nombre_con_extension
                else:
                    nombre_con_extension = ruta_imagen
                    nombre_base = nombre_con_extension.split('.')[0] if '.' in nombre_con_extension else nombre_con_extension
                
                # CORRECCIÓN: PsychEngine requiere SIN extensión .png
                # Nuevo nombre con "1" al final, SIN extensión
                nuevo_nombre_sprite = f"{nombre_base}1"
                
                # Actualizar la ruta en el JSON (SIN .png)
                if '/' in ruta_imagen:
                    datos["image"] = f"characters/{nuevo_nombre_sprite}"  # SIN .png
                else:
                    datos["image"] = nuevo_nombre_sprite  # SIN .png
                
                print(f"   ✅ Sprite renombrado a: {nuevo_nombre_sprite}")
            
            # 3. Guardar archivo (mismo nombre o renombrado si se eligió)
            if agregar_uno == 's':
                # Renombrar archivo JSON también
                nombre_base_json = json_path.stem
                nuevo_nombre_archivo = f"{nombre_base_json}1"
                print(f"   📄 Archivo renombrado a: {nuevo_nombre_archivo}")
            
            archivo_salida = resultados_dir / nuevo_nombre_archivo
            
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent='\t')
            
            print(f"\n✅ Archivo procesado exitosamente")
            print(f"📁 Guardado en: {archivo_salida}")
            print(f"💡 Sprite en JSON: {datos.get('image', 'No encontrado')}")
            
            # Generar mini-reporte
            generar_reporte_manual_scala(json_path, resultados_dir, factor, escala_actual, 
                                         nueva_escala, porcentaje_img, agregar_uno == 's', 
                                         nuevo_nombre_sprite)
            
        except ValueError:
            print("❌ Factor inválido. Debe ser un número (ej: 1.5, 2.0)")
            input("Enter para continuar...")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Enter para continuar...")

def procesar_todos_manual_scala(archivos_json, resultados_dir):
    """Procesar todos los archivos en modo Manual Scala"""
    print("\n📊 PROCESAR TODOS LOS ARCHIVOS CON MANUAL SCALA")
    print("─" * 60)
    
    try:
        factor_input = input("¿Cuánto de Scala para TODOS los archivos? (ej: 1.5, 2.0, 0.75): ").strip()
        factor = float(factor_input)
        
        if factor <= 0:
            print("❌ El factor debe ser mayor que 0")
            return
        
        # Si factor=1, no hacer nada
        if factor == 1.0:
            print("\nℹ️  Factor=1.0, no se requiere cambio en ningún archivo")
            print("   No se generarán archivos en resultados")
            input("Enter para continuar...")
            return
        
        agregar_uno = input("\n¿Añadir un '1' al final del nombre de TODOS? (s/n): ").strip().lower()
        
        # Mostrar confirmación
        print(f"\n⚠️  ATENCIÓN: Se aplicará Scala {factor} a {len(archivos_json)} archivos")
        print(f"   ¿Agregar '1'? {'SÍ' if agregar_uno == 's' else 'NO'}")
        confirmar = input("¿Continuar? (s/n): ").strip().lower()
        
        if confirmar != 's':
            print("\n🚫 Operación cancelada")
            return
        
        procesados = 0
        errores = []
        
        print(f"\n⚙️  Procesando {len(archivos_json)} archivos...")
        print("─" * 60)
        
        for json_path in archivos_json:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                
                # Obtener datos
                ruta_imagen = datos.get("image", "")
                nombre_spritesheet = extraer_nombre_spritesheet(ruta_imagen) or "SIN NOMBRE"
                escala_actual = datos.get("scale", 1.0)
                nueva_escala = escala_actual * factor
                
                # Actualizar escala
                datos["scale"] = round(nueva_escala, 4)
                
                # Determinar nombre de archivo de salida
                nombre_archivo_salida = json_path.name
                
                # Si se eligió agregar "1"
                if agregar_uno == 's' and ruta_imagen:
                    # Renombrar sprite en el JSON
                    if '/' in ruta_imagen:
                        # Separar por "/" y tomar el último elemento
                        partes_ruta = ruta_imagen.split('/')
                        nombre_con_extension = partes_ruta[-1]
                        nombre_base = nombre_con_extension.split('.')[0] if '.' in nombre_con_extension else nombre_con_extension
                    else:
                        nombre_con_extension = ruta_imagen
                        nombre_base = nombre_con_extension.split('.')[0] if '.' in nombre_con_extension else nombre_con_extension
                    
                    # PsychEngine requiere SIN extensión .png
                    nuevo_nombre_sprite = f"{nombre_base}1"  # SIN .png
                    
                    if '/' in ruta_imagen:
                        datos["image"] = f"characters/{nuevo_nombre_sprite}"  # SIN .png
                    else:
                        datos["image"] = nuevo_nombre_sprite  # SIN .png
                    
                    # Renombrar archivo JSON también
                    nombre_base_json = json_path.stem
                    nombre_archivo_salida = f"{nombre_base_json}1.json"
                
                # Guardar archivo
                archivo_salida = resultados_dir / nombre_archivo_salida
                with open(archivo_salida, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, indent='\t')
                
                print(f"✅ {json_path.name:25} → {nombre_archivo_salida:25} | Scale: {escala_actual:.2f} → {nueva_escala:.2f}")
                procesados += 1
                
            except Exception as e:
                print(f"❌ {json_path.name:25} → Error: {e}")
                errores.append(json_path.name)
        
        print("─" * 60)
        print(f"\n🎉 PROCESO COMPLETADO:")
        print(f"   ✅ Procesados: {procesados}")
        
        if errores:
            print(f"   ❌ Errores: {len(errores)}")
            print(f"\n📝 Archivos con errores:")
            for error in errores:
                print(f"   • {error}")
        
        print(f"   📁 Resultados en: {resultados_dir}/")
        
        # Generar reporte
        generar_reporte_todos_manual_scala(archivos_json, resultados_dir, factor, 
                                          procesados, errores, agregar_uno == 's')
        
    except ValueError:
        print("❌ Factor inválido. Debe ser un número")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    input("\nEnter para continuar...")

def generar_reporte_manual_scala(json_path, carpeta_resultados, factor, escala_original, 
                                escala_nueva, porcentaje, agregar_uno, nuevo_nombre_sprite=None):
    """Genera reporte individual para Manual Scala"""
    reporte_path = carpeta_resultados / f"REPORTE_MANUAL_SCALA_{json_path.stem}.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("REPORTE - MANUAL SCALA\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Archivo original: {json_path.name}\n")
        f.write(f"Factor Scala aplicado: {factor}\n")
        f.write(f"Escala original: {escala_original}\n")
        f.write(f"Escala nueva: {escala_nueva:.4f}\n")
        f.write(f"Tamaño imagen: {porcentaje:.1f}%\n")
        f.write(f"¿Agregar '1'?: {'SÍ' if agregar_uno else 'NO'}\n")
        if agregar_uno and nuevo_nombre_sprite:
            f.write(f"Nuevo nombre sprite: {nuevo_nombre_sprite}\n")
        f.write(f"\nFecha: {os.path.basename(json_path)}\n")
    
    print(f"📝 Reporte individual: {reporte_path.name}")

def generar_reporte_todos_manual_scala(archivos_json, carpeta_resultados, factor, 
                                      procesados, errores, agregar_uno):
    """Genera reporte para todos los archivos procesados con Manual Scala"""
    reporte_path = carpeta_resultados / "REPORTE_TODOS_MANUAL_SCALA.txt"
    
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write("REPORTE - MANUAL SCALA DE TODOS LOS ARCHIVOS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Factor Scala aplicado: {factor}\n")
        f.write(f"¿Agregar '1'?: {'SÍ' if agregar_uno else 'NO'}\n")
        f.write(f"Total archivos: {len(archivos_json)}\n")
        f.write(f"Procesados exitosos: {procesados}\n")
        f.write(f"Errores: {len(errores)}\n\n")
        
        if errores:
            f.write("ARCHIVOS CON ERRORES:\n")
            f.write("-" * 40 + "\n")
            for error in errores:
                f.write(f"{error}\n")
            f.write("\n")
        
        f.write("LISTA DE ARCHIVOS PROCESADOS:\n")
        f.write("-" * 70 + "\n")
        
        for json_path in archivos_json:
            try:
                with open(json_path, 'r', encoding='utf-8') as file:
                    datos = json.load(file)
                
                escala_original = datos.get("scale", 1.0)
                nueva_escala = escala_original * factor
                
                f.write(f"\n{json_path.name}\n")
                f.write(f"   Escala original: {escala_original}\n")
                f.write(f"   Nueva escala: {nueva_escala:.4f}\n")
                if agregar_uno:
                    nombre_base = json_path.stem
                    f.write(f"   Nuevo nombre: {nombre_base}1.json\n")
                
            except:
                f.write(f"\n{json_path.name} ❌ ERROR AL LEER\n")
    
    print(f"\n📝 Reporte completo: {reporte_path.name}")

# ============================================================================
# FUNCIONES EXISTENTES (se mantienen igual)
# ============================================================================

def diagnosticar_todos_json(carpeta_json):
    """Muestra diagnóstico con nombres normalizados"""
    print("\n🔍 DIAGNÓSTICO CON NOMBRES NORMALIZADOS")
    print("=" * 60)
    
    for json_path in sorted(carpeta_json.glob("*.json")):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            ruta_imagen = datos.get("image", "")
            nombre_original = Path(ruta_imagen).stem if ruta_imagen else "SIN IMAGE"
            nombre_normalizado = extraer_nombre_spritesheet(ruta_imagen)
            escala = datos.get("scale", 1.0)
            
            print(f"📄 {json_path.name:25}")
            print(f"   Original: '{ruta_imagen}'")
            print(f"   Normalizado: '{nombre_normalizado}'")
            print(f"   Scale: {escala}")
            print()
            
        except Exception as e:
            print(f"❌ {json_path.name:25} → Error: {e}")

def cargar_factores_automatico_insensible(txt_path):
    """Carga factores IGNORANDO mayúsculas/minúsculas"""
    factores = {}
    factores_originales = {}  # Para mostrar
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        
        print(f"\n📖 Leyendo {txt_path.name} (ignorando MAYÚSCULAS)...")
        
        for linea in lineas:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            
            # Buscar: Nombre,Scala=valor
            if 'Scala=' in linea:
                # Separar por coma
                partes = linea.split(',')
                if len(partes) >= 2:
                    nombre_original = partes[0].strip()
                    nombre_normalizado = normalizar_nombre(nombre_original)
                    
                    # Buscar Scala=valor
                    for parte in partes[1:]:
                        if 'Scala=' in parte:
                            valor_str = parte.replace('Scala=', '').strip()
                            # Quitar comentarios
                            if '#' in valor_str:
                                valor_str = valor_str.split('#')[0].strip()
                            try:
                                factor = float(valor_str)
                                factores[nombre_normalizado] = factor
                                factores_originales[nombre_normalizado] = nombre_original
                                print(f"   ✓ '{nombre_original}' → '{nombre_normalizado}' → Factor: {factor}")
                            except:
                                print(f"   ⚠️  Valor inválido: {parte}")
        
        return factores, factores_originales
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}, {}

def scale_y_renombrar_sprites(carpeta_json, scala_txt_path):
    """
    Lee Scala.txt, escala los JSON y renombra los sprites Y archivos JSON
    """
    print("\n" + "═" * 60)
    print("🔄 SCALE Y RENOMBRAR SPRITES Y JSON")
    print("═" * 60)
    
    # Verificar que exista Scala.txt
    if not scala_txt_path.exists():
        print(f"❌ No existe {scala_txt_path.name}")
        print("   Usa opción 4 para generarlo")
        input("Enter para continuar...")
        return
    
    # Carpeta de sprites (misma ubicación que characters)
    carpeta_sprites = carpeta_json.parent / "sprites"
    
    # Verificar carpeta de sprites
    if not carpeta_sprites.exists():
        print(f"❌ No existe la carpeta de sprites: {carpeta_sprites}")
        print("   Crea la carpeta 'sprites' en la misma ubicación que 'characters'")
        print("   y coloca los archivos PNG/XML allí")
        input("Enter para continuar...")
        return
    
    # Diagnosticar primero
    print("\n🔍 DIAGNÓSTICO INICIAL")
    print("─" * 60)
    diagnosticar_todos_json(carpeta_json)
    
    # Cargar factores de Scala.txt
    factores, factores_originales = cargar_factores_automatico_insensible(scala_txt_path)
    
    if not factores:
        print("\n❌ No se pudieron cargar factores de Scala.txt")
        return
    
    print(f"\n✅ Factores cargados: {len(factores)}")
    
    # Crear carpeta de resultados
    resultados_dir = carpeta_json.parent / "resultados_scale_renombrar"
    resultados_dir.mkdir(exist_ok=True)
    
    # Crear carpeta para sprites renombrados
    sprites_renombrados_dir = resultados_dir / "sprites_renombrados"
    sprites_renombrados_dir.mkdir(exist_ok=True)
    
    archivos_json = list(carpeta_json.glob("*.json"))
    
    if not archivos_json:
        print("❌ No hay archivos JSON")
        return
    
    print(f"\n📂 Procesando {len(archivos_json)} archivos...")
    print("─" * 60)
    
    resultados = []
    procesados = 0
    sprites_renombrados = 0
    skip_sprites = 0
    no_encontrados = 0
    
    for json_path in archivos_json:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            # Obtener información del JSON
            ruta_imagen_original = datos.get("image", "")
            nombre_json = extraer_nombre_spritesheet(ruta_imagen_original)
            escala_actual = datos.get("scale", 1.0)
            
            print(f"📄 {json_path.name:25} → '{nombre_json}' → ", end="")
            
            if not nombre_json:
                print("⚠️  Sin nombre")
                no_encontrados += 1
                continue
            
            # Buscar factor en Scala.txt
            if nombre_json in factores:
                factor = factores[nombre_json]
                nombre_scala_original = factores_originales.get(nombre_json, nombre_json)
                
                print(f"Factor: {factor} → ", end="")
                
                # 1. ESCALAR EL JSON (solo scale, sin offsets)
                nueva_escala = escala_actual * factor
                
                # 2. OBTENER NOMBRE ORIGINAL DEL ARCHIVO JSON (sin extensión)
                nombre_archivo_json = json_path.stem  # mouse-suffer
                
                # 3. OBTENER NOMBRE BASE DEL SPRITE
                nombre_base_sprite = ""
                if ruta_imagen_original:
                    # Extraer nombre base del sprite (sin characters/ y sin extensión)
                    if '/' in ruta_imagen_original:
                        # Separar por "/" y tomar el último elemento
                        partes_ruta = ruta_imagen_original.split('/')
                        nombre_con_extension = partes_ruta[-1]
                        nombre_base_sprite = nombre_con_extension.split('.')[0] if '.' in nombre_con_extension else nombre_con_extension
                    else:
                        nombre_con_extension = ruta_imagen_original
                        nombre_base_sprite = nombre_con_extension.split('.')[0] if '.' in nombre_con_extension else nombre_con_extension
                
                # 4. BUSCAR Y COPIAR LOS ARCHIVOS DE SPRITE EN LA CARPETA SPRITES
                archivos_encontrados = 0
                
                # Buscar archivos .png y .xml específicamente
                for extension in ['.png', '.xml', '.PNG', '.XML']:
                    sprite_path = carpeta_sprites / f"{nombre_base_sprite}{extension}"
                    if sprite_path.exists():
                        # Determinar el nombre del archivo de salida
                        if factor == 1.0:
                            # Para factor=1: mantener el mismo nombre (sin "1")
                            nuevo_nombre_archivo_sprite = sprite_path.name
                        else:
                            # Para factor≠1: agregar "1" antes de la extensión
                            nuevo_nombre_archivo_sprite = f"{nombre_base_sprite}1{extension}"
                        
                        nuevo_path_sprite = sprites_renombrados_dir / nuevo_nombre_archivo_sprite
                        
                        # Copiar archivo
                        shutil.copy2(sprite_path, nuevo_path_sprite)
                        archivos_encontrados += 1
                        
                        print(f"   🖼️  {sprite_path.name} → {nuevo_nombre_archivo_sprite}")
                
                # 5. PROCESAR JSON
                if factor == 1.0:
                    # Factor=1: no crear archivo JSON de salida, solo mostrar mensaje
                    print(f"SKIP JSON (factor=1)")
                    resultados.append({
                        'archivo_original': json_path.name,
                        'nombre': nombre_json,
                        'factor': factor,
                        'accion': 'skip_factor_1',
                        'razon': 'Factor=1, solo sprites copiados',
                        'sprites_copiados': archivos_encontrados
                    })
                    skip_sprites += 1
                else:
                    # Factor≠1: procesar JSON normalmente
                    datos["scale"] = round(nueva_escala, 4)
                    
                    # Renombrar sprite en el JSON
                    if ruta_imagen_original:
                        # Nuevo nombre del sprite con "1" al final, SIN extensión
                        nuevo_nombre_sprite = f"{nombre_base_sprite}1"
                        
                        # Actualizar la ruta en el JSON (SIN .png)
                        if '/' in ruta_imagen_original:
                            # Mantener la carpeta "characters/"
                            datos["image"] = f"characters/{nuevo_nombre_sprite}"  # SIN .png
                        else:
                            datos["image"] = nuevo_nombre_sprite  # SIN .png
                    
                    # Guardar archivo JSON con nuevo nombre
                    nuevo_nombre_json = f"{nombre_archivo_json}1.json"
                    archivo_salida = resultados_dir / nuevo_nombre_json
                    
                    with open(archivo_salida, 'w', encoding='utf-8') as f:
                        json.dump(datos, f, indent='\t')
                    
                    print(f"   📄 {json_path.name} → {nuevo_nombre_json}")
                    
                    porcentaje_img = 100 / factor if factor != 0 else 100
                    print(f"✅ Escala: {escala_actual} → {nueva_escala:.4f}")
                    print(f"   Sprite en JSON: {datos.get('image', 'No encontrado')}")
                    
                    resultados.append({
                        'archivo_original': json_path.name,
                        'archivo_nuevo': nuevo_nombre_json,
                        'nombre_original': nombre_json,
                        'nombre_sprite_original': nombre_base_sprite,
                        'nombre_sprite_nuevo': f"{nombre_base_sprite}1" if factor != 1.0 else nombre_base_sprite,
                        'factor': factor,
                        'escala_original': escala_actual,
                        'escala_nueva': nueva_escala,
                        'archivos_copiados': archivos_encontrados,
                        'ruta_final_sprite': datos.get('image', '') if factor != 1.0 else 'No modificado',
                        'accion': 'procesado'
                    })
                    
                    procesados += 1
                
                # Actualizar contador de sprites copiados
                if archivos_encontrados > 0:
                    sprites_renombrados += archivos_encontrados
                
            else:
                print(f"⚠️  No encontrado en Scala.txt")
                resultados.append({
                    'archivo_original': json_path.name,
                    'nombre': nombre_json,
                    'factor': None,
                    'accion': 'no_encontrado',
                    'razon': 'No encontrado en Scala.txt'
                })
                no_encontrados += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            resultados.append({
                'archivo_original': json_path.name,
                'nombre': 'ERROR',
                'factor': None,
                'accion': 'error',
                'razon': str(e)
            })
    
    print("\n" + "═" * 60)
    print("🎉 PROCESO COMPLETADO!")
    print("═" * 60)
    print(f"   ✅ JSONs procesados (factor≠1): {procesados}")
    print(f"   📁 JSONs skipeados (factor=1): {skip_sprites}")
    print(f"   ❓ No encontrados en Scala.txt: {no_encontrados}")
    print(f"   🖼️  Sprites copiados totales: {sprites_renombrados} archivos")
    print(f"   📂 JSONs resultantes (solo factor≠1): {resultados_dir}/")
    print(f"   📂 Sprites copiados (todos): {sprites_renombrados_dir}/")
    print("\n💡 NOTA IMPORTANTE:")
    print("   • Para factor=1: Solo se copian sprites (mismo nombre)")
    print("   • Para factor≠1: Se copian sprites con '1' y se crea JSON")
    print("   • Los sprites en el JSON NO tienen extensión")
    print("=" * 60)
    
    # Mostrar resumen de cambios
    if resultados:
        print("\n📊 RESUMEN DE CAMBIOS:")
        print("─" * 60)
        for res in resultados:
            if res['accion'] == 'procesado':
                print(f"• {res['archivo_original']} → {res['archivo_nuevo']}:")
                print(f"  Factor: {res['factor']}")
                print(f"  Escala: {res['escala_original']} → {res['escala_nueva']:.4f}")
                print(f"  Sprite: {res['nombre_sprite_original']} → {res['nombre_sprite_nuevo']}")
                print(f"  Ruta final en JSON: {res['ruta_final_sprite']}")
                print(f"  Archivos copiados: {res['archivos_copiados']}")
                print()
            elif res['accion'] == 'skip_factor_1':
                print(f"• {res['archivo_original']}: SKIP JSON (factor=1)")
                print(f"  Sprites copiados: {res.get('sprites_copiados', 0)} (mismo nombre)")
                print()
                
def main():
    """Función principal"""
    
    # enguine/
    script_dir = Path(__file__).parent

    # Carpeta principal (subimos un nivel)
    base_dir = script_dir.parent

    # Rutas reales (sin cambios)
    scala_txt_path = base_dir / "Optimizacion-psychEnguine" / "Scale_Json_psychEnguine" / "Scala.txt"
    json_folder   = base_dir / "Optimizacion-psychEnguine" / "Scale_Json_psychEnguine" / "characters"
    
    # NUEVO: Carpeta de sprites
    sprites_folder = base_dir / "Optimizacion-psychEnguine" / "Scale_Json_psychEnguine" / "sprites"

    # Crear carpetas si no existen
    json_folder.mkdir(parents=True, exist_ok=True)
    sprites_folder.mkdir(parents=True, exist_ok=True)  # NUEVO: Crear carpeta sprites automáticamente
    
    print(f"\n📁 Carpetas configuradas:")
    print(f"   • characters/: {json_folder}")
    print(f"   • sprites/: {sprites_folder}")
    print(f"   • Scala.txt: {scala_txt_path}")
    print()
    print("💡 Coloca tus archivos JSON en 'characters/' y los sprites (PNG/XML) en 'sprites/'")
    input("Presiona Enter para continuar al menú...")
    
    while True:
        limpiar_pantalla()
        mostrar_logo()
        
        print("🎯 MENÚ - VERSIÓN 5.0:\n")
        print("1. 📝 Ver Scala.txt actual")
        print("2. 🔄 SCALE Y RENOMBRAR SPRITES Y JSON (automático)")
        print("3. 🎮 MANUAL SCALA (escala personalizada)")
        print("4. ❌ Salir")
        print()
        
        try:
            opcion = input("Selección (1-4): ").strip()
            
            if opcion == "1":
                limpiar_pantalla()
                if scala_txt_path.exists():
                    print(f"\n📄 CONTENIDO DE {scala_txt_path.name}:")
                    print("=" * 60)
                    with open(scala_txt_path, 'r', encoding='utf-8') as f:
                        print(f.read())
                else:
                    print("❌ El archivo no existe")
                input("\nEnter para continuar...")
                
            elif opcion == "2":
                limpiar_pantalla()
                print("\n🔄 SCALE Y RENOMBRAR SPRITES Y JSON")
                print("═" * 60)
                print("📁 RUTAS CONFIGURADAS:")
                print(f"   • characters/: {json_folder}")
                print(f"   • sprites/: {sprites_folder}")
                print(f"   • Scala.txt: {scala_txt_path}")
                print()
                print("⚠️  IMPORTANTE:")
                print("   • Scala.txt debe tener los nombres en minúsculas")
                print("   • Los sprites deben estar en la carpeta 'sprites/'")
                print("   • Se creará '1' al final del nombre del sprite Y del archivo JSON")
                print("   • Ejemplo: 'mouse-suffer.json' → 'mouse-suffer1.json'")
                print("   • Ejemplo sprite: 'mouse-suffer.png' → 'mouse-suffer1.png'")
                print("   • En el JSON: 'characters/mouse-suffer1' (SIN extensión .png)")
                print("   • Si factor=1, se skipea (NO se generará archivo en resultados)")
                print("   • Solo los archivos con factor ≠ 1 aparecerán en la carpeta resultados")
                print()
                confirmar = input("¿Continuar? (s/n): ").strip().lower()
                
                if confirmar == 's':
                    scale_y_renombrar_sprites(json_folder, scala_txt_path)
                input("\nEnter para continuar...")
                
            elif opcion == "3":
                limpiar_pantalla()
                manual_scala(json_folder)
                
            elif opcion == "4":
                print("\n👋 ¡Hasta luego!")
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Programa interrumpido")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("Enter para continuar...")

if __name__ == "__main__":
    main()