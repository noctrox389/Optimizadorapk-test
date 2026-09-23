from __future__ import annotations

import os
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from fnf_optimizer.android_storage import default_external_path, request_storage_permissions
from fnf_optimizer.core import (
    clean_directory,
    extract_frames,
    full_pipeline,
    generate_spritesheets,
    resize_frames,
)


class OptimizerRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kwargs)
        self.running = False

        title = Label(text="FNF MOD OPTIMIZER", size_hint_y=None, height=dp(45), font_size="22sp")
        self.add_widget(title)

        form = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        form.add_widget(Label(text="Engine", size_hint_y=None, height=dp(42)))
        self.engine = Spinner(text="V-Slice", values=("V-Slice", "Psych Engine"), size_hint_y=None, height=dp(42))
        form.add_widget(self.engine)

        form.add_widget(Label(text="Carpeta fuente", size_hint_y=None, height=dp(42)))
        source_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.source = TextInput(text=default_external_path(), multiline=False)
        browse = Button(text="...", size_hint_x=None, width=dp(52))
        browse.bind(on_release=lambda *_: self.open_folder_picker(self.source))
        source_row.add_widget(self.source)
        source_row.add_widget(browse)
        form.add_widget(source_row)

        form.add_widget(Label(text="Salida", size_hint_y=None, height=dp(42)))
        output_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.workspace = TextInput(text=os.path.join(default_external_path(), "optimizer_output"), multiline=False)
        browse_output = Button(text="...", size_hint_x=None, width=dp(52))
        browse_output.bind(on_release=lambda *_: self.open_folder_picker(self.workspace))
        output_row.add_widget(self.workspace)
        output_row.add_widget(browse_output)
        form.add_widget(output_row)

        form.add_widget(Label(text="Escala", size_hint_y=None, height=dp(42)))
        self.factor = Spinner(text="Automática", values=("Automática", "75%", "50%", "40%", "25%"), size_hint_y=None, height=dp(42))
        form.add_widget(self.factor)

        form.add_widget(Label(text="Hilos", size_hint_y=None, height=dp(42)))
        self.workers = Spinner(text="4", values=("1", "2", "4", "6", "8"), size_hint_y=None, height=dp(42))
        form.add_widget(self.workers)
        self.add_widget(form)

        permission = Button(text="Dar permiso de almacenamiento", size_hint_y=None, height=dp(44))
        permission.bind(on_release=self.on_permissions)
        self.add_widget(permission)

        buttons = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        buttons.bind(minimum_height=buttons.setter("height"))
        for text, action in (
            ("1. Extraer frames", self.run_extract),
            ("2. Redimensionar", self.run_resize),
            ("3. Generar sprites", self.run_generate),
            ("Flujo completo", self.run_full),
            ("Limpiar salida", self.run_clean),
            ("Abrir carpeta fuente", lambda *_: self.open_folder_picker(self.source)),
        ):
            btn = Button(text=text, size_hint_y=None, height=dp(48))
            btn.bind(on_release=action)
            buttons.add_widget(btn)
        self.add_widget(buttons)

        self.status = Label(text="Listo", size_hint_y=None, height=dp(30))
        self.add_widget(self.status)
        self.progress = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(18))
        self.add_widget(self.progress)

        scroll = ScrollView()
        self.log_box = Label(text="", size_hint_y=None, halign="left", valign="top")
        self.log_box.bind(width=lambda inst, value: setattr(inst, "text_size", (value - dp(12), None)))
        self.log_box.bind(texture_size=lambda inst, value: setattr(inst, "height", max(value[1] + dp(20), dp(200))))
        scroll.add_widget(self.log_box)
        self.add_widget(scroll)

    def open_folder_picker(self, target: TextInput):
        start = target.text.strip() or default_external_path()
        if not os.path.isdir(start):
            start = os.path.dirname(start) if os.path.isdir(os.path.dirname(start)) else "/"
        chooser = FileChooserListView(path=start, dirselect=True)
        content = BoxLayout(orientation="vertical")
        content.add_widget(chooser)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        select = Button(text="Seleccionar")
        cancel = Button(text="Cancelar")
        row.add_widget(select)
        row.add_widget(cancel)
        content.add_widget(row)
        popup = Popup(title="Seleccionar carpeta", content=content, size_hint=(0.95, 0.9))

        def choose(*_):
            selected = chooser.selection[0] if chooser.selection else chooser.path
            if os.path.isfile(selected):
                selected = os.path.dirname(selected)
            target.text = selected
            popup.dismiss()

        select.bind(on_release=choose)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def append_log(self, message: str):
        Clock.schedule_once(lambda _dt: self._append_log_ui(message))

    def _append_log_ui(self, message: str):
        old = self.log_box.text
        lines = (old + "\n" + message).strip().splitlines()
        self.log_box.text = "\n".join(lines[-150:])

    def set_progress(self, label: str, done: int, total: int):
        def update(_dt):
            self.status.text = f"{label}: {done}/{total}"
            self.progress.max = max(1, total)
            self.progress.value = done
        Clock.schedule_once(update)

    def on_permissions(self, *_):
        self.append_log(request_storage_permissions())

    def selected_factor(self):
        values = {"Automática": None, "75%": 0.75, "50%": 0.50, "40%": 0.40, "25%": 0.25}
        return values[self.factor.text]

    def _paths(self):
        source = os.path.abspath(self.source.text.strip())
        workspace = os.path.abspath(self.workspace.text.strip())
        frames = os.path.join(workspace, "frames")
        resized = os.path.join(workspace, "resized")
        sprites = os.path.join(workspace, "sprites")
        return source, workspace, frames, resized, sprites

    def run_job(self, name, func):
        if self.running:
            self.append_log("Ya hay un proceso ejecutándose.")
            return
        self.running = True
        self.progress.value = 0
        self.status.text = name
        self.append_log(f"\n=== {name} ===")

        def worker():
            try:
                func()
                self.append_log("Proceso terminado.")
            except Exception as exc:
                self.append_log(f"ERROR: {exc}")
            finally:
                Clock.schedule_once(lambda _dt: self._job_finished())

        threading.Thread(target=worker, daemon=True).start()

    def _job_finished(self):
        self.running = False
        self.status.text = "Listo"

    def run_extract(self, *_):
        source, _, frames, _, _ = self._paths()
        self.run_job("Extracción", lambda: extract_frames(source, frames, int(self.workers.text), self.set_progress, self.append_log))

    def run_resize(self, *_):
        _, _, frames, resized, _ = self._paths()
        self.run_job("Redimensión", lambda: resize_frames(frames, resized, self.selected_factor(), int(self.workers.text), self.set_progress, self.append_log))

    def run_generate(self, *_):
        _, _, frames, resized, sprites = self._paths()
        input_dir = resized if os.path.isdir(resized) and any(Path(resized).rglob("*.png")) else frames
        self.run_job("Generación", lambda: generate_spritesheets(input_dir, sprites, int(self.workers.text), self.set_progress, self.append_log))

    def run_full(self, *_):
        source, workspace, _, _, _ = self._paths()
        self.run_job(
            "Flujo completo",
            lambda: full_pipeline(source, workspace, self.selected_factor(), int(self.workers.text), self.set_progress, self.append_log),
        )

    def run_clean(self, *_):
        _, workspace, _, _, _ = self._paths()
        def clean():
            clean_directory(workspace)
            self.append_log(f"Salida limpiada: {workspace}")
        self.run_job("Limpieza", clean)


class FNFOptimizerApp(App):
    title = "FNF Optimizer"

    def build(self):
        return OptimizerRoot()


if __name__ == "__main__":
    FNFOptimizerApp().run()
