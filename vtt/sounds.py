"""Sounds tab: music playlists (one track at a time) and a soundboard of effect pads that can play over each other."""
import os, random, uuid
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QGridLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMenu, QMessageBox, QPushButton, QScrollArea, QSlider, QSplitter, QVBoxLayout,
                               QWidget)
from .panels import SOUND_FILTER, btn, check, combo, group, hint, hrow, slider

REPEAT = ["Repeat playlist", "Repeat track", "Play once"]
PLAYING = QMediaPlayer.PlaybackState.PlayingState


def mmss(ms):
    s = max(0, ms) // 1000
    return f"{s // 60}:{s % 60:02d}"


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


class SoundsPanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.playlists, self.current, self.playing_list, self.index = {"Ambience": []}, "Ambience", "Ambience", -1
        self.pads, self.pad_players, self.pad_buttons = [], {}, {}
        self.music, self.music_out = QMediaPlayer(), QAudioOutput()
        self.music.setAudioOutput(self.music_out)
        self.music.mediaStatusChanged.connect(self.media_status)
        self.music.positionChanged.connect(self.position)
        self.music.durationChanged.connect(lambda d: self.seek.setRange(0, d))
        self.music.playbackStateChanged.connect(lambda st: self.play_btn.setText("❚❚ Pause" if st == PLAYING else "▶ Play"))
        split = QSplitter()

        mw = QWidget()  # ---- music ----
        mv = QVBoxLayout(mw)
        f = group("Music", mv)
        self.pl_box = QComboBox()
        self.pl_box.currentTextChanged.connect(self.show_playlist)
        f.addRow("Playlist", hrow(self.pl_box, btn("New", self.new_playlist), btn("Rename", self.rename_playlist),
                                  btn("Delete", self.delete_playlist)))
        self.tracks = QListWidget()
        self.tracks.setDragDropMode(QAbstractItemView.InternalMove)  # drag to reorder
        self.tracks.model().rowsMoved.connect(self.sync_order)
        self.tracks.itemDoubleClicked.connect(lambda it: self.play_index(self.tracks.row(it), self.current))
        mv.addWidget(self.tracks, 1)
        mv.addWidget(hrow(btn("Add music…", self.add_tracks), btn("Remove", self.remove_track)))
        mv.addWidget(hint("Double-click a track to play it. Drag tracks to reorder."))
        self.now = QLabel("Nothing playing")
        self.now.setObjectName("title")
        self.seek = QSlider(Qt.Horizontal)
        self.seek.sliderReleased.connect(lambda: self.music.setPosition(self.seek.value()))
        self.time = QLabel("0:00 / 0:00")
        self.play_btn = btn("▶ Play", self.toggle_play)
        self.shuffle = check("Shuffle", False, lambda _: None)
        self.repeat = combo(REPEAT, REPEAT[0])
        self.music_vol = slider(0, 100, 60, lambda v: self.music_out.setVolume(v / 100))
        self.music_out.setVolume(0.6)
        for w in (self.now, hrow(self.seek, self.time), hrow(btn("⏮", self.prev), self.play_btn, btn("■ Stop", self.stop_music), btn("⏭", self.next)),
                  hrow(self.shuffle, self.repeat), hrow(QLabel("Music volume"), self.music_vol)):
            mv.addWidget(w)

        sw = QWidget()  # ---- soundboard ----
        sv = QVBoxLayout(sw)
        title = QLabel("Soundboard")
        title.setObjectName("title")
        sv.addWidget(title)
        host = QWidget()
        self.grid = QGridLayout(host)
        self.grid.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidget(host)
        scroll.setWidgetResizable(True)
        sv.addWidget(scroll, 1)
        self.fx_vol = slider(0, 100, 80, lambda _: self.apply_fx_volume())
        sv.addWidget(hrow(btn("Add sounds…", self.add_pads), btn("■ Stop all sounds", self.stop_pads)))
        sv.addWidget(hrow(QLabel("Effects volume"), self.fx_vol))
        sv.addWidget(hint("Click a pad to play it; sounds can overlap. Looping pads (↻) keep going until you click them again. "
                          "Right-click a pad to rename it, loop it, set its volume, change its file or remove it."))
        split.addWidget(mw)
        split.addWidget(sw)
        split.setSizes([520, 760])
        QVBoxLayout(self).addWidget(split)
        self.load({})

    # ---------- music ----------
    def fill_playlists(self):
        self.pl_box.blockSignals(True)
        self.pl_box.clear()
        self.pl_box.addItems(list(self.playlists))
        self.pl_box.setCurrentText(self.current)
        self.pl_box.blockSignals(False)
        self.show_playlist(self.current)

    def show_playlist(self, name):
        if name not in self.playlists:
            return
        self.current = name
        self.tracks.clear()
        for i, path in enumerate(self.playlists[name]):
            on = name == self.playing_list and i == self.index
            it = QListWidgetItem(("♪  " if on else "     ") + stem(path))
            it.setData(Qt.UserRole, path)
            it.setToolTip(path)
            self.tracks.addItem(it)

    def sync_order(self, *_):
        playing = self.playlists[self.playing_list][self.index] if self.current == self.playing_list and 0 <= self.index < len(self.playlists[self.current]) else None
        self.playlists[self.current] = [self.tracks.item(i).data(Qt.UserRole) for i in range(self.tracks.count())]
        if playing in self.playlists[self.current]:
            self.index = self.playlists[self.current].index(playing)  # keep pointing at the song that is playing

    def new_playlist(self):
        name, ok = QInputDialog.getText(self, "New playlist", "Name (e.g. Tavern, Battle, Dungeon):")
        if ok and name.strip() and name.strip() not in self.playlists:
            self.playlists[name.strip()] = []
            self.current = name.strip()
            self.fill_playlists()

    def rename_playlist(self):
        name, ok = QInputDialog.getText(self, "Rename playlist", "New name:", text=self.current)
        name = name.strip()
        if ok and name and name not in self.playlists:
            self.playlists = {name if k == self.current else k: v for k, v in self.playlists.items()}
            if self.playing_list == self.current:
                self.playing_list = name
            self.current = name
            self.fill_playlists()

    def delete_playlist(self):
        if len(self.playlists) == 1:
            return
        if QMessageBox.question(self, "Delete playlist", f"Delete the playlist '{self.current}'? (The music files stay.)") == QMessageBox.Yes:
            if self.playing_list == self.current:
                self.stop_music()
                self.index = -1
            del self.playlists[self.current]
            self.current = self.playing_list = next(iter(self.playlists))
            self.fill_playlists()

    def add_tracks(self, paths=None):
        paths = paths or QFileDialog.getOpenFileNames(self, "Add music", "", SOUND_FILTER)[0]
        self.playlists[self.current] += [p for p in paths if p not in self.playlists[self.current]]
        self.show_playlist(self.current)

    def remove_track(self):
        row = self.tracks.currentRow()
        if row < 0:
            return
        del self.playlists[self.current][row]
        if self.current == self.playing_list and row < self.index:
            self.index -= 1
        self.show_playlist(self.current)

    def play_index(self, i, playlist=None):
        self.playing_list = playlist or self.playing_list
        tracks = self.playlists.get(self.playing_list, [])
        if not tracks:
            return
        self.index = i % len(tracks)
        self.music.setSource(QUrl.fromLocalFile(tracks[self.index]))
        self.music.play()
        self.now.setText(f"♪  {stem(tracks[self.index])}   ·  {self.playing_list}")
        self.show_playlist(self.current)

    def toggle_play(self):
        if self.music.playbackState() == PLAYING:
            self.music.pause()
        elif self.music.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.music.play()
        else:
            row = self.tracks.currentRow()
            self.play_index(row if row >= 0 else max(0, self.index), self.current)

    def stop_music(self):
        self.music.stop()
        self.now.setText("Nothing playing")

    def next(self):
        tracks = self.playlists.get(self.playing_list, [])
        if not tracks:
            return
        if self.shuffle.isChecked() and len(tracks) > 1:
            self.play_index(random.choice([i for i in range(len(tracks)) if i != self.index]))
        else:
            self.play_index(self.index + 1)

    def prev(self):
        if self.music.position() > 3000:  # like most players: first press restarts the song
            self.music.setPosition(0)
        else:
            self.play_index(self.index - 1)

    def media_status(self, st):
        if st != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        mode, last = self.repeat.currentText(), self.index >= len(self.playlists.get(self.playing_list, [])) - 1
        if mode == "Repeat track":
            self.play_index(self.index)
        elif mode == "Play once" and last and not self.shuffle.isChecked():
            self.stop_music()
        else:
            self.next()

    def position(self, ms):
        if not self.seek.isSliderDown():
            self.seek.setValue(ms)
        self.time.setText(f"{mmss(ms)} / {mmss(self.music.duration())}")

    # ---------- soundboard ----------
    def add_pads(self, paths=None):
        paths = paths or QFileDialog.getOpenFileNames(self, "Add sound effects", "", SOUND_FILTER)[0]
        for p in paths:
            self.pads.append(dict(id=uuid.uuid4().hex[:8], name=stem(p), path=p, volume=100, loop=False))
        self.fill_pads()

    def fill_pads(self):
        while self.grid.count():
            self.grid.takeAt(0).widget().deleteLater()
        self.pad_buttons = {}
        for i, pad in enumerate(self.pads):
            b = QPushButton(("↻  " if pad["loop"] else "") + pad["name"])
            b.setMinimumHeight(70)
            b.setToolTip(pad["path"])
            b.clicked.connect(lambda _=False, pad=pad: self.play_pad(pad))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda pos, pad=pad, b=b: self.pad_menu(pad, b.mapToGlobal(pos)))
            self.pad_buttons[pad["id"]] = b
            self.grid.addWidget(b, i // 4, i % 4)
            self.pad_style(pad["id"])
        if not self.pads:
            self.grid.addWidget(hint("No sounds yet. Add some: door creaks, sword clashes, dragon roars, thunder…"), 0, 0)

    def player(self, pad):
        if pad["id"] not in self.pad_players or self.pad_players[pad["id"]][2] != pad["path"]:
            pl, out = QMediaPlayer(), QAudioOutput()
            pl.setAudioOutput(out)
            pl.setSource(QUrl.fromLocalFile(pad["path"]))
            pl.playbackStateChanged.connect(lambda _st, i=pad["id"]: self.pad_style(i))
            self.pad_players[pad["id"]] = (pl, out, pad["path"])
        return self.pad_players[pad["id"]]

    def play_pad(self, pad):
        pl, out, _ = self.player(pad)
        if pad["loop"] and pl.playbackState() == PLAYING:
            pl.stop()
            return
        pl.setLoops(QMediaPlayer.Loops.Infinite if pad["loop"] else 1)
        out.setVolume(pad["volume"] / 100 * self.fx_vol.value() / 100)
        pl.setPosition(0)  # clicking a playing one-shot restarts it
        pl.play()

    def pad_style(self, pid):
        b, p = self.pad_buttons.get(pid), self.pad_players.get(pid)
        if b is not None:
            b.setStyleSheet("background: #7a2020; border-color: #e0b84f;" if p and p[0].playbackState() == PLAYING else "")

    def pad_menu(self, pad, pos):
        m = QMenu(self)
        m.addAction("Rename…").triggered.connect(lambda: self.edit_pad(pad, "name"))
        loop = m.addAction("Loop (ambience)")
        loop.setCheckable(True)
        loop.setChecked(pad["loop"])
        loop.triggered.connect(lambda on: self.edit_pad(pad, "loop", on))
        m.addAction(f"Volume… ({pad['volume']}%)").triggered.connect(lambda: self.edit_pad(pad, "volume"))
        m.addAction("Change sound file…").triggered.connect(lambda: self.edit_pad(pad, "path"))
        m.addSeparator()
        m.addAction("Remove").triggered.connect(lambda: self.edit_pad(pad, "remove"))
        m.exec(pos)

    def edit_pad(self, pad, what, value=None):
        if what == "name":
            name, ok = QInputDialog.getText(self, "Rename sound", "Name:", text=pad["name"])
            if ok and name.strip():
                pad["name"] = name.strip()
        elif what == "loop":
            pad["loop"] = value
            if not value and pad["id"] in self.pad_players:
                self.pad_players[pad["id"]][0].stop()
        elif what == "volume":
            v, ok = QInputDialog.getInt(self, "Sound volume", "Volume (%):", pad["volume"], 0, 100)
            if ok:
                pad["volume"] = v
        elif what == "path":
            p, _ = QFileDialog.getOpenFileName(self, "Sound file", os.path.dirname(pad["path"]), SOUND_FILTER)
            if p:
                pad["path"] = p
        elif what == "remove":
            if pad["id"] in self.pad_players:
                self.pad_players.pop(pad["id"])[0].stop()
            self.pads.remove(pad)
        self.fill_pads()

    def apply_fx_volume(self):
        fx = self.fx_vol.value() / 100
        for pad in self.pads:
            if pad["id"] in self.pad_players:
                self.pad_players[pad["id"]][1].setVolume(pad["volume"] / 100 * fx)
        self.app.sfx_audio.setVolume(fx)  # sounds that triggered map objects play follow this too

    def stop_pads(self):
        for pl, _out, _p in self.pad_players.values():
            pl.stop()

    def stop_all(self):
        self.stop_music()
        self.stop_pads()

    # ---------- campaign ----------
    def state(self):
        return dict(playlists=self.playlists, current=self.current, pads=self.pads, music_volume=self.music_vol.value(),
                    fx_volume=self.fx_vol.value(), repeat=self.repeat.currentText(), shuffle=self.shuffle.isChecked())

    def load(self, st):
        self.stop_all()
        self.pad_players = {}
        self.playlists = st.get("playlists") or {"Ambience": []}
        self.current = self.playing_list = st.get("current") if st.get("current") in self.playlists else next(iter(self.playlists))
        self.index = -1
        self.pads = st.get("pads", [])
        self.music_vol.setValue(st.get("music_volume", 60))
        self.fx_vol.setValue(st.get("fx_volume", 80))
        self.repeat.setCurrentText(st.get("repeat", REPEAT[0]))
        self.shuffle.setChecked(st.get("shuffle", False))
        self.apply_fx_volume()
        self.fill_playlists()
        self.fill_pads()
