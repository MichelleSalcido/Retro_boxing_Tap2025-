import json
import sys
import os
import random
import socket
import sqlite3
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit, QMessageBox, QToolBar, QTableWidgetItem, QTableWidget,
    QSizePolicy, QProgressBar, QInputDialog
)
from PySide6.QtGui import (
    QFont, QPixmap, QPalette, QBrush, QPainter, QLinearGradient, 
    QColor, QIcon, QPen
)
from PySide6.QtCore import Qt, QUrl, QSize, QRect, QTimer, QTime, QPointF
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect
from PySide6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress
from PySide6.QtCore import QObject, Signal

# Rutas de recursos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Esto es la carpeta 'codigo'

RUTA_MUSICA = os.path.join(BASE_DIR, "music", "fondo2.mp3")
RUTA_FONDO = os.path.join(BASE_DIR, "imagenes", "fondo_inicio.jpg")
RUTA_ICONMUSICA = os.path.join(BASE_DIR, "imagenes", "musica.png")
CAMPANA = os.path.join(BASE_DIR, "music", "campana.mp3")
ROUND1 = os.path.join(BASE_DIR, "music", "round1.mp3")
ROUND2 = os.path.join(BASE_DIR, "music", "round2.mp3")
ROUND3 = os.path.join(BASE_DIR, "music", "round3.mp3")

# Sprites de jugadores
SPRITE_PLAYER1_IDLE = os.path.join(BASE_DIR, "imagenes", "player1_idle.png")
SPRITE_PLAYER1_PUNCH = os.path.join(BASE_DIR, "imagenes", "player1_punch.png")
SPRITE_PLAYER2_IDLE = os.path.join(BASE_DIR, "imagenes", "player2_idle.png")
SPRITE_PLAYER2_PUNCH = os.path.join(BASE_DIR, "imagenes", "player2_punch.png")

# ==================================================
# CLASE PARA OBTENER IP AUTOMATICAMENTE
# ==================================================
def obtener_ip_local():
    s= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

# ==================================================
# BASE DATOS
# ==================================================

