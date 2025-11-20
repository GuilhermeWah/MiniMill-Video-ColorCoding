from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QSlider
from mill_presenter.ui.widgets import VideoWidget
from mill_presenter.ui.playback_controller import PlaybackController

class MainWindow(QMainWindow):
    def __init__(self, config: dict, frame_loader=None, results_cache=None):
        super().__init__()
        self.config = config
        self.playback_controller = None
        self.setWindowTitle("MillPresenter")
        self.resize(1280, 720)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Video Widget
        self.video_widget = VideoWidget(config)
        layout.addWidget(self.video_widget, stretch=1)
        
        # Controls
        controls_layout = QHBoxLayout()
        layout.addLayout(controls_layout)
        
        self.play_button = QPushButton("Play")
        self.play_button.setCheckable(True)
        self.play_button.toggled.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        # We use sliderMoved for smooth scrubbing while dragging
        # and valueChanged for clicks, but we need to be careful with loops.
        # For now, let's use sliderMoved for the test requirement and direct interaction.
        # To support clicks, we might need to subclass or use valueChanged with signal blocking.
        # Let's start with sliderMoved as requested by the test plan, 
        # but actually the test uses sliderMoved.
        # I will add valueChanged support too, but carefully.
        self.slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.slider)
        
        # Toggles
        self.toggles = {}
        colors = self.config.get('overlay', {}).get('colors', {})
        
        for size in [4, 6, 8, 10]:
            btn = QPushButton(f"{size}mm")
            btn.setCheckable(True)
            btn.setChecked(True)
            
            # Apply color from config
            color_hex = colors.get(size, "#000000")
            # Simple styling: colored text
            btn.setStyleSheet(f"color: {color_hex}; font-weight: bold;")
            
            btn.toggled.connect(lambda checked, s=size: self.toggle_class(s, checked))
            controls_layout.addWidget(btn)
            self.toggles[size] = btn

        if frame_loader and results_cache:
            self.attach_playback_sources(frame_loader, results_cache)

    def toggle_class(self, size: int, visible: bool):
        if visible:
            self.video_widget.visible_classes.add(size)
        else:
            self.video_widget.visible_classes.discard(size)
        self.video_widget.update()

    def attach_playback_sources(self, frame_loader, results_cache):
        self.playback_controller = PlaybackController(
            frame_loader,
            results_cache,
            self.video_widget,
            parent=self,
        )
        
        # Configure slider range
        total_frames = getattr(frame_loader, "total_frames", 0)
        if total_frames > 0:
            self.slider.setRange(0, total_frames - 1)
            
        # Connect controller updates to slider
        self.playback_controller.frame_changed.connect(self._on_frame_changed)

    def _on_slider_moved(self, value):
        if self.playback_controller:
            self.playback_controller.seek(value)

    def _on_frame_changed(self, frame_index):
        # Update slider without triggering signals to avoid feedback loop
        self.slider.blockSignals(True)
        self.slider.setValue(frame_index)
        self.slider.blockSignals(False)

    def toggle_playback(self, playing: bool):
        if not self.playback_controller:
            # Reset button state if controller missing
            self.play_button.setChecked(False)
            return

        if playing:
            self.play_button.setText("Pause")
            self.playback_controller.play()
        else:
            self.play_button.setText("Play")
            self.playback_controller.pause()
