import os
import json
import re
from datetime import datetime

# Colores
VERDE = '\033[92m'
AMARILLO = '\033[93m'
ROJO = '\033[91m'
CIAN = '\033[96m'
MAGENTA = '\033[95m'
AZUL = '\033[94m'
RESET = '\033[0m'

# Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

input_folder = os.path.join(
    BASE_DIR,
    'Optimizacion_V-slice',
    'Scale_Json_V-slice'
)

output_folder = os.path.join(input_folder, 'Modificado_nuevo')
os.makedirs(output_folder, exist_ok=True)

# Ruta base para automatización de mods
AUTO_MODS_DIR = os.path.join(input_folder, 'Automatizacion_mods')

# Ruta del archivo de debug
DEBUG_LOG_PATH = os.path.join(AUTO_MODS_DIR, 'Debug.txt')

# =========================
# SISTEMA DE LOGGING
# =========================

class DebugLogger:
    """Logger simple que escribe todo a un archivo y opcionalmente a consola"""
    
    def __init__(self, path):
        self.path = path
        self.enabled = False
        self._buffer = []
    
    def iniciar_sesion(self, titulo):
        """Inicia una nueva sesión de log (sobrescribe el archivo)"""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self.enabled = True
            self._buffer = []
            
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write("="*70 + "\n")
                f.write(f"  DEBUG LOG - {titulo}\n")
                f.write(f"  Sesión iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
            
            return True
        except Exception as e:
            print(f"{ROJO}⚠ No se pudo iniciar el log: {e}{RESET}")
            self.enabled = False
            return False
    
    def log(self, mensaje, nivel="INFO"):
        """Escribe una línea al log"""
        if not self.enabled:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefijo = {
            "INFO":    "[INFO]",
            "OK":      "[ ✓  ]",
            "WARN":    "[ ⚠  ]",
            "ERROR":   "[ ✗  ]",
            "SECTION": "[════]",
            "DEBUG":   "[····]",
            "HEADER":  "[####]",
        }.get(nivel, "[INFO]")
        
        linea = f"[{timestamp}] {prefijo} {mensaje}\n"
        
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(linea)
        except Exception:
            pass
    
    def seccion(self, titulo):
        """Escribe un separador de sección"""
        if not self.enabled:
            return
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write("\n" + "─"*70 + "\n")
                f.write(f"  {titulo}\n")
                f.write("─"*70 + "\n")
        except Exception:
            pass
    
    def cerrar_sesion(self, resumen=None):
        """Cierra la sesión"""
        if not self.enabled:
            return
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*70 + "\n")
                f.write(f"  Sesión finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if resumen:
                    f.write(f"  {resumen}\n")
                f.write("="*70 + "\n")
            self.enabled = False
        except Exception:
            pass


# Instancia global
logger = DebugLogger(DEBUG_LOG_PATH)


# =========================
# FUNCIONES AUXILIARES
# =========================

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def parse_selection(text, max_len):
    """Interpreta entradas como '1,2,4-6'"""
    result = set()
    parts = text.split(',')
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                result.update(range(start, end + 1))
            except:
                pass
        elif part.isdigit():
            result.add(int(part))
    return sorted(i - 1 for i in result if 0 < i <= max_len)


def buscar_assetpaths(obj):
    """Busca assetPath secundarios"""
    encontrados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'assetPath' and isinstance(v, str):
                encontrados.append(v)
            else:
                encontrados += buscar_assetpaths(v)
    elif isinstance(obj, list):
        for item in obj:
            encontrados += buscar_assetpaths(item)
    return encontrados


def dividir_offsets(obj, factor):
    """Divide offsets generales"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'offsets' and isinstance(value, list) and len(value) == 2:
                obj[key] = [round(value[0]/factor, 2), round(value[1]/factor, 2)]
            else:
                dividir_offsets(value, factor)
    elif isinstance(obj, list):
        for item in obj:
            dividir_offsets(item, factor)


def dividir_animations_offsets(data, factor):
    """Divide offsets en animations"""
    if 'animations' in data and isinstance(data['animations'], list):
        for anim in data['animations']:
            if isinstance(anim, list) and len(anim) >= 3:
                offsets = anim[2]
                if isinstance(offsets, list) and len(offsets) == 2:
                    anim[2] = [round(offsets[0]/factor, 2), round(offsets[1]/factor, 2)]


def cargar_escalas_desde_txt(scala_path=None):
    """Carga las escalas desde Scala.txt"""
    if scala_path is None:
        scala_path = os.path.join(input_folder, 'Scala.txt')
    
    escalas = {}
    
    if not os.path.exists(scala_path):
        return None
    
    try:
        with open(scala_path, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith('#') or linea.startswith('--'):
                    continue
                
                if ',' in linea and 'Scala=' in linea:
                    parts = linea.split(',')
                    nombre = parts[0].strip()
                    for part in parts:
                        if part.strip().startswith('Scala='):
                            try:
                                valor = float(part.strip().split('=')[1])
                                escalas[nombre] = valor
                            except:
                                pass
        return escalas
    except Exception as e:
        print(f"{ROJO}Error al leer Scala.txt: {e}{RESET}")
        logger.log(f"Error al leer Scala.txt ({scala_path}): {e}", "ERROR")
        return None


def obtener_factor_por_assetpath(asset_path, escalas_dict):
    """
    Verifica el assetPath probando en este orden:
    
    1. Ruta completa con slashes (exacto):  "lovebf/bf" == "lovebf/bf"
    2. Ruta completa (case-insensitive):    "LoveBF/BF" == "lovebf/bf"
    3. Basename (exacto):                   "lovebf/bf" == "bf"  ✔ fallback
    4. Basename (case-insensitive):         "LoveBF/BF" == "bf"
    
    Ejemplos:
        JSON "lovebf/bf"  ↔  Scala "lovebf/bf"   → MATCH exacto (ruta)
        JSON "lovebf/bf"  ↔  Scala "bf"          → MATCH basename
        JSON "bf"         ↔  Scala "lovebf/bf"   → MATCH basename
        JSON "Animacion/dad/e/daddy" ↔ Scala "Animacion/dad/e/daddy" → MATCH exacto
    """
    if not asset_path:
        return None, 'sin assetPath'
    
    # Normalizar el assetPath
    asset_norm = asset_path.replace("\\", "/").strip("/")
    basename_asset = os.path.basename(asset_norm)
    
    # ═══════════════════════════════════════════════════════
    # 1. RUTA COMPLETA — coincidencia exacta
    # ═══════════════════════════════════════════════════════
    if asset_norm in escalas_dict:
        return (
            escalas_dict[asset_norm],
            f'ruta exacta: "{asset_norm}"'
        )
    
    # ═══════════════════════════════════════════════════════
    # 2. RUTA COMPLETA — case-insensitive
    # ═══════════════════════════════════════════════════════
    for key in escalas_dict:
        key_norm = key.replace("\\", "/").strip("/")
        if key_norm.lower() == asset_norm.lower():
            return (
                escalas_dict[key],
                f'ruta exacta (case-insensitive): "{key}"'
            )
    
    # ═══════════════════════════════════════════════════════
    # 3. BASENAME — coincidencia exacta (fallback)
    # ═══════════════════════════════════════════════════════
    if basename_asset:
        for key in escalas_dict:
            key_norm = key.replace("\\", "/").strip("/")
            key_basename = os.path.basename(key_norm)
            
            if key_basename == basename_asset:
                return (
                    escalas_dict[key],
                    f'basename: "{key}" → "{basename_asset}"'
                )
        
        # ═══════════════════════════════════════════════════
        # 4. BASENAME — case-insensitive
        # ═══════════════════════════════════════════════════
        for key in escalas_dict:
            key_norm = key.replace("\\", "/").strip("/")
            key_basename = os.path.basename(key_norm)
            
            if key_basename.lower() == basename_asset.lower():
                return (
                    escalas_dict[key],
                    f'basename (case-insensitive): "{key}" → "{basename_asset}"'
                )
    
    return None, f'no encontrado para "{basename_asset or asset_norm}"'


def obtener_factor_para_json(json_path, escalas_dict):
    """Obtiene el factor para un archivo JSON basado en su assetPath"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        asset_path = data.get('assetPath', '')
        
        if not asset_path:
            asset_paths = buscar_assetpaths(data)
            if asset_paths:
                asset_path = asset_paths[0]
        
        return obtener_factor_por_assetpath(asset_path, escalas_dict)
        
    except Exception as e:
        return None, f'error al leer archivo: {e}'


def procesar_json(json_path, output_path, escalas_dict):
    """Procesa un solo JSON con el diccionario de escalas"""
    try:
        factor, tipo_coincidencia = obtener_factor_para_json(json_path, escalas_dict)
        
        if factor is None:
            return False, f"sin asignación → {tipo_coincidencia}"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'scale' in data and isinstance(data['scale'], (int, float)):
            data['scale'] = round(data['scale'] * factor, 2)
        else:
            data['scale'] = factor
        
        dividir_offsets(data, factor)
        dividir_animations_offsets(data, factor)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return True, f"factor: {factor:.4f} ({tipo_coincidencia})"
    
    except Exception as e:
        return False, f"error: {e}"


# =========================
# AUTOMATIZACIÓN MODS
# =========================

def listar_mods_automatizacion():
    """Lista los mods disponibles en Automatizacion_mods/"""
    if not os.path.exists(AUTO_MODS_DIR):
        os.makedirs(AUTO_MODS_DIR, exist_ok=True)
        return []
    
    return sorted([
        d for d in os.listdir(AUTO_MODS_DIR)
        if os.path.isdir(os.path.join(AUTO_MODS_DIR, d))
    ])


def encontrar_scalas_de_mod(mod_path):
    """Busca Scala.txt en las dos rutas típicas de un mod de V-Slice"""
    ruta_1 = os.path.join(mod_path, 'images', 'characters', 'Scala.txt')
    ruta_2 = os.path.join(mod_path, 'shared', 'images', 'characters', 'Scala.txt')
    
    rutas_encontradas = []
    escalas_combinadas = {}
    
    logger.log(f"Buscando Scala.txt en:", "DEBUG")
    logger.log(f"  → {ruta_1}", "DEBUG")
    logger.log(f"  → {ruta_2}", "DEBUG")
    
    if os.path.exists(ruta_1):
        logger.log(f"  ✓ Existe: images/characters/Scala.txt", "OK")
        escalas_1 = cargar_escalas_desde_txt(ruta_1)
        if escalas_1:
            escalas_combinadas.update(escalas_1)
            rutas_encontradas.append(('images/characters', ruta_1, len(escalas_1)))
            logger.log(f"    → {len(escalas_1)} entradas cargadas", "OK")
            for k, v in escalas_1.items():
                logger.log(f"       · {k} = {v}", "DEBUG")
        else:
            logger.log(f"    → No se pudieron leer las escalas", "WARN")
    else:
        logger.log(f"  ✗ No existe: images/characters/Scala.txt", "DEBUG")
    
    if os.path.exists(ruta_2):
        logger.log(f"  ✓ Existe: shared/images/characters/Scala.txt", "OK")
        escalas_2 = cargar_escalas_desde_txt(ruta_2)
        if escalas_2:
            escalas_combinadas.update(escalas_2)
            rutas_encontradas.append(('shared/images/characters', ruta_2, len(escalas_2)))
            logger.log(f"    → {len(escalas_2)} entradas cargadas", "OK")
            for k, v in escalas_2.items():
                logger.log(f"       · {k} = {v}", "DEBUG")
        else:
            logger.log(f"    → No se pudieron leer las escalas", "WARN")
    else:
        logger.log(f"  ✗ No existe: shared/images/characters/Scala.txt", "DEBUG")
    
    return rutas_encontradas, escalas_combinadas


def procesar_mod_individual(mod_name, verbose=True):
    """Procesa un mod completo"""
    mod_path = os.path.join(AUTO_MODS_DIR, mod_name)
    json_folder = os.path.join(mod_path, 'data', 'characters')
    output_mod_folder = os.path.join(mod_path, 'Modificado_nuevo')
    
    logger.seccion(f"MOD: {mod_name}")
    logger.log(f"Ruta del mod: {mod_path}", "INFO")
    logger.log(f"Carpeta JSONs: {json_folder}", "INFO")
    logger.log(f"Carpeta salida: {output_mod_folder}", "INFO")
    
    # Verificar carpeta de JSONs
    if not os.path.exists(json_folder):
        if verbose:
            print(f"  {ROJO}✗ No existe: {json_folder}{RESET}")
        logger.log(f"No existe carpeta data/characters", "ERROR")
        return 0, 0, [], f"No existe carpeta data/characters en {mod_name}"
    
    json_files = sorted([f for f in os.listdir(json_folder) if f.endswith('.json')])
    if not json_files:
        if verbose:
            print(f"  {ROJO}✗ No hay JSONs en: {json_folder}{RESET}")
        logger.log(f"No hay archivos JSON en data/characters", "ERROR")
        return 0, 0, [], f"No hay JSONs en {mod_name}"
    
    logger.log(f"JSONs encontrados: {len(json_files)}", "INFO")
    
    # Buscar Scala.txt
    rutas_encontradas, escalas_combinadas = encontrar_scalas_de_mod(mod_path)
    
    if not rutas_encontradas:
        if verbose:
            print(f"  {ROJO}✗ No se encontró Scala.txt en:{RESET}")
            print(f"    - images/characters/Scala.txt")
            print(f"    - shared/images/characters/Scala.txt")
        logger.log(f"No se encontró ningún Scala.txt", "ERROR")
        return 0, 0, [], f"No se encontró Scala.txt en {mod_name}"
    
    if verbose:
        print(f"  {VERDE}✓ Scala.txt encontrados:{RESET}")
        for tipo, ruta, cant in rutas_encontradas:
            print(f"      • {tipo}/Scala.txt {CIAN}({cant} entradas){RESET}")
        print(f"  {AMARILLO}📊 Total escalas combinadas: {len(escalas_combinadas)}{RESET}")
        print(f"  {AMARILLO}📄 JSONs a procesar: {len(json_files)}{RESET}\n")
    
    logger.log(f"Scala.txt encontrados: {len(rutas_encontradas)}", "OK")
    logger.log(f"Total escalas combinadas: {len(escalas_combinadas)}", "INFO")
    
    # Crear carpeta de salida
    os.makedirs(output_mod_folder, exist_ok=True)
    
    procesados = 0
    sin_asignacion = []
    
    logger.log(f"--- Procesando {len(json_files)} JSONs ---", "INFO")
    
    for filename in json_files:
        json_path = os.path.join(json_folder, filename)
        output_path = os.path.join(output_mod_folder, filename)
        
        # Leer assetPath para el log
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                tmp_data = json.load(f)
            asset_path = tmp_data.get('assetPath', '(sin assetPath)')
            logger.log(f"→ {filename} | assetPath: {asset_path}", "DEBUG")
        except Exception as e:
            logger.log(f"→ {filename} | Error leyendo: {e}", "ERROR")
        
        exito, mensaje = procesar_json(json_path, output_path, escalas_combinadas)
        
        if exito:
            if verbose:
                print(f"    {VERDE}✓ {filename} → {mensaje}{RESET}")
            logger.log(f"  ✓ {filename} → {mensaje}", "OK")
            procesados += 1
        else:
            sin_asignacion.append(filename)
            if verbose:
                print(f"    {ROJO}✗ {filename} → {mensaje}{RESET}")
            logger.log(f"  ✗ {filename} → {mensaje}", "ERROR")
    
    logger.log(f"Mod '{mod_name}' → {procesados} OK / {len(sin_asignacion)} sin asignación", "INFO")
    
    return procesados, len(sin_asignacion), sin_asignacion, None


def automatizacion_mods():
    """Menú de automatización de mods"""
    while True:
        clear_screen()
        
        if not os.path.exists(AUTO_MODS_DIR):
            os.makedirs(AUTO_MODS_DIR, exist_ok=True)
        
        mods = listar_mods_automatizacion()
        
        print(f"{CIAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{CIAN}║{MAGENTA}      AUTOMATIZACIÓN DE MODS - V-SLICE             {CIAN}║{RESET}")
        print(f"{CIAN}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"\n{AMARILLO}📂 Buscando mods en:{RESET}")
        print(f"{CIAN}{AUTO_MODS_DIR}{RESET}")
        print(f"{AMARILLO}📄 Debug log:{RESET} {CIAN}{DEBUG_LOG_PATH}{RESET}\n")
        
        if not mods:
            print(f"{ROJO}❌ No hay mods disponibles.{RESET}")
            print(f"{AMARILLO}💡 Coloca tus mods dentro de: Automatizacion_mods/{RESET}")
            print(f"{AMARILLO}   Cada mod debe tener la estructura:{RESET}")
            print(f"{CIAN}   ModName/{RESET}")
            print(f"{CIAN}   ├── data/characters/*.json{RESET}")
            print(f"{CIAN}   ├── images/characters/Scala.txt       (o){RESET}")
            print(f"{CIAN}   └── shared/images/characters/Scala.txt{RESET}")
            input(f"\n{AMARILLO}⏎ Presione Enter para volver...{RESET}")
            return
        
        print(f"{VERDE}📦 Mods Disponibles:{RESET}\n")
        print(f"{AMARILLO}999.{RESET} ⚙  Automatizar TODOS los mods")
        print(f"{AMARILLO}  0.{RESET} ↩  Volver al menú principal")
        print()
        
        for i, mod in enumerate(mods, 1):
            mod_path = os.path.join(AUTO_MODS_DIR, mod)
            tiene_json = os.path.exists(os.path.join(mod_path, 'data', 'characters'))
            tiene_scala = (
                os.path.exists(os.path.join(mod_path, 'images', 'characters', 'Scala.txt')) or
                os.path.exists(os.path.join(mod_path, 'shared', 'images', 'characters', 'Scala.txt'))
            )
            
            estado = ""
            if tiene_json and tiene_scala:
                estado = f"{VERDE}[✓ listo]{RESET}"
            elif not tiene_json:
                estado = f"{ROJO}[✗ sin data/characters]{RESET}"
            elif not tiene_scala:
                estado = f"{AMARILLO}[⚠ sin Scala.txt]{RESET}"
            
            print(f"{VERDE}{i:>3}.{RESET} {mod:<30} {estado}")
        
        opcion = input(f"\n{CIAN}👉 Seleccione mod (1-{len(mods)}) | 999 Auto | 0 Salir: {RESET}").strip()
        
        if opcion == "0":
            return
        
        # ─── 999: Automatizar TODOS los mods ───
        if opcion == "999":
            clear_screen()
            print(f"{CIAN}╔══════════════════════════════════════════════════════╗{RESET}")
            print(f"{CIAN}║{MAGENTA}          ⚙ AUTOMATIZAR TODOS LOS MODS            {CIAN}║{RESET}")
            print(f"{CIAN}╚══════════════════════════════════════════════════════╝{RESET}")
            print(f"\n{AMARILLO}📦 Mods a procesar: {len(mods)}{RESET}\n")
            
            for i, mod in enumerate(mods, 1):
                print(f"  {i}. {mod}")
            
            confirmar = input(f"\n{CIAN}¿Continuar? (s/n): {RESET}").lower()
            if confirmar != 's':
                print(f"{AMARILLO}❌ Cancelado{RESET}")
                input(f"\n{AMARILLO}⏎ Presione Enter para volver...{RESET}")
                continue
            
            # Iniciar sesión de log
            logger.iniciar_sesion("AUTOMATIZAR TODOS LOS MODS")
            logger.log(f"Modo: 999 - Automatizar TODOS", "HEADER")
            logger.log(f"Total de mods: {len(mods)}", "INFO")
            logger.log(f"Mods: {', '.join(mods)}", "INFO")
            
            print(f"\n{CIAN}{'═'*60}{RESET}")
            
            total_procesados = 0
            total_sin_asignacion = 0
            mods_ok = []
            mods_error = []
            
            for i, mod in enumerate(mods, 1):
                print(f"\n{MAGENTA}━━━ [{i}/{len(mods)}] Procesando: {mod} ━━━{RESET}")
                print(f"{CIAN}{'─'*60}{RESET}")
                
                logger.log(f"--- Procesando [{i}/{len(mods)}]: {mod} ---", "SECTION")
                
                procesados, sin_asig, lista_sin, error = procesar_mod_individual(mod, verbose=True)
                
                if error:
                    mods_error.append((mod, error))
                    logger.log(f"Mod '{mod}' ERROR: {error}", "ERROR")
                else:
                    mods_ok.append((mod, procesados, sin_asig))
                    total_procesados += procesados
                    total_sin_asignacion += sin_asig
            
            # ─── Resumen final ───
            print(f"\n{CIAN}{'═'*60}{RESET}")
            print(f"{CIAN}╔══════════════════════════════════════════════════════╗{RESET}")
            print(f"{CIAN}║{VERDE}              ✅ RESUMEN DE AUTOMATIZACIÓN        {CIAN}║{RESET}")
            print(f"{CIAN}╚══════════════════════════════════════════════════════╝{RESET}")
            
            logger.seccion("RESUMEN FINAL")
            
            if mods_ok:
                print(f"\n{VERDE}✓ Mods procesados: {len(mods_ok)}{RESET}")
                logger.log(f"Mods OK: {len(mods_ok)}", "OK")
                for mod, proc, sin in mods_ok:
                    linea = f"   • {mod:<25} → {VERDE}{proc} procesados{RESET}"
                    if sin > 0:
                        linea += f" {AMARILLO}({sin} sin asignación){RESET}"
                    print(linea)
                    logger.log(f"  ✓ {mod} → {proc} procesados, {sin} sin asignación", "OK")
            
            if mods_error:
                print(f"\n{ROJO}✗ Mods con error: {len(mods_error)}{RESET}")
                logger.log(f"Mods con error: {len(mods_error)}", "ERROR")
                for mod, err in mods_error:
                    print(f"   • {mod:<25} → {err}")
                    logger.log(f"  ✗ {mod} → {err}", "ERROR")
            
            print(f"\n{AMARILLO}📊 TOTAL: {VERDE}{total_procesados} JSONs procesados{RESET}", end="")
            if total_sin_asignacion > 0:
                print(f" {AMARILLO}| {total_sin_asignacion} sin asignación{RESET}")
            else:
                print()
            
            resumen = f"TOTAL: {total_procesados} procesados | {total_sin_asignacion} sin asignación | {len(mods_error)} errores"
            logger.cerrar_sesion(resumen)
            
            print(f"\n{CIAN}📄 Debug log guardado en:{RESET}")
            print(f"{AMARILLO}{DEBUG_LOG_PATH}{RESET}")
            
            input(f"\n{AMARILLO}⏎ Presione Enter para volver...{RESET}")
            continue
        
        # ─── Seleccionar mod individual ───
        try:
            idx = int(opcion) - 1
            if not (0 <= idx < len(mods)):
                print(f"{ROJO}❌ Opción no válida{RESET}")
                input(f"\n{AMARILLO}⏎ Presione Enter para continuar...{RESET}")
                continue
        except ValueError:
            print(f"{ROJO}❌ Ingrese un número válido{RESET}")
            input(f"\n{AMARILLO}⏎ Presione Enter para continuar...{RESET}")
            continue
        
        mod_elegido = mods[idx]
        
        clear_screen()
        print(f"{CIAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{CIAN}║{MAGENTA}              PROCESANDO MOD INDIVIDUAL            {CIAN}║{RESET}")
        print(f"{CIAN}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"\n{VERDE}📦 Mod:{RESET} {mod_elegido}\n")
        print(f"{CIAN}{'─'*60}{RESET}\n")
        
        # Iniciar sesión de log
        logger.iniciar_sesion(f"MOD INDIVIDUAL: {mod_elegido}")
        logger.log(f"Modo: Individual - {mod_elegido}", "HEADER")
        
        procesados, sin_asig, lista_sin, error = procesar_mod_individual(mod_elegido, verbose=True)
        
        print(f"\n{CIAN}{'─'*60}{RESET}")
        
        if error:
            print(f"{ROJO}❌ Error: {error}{RESET}")
            logger.log(f"Error: {error}", "ERROR")
            resumen = f"ERROR: {error}"
        else:
            print(f"\n{VERDE}✅ Procesados: {procesados}{RESET}")
            if sin_asig > 0:
                print(f"{AMARILLO}⚠️  Sin asignación: {sin_asig}{RESET}")
                for nombre in lista_sin:
                    print(f"   - {nombre}")
                    logger.log(f"  Sin asignación: {nombre}", "WARN")
            
            output_dir = os.path.join(AUTO_MODS_DIR, mod_elegido, 'Modificado_nuevo')
            print(f"\n{CIAN}📁 Resultados en:{RESET}")
            print(f"   {output_dir}/")
            
            resumen = f"Mod: {mod_elegido} | Procesados: {procesados} | Sin asignación: {sin_asig}"
        
        logger.cerrar_sesion(resumen)
        
        print(f"\n{CIAN}📄 Debug log guardado en:{RESET}")
        print(f"{AMARILLO}{DEBUG_LOG_PATH}{RESET}")
        
        input(f"\n{AMARILLO}⏎ Presione Enter para volver...{RESET}")


# =========================
# LOOP PRINCIPAL
# =========================

while True:
    os.system('clear' if os.name == 'posix' else 'cls')

    json_files = [f for f in os.listdir(input_folder) if f.endswith('.json')]
    
    print("====================================")
    print("   SELECCIONA MODO DE OPERACIÓN")
    print("====================================")
    print("1. Manual - Seleccionar archivos individuales")
    print("2. Automático - Usar Scala.txt (basado en assetPath)")
    print(f"{AMARILLO}3. Automatización Mods{RESET}")
    print("4. Salir")
    
    modo = input("\nElige modo (1, 2, 3 o 4): ").strip()
    
    if modo == '4':
        print(f"\n{VERDE}Programa finalizado correctamente.{RESET}")
        break
    
    if modo == '3':
        automatizacion_mods()
        continue
    
    if modo == '2':
        if not json_files:
            print(f"{ROJO}No hay archivos JSON en la carpeta.{RESET}")
            input("\nPresiona Enter para volver al menú...")
            continue
        
        print("\n" + "="*40)
        print("   PROCESANDO EN MODO AUTOMÁTICO")
        print("="*40)
        
        escalas = cargar_escalas_desde_txt()
        if escalas is None:
            print(f"{ROJO}No se encontró el archivo Scala.txt{RESET}")
            input("\nPresiona Enter para volver al menú...")
            continue
        
        print(f"\n{VERDE}Escalas cargadas: {len(escalas)} entradas{RESET}")
        print(f"{AMARILLO}Keys disponibles: {', '.join(escalas.keys())}{RESET}\n")
        
        procesados = 0
        no_encontrados = []
        
        for filename in json_files:
            try:
                with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                asset_path = data.get('assetPath', 'No encontrado')
                print(f"{AMARILLO}📄 {filename} -> assetPath: {asset_path}{RESET}")
            except:
                pass
            
            factor, tipo_coincidencia = obtener_factor_para_json(
                os.path.join(input_folder, filename), escalas
            )
            
            if factor is None:
                no_encontrados.append(filename)
                print(f"{ROJO}✗ {filename} -> {tipo_coincidencia}{RESET}\n")
                continue
            
            json_path = os.path.join(input_folder, filename)
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'scale' in data and isinstance(data['scale'], (int, float)):
                    data['scale'] = round(data['scale'] * factor, 2)
                else:
                    data['scale'] = factor
                
                dividir_offsets(data, factor)
                dividir_animations_offsets(data, factor)
                
                output_path = os.path.join(output_folder, filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                print(f"{VERDE}✓ {filename} -> factor: {factor:.4f} ({tipo_coincidencia}){RESET}\n")
                procesados += 1
                
            except Exception as e:
                print(f"{ROJO}✗ Error en {filename}: {e}{RESET}\n")
        
        print("\n" + "="*40)
        print(f"{VERDE}✅ Procesados: {procesados}{RESET}")
        if no_encontrados:
            print(f"{AMARILLO}⚠️ Sin asignación: {len(no_encontrados)}{RESET}")
            for nombre in no_encontrados:
                print(f"  - {nombre}")
        
        input("\nPresiona Enter para volver al menú...")
        continue
    
    if modo == '1':
        if not json_files:
            print(f"{ROJO}No hay archivos JSON en la carpeta.{RESET}")
            input("\nPresiona Enter para volver al menú...")
            continue
        
        print("\n" + "="*40)
        print("   SELECCIONA ARCHIVOS JSON (MANUAL)")
        print("="*40)
        
        for i, filename in enumerate(json_files, 1):
            print(f"{i:02d}. {filename}")
            
            try:
                with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'assetPath' in data:
                    print(f"     |-{VERDE}{data['assetPath']}{RESET}")
                
                secundarios = buscar_assetpaths(data)
                if 'assetPath' in data:
                    try:
                        secundarios.remove(data['assetPath'])
                    except:
                        pass
                
                for ruta in set(secundarios):
                    print(f"     |-{AMARILLO}{ruta}{RESET}")
                    
            except Exception as e:
                print(f"     |-Error: {e}")
        
        opcion = input("\nElige archivos (ej: 1,2,4-6): ").replace(' ', '')
        
        if opcion == '09' or opcion.lower() == 'salir':
            print(f"\n{VERDE}Programa finalizado correctamente.{RESET}")
            break
        
        choices = parse_selection(opcion, len(json_files))
        if not choices:
            print(f"{ROJO}Selección inválida.{RESET}")
            input("Presiona Enter para volver al menú...")
            continue
        
        try:
            factor = float(input("Pon tu valor para dividir: "))
        except:
            print(f"{ROJO}Valor inválido.{RESET}")
            input("Presiona Enter para volver al menú...")
            continue
        
        for idx in choices:
            selected_file = json_files[idx]
            json_path = os.path.join(input_folder, selected_file)
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'scale' in data and isinstance(data['scale'], (int, float)):
                data['scale'] = round(data['scale'] * factor, 2)
            else:
                data['scale'] = factor
            
            dividir_offsets(data, factor)
            dividir_animations_offsets(data, factor)
            
            output_path = os.path.join(output_folder, selected_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"{VERDE}✓ {selected_file} procesado correctamente{RESET}")
        
        input("\nProceso terminado. Presiona Enter para volver al menú...")