def inicializar_db():
    con = sqlite3.connect("confiuracion.db")
    cur = con.cursor()
    cur. execute("""
        CREATE TABLE IF NOT EXISTS jugador (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT NOT NULL, 
        ip TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

def guardar_jugador(nombre, ip):
    con =sqlite3.connect("configuracion.db")
    cur = con.cursor()
    cur.execute("INSERT INTO jugador (nombre, ip), VALUES(?, ?)", (nombre, ip))
    con.commit()
    con.close()

def obtener_jugador():
    con = sqlite3.connect("configuracion.db")
    cur = con.cursor()
    cur.execute("SELECT nombre, ip FROM jugador ORDER BY id DESC LIMIT 1")
    jugador = cur.fetchone()
    con.close()
    return jugador if jugador else (None, None)

def obtener_configuracion_guardada():
    try:
        con = sqlite3.connect("configuracion.db")
        cur = con.cursor()
        cur.execute("SELECT nombre, ip FROM configuracion LIMIT 1")
        fila = cur.fetchone()
        con.close()
        if fila:
            return fila[0], fila[1]  # nombre, ip
    except Exception:
        pass
    return "", ""


def guardar_puntuacion(nombre, puntos):
    con = sqlite3.connect("configuracion.db")
    cur = con.cursor()
    cur.execute("""
            CREATE TABLE IF NOT EXISTS puntuaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                puntos INTEGER NOT NULL
            )
        """)
    cur.execute("INSERT INTO puntuaciones (nombre, puntos) VALUES (?, ?)", (nombre, puntos))
    con.commit()
    con.close()

# ==================================================
# CLASES PARA SERVIDOR
# ==================================================
class Servidorjuego(QObject):
    nueva_conexion = Signal(str)
    datos_recibidos = Signal(bytes)


    def __init__(self, port = 12345):
        super().__init__()
        self.server = QTcpServer()
        self.server.listen(QHostAddress.Any, port)
        self.server.newConnection.connect(self.aceptar_conexion)
        self.socket_cliente = None

    def aceptar_conexion(self):
        if self.socket_cliente is None:
            self.socket_cliente = self.server.nextPendingConnection()
            self.socket_cliente.readyRead.connect(self.leer_datos)
            direccion_ip= self.socket_cliente.peerAddress().toString()
            self.nueva_conexion.emit(direccion_ip)

    def leer_datos(self):
        if self.socket_cliente:
            datos =self.socket_cliente.readAll().data
            self.datos_recibidos.emit(datos)
            self.socket_cliente.write(b"Echo: " + datos)

    def enviar_datos(self, datos: bytes):
        if self.socket_cliente:
            self.socket_cliente.write(datos)

    def enviar_estado_juego(self, juego):
        if self.socket_cliente:
            data = {
                "type": "game_state",
                "player1": {
                    "x": juego.player1.x,
                    "y": juego.player1.y,
                    "health": juego.player1.health
                },
                "player2": {
                    "x": juego.player2.x,
                    "y": juego.player2.y,
                    "health": juego.player2.health
                }
            }
            self.enviar_datos(json.dumps(data).encode())

class Clientejuego(QObject):
    conectado = Signal()
    datos_recibidos = Signal(bytes)
    error_conexion = Signal(str)

    def __init__(self, host: str, port: int= 12345):
        super().__init__()
        self.socket = QTcpSocket()
        self.socket.connected.connect(self.conectado)
        self.socket.readyRead.connect(self._leer_datos)
        self.socket.errorOccurred.connect(self._manejar_error)

        self.socket.connectToHost(QHostAddress(host), port)

    def _conectado(self):
        self.conectado.emit()

    def _leer_datos(self):
        datos = self.socket.readAll().data()
        self.datos_recibidos.emit(datos)

    def _manejar_error(self, error):
        mensaje = self.socket.errorString()
        self.error_conexion.emit(mensaje)

    def enviar_datos(self, datos: bytes):
        if self.socket.state() == QTcpSocket.ConnectedState:
            self.socket.write(datos)

# ==================================================
# Clases del juego (Boxing)
# ==================================================
class Player:
    WIDTH =100
    HEIGHT = 150
    SPEED = 20
    PUNCH_RANGE = 60
    PUNCH_DURATION = 200  # ms
    SHAKE_DURATION = 300  # ms para sacudida tras golpe

    def __init__(self, x, y, color, keys, sprite_idle, sprite_punch, name=""):
        self.x = x
        self.y = y
        self.color = color
        self.keys = keys
        self.name = name
        self.width = Player.WIDTH
        self.height = Player.HEIGHT
        self.health = 100
        self.is_punching = False
        self.punch_start_time = None
        self.last_hit_time = None
        self.shake_offset = QPointF(0, 0)
        self.hit_flash_alpha = 0

        self.sprite_idle = self.load_sprite(sprite_idle, color)
        self.sprite_punch = self.load_sprite(sprite_punch, color.darker(150))

    def load_sprite(self, path, default_color):
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap.scaled(self.width, self.height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        pixmap = QPixmap(self.width, self.height)
        pixmap.fill(default_color)
        painter = QPainter(pixmap)
        painter.setPen(Qt.black)
        painter.drawRect(0, 0, self.width - 1, self.height - 1)
        painter.end()
        return pixmap

    def rect(self):
        return QRect(int(self.x), int(self.y), self.width, self.height)

    def punch_rect(self):
        if self.is_punching:
            if self.color == QColor(200, 50, 50):  # Jugador 1
                return QRect(int(self.x + self.width), int(self.y + self.height / 3),
                             self.PUNCH_RANGE, int(self.height / 3))
            else:  # Jugador 2
                return QRect(int(self.x - self.PUNCH_RANGE), int(self.y + self.height / 3),
                             self.PUNCH_RANGE, int(self.height / 3))
        return QRect(0, 0, 0, 0)

    def move(self, direction, bounds):
        if direction == 'left':
            self.x = max(bounds.left(), self.x - Player.SPEED)
        elif direction == 'right':
            self.x = min(bounds.right() - self.width, self.x + Player.SPEED)
        elif direction == 'up':
            self.y = max(bounds.top(), self.y - Player.SPEED)
        elif direction == 'down':
            self.y = min(bounds.bottom() - self.height, self.y + Player.SPEED)

    def start_punch(self):
        self.is_punching = True
        self.punch_start_time = QTime.currentTime()

    def update_punch(self):
        if self.is_punching:
            elapsed = self.punch_start_time.msecsTo(QTime.currentTime())
            if elapsed > Player.PUNCH_DURATION:
                self.is_punching = False
                self.punch_start_time = None

    def got_hit(self):
        self.last_hit_time = QTime.currentTime()
        self.hit_flash_alpha = 255

    def update_shake(self):
        if self.last_hit_time:
            elapsed = self.last_hit_time.msecsTo(QTime.currentTime())
            if elapsed > Player.SHAKE_DURATION:
                self.last_hit_time = None
                self.shake_offset = QPointF(0, 0)
                self.hit_flash_alpha = 0
            else:
                self.shake_offset = QPointF(random.randint(-3, 3), random.randint(-3, 3))
                self.hit_flash_alpha = max(0, 255 - int(255 * elapsed / Player.SHAKE_DURATION))


class ImpactEffect:
    MAX_RADIUS = 40
    DURATION = 400

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.start_time = QTime.currentTime()

    def elapsed(self):
        return self.start_time.msecsTo(QTime.currentTime())

    def is_alive(self):
        return self.elapsed() < ImpactEffect.DURATION

    def progress(self):
        return min(1.0, self.elapsed() / ImpactEffect.DURATION)

    def radius(self):
        return ImpactEffect.MAX_RADIUS * self.progress()

    def alpha(self):
        return 255 * (1 - self.progress())


class BoxingGame(QWidget):
    ROUND_TIME = 30

    def __init__(self, player1_name="Jugador 1", player2_name="Jugador 2"):
        super().__init__()
        self.setWindowTitle("Retro Fight - Partida")
        self.setFixedSize(1200, 700)
        self.setFocusPolicy(Qt.StrongFocus)

        self.player1 = Player(200, 300, QColor(200, 50, 50), {
            'left': Qt.Key_A,
            'right': Qt.Key_D,
            'up': Qt.Key_W,
            'down': Qt.Key_S,
            'punch': Qt.Key_Space
        }, SPRITE_PLAYER2_IDLE, SPRITE_PLAYER2_PUNCH, player1_name)

        self.player2 = Player(900, 300, QColor(50, 50, 200), {
            'left': Qt.Key_Left,
            'right': Qt.Key_Right,
            'up': Qt.Key_Up,
            'down': Qt.Key_Down,
            'punch': Qt.Key_Return
        },  SPRITE_PLAYER1_IDLE, SPRITE_PLAYER1_PUNCH, player2_name)

        self.keys_pressed = set()
        self.flash_color = None
        self.flash_alpha = 0
        self.impact_effects = []

        self.round_timer = BoxingGame.ROUND_TIME
        self.round_active = False
        self.round_count = 1
        self.max_rounds = 3
        self.score_p1 = 0
        self.score_p2 = 0
        self.setup_ui()

        # Temporizadores
        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.game_loop)
        self.game_timer.start(30)

        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_timer)

    def setup_ui(self):
        #barras de salud
        self.health_bar1 = QProgressBar(self)
        self.health_bar1.setGeometry(100, 30, 450, 35)
        self.health_bar1.setValue(self.player1.health)
        self.health_bar1.setFormat(f"{self.player1.name} - Vida: %p%")
        self.health_bar1.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: white;
                font-size: 16px;
                height: 30px;
            }
            QProgressBar::chunk {
                background-color: red;
                width: 10px;
            }
        """)

        self.health_bar2 = QProgressBar(self)
        self.health_bar2.setGeometry(650, 30, 450, 35)
        self.health_bar2.setValue(self.player2.health)
        self.health_bar2.setFormat(f"{self.player2.name} - Vida: %p%")
        self.health_bar2.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: white;
                font-size: 16px;
                height: 30px;
            }
            QProgressBar::chunk {
                background-color: blue;
                width: 10px;
            }
        """)


        self.timer_label = QLabel(f"Tiempo: {self.round_timer}", self)
        self.timer_label.setGeometry(500, 80, 200, 40)
        self.timer_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.timer_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0.5); border-radius: 10px;")
        self.timer_label.setAlignment(Qt.AlignCenter)

        #barra progreso tiempo
        self.time_progress = QProgressBar(self)
        self.time_progress.setGeometry(400, 130, 400, 25)
        self.time_progress.setRange(0, BoxingGame.ROUND_TIME)
        self.time_progress.setValue(self.round_timer)
        self.time_progress.setFormat("Tiempo restante")
        self.time_progress.setStyleSheet("""
                   QProgressBar {
                       border: 2px solid grey;
                       border-radius: 5px;
                       text-align: center;
                       color: white;
                       font-size: 14px;
                       height: 25px;
                       background-color: #222;
                   }
                   QProgressBar::chunk {
                       background-color: #ffa500;  /* naranja */
                       width: 10px;
                   }
               """)

        #boton inicio
        self.start_button = QPushButton("Iniciar Round", self)
        self.start_button.setGeometry(500, 600, 200, 50)
        self.start_button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 10px;
                        font-size: 18px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:disabled {
                        background-color: #cccccc;
                    }
                """)
        self.start_button.clicked.connect(self.start_round)

        #boton salir
        self.exit_button = QPushButton("Salir", self)
        self.exit_button.setGeometry(100, 600, 100, 50)
        self.exit_button.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 10px;
                        font-size: 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                """)
        self.exit_button.clicked.connect(self.close)

        self.round_label = QLabel("", self)
        self.round_label.setGeometry(300, 250, 600, 80)
        self.round_label.setAlignment(Qt.AlignCenter)
        self.round_label.setFont(QFont("Arial", 36, QFont.Bold))
        self.round_label.setStyleSheet("color: gold; background-color: rgba(0, 0, 0, 150); border-radius: 15px;")
        self.round_label.hide()

        self.campana_sound = QSoundEffect()
        self.campana_sound.setSource(QUrl.fromLocalFile(CAMPANA))
        self.campana_sound.setVolume(0.5)

    def start_round(self):
        self.round_timer = BoxingGame.ROUND_TIME
        self.round_active = True
        self.player1.health = 100
        self.player2.health = 100
        self.health_bar1.setValue(self.player1.health)
        self.health_bar2.setValue(self.player2.health)
        self.timer_label.setText(f"Tiempo: {self.round_timer}")

        self.time_progress.setMaximum(BoxingGame.ROUND_TIME)
        self.time_progress.setValue(self.round_timer)

        self.start_button.setEnabled(False)
        self.countdown_timer.start(1000)
        self.player1.x, self.player1.y = 200, 300
        self.player2.x, self.player2.y = 900, 300
        self.show_round_message(f"ROUND {self.round_count}", 2000)
        self.update()

    def update_timer(self):
        if self.round_timer > 0:
            self.round_timer -= 1
            self.timer_label.setText(f"Tiempo: {self.round_timer}")
            self.time_progress.setValue(self.round_timer)
        else:
            self.end_round("Tiempo terminado, ¡empate!")

    def end_round(self, result_text):
        self.round_active = False
        self.countdown_timer.stop()
        self.start_button.setEnabled(True)

        if result_text == f"{self.player1.name} gana!":
            self.score_p1 += 1
        elif result_text == f"{self.player2.name} gana!":
            self.score_p2 += 1

        self.campana_sound.play()

        if self.round_count >= self.max_rounds:  # Ya llegó al máximo
            self.end_game()
        else:
            self.round_count += 1  # Solo aumenta si no terminó el juego
            self.start_round()

        self.update_score_label()

    def end_game(self):
        self.show_final_result()  # Puedes reutilizar tu método que muestra el ganador
        self.start_button.setEnabled(False)

    def update_score_label(self):
        print(f"Ronda {self.round_count - 1} - {self.player1.name}: {self.score_p1} | {self.player2.name}: {self.score_p2}")

    def show_round_message(self, text, duration=2000):
        self.round_label.setText(text)
        self.round_label.show()
        QTimer.singleShot(duration, self.round_label.hide)

    def show_final_result(self):
        if self.score_p1 > self.score_p2:
            winner = self.player1.name
        elif self.score_p2 > self.score_p1:
            winner = self.player2.name
        else:
            winner = "¡Empate!"

        self.show_round_message(f"¡{winner} gana la partida!", 4000)
        self.start_button.setEnabled(False)
        QTimer.singleShot(4500, self.reset_game)

    def reset_game(self):
        self.round_count = 1
        self.score_p1 = 0
        self.score_p2 = 0
        self.start_button.setEnabled(True)

    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())

        if self.round_active:
            if event.key() == self.player1.keys['punch'] and not self.player1.is_punching:
                self.player1.start_punch()
            if event.key() == self.player2.keys['punch'] and not self.player2.is_punching:
                self.player2.start_punch()

    def keyReleaseEvent(self, event):
        if event.key() in self.keys_pressed:
            self.keys_pressed.remove(event.key())

    def game_loop(self):
        if not self.round_active:
            self.update()
            return

        bounds = self.rect()

        for player in (self.player1, self.player2):
            player.update_punch()
            player.update_shake()

        for key, direction in [(self.player1.keys['left'], 'left'),
                               (self.player1.keys['right'], 'right'),
                               (self.player1.keys['up'], 'up'),
                               (self.player1.keys['down'], 'down')]:
            if key in self.keys_pressed:
                self.player1.move(direction, bounds)

        for key, direction in [(self.player2.keys['left'], 'left'),
                               (self.player2.keys['right'], 'right'),
                               (self.player2.keys['up'], 'up'),
                               (self.player2.keys['down'], 'down')]:
            if key in self.keys_pressed:
                self.player2.move(direction, bounds)

        self.check_punches()

        #actualiza interfaz
        self.health_bar1.setValue(self.player1.health)
        self.health_bar2.setValue(self.player2.health)

        #condicion de victoria
        if self.player1.health <= 0:
            self.end_round(f"{self.player2.name} gana!")
        elif self.player2.health <= 0:
            self.end_round(f"{self.player1.name} gana!")

       #actualiza efectos
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 15)
        #filtrar efectos que aun esten activos
        self.impact_effects = [e for e in self.impact_effects if e.is_alive()]
        self.update()
#=============
#FALTA TERMINAR DE REVISAR
#=============
    def check_punches(self):
        if self.player1.is_punching and self.player1.punch_rect().intersects(self.player2.rect()):

            if not self.player2.last_hit_time or self.player2.last_hit_time.msecsTo(QTime.currentTime()) > 300:
                self.player2.health = max(0, self.player2.health - 3)
                self.player2.got_hit()
                self.create_impact(self.player1.punch_rect().center(), QColor(255, 100, 100))
                self.flash_screen(QColor(255, 100, 100))

        if self.player2.is_punching and self.player2.punch_rect().intersects(self.player1.rect()):
            if not self.player1.last_hit_time or self.player1.last_hit_time.msecsTo(QTime.currentTime()) > 300:
                self.player1.health = max(0, self.player1.health - 3)
                self.player1.got_hit()
                self.create_impact(self.player2.punch_rect().center(), QColor(100, 100, 255))
                self.flash_screen(QColor(100, 100, 255))

    def create_impact(self, pos, color):
        if pos.isValid():
            effect = ImpactEffect(pos.x(), pos.y())
            self.impact_color = color
            self.impact_effects.append(effect)

    def flash_screen(self, color):
        self.flash_color = color
        self.flash_alpha = 150

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            #fondo
            painter.fillRect(self.rect(), QColor(20, 20, 20))

            #efecto de destello
            if self.flash_alpha > 0 and self.flash_color:
                color = QColor(self.flash_color)
                color.setAlpha(self.flash_alpha)
                painter.fillRect(self.rect(), color)

            #lineas del ring
            for y in (200, 500):
                painter.setPen(QPen(QColor(200, 200, 200),3))
                painter.drawLine(50, y, self.width()-50, y)

            #dibuja jugadores
            for player in (self.player1, self.player2):
                offset = player.shake_offset
                r = player.rect().translated(offset.x(), offset.y())

                sprite = player.sprite_punch if player.is_punching else player.sprite_idle
                painter.drawPixmap(r, sprite)

                #efecto golpe
                if player.hit_flash_alpha > 0:
                    pen = QPen(player.color.lighter(200), 4)
                    c = player.color
                    pen.setColor(QColor(c.red(), c.green(), c.blue(), player.hit_flash_alpha))
                    painter.setPen(pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(r.adjusted(-5, -5, 5, 5))

            #efectos de impacto
            for effect in self.impact_effects:
                if effect.is_alive():
                    radius = effect.radius()
                    alpha = int(effect.alpha())
                    color = self.impact_color if hasattr(self, "impact_color") else QColor(255, 255, 255)
                    color.setAlpha(alpha)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawEllipse(QPointF(effect.x, effect.y), radius, radius)
            painter.end()
        except Exception as e:
            print(f"Error en paintEvent: {str(e)}")

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
    def __init__(self, ventana_anterior, is_local = True):
        # Gradiente de azul oscuro a azul (en hexadecimal)
        super().__init__(gradient_start="#000428", gradient_end="#004e92")
        self.ventana_anterior = ventana_anterior
        self.is_local = is_local
        self.setWindowTitle("Nombres de jugadores" if is_local else "Conectar a partida")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        central = QWidget()
        self.setCentralWidget(central)

        label_text = "INGRESE LOS NOMBRES DE LOS JUGADORES:" if is_local else "CONECTARSE A PARTIDA"
        label = QLabel(label_text, self)
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
        self.input_jugador2.setVisible(is_local)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP del servidor")
        self.ip_input.setFont(QFont("Arial", 18))
        self.ip_input.setAlignment(Qt.AlignCenter)
        self.ip_input.setStyleSheet("padding: 8px; border: 2px solid #bbb; border-radius: 5px;")
        self.ip_input.setVisible(not is_local)
        if not is_local:
            self.ip_input.setText(obtener_ip_local())

        btn_comenzar = QPushButton("Comenzar juego" if is_local else "Conectar", self)
        btn_comenzar.setFont(QFont("Arial", 18, QFont.Bold))
        btn_comenzar.setStyleSheet("background-color: #4caf50; color: white; padding: 10px; border-radius: 5px;")
        btn_comenzar.clicked.connect(self.comenzar_juego)

        btn_regresar = QPushButton("Regresar", self)
        btn_regresar.setFont(QFont("Arial", 16))
        btn_regresar.setStyleSheet("background-color: #f44336; color: white; padding: 8px; border-radius: 5px;")
        btn_regresar.clicked.connect(self.regresar)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addSpacing(20)
        layout.addWidget(self.input_jugador1)
        if is_local:
            layout.addWidget(self.input_jugador2)
        layout.addSpacing(20)
        layout.addWidget(btn_comenzar, alignment=Qt.AlignCenter)
        layout.addWidget(btn_regresar, alignment=Qt.AlignCenter)
        layout.addStretch()

        central.setLayout(layout)

    def comenzar_juego(self):
        nombre1 = self.input_jugador1.text()
        nombre2 = self.input_jugador2.text()
        if not nombre1:
            QMessageBox.warning(self, "Error", "Ingrese su nombre")
            return
        if self.is_local:
            nombre2 = self.input_jugador2.text().strip()
            if not nombre2:
                QMessageBox.warning(self, "Error", "Ingrese ambos nombres")
                return

            #juego local
            self.ventana_juego = BoxingGame(nombre1, nombre2)
            self.ventana_juego.show()
        else:
            # Network game
            ip_servidor = self.ip_input.text().strip()
            if not ip_servidor:
                QMessageBox.warning(self, "Error", "Ingrese la IP del servidor")
                return
            self.cliente = Clientejuego(ip_servidor, 12345)
            self.cliente.conectado.connect(self.on_conexion_exitosa)
            self.cliente.error_conexion.connect(self.on_error_conexion)

            QMessageBox.information(self, "Conectando", f"Conectando a {ip_servidor}...")

        # Se crea la ventana de juego con los nombres ingresados
        self.ventana_juego = BoxingGame(nombre1, nombre2)
        self.ventana_juego.show()
        self.ventana_anterior.hide()
        self.close()

    def on_conexion_exitosa(self):
        QMessageBox.information(self, "Éxito", "Conexión establecida")
        # Here you would create the network game window
        nombre = self.input_jugador1.text()
        self.ventana_juego = NetworkBoxingGame(nombre, self.cliente)
        self.ventana_juego.show()

    def on_error_conexion(self, mensaje):
        QMessageBox.critical(self, "Error", f"No se pudo conectar: {mensaje}")

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

        btn_unirse = QPushButton("UNIRSE A PARTIDA", self)
        btn_unirse.setFont(QFont("Arial", 16))
        btn_unirse.setFixedSize(200, 80)
        btn_unirse.setStyleSheet("background-color: #9c27b0; color: white; border-radius: 5px;")
        btn_unirse.clicked.connect(self.unirse_partida)

        btn_crear = QPushButton("CREAR PARTIDA", self)
        btn_crear.setFont(QFont("Arial", 16))
        btn_crear.setFixedSize(200, 80)
        btn_crear.setStyleSheet("background-color: #2786b0; color: white; border-radius: 5px;")
        btn_crear.clicked.connect(self.crear_partida_local)

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

    def crear_partida_local(self):
        self.ventana_nombres = VentanaNombres(ventana_anterior=self, is_local=True)
        self.ventana_nombres.show()
        self.hide()

    def unirse_partida(self):
        self.ventana_nombres = VentanaNombres(ventana_anterior=self, is_local=False)
        self.ventana_nombres.show()
        self.hide()

# ============================================
# clase juego en red
# ============================================
class NetworkBoxingGame(BoxingGame):
    def __init__(self, player_name, cliente):
        super().__init__(player_name, "Esperando oponente...")
        self.cliente = cliente
        self.player_name = player_name
        self.is_host = False
        self.opponent_name = ""

        # Connect signals
        self.cliente.datos_recibidos.connect(self.on_datos_recibidos)

        # Send player info to server
        self.send_player_info()

    def send_player_info(self):
        data = {
            "type": "player_info",
            "name": self.player_name
        }
        self.cliente.enviar_datos(json.dumps(data).encode())

    def on_datos_recibidos(self, datos):
        try:
            data = json.loads(datos.decode())
            if data["type"] == "player_info":
                self.opponent_name = data["name"]
                self.player2.name = self.opponent_name
                self.health_bar2.setFormat(f"{self.player2.name} - Vida: %p%")
            elif data["type"] == "game_state":
                self.update_game_state(data)
            elif data["type"] == "player_move":
                self.update_opponent_position(data)
            elif data["type"] == "player_punch":
                self.opponent_punch()

        except Exception as e:
            print("Error processing network data:", e)


    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        # Send movement data over network
        if event.key() in (self.player1.keys['left'], self.player1.keys['right'],
                           self.player1.keys['up'], self.player1.keys['down']):
            data = {
                "type": "player_move",
                "x": self.player1.x,
                "y": self.player1.y
            }
            self.cliente.enviar_datos(json.dumps(data).encode())

        # Send punch data over network
        if event.key() == self.player1.keys['punch']:
            data = {
                "type": "player_punch"
            }
            self.cliente.enviar_datos(json.dumps(data).encode())

        def update_opponent_position(self, data):
            self.player2.x = data["x"]
            self.player2.y = data["y"]
            self.update()

        def opponent_punch(self):
            self.player2.start_punch()
            self.update()

            def update_game_state(self, data):
                # Update both players' positions and health
                self.player1.x = data["player1"]["x"]
                self.player1.y = data["player1"]["y"]
                self.player1.health = data["player1"]["health"]

                self.player2.x = data["player2"]["x"]
                self.player2.y = data["player2"]["y"]
                self.player2.health = data["player2"]["health"]

                self.update()


# ============================================
# Ventana para unirse partida CORREGIR
# ============================================
class Ventanacrearpartida(GradientWindow):
    def __init__(self, ventana_principal=None):
        # Gradiente de naranja a dorado claro
        super().__init__(gradient_start="#FF7E5F", gradient_end="#FEB47B")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Unirse a una partida")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        self.nombre_jugador, self.ip_local = obtener_configuracion_guardada()

        central = QWidget()
        self.setCentralWidget(central)

        label = QLabel("Unirse a una nueva partida", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")

        label_info = QLabel(f"Jugador: {self.nombre_jugador} | IP Local: {self.ip_local}", self)
        label_info.setAlignment(Qt.AlignCenter)
        label_info.setFont(QFont("Arial", 14))
        label_info.setStyleSheet("color: white;")

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
        layoutv.addWidget(label_info, alignment=Qt.AlignCenter)
        layoutv.addLayout(layouth)

        central.setLayout(layoutv)

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

    def continuar(self):

        self.servidor = Servidorjuego(port=12345)
        self.servidor.nueva_conexion.connect(self.on_player_joined)
        QMessageBox.information(self, "CONECTANDO",f"{self.nombre_jugador} se conectará al servidor en {self.ip_local}")

    def on_player_joined(self, direccion_ip):
        QMessageBox.information(self, "JUGADOR CONECTADO", f"SE HA CONECTADO UN JUGADOR DESDE: {direccion_ip}")

# ============================================
# Ventana para CREAR a una partida CORREGIR
# ============================================
class Ventanaunirsepartida(GradientWindow):
    def __init__(self, ventana_principal=None):
        # Gradiente de verde a un tono más claro
        super().__init__(gradient_start="#56ab2f", gradient_end="#a8e063")
        self.ventana_principal = ventana_principal
        self.setWindowTitle("Crear partida")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        self.nombre_jugador, self.ip_local = obtener_configuracion_guardada()

        # (Opcional) Mostrar los datos en un QLabel para confirmar
        self.label_info = QLabel(f"Jugador: {self.nombre_jugador} | IP: {self.ip_local}")
        self.label_info.setAlignment(Qt.AlignCenter)
        self.label_info.setFont(QFont("Arial", 14))
        self.label_info.setStyleSheet("color: white;")

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
        layoutv.addWidget(self.label_info, alignment=Qt.AlignCenter)
        layoutv.addLayout(layouth)

        central.setLayout(layoutv)

    def regresar_principal(self):
        if self.ventana_principal is not None:
            self.ventana_principal.show()
        self.close()

    def continuar(self):
        self.servidor = Servidorjuego(port=12345)
        self.servidor.nueva_conexion.connect(self.on_player_joined)
        QMessageBox.information(self, "SERVIDOR",f"{self.nombre_jugador} ha iniciado el servidor en {self.ip_local}.\nEsperando jugador...")

    def on_conectado(self):
        QMessageBox.information(self, "Conexión", "Conectado al servidor")
        self.cliente.enviar_datos(b"Hola desde el cliente")

    def on_datos_recibidos(self, datos: bytes):
        QMessageBox.information(self, "Servidor", f"Datos recibidos: {datos.decode()}")

    def on_error_conexion(self, mensaje: str):
        QMessageBox.critical(self, "Error de conexión", mensaje)

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

        titulo = QLabel("LISTA DE RECORDS", self)
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Arial", 24, QFont.Bold))
        titulo.setStyleSheet("color: white; font-size: 30px; font-weight: bold;")

        self.label_puntuaciones = QLabel()
        self.label_puntuaciones.setAlignment(Qt.AlignTop)
        self.label_puntuaciones.setStyleSheet("color: white; font-size: 18px; margin: 20px;")

        btn_regreso = QPushButton("REGRESAR", self)
        btn_regreso.setFont(QFont("Arial", 16))
        btn_regreso.setFixedSize(200, 80)
        btn_regreso.setStyleSheet("background-color: #dcc041; color: white; border-radius: 10px;")
        btn_regreso.clicked.connect(self.regresar_principal)

        layout = QVBoxLayout()
        layout.addWidget(titulo)
        layout.addWidget(self.label_puntuaciones)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(btn_regreso, alignment=Qt.AlignCenter)

        central.setLayout(layout)

        self.mostrar_puntuaciones()

    def mostrar_puntuaciones(self):
        con = sqlite3.connect("configuracion.db")
        cur = con.cursor()
        cur.execute("""
                SELECT nombre, puntos FROM puntuaciones
                ORDER BY puntos DESC
                LIMIT 10
            """)
        resultados = cur.fetchall()
        con.close()

        if resultados:
            texto = ""
            for idx, (nombre, puntos) in enumerate(resultados, start=1):
                texto += f"{idx}. {nombre} - {puntos} puntos\n"
        else:
            texto = "No hay puntuaciones guardadas."

        self.label_puntuaciones.setText(texto)

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

        self.nombre_input = QLineEdit(self)
        self.nombre_input.setPlaceholderText("Ingresa tu nombre")
        self.nombre_input.setFont(QFont("Arial", 18))
        self.nombre_input.setFixedWidth(400)

        self.ip_input = QLineEdit(self)
        self.ip_input.setFont(QFont("Arial", 18))
        self.ip_input.setFixedWidth(400)
        self.ip_input.setReadOnly(True)
        self.ip_input.setText(obtener_ip_local())

        btn_guardar = QPushButton("GUARDAR", self)
        btn_guardar.setFont(QFont("Arial", 16))
        btn_guardar.setFixedSize(200, 80)
        btn_guardar.setStyleSheet("background-color: #4caf50; color: white; border-radius: 10px;")
        btn_guardar.clicked.connect(self.guardar_datos)

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

        btn_musica = QPushButton(self)
        btn_musica.setIcon(QIcon(RUTA_ICONMUSICA))
        btn_musica.setIconSize(QSize(200, 80))
        btn_musica.setStyleSheet("background-color: #76c7f0; color: white; border-radius: 5px;")
        btn_regreso.clicked.connect(self.apagar_musica)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.nombre_input, alignment=Qt.AlignCenter)
        layout.addWidget(self.ip_input, alignment=Qt.AlignCenter)
        layout.addWidget(btn_guardar, alignment=Qt.AlignCenter)
        layout.addWidget(btn_regreso, alignment=Qt.AlignCenter)
        layout.addWidget(btn_musica, alignment=Qt.AlignCenter)


        central.setLayout(layout)
    def guardar_datos(self):
        nombre = self.nombre_input.text().strip()
        ip = self.ip_input.text().strip()

        if not nombre:
            QMessageBox.warning(self, "Advertencia", "Debes de ingresar un nombre.")
            return
        con = sqlite3.connect("configuracion.db")
        cur = con.cursor()
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS configuracion (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        ip TEXT NOT NULL
                    )
                """)
        cur.execute("DELETE FROM configuracion")  # solo se guarda uno
        cur.execute("INSERT INTO configuracion (nombre, ip) VALUES (?, ?)", (nombre, ip))
        con.commit()
        con.close()

        QMessageBox.information(self, "Éxito", "Datos guardados correctamente.")

    def cargar_datos_guardados(self):
        try:
            conn = sqlite3.connect("configuracion.db")
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, ip FROM configuracion LIMIT 1")
            fila = cursor.fetchone()
            conn.close()

            if fila:
                self.nombre_input.setText(fila[0])
                self.ip_input.setText(fila[1])
        except Exception:
            pass

    def apagar_musica(self):
        if hasattr(self, "player") and self.player.isPlaying():
            self.player.stop()

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
        #dialogo_bienv = QMessageBox(self)
        #dialogo_bienv.setWindowTitle("Bienvenido")
        #dialogo_bienv.setText("Retro Fight\nJuego realizado por:\nJimena Muñoz\nMichelle Salcido")
        #dialogo_bienv.exec()

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
        self.audio_output.setVolume(50)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.player.play()

    def iniciar_juego(self):
        # Abre directamente la ventana de Retro Fight sin pedir nombres.
        try:
            self.ventana_juego = Ventanajuego(ventana_principal=self)
            self.ventana_juego.show()
            self.hide()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo iniciar el juego:\n{e}")
            print("Error al iniciar el juego:", e)

    def acerca_de(self):
        QMessageBox.information(self, "Acerca de", "Retro Fight\n Juego creado por las\n -Increibles\n -Talentosas\n -Y creativas\n Inges Michelle y Jimena  ")

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