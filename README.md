# FNF Optimizer APK

Proyecto Android basado en las rutinas del optimizador de mods para **FNF V-Slice / Psych Engine**. Esta versión reemplaza el menú de terminal por una interfaz Kivy y está preparada para compilarse con Buildozer o GitHub Actions.

## Qué incluye

- Extracción recursiva de frames desde spritesheets `PNG + XML` Sparrow.
- Redimensión multihilo con factores `75%`, `50%`, `40%`, `25%` o modo automático.
- Generación multihilo de spritesheets `PNG + XML` con recorte transparente y detección de frames duplicados.
- `Scala.txt` generado después de redimensionar.
- Flujo completo: extraer → redimensionar → generar.
- Selector de carpeta y campo editable para rutas Android.
- Botón para solicitar acceso al almacenamiento.
- Sin icono personalizado y sin ejecutables `.exe`.

> Nota: el selector trabaja con rutas del sistema. En Android 11+ el proyecto solicita `MANAGE_EXTERNAL_STORAGE`, pensado para APK instalada manualmente. Google Play restringe ese permiso y puede requerir otra estrategia basada en Storage Access Framework.

## Estructura

```text
.
├── main.py
├── fnf_optimizer/
│   ├── __init__.py
│   ├── core.py
│   └── android_storage.py
├── buildozer.spec
├── requirements.txt
└── .github/workflows/build-apk.yml
```

## Compilar desde GitHub

1. Crea un repositorio y sube todos los archivos.
2. En GitHub abre **Actions**.
3. Selecciona **Build Android APK**.
4. Pulsa **Run workflow**.
5. Cuando termine, abre la ejecución y descarga el artefacto **FNF-Optimizer-APK**.

También se compila automáticamente con cada `push` a `main` o `master` que modifique el código del APK.

## Compilar localmente en Ubuntu / WSL2

Instala las dependencias de Buildozer y luego ejecuta:

```bash
python3 -m pip install --user "cython<3" buildozer
buildozer -v android debug
```

El APK resultante queda en `bin/`.

## Uso

1. Instala el APK.
2. Pulsa **Dar permiso de almacenamiento** y concede acceso si Android lo solicita.
3. En **Carpeta fuente**, selecciona la carpeta que contiene los sprites `PNG + XML`.
4. Elige la escala y cantidad de hilos.
5. Usa una operación individual o **Flujo completo**.

La salida se crea por defecto en:

```text
/storage/emulated/0/Download/FNFOptimizer/optimizer_output/
```

con estas subcarpetas:

```text
frames/
resized/
sprites/
```

## Créditos de la base original

El paquete fuente proporcionado identifica a **Noctrox Gato** como autor del optimizador original. Esta adaptación conserva la lógica esencial de sprites y la convierte en una aplicación Android.

## Estado de esta adaptación

El núcleo de sprites está adaptado a GUI y probado con un flujo completo automatizado. Los scripts CLI originales de JSON/Stage se conservan en `legacy_cli/` como referencia, pero están excluidos del APK hasta convertir sus menús `input()` a pantallas Android.
