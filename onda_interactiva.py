from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.axes
    import matplotlib.figure

INIT = {
    'amplitud': 1.0,
    'frecuencia': 2.0,
    'fase': 0.0,
    'muestras': 1000,
    'ruido_std': 0.3,
    'ruido_activo': False,
    't_max': 2.0,
}

TIPOS_ONDA = ['Senoidal', 'Cuadrada', 'Triangular']
TIPOS_RUIDO = ['Gaussiano', 'Uniforme']


def generar_onda(t, amplitud, frecuencia, fase, tipo='Senoidal'):
    omega = 2 * np.pi * frecuencia
    if tipo == 'Senoidal':
        return amplitud * np.sin(omega * t + fase)
    elif tipo == 'Cuadrada':
        return amplitud * np.sign(np.sin(omega * t + fase))
    elif tipo == 'Triangular':
        return amplitud * (2 / np.pi) * np.arcsin(np.sin(omega * t + fase))
    return amplitud * np.sin(omega * t + fase)


def generar_ruido(n, std, tipo='Gaussiano'):
    if tipo == 'Gaussiano':
        return np.random.normal(0, std, n)
    elif tipo == 'Uniforme':
        return np.random.uniform(-std * np.sqrt(3), std * np.sqrt(3), n)
    return np.random.normal(0, std, n)


def calcular_snr(senal, ruido):
    p_senal = np.mean(senal ** 2)
    p_ruido = np.mean(ruido ** 2)
    if p_ruido == 0:
        return float('inf')
    return 10 * np.log10(p_senal / p_ruido)


