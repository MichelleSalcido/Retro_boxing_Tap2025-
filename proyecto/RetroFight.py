import sys
import os

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit, QMessageBox, QToolBar, QTableWidgetItem, QTableWidget, QSizePolicy
)
from PySide6.QtGui import QFont, QPixmap, QPalette, QBrush, QPainter, QLinearGradient, QColor
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# Rutas de recursos (asegúrate de que sean correctas)
RUTA_MUSICA = "proyecto/music/fondo2.mp3"
RUTA_FONDO = "proyecto/imagenes/fondo_inicio.jpg"

# ==================================================
# Clase base para ventanas con fondo de gradiente
# ==================================================
class GradientWindow(QMainWindow):
    def __init__(self, gradient_start="#1e1e50", gradient_end="#640064", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gradient_start = gradient_start
        self.gradient_end = gradient_end

    def paintEvent(self, event):
        painter = QPainter(self)
        gradiente = QLinearGradient(0, 0, self.width(), self.height())
        gradiente.setColorAt(0, QColor(self.gradient_start))
        gradiente.setColorAt(1, QColor(self.gradient_end))
        painter.fillRect(self.rect(), gradiente)
        super().paintEvent(event)

# ============================================
# Ventana para ingresar nombres de jugadores
# ============================================
class VentanaNombres(GradientWindow):
    def __init__(self, ventana_anterior):
        # Gradiente de azul oscuro a azul (en hexadecimal)
        super().__init__(gradient_start="#000428", gradient_end="#004e92")
        self.ventana_anterior = ventana_anterior
        self.setWindowTitle("Nombres de jugadores")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("INGRESE LOS NOMBRES DE LOS JUGADORES:")
        label.setFont(QFont("Arial", 26, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #ffffff;")

        self.input_jugador1 = QLineEdit()
        self.input_jugador1.setPlaceholderText("Jugador 1")
        self.input_jugador1.setFont(QFont("Arial", 18))
        self.input_jugador1.setAlignment(Qt.AlignCenter)
        self.input_jugador1.setStyleSheet("padding: 8px; border: 2px solid #bbb; border-radius: 5px;")

        self.input_jugador2 = QLineEdit()
        self.input_jugador2.setPlaceholderText("Jugador 2")
        self.input_jugador2.setFont(QFont("Arial", 18))
        self.input_jugador2.setAlignment(Qt.AlignCenter)
        self.input_jugador2.setStyleSheet("padding: 8px; border: 2px solid #bbb; border-radius: 5px;")

        btn_comenzar = QPushButton("Comenzar juego")
        btn_comenzar.setFont(QFont("Arial", 18, QFont.Bold))
        btn_comenzar.setStyleSheet("background-color: #4caf50; color: white; padding: 10px; border-radius: 5px;")
        btn_comenzar.clicked.connect(self.comenzar_juego)

        btn_regresar = QPushButton("Regresar")
        btn_regresar.setFont(QFont("Arial", 16))
        btn_regresar.setStyleSheet("background-color: #f44336; color: white; padding: 8px; border-radius: 5px;")
        btn_regresar.clicked.connect(self.regresar)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addSpacing(20)
        layout.addWidget(self.input_jugador1)
        layout.addWidget(self.input_jugador2)
        layout.addSpacing(20)
        layout.addWidget(btn_comenzar, alignment=Qt.AlignCenter)
        layout.addWidget(btn_regresar, alignment=Qt.AlignCenter)
        layout.addStretch()

        central.setLayout(layout)

    def comenzar_juego(self):
        nombre1 = self.input_jugador1.text()
        nombre2 = self.input_jugador2.text()
        if not nombre1 or not nombre2:
            QMessageBox.warning(self, "Error", "Ingrese ambos nombres")
            return

        QMessageBox.information(self, "Inicio", f"Comenzando partida entre {nombre1} y {nombre2}")
        # Se crea la ventana de Retro Fight (Ventanajuego) con los nombres ingresados.
        self.ventana_juego = Ventanajuego(ventana_principal=self.ventana_anterior)
        self.ventana_juego.show()
        self.ventana_anterior.hide()
        self.close()

    def regresar(self):
        self.close()
        self.ventana_anterior.show()

# ============================================
# Ventana del juego (con opciones de partida)
# ============================================
class Ventanajuego(GradientWindow):
    def __init__(self, ventana_principal=None):
        # Gradiente de azul oscuro a púrpura
        super().__init__(gradient_start="#1e1e50", gradient_end="#640064")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Retro Fight")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("LISTO PARA INICIAR?", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        btn_regreso = QPushButton("REGRESAR", self)
        btn_regreso.setFont(QFont("Arial", 16))
        btn_regreso.setFixedSize(200, 80)
        btn_regreso.setStyleSheet("background-color: #153999; color: white; border-radius: 5px;")
        btn_regreso.clicked.connect(self.regresar_principal)

        # Ahora, el botón "UNIRSE A PARTIDA" abre la ventana para pedir nombres.
        btn_unirse = QPushButton("UNIRSE A PARTIDA", self)
        btn_unirse.setFont(QFont("Arial", 16))
        btn_unirse.setFixedSize(200, 80)
        btn_unirse.setStyleSheet("background-color: #9c27b0; color: white; border-radius: 5px;")
        btn_unirse.clicked.connect(self.unirse_partida)

        # Puedes dejar "CREAR PARTIDA" si lo usas para otra acción (por ejemplo, crear partida sin nombres, según tus requerimientos)
        btn_crear = QPushButton("CREAR PARTIDA", self)
        btn_crear.setFont(QFont("Arial", 16))
        btn_crear.setFixedSize(200, 80)
        btn_crear.setStyleSheet("background-color: #2786b0; color: white; border-radius: 5px;")
        btn_crear.clicked.connect(self.crear_partida)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(btn_regreso, alignment=Qt.AlignCenter)
        layout.addWidget(btn_crear, alignment=Qt.AlignCenter)
        layout.addWidget(btn_unirse, alignment=Qt.AlignCenter)

        central.setLayout(layout)

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

    def unirse_partida(self):
        # Al presionar "UNIRSE A PARTIDA", se abre la ventana para ingresar nombres de jugadores.
        self.ventana_nombres = VentanaNombres(ventana_anterior=self)
        self.ventana_nombres.show()
        self.hide()

    def crear_partida(self):
        self.ventana_crear = Ventanacrearpartida(ventana_principal=self)
        self.ventana_crear.show()
        self.hide()

# ============================================
# Ventana para crear partida
# ============================================
class Ventanacrearpartida(GradientWindow):
    def __init__(self, ventana_principal=None):
        # Gradiente de naranja a dorado claro
        super().__init__(gradient_start="#FF7E5F", gradient_end="#FEB47B")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Unirse a una partida")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("Unirse a una nueva partida", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        btn_regreso = QPushButton("REGRESAR", self)
        btn_regreso.setFont(QFont("Arial", 16))
        btn_regreso.setFixedSize(200, 80)
        btn_regreso.setStyleSheet("background-color: #f44336; color: white; border-radius: 5px;")
        btn_regreso.clicked.connect(self.regresar_principal)

        btn_continuar = QPushButton("CONTINUAR", self)
        btn_continuar.setFont(QFont("Arial", 16))
        btn_continuar.setFixedSize(200, 80)
        btn_continuar.setStyleSheet("background-color: #4caf50; color: white; border-radius: 5px;")
        btn_continuar.clicked.connect(self.continuar)

        layouth = QHBoxLayout()
        layouth.addWidget(btn_regreso, alignment=Qt.AlignCenter)
        layouth.addWidget(btn_continuar, alignment=Qt.AlignCenter)

        layoutv = QVBoxLayout()
        layoutv.addWidget(label, alignment=Qt.AlignCenter)
        layoutv.addLayout(layouth)

        central.setLayout(layoutv)

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

    def continuar(self):
        QMessageBox.information(self, "Creando", "Creando partida")

# ============================================
# Ventana para unirse a una partida
# ============================================
class Ventanaunirsepartida(GradientWindow):
    def __init__(self, ventana_principal=None):
        # Gradiente de verde a un tono más claro
        super().__init__(gradient_start="#56ab2f", gradient_end="#a8e063")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Crear partida")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("CREAR NUEVA PARTIDA", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        btn_regreso = QPushButton("REGRESAR", self)
        btn_regreso.setFont(QFont("Arial", 16))
        btn_regreso.setFixedSize(200, 80)
        btn_regreso.setStyleSheet("background-color: #f44336; color: white; border-radius: 5px;")
        btn_regreso.clicked.connect(self.regresar_principal)

        btn_continuar = QPushButton("CONTINUAR", self)
        btn_continuar.setFont(QFont("Arial", 16))
        btn_continuar.setFixedSize(200, 80)
        btn_continuar.setStyleSheet("background-color: #4caf50; color: white; border-radius: 5px;")
        btn_continuar.clicked.connect(self.continuar)

        layouth = QHBoxLayout()
        layouth.addWidget(btn_regreso, alignment=Qt.AlignCenter)
        layouth.addWidget(btn_continuar, alignment=Qt.AlignCenter)

        layoutv = QVBoxLayout()
        layoutv.addWidget(label, alignment=Qt.AlignCenter)
        layoutv.addLayout(layouth)

        central.setLayout(layoutv)

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

    def continuar(self):
        QMessageBox.information(self, "Unirse", "Uniéndose a partida")

# ============================================
# Ventana de puntuaciones
# ============================================
class Ventanapuntuaciones(GradientWindow):
    def __init__(self, ventana_principal):
        # Gradiente de rojo a naranja
        super().__init__(gradient_start="#ee0979", gradient_end="#ff6a00")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Puntuaciones")
        self.setMinimumSize(400, 600)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("LISTA DE RECORDS", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        self.tabla_puntuaciones = QTableWidget(self)
        self.tabla_puntuaciones.setColumnCount(2)
        self.tabla_puntuaciones.setHorizontalHeaderLabels(["Jugador", "Puntuación"])
        self.tabla_puntuaciones.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_puntuaciones.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.tabla_puntuaciones.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.tabla_puntuaciones.setFixedSize(800, 400)
        self.tabla_puntuaciones.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.tabla_puntuaciones.setColumnWidth(0, 400)
        self.tabla_puntuaciones.setColumnWidth(1, 385)

        self.tabla_puntuaciones.setStyleSheet("""
        QTableWidget {
                background-color: rgba(0, 0, 0, 0);  /* fondo completamente transparente */
                color: white;
                border: none;
                gridline-color: white;
            }
            QHeaderView::section {
                background-color: rgba(0, 0, 0, 80);  /* encabezado semi transparente */
                color: white;
                font-weight: bold;
            }
            QTableWidget::item {
                background-color: rgba(255, 255, 255, 30);  /* celdas semi transparentes */
            }
        """)

        self.llenar_tabla_dummy()

        tabla_container = QWidget()
        tabla_layout = QHBoxLayout()
        tabla_layout.addStretch()
        tabla_layout.addWidget(self.tabla_puntuaciones)
        tabla_layout.addStretch()
        tabla_container.setLayout(tabla_layout)

        btn_regreso = QPushButton("REGRESAR", self)
        btn_regreso.setFont(QFont("Arial", 16))
        btn_regreso.setFixedSize(200, 80)
        btn_regreso.setStyleSheet("background-color: #dcc041; color: white; border-radius: 10px;")
        btn_regreso.clicked.connect(self.regresar_principal)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.tabla_puntuaciones)
        layout.setAlignment(Qt.AlignCenter) 
        layout.addWidget(tabla_container, alignment=Qt.AlignCenter)
        layout.addWidget(tabla_container, alignment=Qt.AlignCenter)
        layout.addWidget(btn_regreso, alignment=Qt.AlignCenter)

        central.setLayout(layout)

    def llenar_tabla_dummy(self):
        datos=[
            ("Jimena", 1200),
            ("Miechelle", 950)
        ]
        self.tabla_puntuaciones.setRowCount(len(datos))
        for fila, (nombre, puntaje) in enumerate(datos):
            self.tabla_puntuaciones.setItem(fila, 0, QTableWidgetItem(nombre))
            self.tabla_puntuaciones.setItem(fila, 1, QTableWidgetItem(str(puntaje)))

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

# ============================================
# Ventana de configuración
# ============================================
class Ventanaconfiguracion(GradientWindow):
    def __init__(self, ventana_principal=None):
        # Gradiente de rosa fuerte a rosa claro
        super().__init__(gradient_start="#ff0099", gradient_end="#ff66cc")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Configuración")
        self.setMinimumSize(900, 800)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("CONFIGURACION", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        btn_regreso = QPushButton("REGRESAR", self)
        btn_regreso.setFont(QFont("Arial", 16))
        btn_regreso.setFixedSize(200, 80)
        btn_regreso.setStyleSheet("background-color: #76c7f0; color: white; border-radius: 5px;")
        btn_regreso.clicked.connect(self.regresar_principal)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(btn_regreso, alignment=Qt.AlignCenter)

        central.setLayout(layout)

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

# ============================================
# Ventana principal (Menú de Boxing)
# ============================================
class Juego(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RETRO FIGTH")
        self.setMinimumSize(900, 800)
        self.showMaximized()

        # Mostrar mensaje de bienvenida
        dialogo_bienv = QMessageBox(self)
        dialogo_bienv.setWindowTitle("Bienvenido")
        dialogo_bienv.setText("BOXING\nJuego realizado por:\nJimena Muñoz\nMichelle Salcido")
        dialogo_bienv.exec()

        self.inicializar_musica()
        # Se conserva el fondo de imagen en la ventana principal, como estaba.
        self.set_background_image(RUTA_FONDO)

        central = QWidget()
        self.setCentralWidget(central)

        layout_vertical = QVBoxLayout()
        layout_horizontal = QHBoxLayout()

        label = QLabel("RETRO FIGTH", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 90, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        layout_vertical.addWidget(label)
        layout_vertical.addStretch()
        layout_vertical.addLayout(layout_horizontal)
        layout_vertical.addStretch()
        central.setLayout(layout_vertical)

        font_boton = QFont("Arial", 16, QFont.Bold)
        ancho_boton = 200
        alto_boton = 80

        # Al presionar "Iniciar juego" se abre directamente la ventana de Retro Fight.
        boton_iniciar = QPushButton("Iniciar juego")
        boton_iniciar.setFont(font_boton)
        boton_iniciar.setFixedSize(ancho_boton, alto_boton)
        boton_iniciar.setStyleSheet("background-color: #202123; color: white; border-radius: 10px;")
        boton_iniciar.clicked.connect(self.iniciar_juego)
        layout_horizontal.addWidget(boton_iniciar)

        boton_recrd = QPushButton("Records")
        boton_recrd.setFont(font_boton)
        boton_recrd.setFixedSize(ancho_boton, alto_boton)
        boton_recrd.setStyleSheet("background-color: #202123; color: white; border-radius: 10px;")
        boton_recrd.clicked.connect(self.puntuaciones)
        layout_horizontal.addWidget(boton_recrd)

        btn_configuracion = QPushButton("Configuración")
        btn_configuracion.setFont(font_boton)
        btn_configuracion.setFixedSize(ancho_boton, alto_boton)
        btn_configuracion.setStyleSheet("background-color: #202123; color: white; border-radius: 10px;")
        btn_configuracion.clicked.connect(self.configuracion)
        layout_horizontal.addWidget(btn_configuracion)

        self.toolbar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        btn_acerca = QPushButton("Acerca de")
        btn_acerca.setStyleSheet("background-color: #607d8b; color: white; border-radius: 5px;")
        btn_acerca.clicked.connect(self.acerca_de)
        self.toolbar.addWidget(btn_acerca)

    def set_background_image(self, path):
        fondo = QPixmap(path).scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(fondo))
        self.setPalette(palette)

    def inicializar_musica(self):
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(RUTA_MUSICA)))
        self.player.setLoops(QMediaPlayer.Infinite)
        self.player.play()

    def iniciar_juego(self):
        # Abre directamente la ventana de Retro Fight sin pedir nombres.
        self.ventana_juego = Ventanajuego(ventana_principal=self)
        self.ventana_juego.show()
        self.hide()

    def acerca_de(self):
        QMessageBox.information(self, "Acerca de", "BOXING\n Juego creado por las\n -increibles\n -talentosas\n -y creativas\n inges Michelle y Jimena  ")

    def puntuaciones(self):
        self.ventana_puntuaciones = Ventanapuntuaciones(ventana_principal=self)
        self.ventana_puntuaciones.show()
        self.hide()

    def configuracion(self):
        self.ventana_configuracion = Ventanaconfiguracion(ventana_principal=self)
        self.ventana_configuracion.show()
        self.hide()

# ============================================
# Bloque principal
# ============================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = Juego()
    ventana.show()
    sys.exit(app.exec())
