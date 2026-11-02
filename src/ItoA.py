import sys
import os
import shutil
import time
import traceback
import mimetypes

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QTextEdit, QFileDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QSlider, QComboBox, QListWidget, QFrame, QAbstractScrollArea,
    QStackedWidget, QStyle
)
from PyQt6.QtCore import Qt, QUrl, QTime, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon

# Multimedia imports for Video Playback
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

# Vertex AI imports
from google import genai
from google.genai import types

# --- MODERN PRODUCTION DARK STYLE ---
POLISHED_DARK_STYLE = """
QMainWindow { background-color: #0E0E10; }
QWidget { color: #EFEFEF; font-family: 'Segoe UI', -apple-system, Roboto, sans-serif; font-size: 13px; }

/* Group Boxes */
QGroupBox {
    background-color: #18181B; border: 1px solid #27272A;
    border-radius: 8px; margin-top: 1.2em; padding-top: 15px; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #A1A1AA; left: 10px; }

/* Buttons */
QPushButton {
    background-color: #27272A; color: #FFFFFF; border: 1px solid #3F3F46;
    border-radius: 6px; padding: 10px 15px; font-weight: 500;
}
QPushButton:hover { background-color: #3F3F46; border: 1px solid #FF9F1C; }
QPushButton:pressed { background-color: #18181B; }

/* Primary Accent Button */
QPushButton#primaryBtn { background-color: #FF9F1C; color: #000000; border: none; font-weight: 700; }
QPushButton#primaryBtn:hover { background-color: #FFB347; }
QPushButton#primaryBtn:pressed { background-color: #E68A00; }
QPushButton#primaryBtn:disabled { background-color: #555555; color: #888888; }

/* Media Controls */
QPushButton#mediaBtn { background-color: transparent; border: none; font-size: 16px; padding: 5px; }
QPushButton#mediaBtn:hover { color: #FF9F1C; }

/* Inputs & Dropdowns */
QTextEdit, QListWidget { background-color: #121214; border: 1px solid #27272A; border-radius: 6px; padding: 8px; selection-background-color: #FF9F1C; selection-color: black; }
QTextEdit:focus, QListWidget:focus { border: 1px solid #FF9F1C; }
QComboBox { background-color: #121214; border: 1px solid #27272A; border-radius: 6px; padding: 8px 12px; }
QComboBox:hover { border: 1px solid #FF9F1C; }
QComboBox::drop-down { border: none; padding-right: 10px; }
QComboBox QAbstractItemView { background-color: #18181B; border: 1px solid #27272A; selection-background-color: #FF9F1C; selection-color: black; }

/* Sliders */
QSlider::groove:horizontal { border: 1px solid #27272A; height: 6px; background: #121214; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #FF9F1C; border-radius: 3px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #FF9F1C; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
QSlider::handle:horizontal:hover { background: #FF9F1C; }

/* Media Slider (Slimmer) */
QSlider#mediaSlider::groove:horizontal { height: 4px; }
QSlider#mediaSlider::handle:horizontal { width: 10px; margin-top: -3px; margin-bottom: -3px; border-radius: 5px; }

/* Scrollbars */
QScrollBar:vertical { border: none; background: #121214; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #3F3F46; min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #FF9F1C; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
"""