class VisualizadorOndas:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Visualizador de Ondas Electromagnéticas')
        self.root.configure(bg='#1a1a2e')

        self.params: dict = dict(INIT)
        self.tipo_onda: str = 'Senoidal'
        self.tipo_ruido: str = 'Gaussiano'

        self.fig: matplotlib.figure.Figure
        self.ax: matplotlib.axes.Axes
        self.canvas: FigureCanvasTkAgg
        self.lbl_periodo: tk.Label
        self.lbl_snr: tk.Label
        self.var_amplitud: tk.DoubleVar
        self.var_frecuencia: tk.DoubleVar
        self.var_fase: tk.DoubleVar
        self.var_muestras: tk.DoubleVar
        self.var_ruido: tk.DoubleVar
        self.var_ruido_activo: tk.BooleanVar
        self.var_tipo_onda: tk.StringVar
        self.var_tipo_ruido: tk.StringVar

        self._build_ui()
        self._actualizar_grafica()

    def _build_ui(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)

        frame_graph = tk.Frame(self.root, bg='#1a1a2e')
        frame_graph.grid(row=0, column=0, sticky='nsew', padx=(10, 5), pady=10)
        frame_graph.rowconfigure(0, weight=1)
        frame_graph.columnconfigure(0, weight=1)

        self.fig, self.ax = plt.subplots(figsize=(9, 5), facecolor='#1a1a2e')
        self.ax.set_facecolor('#0f0f23')
        self.fig.tight_layout(pad=2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_graph)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

        frame_ctrl_outer = tk.Frame(self.root, bg='#16213e', relief='flat')
        frame_ctrl_outer.grid(row=0, column=1, sticky='nsew', padx=(5, 10), pady=10)
        frame_ctrl_outer.rowconfigure(0, weight=1)
        frame_ctrl_outer.columnconfigure(0, weight=1)

        ctrl_canvas = tk.Canvas(frame_ctrl_outer, bg='#16213e', highlightthickness=0)
        ctrl_canvas.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(frame_ctrl_outer, orient='vertical', command=ctrl_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        ctrl_canvas.configure(yscrollcommand=scrollbar.set)

        frame_ctrl = tk.Frame(ctrl_canvas, bg='#16213e')
        frame_ctrl.columnconfigure(0, weight=1)

        ctrl_window = ctrl_canvas.create_window((0, 0), window=frame_ctrl, anchor='nw')

        def _on_canvas_resize(event):
            ctrl_canvas.itemconfig(ctrl_window, width=event.width)
        ctrl_canvas.bind('<Configure>', _on_canvas_resize)

        def _on_frame_resize(event):
            ctrl_canvas.configure(scrollregion=ctrl_canvas.bbox('all'))
        frame_ctrl.bind('<Configure>', _on_frame_resize)

        def _on_mousewheel(event):
            ctrl_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        ctrl_canvas.bind_all('<MouseWheel>', _on_mousewheel)

        self._build_controls(frame_ctrl)

    def _label(self, parent, text, row, small=False):
        size = 9 if small else 11
        lbl = tk.Label(parent, text=text, bg='#16213e', fg='#a0aec0',
                       font=('Consolas', size), anchor='w')
        lbl.grid(row=row, column=0, sticky='ew', padx=12, pady=(8, 0))
        return lbl

    def _slider(self, parent, row, from_, to, init, resolution, var_name, label_text):
        self._label(parent, label_text, row)
        frame = tk.Frame(parent, bg='#16213e')
        frame.grid(row=row + 1, column=0, sticky='ew', padx=12, pady=(2, 0))
        frame.columnconfigure(0, weight=1)

        var = tk.DoubleVar(value=init)
        setattr(self, f'var_{var_name}', var)

        _ = tk.Label(frame, textvariable=var, bg='#16213e', fg='#63b3ed',
                    font=('Consolas', 10), width=6, anchor='e')
        _.grid(row=0, column=1, padx=(4, 0))

        slider = ttk.Scale(frame, from_=from_, to=to, orient='horizontal',
                           variable=var, command=lambda _: self._on_change())
        slider.grid(row=0, column=0, sticky='ew')
        slider.configure(style='Custom.Horizontal.TScale')

        return var

    def _build_controls(self, parent):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.Horizontal.TScale',
                        background='#16213e',
                        troughcolor='#2d3748',
                        sliderthickness=14,
                        sliderrelief='flat')

        title = tk.Label(parent, text='PARÁMETROS', bg='#16213e', fg='#63b3ed',
                         font=('Consolas', 12, 'bold'), anchor='center')
        title.grid(row=0, column=0, sticky='ew', padx=12, pady=(14, 4))

        sep = tk.Frame(parent, bg='#2d3748', height=1)
        sep.grid(row=1, column=0, sticky='ew', padx=12, pady=4)

        row = 2
        self.var_amplitud = self._slider(parent, row, 0.1, 5.0, self.params['amplitud'], 0.1, 'amplitud', 'Amplitud')
        row += 2
        self.var_frecuencia = self._slider(parent, row, 0.1, 20.0, self.params['frecuencia'], 0.1, 'frecuencia', 'Frecuencia (Hz)')
        row += 2

        self._label(parent, 'Período (s) — calculado', row)
        self.lbl_periodo = tk.Label(parent, text='0.50 s', bg='#16213e', fg='#68d391',
                                    font=('Consolas', 11), anchor='w')
        self.lbl_periodo.grid(row=row + 1, column=0, sticky='ew', padx=12)
        row += 2

        self.var_fase = self._slider(parent, row, 0.0, 2 * np.pi, self.params['fase'], 0.01, 'fase', 'Fase (rad)')
        row += 2
        self.var_muestras = self._slider(parent, row, 100, 5000, self.params['muestras'], 50, 'muestras', 'Puntos de muestreo')
        row += 2

        sep2 = tk.Frame(parent, bg='#2d3748', height=1)
        sep2.grid(row=row, column=0, sticky='ew', padx=12, pady=8)
        row += 1

        title2 = tk.Label(parent, text='RUIDO', bg='#16213e', fg='#fc8181',
                          font=('Consolas', 12, 'bold'), anchor='center')
        title2.grid(row=row, column=0, sticky='ew', padx=12)
        row += 1

        self.var_ruido = self._slider(parent, row, 0.0, 3.0, self.params['ruido_std'], 0.05, 'ruido', 'Intensidad de ruido (σ)')
        row += 2

        self.var_ruido_activo = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(parent, text='Activar ruido', variable=self.var_ruido_activo,
                             bg='#16213e', fg='#fc8181', activebackground='#16213e',
                             activeforeground='#fc8181', selectcolor='#2d3748',
                             font=('Consolas', 11), command=self._on_change)
        chk.grid(row=row, column=0, sticky='w', padx=12, pady=(4, 0))
        row += 1

        self._label(parent, 'SNR efectivo', row)
        self.lbl_snr = tk.Label(parent, text='— dB', bg='#16213e', fg='#f6e05e',
                                font=('Consolas', 11), anchor='w')
        self.lbl_snr.grid(row=row + 1, column=0, sticky='ew', padx=12)
        row += 2

        sep3 = tk.Frame(parent, bg='#2d3748', height=1)
        sep3.grid(row=row, column=0, sticky='ew', padx=12, pady=8)
        row += 1

        title3 = tk.Label(parent, text='TIPO DE ONDA', bg='#16213e', fg='#b794f4',
                          font=('Consolas', 12, 'bold'), anchor='center')
        title3.grid(row=row, column=0, sticky='ew', padx=12)
        row += 1

        self.var_tipo_onda = tk.StringVar(value='Senoidal')
        for tipo in TIPOS_ONDA:
            rb = tk.Radiobutton(parent, text=tipo, variable=self.var_tipo_onda, value=tipo,
                                bg='#16213e', fg='#e9d8fd', activebackground='#16213e',
                                activeforeground='#b794f4', selectcolor='#2d3748',
                                font=('Consolas', 10), command=self._on_change)
            rb.grid(row=row, column=0, sticky='w', padx=20)
            row += 1

        self._label(parent, 'TIPO DE RUIDO', row)
        row += 1
        self.var_tipo_ruido = tk.StringVar(value='Gaussiano')
        for tipo in TIPOS_RUIDO:
            rb = tk.Radiobutton(parent, text=tipo, variable=self.var_tipo_ruido, value=tipo,
                                bg='#16213e', fg='#e9d8fd', activebackground='#16213e',
                                activeforeground='#b794f4', selectcolor='#2d3748',
                                font=('Consolas', 10), command=self._on_change)
            rb.grid(row=row, column=0, sticky='w', padx=20)
            row += 1

        sep4 = tk.Frame(parent, bg='#2d3748', height=1)
        sep4.grid(row=row, column=0, sticky='ew', padx=12, pady=8)
        row += 1

        btn_reset = tk.Button(parent, text='↺  Restablecer valores',
                              command=self._reset,
                              bg='#2d3748', fg='#63b3ed', activebackground='#4a5568',
                              font=('Consolas', 10), relief='flat', cursor='hand2',
                              padx=8, pady=5)
        btn_reset.grid(row=row, column=0, sticky='ew', padx=12, pady=(0, 4))
        row += 1

        btn_guardar = tk.Button(parent, text='💾  Guardar imagen',
                                command=self._guardar,
                                bg='#2d3748', fg='#68d391', activebackground='#4a5568',
                                font=('Consolas', 10), relief='flat', cursor='hand2',
                                padx=8, pady=5)
        btn_guardar.grid(row=row, column=0, sticky='ew', padx=12, pady=(0, 12))

    def _on_change(self):
        self._actualizar_grafica()

    def _reset(self) -> None:
        self.var_amplitud.set(float(INIT['amplitud']))
        self.var_frecuencia.set(float(INIT['frecuencia']))
        self.var_fase.set(float(INIT['fase']))
        self.var_muestras.set(float(INIT['muestras']))
        self.var_ruido.set(float(INIT['ruido_std']))
        self.var_ruido_activo.set(bool(INIT['ruido_activo']))
        self.var_tipo_onda.set('Senoidal')
        self.var_tipo_ruido.set('Gaussiano')
        self._actualizar_grafica()

    def _guardar(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG', '*.png'), ('JPG', '*.jpg'), ('SVG', '*.svg')],
            title='Guardar imagen'
        )
        if ruta:
            self.fig.savefig(ruta, dpi=150, bbox_inches='tight', facecolor=self.fig.get_facecolor())
            messagebox.showinfo('Guardado', f'Imagen guardada en:\n{ruta}')

    def _actualizar_grafica(self) -> None:
        amp = float(round(self.var_amplitud.get(), 2))
        freq = float(round(self.var_frecuencia.get(), 2))
        fase = float(round(self.var_fase.get(), 3))
        muestras = int(self.var_muestras.get())
        ruido_std = float(round(self.var_ruido.get(), 3))
        ruido_activo = self.var_ruido_activo.get()
        tipo_onda = self.var_tipo_onda.get()
        tipo_ruido = self.var_tipo_ruido.get()

        periodo = float(round(1 / freq, 4)) if freq > 0 else 0.0
        self.lbl_periodo.config(text=f'{periodo} s')

        t = np.linspace(0, INIT['t_max'], muestras)
        senal = generar_onda(t, amp, freq, fase, tipo_onda)
        ruido = generar_ruido(muestras, ruido_std, tipo_ruido)

        self.ax.clear()
        self.ax.set_facecolor('#0f0f23')

        if ruido_activo and ruido_std > 0:
            self.ax.plot(t, senal + ruido, color='#fc8181', lw=1.2, alpha=0.75,
                         label='Señal con ruido', zorder=2)
            snr = calcular_snr(senal, ruido)
            self.lbl_snr.config(text=f'{snr:.1f} dB')
        else:
            self.lbl_snr.config(text='— dB')

        self.ax.plot(t, senal, color='#63b3ed', lw=2, label='Señal original', zorder=3)

        margen_y = max(amp * 0.3, ruido_std * 1.5 if ruido_activo else 0.3)
        self.ax.set_ylim(-(amp + margen_y), amp + margen_y)
        self.ax.set_xlim(0, INIT['t_max'])

        self.ax.set_xlabel('Tiempo (s)', color='#a0aec0', fontsize=10)
        self.ax.set_ylabel('Amplitud', color='#a0aec0', fontsize=10)
        self.ax.set_title(
            f'{tipo_onda}  |  A={amp}  f={freq} Hz  T={periodo} s  φ={fase:.2f} rad',
            color='#e2e8f0', fontsize=10, pad=10
        )
        self.ax.tick_params(colors='#718096', labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#2d3748')
        self.ax.grid(True, linestyle='--', alpha=0.25, color='#4a5568')
        self.ax.axhline(0, color='#4a5568', lw=0.8)
        self.ax.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='#2d3748',
                       labelcolor='#e2e8f0', fontsize=9)

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()


def main():
    root = tk.Tk()
    root.geometry('1100x680')
    root.minsize(800, 500)
    app = VisualizadorOndas(root)
    root.mainloop()


if __name__ == '__main__':
    main()