# =========================================================================
# VEO GENERATOR THREAD CLASS
# =========================================================================
class VeoGeneratorThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # success_status, message_or_path

    def __init__(self, prompt, image_path, model_name):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path
        
        # Map our UI dropdown to the actual model name that works in your console
        if "Fast" in model_name:
            self.model_name = "veo-3.1-lite-generate-001"
        else:
            self.model_name = "veo-3.1-lite-generate-001" 

    def run(self):
        try:
            self.log_signal.emit("► Image loaded")
            self.log_signal.emit("► Prompt built")
            
            client = genai.Client(
                vertexai=True,
                project=[Your API TOken],
                location="us-central1",
            )
            
            mime_type, _ = mimetypes.guess_type(self.image_path)
            if not mime_type:
                mime_type = "image/jpeg"

            self.log_signal.emit(f"► Preparing {mime_type} for upload...")

            with open(self.image_path, "rb") as f:
                image_bytes = f.read()

            source = types.GenerateVideosSource(
                prompt=self.prompt,
                image=types.Image(
                    image_bytes=image_bytes,
                    mime_type=mime_type
                )
            )

            config = types.GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                duration_seconds=8,
                person_generation="allow_all",
                generate_audio=True,
                resolution="720p",
                seed=0,
            )

            self.log_signal.emit(f"► Submitting LRO request to {self.model_name}...")
            
            operation = client.models.generate_videos(
                model=self.model_name, 
                source=source, 
                config=config
            )

            check_count = 0
            while not operation.done:
                check_count += 1
                self.log_signal.emit(f"⏳ Rendering video on Google Cloud... (Check #{check_count})")
                time.sleep(10)
                operation = client.operations.get(operation)

            response = operation.result
            if not response:
                raise Exception("API returned an empty response.")

            generated_videos = response.generated_videos
            if not generated_videos:
                raise Exception("No videos were generated by Veo.")

            self.log_signal.emit("► Downloading MP4 to local disk...")

            output_dir = "generated_videos"
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"output_{int(time.time())}.mp4"
            output_path = os.path.join(output_dir, filename)

            video_bytes = generated_videos[0].video.video_bytes
            with open(output_path, "wb") as f:
                f.write(video_bytes)

            self.finished_signal.emit(True, output_path)

        except Exception as e:
            traceback.print_exc()
            self.finished_signal.emit(False, str(e))


class CinemaStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_path = None
        self.generated_video_path = None
        
        self.setWindowTitle("Cinema Studio - Bring Images To Life")
        self.resize(1450, 850)
        self.setStyleSheet(POLISHED_DARK_STYLE)
        
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(15, 15, 15, 15)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #27272A; }")
        
        root_layout.addWidget(splitter)

        self.build_left_panel(splitter)
        self.build_center_panel(splitter)
        self.build_right_panel(splitter)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 2)

    def build_left_panel(self, splitter):
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 15, 0)
        layout.setSpacing(15)

        # Header (Logo removed from here)
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        title = QLabel("🎬 Cinema Studio")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        subtitle = QLabel("Bring Images To Life")
        subtitle.setStyleSheet("color: #A1A1AA; font-size: 13px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)

        # Source Section
        source_group = QGroupBox("Source Management")
        source_layout = QVBoxLayout(source_group)
        
        self.upload_btn = QPushButton("📁 Upload Image")
        self.upload_btn.setObjectName("primaryBtn")
        self.upload_btn.clicked.connect(self.import_image)
        
        self.file_label = QLabel("No image selected")
        self.file_label.setStyleSheet("color: #71717A; font-style: italic;")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        source_layout.addWidget(self.upload_btn)
        source_layout.addWidget(self.file_label)

        self.prompt_box = QTextEdit()
        self.prompt_box.setPlaceholderText("Describe how the image should come alive...")
        self.prompt_box.setFixedHeight(140)
        source_layout.addWidget(self.prompt_box)

        layout.addWidget(source_group)

        # Model Section
        model_group = QGroupBox("Model Configuration")
        model_layout = QVBoxLayout(model_group)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Veo 3.1 Fast", "Veo 3.1 Quality"])
        model_layout.addWidget(self.model_combo)
        layout.addWidget(model_group)

        # Generate Button
        self.generate_btn = QPushButton("✨ Generate Video")
        self.generate_btn.clicked.connect(self.generate_video)
        self.generate_btn.setObjectName("primaryBtn")
        self.generate_btn.setMinimumHeight(45)
        layout.addWidget(self.generate_btn)

        # This invisible stretch pushes everything above it to the top, 
        # and everything below it to the very bottom!
        layout.addStretch()

        # --- LOGO AT BOTTOM LEFT ---
        self.logo_label = QLabel()
        logo_pixmap = QPixmap("your_logo.png") # <--- REPLACE WITH YOUR ACTUAL LOGO FILE NAME
        
        # Scale to fit nicely at the bottom
        scaled_logo = logo_pixmap.scaled(
            280, 80, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.logo_label.setPixmap(scaled_logo)
        
        # Centering it looks cleaner at the bottom, but you can change to AlignLeft if you prefer!
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        # Add a tiny bit of bottom margin so it doesn't scrape the floor of the window
        self.logo_label.setContentsMargins(0, 10, 0, 10)
        
        layout.addWidget(self.logo_label)
        # --- END OF LOGO SECTION ---

        splitter.addWidget(left)

    def build_center_panel(self, splitter):
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(10, 0, 10, 0)
        
        header = QLabel("Workspace: Image → Video")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #FF9F1C;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(20)

        # --- ORIGINAL IMAGE PANEL ---
        before_layout = QVBoxLayout()
        before_title = QLabel("Original Reference")
        before_title.setStyleSheet("color: #A1A1AA; font-weight: 600; padding-bottom: 5px;")
        before_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_preview = QLabel("Waiting for upload...")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumSize(250, 250)
        self.image_preview.setStyleSheet("border: 2px dashed #3F3F46; border-radius: 12px; background: #121214; color: #71717A;")

        before_layout.addWidget(before_title)
        before_layout.addWidget(self.image_preview, 1)

        # --- GENERATED VIDEO PANEL ---
        after_layout = QVBoxLayout()
        after_title = QLabel("Generated Output")
        after_title.setStyleSheet("color: #FF9F1C; font-weight: 600; padding-bottom: 5px;")
        after_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Use a QStackedWidget to swap between "Generating" text and the Video Player
        self.video_stack = QStackedWidget()
        
        # Stack Page 0: Placeholder
        self.video_placeholder = QLabel("Video will appear here")
        self.video_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_placeholder.setStyleSheet("border: 2px solid #3F3F46; border-radius: 12px; background: #000000; color: #71717A;")
        self.video_stack.addWidget(self.video_placeholder)

        # Stack Page 1: Active Video Player
        player_container = QWidget()
        player_layout = QVBoxLayout(player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(5)

        # Media Player Setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.7)
        self.media_player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000; border: 2px solid #FF9F1C; border-radius: 8px;")
        self.media_player.setVideoOutput(self.video_widget)

        # Media Controls Layout
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("mediaBtn")
        self.play_btn.clicked.connect(self.toggle_playback)
        
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("mediaSlider")
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_video_position)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #A1A1AA; font-family: monospace; font-size: 11px;")

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.position_slider)
        controls_layout.addWidget(self.time_label)

        player_layout.addWidget(self.video_widget, 1)
        player_layout.addLayout(controls_layout)
        
        self.video_stack.addWidget(player_container)

        # Connect media player signals to update UI
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.update_play_button)

        after_layout.addWidget(after_title)
        after_layout.addWidget(self.video_stack, 1)

        panels_layout.addLayout(before_layout, 1)
        panels_layout.addLayout(after_layout, 1)
        
        layout.addLayout(panels_layout, 1)
        splitter.addWidget(center)

    def build_right_panel(self, splitter):
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(15, 0, 0, 0)
        
        title = QLabel("Parameters")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FF9F1C;")
        layout.addWidget(title)

        # Settings
        settings_group = QGroupBox("Visual Settings")
        settings_layout = QVBoxLayout(settings_group)
        self.sliders = {}
        self.create_slider(settings_layout, "Brightness")
        self.create_slider(settings_layout, "Motion Intensity")
        self.create_slider(settings_layout, "Camera Movement")
        self.create_slider(settings_layout, "Animation Smoothness")
        self.create_slider(settings_layout, "Detail Level")

        style_label = QLabel("Render Style")
        style_label.setStyleSheet("color: #A1A1AA;")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Realistic", "Cinematic", "Anime", "Fantasy", "Documentary"])
        settings_layout.addWidget(style_label)
        settings_layout.addWidget(self.style_combo)
        layout.addWidget(settings_group)

        # History
        history_group = QGroupBox("Console & History")
        history_layout = QVBoxLayout(history_group)
        self.history_list = QListWidget()
        self.history_list.addItem("System initialized and ready.")
        history_layout.addWidget(self.history_list)
        layout.addWidget(history_group)

        # Export
        self.export_btn = QPushButton("🎬 Export MP4")
        self.export_btn.setMinimumHeight(45)
        self.export_btn.clicked.connect(self.export_video)
        layout.addWidget(self.export_btn)

        splitter.addWidget(right)

    def create_slider(self, parent_layout, label_text):
        container = QVBoxLayout()
        header_layout = QHBoxLayout()
        name_label = QLabel(label_text)
        val_label = QLabel("50")
        val_label.setStyleSheet("color: #FF9F1C; font-weight: bold;")
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(val_label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(50)
        slider.valueChanged.connect(lambda value, lbl=val_label: lbl.setText(str(value)))

        container.addLayout(header_layout)
        container.addWidget(slider)
        parent_layout.addLayout(container)
        self.sliders[label_text] = slider

    # ==========================
    # LOGIC & VIDEO GENERATION
    # ==========================
    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not file_path: return

        self.image_path = file_path
        filename = os.path.basename(file_path)
        
        self.file_label.setText(filename)
        self.file_label.setStyleSheet("color: #10B981; font-weight: bold;")
        self.image_preview.setStyleSheet("border: 2px solid #3F3F46; border-radius: 12px; background: #000000;")

        pixmap = QPixmap(file_path)
        self.image_preview.setPixmap(pixmap.scaled(
            self.image_preview.width(), self.image_preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        self.log_message(f"► Loaded image: {filename}")

    def generate_video(self):
        if not self.image_path:
            self.log_message("⚠️ Error: Please upload an image first.")
            return

        user_prompt = self.prompt_box.toPlainText()
        if not user_prompt.strip():
            self.log_message("⚠️ Error: Prompt cannot be empty.")
            return

        # Prepare UI for generating state
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("⏳ Generating...")
        self.export_btn.setEnabled(False)
        
        # Stop current video and show placeholder
        self.media_player.stop()
        self.video_stack.setCurrentIndex(0)
        self.video_placeholder.setStyleSheet("border: 2px solid #FF9F1C; border-radius: 12px; background: #18181B; color: #FF9F1C; font-size: 16px; font-weight: bold;")
        self.video_placeholder.setText("⚙ Generating Video...\n(This will take a few minutes)")

        # Combine parameters into prompt
        final_prompt = f"""{user_prompt}\nVisual settings: Brightness: {self.sliders["Brightness"].value()} Motion: {self.sliders["Motion Intensity"].value()} Camera: {self.sliders["Camera Movement"].value()} Smoothness: {self.sliders["Animation Smoothness"].value()} Detail: {self.sliders["Detail Level"].value()}\nStyle: {self.style_combo.currentText()}"""
        
        # Start Worker Thread
        self.worker = VeoGeneratorThread(final_prompt, self.image_path, self.model_combo.currentText())
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.on_generation_finished)
        self.worker.start()

    def on_generation_finished(self, success, result):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("✨ Generate Video")
        self.export_btn.setEnabled(True)

        if success:
            self.log_message("► Video generated successfully!")
            self.generated_video_path = result
            
            # Switch Stack to Video Player and load the file
            self.video_stack.setCurrentIndex(1)
            self.media_player.setSource(QUrl.fromLocalFile(result))
            self.media_player.play()
        else:
            self.log_message(f"⚠️ Generation Failed: {result}")
            self.video_stack.setCurrentIndex(0)
            self.video_placeholder.setStyleSheet("border: 2px solid #EF4444; border-radius: 12px; background: #18181B; color: #EF4444;")
            self.video_placeholder.setText("❌ Generation Failed")

    def export_video(self):
        if not self.generated_video_path or not os.path.exists(self.generated_video_path):
            self.log_message("⚠️ Error: No video generated yet.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Export Video", "output.mp4", "Video Files (*.mp4)")
        if save_path:
            try:
                shutil.copy2(self.generated_video_path, save_path)
                self.log_message(f"► Exported to {save_path}")
            except Exception as e:
                self.log_message(f"⚠️ Export Failed: {str(e)}")

    def log_message(self, message):
        self.history_list.addItem(message)
        self.history_list.scrollToBottom()

    # ==========================
    # MEDIA PLAYER CONTROLS
    # ==========================
    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_button(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def set_video_position(self, position):
        self.media_player.setPosition(position)

    def update_position(self, position):
        self.position_slider.setValue(position)
        self.update_time_label()

    def update_duration(self, duration):
        self.position_slider.setRange(0, duration)
        self.update_time_label()

    def update_time_label(self):
        current = self.media_player.position()
        total = self.media_player.duration()
        
        current_time = QTime(0, 0, 0).addMSecs(current).toString("mm:ss")
        total_time = QTime(0, 0, 0).addMSecs(total).toString("mm:ss")
        self.time_label.setText(f"{current_time} / {total_time}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CinemaStudio()
    window.show()
    sys.exit(app.exec())