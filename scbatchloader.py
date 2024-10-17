from raincloud import SCTrack, SCSet
from raincloud.shared import scrape_client_id, test_client_id
from raincloud.exceptions import TrackSetMismatchError

from PySide6 import QtWidgets as qtw
from PySide6.QtCore import Qt, QSize
import PySide6.QtGui as qtg

import pandas as pd

import sys
import subprocess
import json
import os

from typing import Any, Iterator, Generator

cid = open('client_id.txt').read()
if not test_client_id(cid):
    cid = scrape_client_id()

DEFAULT_CFG: dict = {
    'metadata': True,
    'player_cmd': 'audacious'
}

class SCASettingsDialog(qtw.QDialog):
    def __init__(self, parent: qtw.QWidget | None = None, cfg: dict = DEFAULT_CFG) -> None:
        super().__init__()
        
        self.setFixedSize(QSize(300, 100))

        self.cfg = cfg.copy()
        self.setWindowTitle("settings")
        self.setModal(True)

        self.metadata_checkbox = qtw.QCheckBox("dl+metadata")
        self.metadata_checkbox.setChecked(self.cfg['metadata'])

        self.player_cmd_label = qtw.QLabel("music player command")
        self.player_cmd_entry = qtw.QLineEdit(self.cfg['player_cmd'])

        self.ok_button = qtw.QPushButton("ok")
        self.cancel_button = qtw.QPushButton("cancel")

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        opts_lt = qtw.QFormLayout()
        opts_lt.addRow(self.metadata_checkbox)
        opts_lt.addRow(self.player_cmd_label, self.player_cmd_entry)

        btns_lt = qtw.QHBoxLayout()
        btns_lt.addWidget(self.ok_button)
        btns_lt.addWidget(self.cancel_button)

        main_lt = qtw.QVBoxLayout()
        main_lt.addLayout(opts_lt)
        main_lt.addLayout(btns_lt)

        self.setLayout(main_lt)

    def get_cfg(self) -> dict:
        self.cfg['metadata'] = self.metadata_checkbox.isChecked()
        self.cfg['player_cmd'] = self.player_cmd_entry.text()

        return self.cfg

        

class SCBatchLoader(qtw.QWidget):
    def __init__(self, client_id: str, cfg: dict = DEFAULT_CFG) -> None:
        super().__init__()
        self.client_id = client_id

        self.tracks: list["SCTrack" | None] = []
        self.urls: list[str | None] = []

        self.tracks_dt: pd.DataFrame = pd.DataFrame(columns=["track_name", "stream_url", "track_idx"])

        self.track_counter: int = 0

        self.cfg = cfg

        self.initUi()

    def initUi(self) -> None:
        self.url_entry_label = qtw.QLabel("SC url:")
        self.url_entry = qtw.QLineEdit()
        self.url_entry_sub = qtw.QPushButton("add SC URL")

        self.url_entry_sub.clicked.connect(self.add_url)

        url_entry_lt = qtw.QHBoxLayout()
        url_entry_lt.addWidget(self.url_entry_label)
        url_entry_lt.addWidget(self.url_entry)
        url_entry_lt.addWidget(self.url_entry_sub)

        self.tree = qtw.QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["track", "stream_url"])

        self.tree.itemDoubleClicked.connect(self.tree_item_clicked)

        self.download_button = qtw.QPushButton("download all tracks")
        self.player_button = qtw.QPushButton("open music player")

        self.download_button.clicked.connect(self.download_all_tracks)
        self.player_button.clicked.connect(self.open_player)


        btns_lt = qtw.QHBoxLayout()
        btns_lt.addWidget(self.download_button)
        btns_lt.addWidget(self.player_button)

        main_lt = qtw.QVBoxLayout()
        main_lt.addLayout(url_entry_lt)
        main_lt.addWidget(self.tree)
        main_lt.addLayout(btns_lt)

        self.setLayout(main_lt)

        # menu bar
        menubar = qtw.QMenuBar(self)
        file_menu = qtw.QMenu("file", self)

        create_csv_action = qtg.QAction("delete all tracks", self)
        create_csv_action.triggered.connect(self.delete_all_tracks)
        file_menu.addAction(create_csv_action)

        file_menu.addSeparator()

        settings_action = qtg.QAction("settings", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        exit_action = qtg.QAction("exit", self)
        exit_action.triggered.connect(qtw.QApplication.instance().quit)
        file_menu.addAction(exit_action)

        menubar.addMenu(file_menu)
        main_lt.setMenuBar(menubar)

        self.setFixedSize(self.sizeHint())

    def add_url(self) -> None:
        print("Add URL button clicked")
        url: str = self.url_entry.text()
        print(url)
        try:
            sc_track = SCTrack(self.client_id, url)
            if sc_track.resolved['permalink_url'] not in [t.resolved['permalink_url'] for t in self.tracks]:
                item = qtw.QTreeWidgetItem([sc_track.title, sc_track.stream_url])
                item.setData(0, Qt.UserRole, self.track_counter)

                self.track_counter += 1
                self.tree.addTopLevelItem(item)

                self.tracks.append(sc_track)
                self.urls.append(sc_track.stream_url)
        except TrackSetMismatchError as e:
            info = qtw.QMessageBox(self)
            info.setWindowTitle("parsing SCSet")
            info.setText("this may take a while")
            info.exec()
            set = SCSet(self.client_id, url)
            for sc_track in set.tracks:
                if sc_track.resolved['permalink_url'] not in [t.resolved['permalink_url'] for t in self.tracks]:
                    item = qtw.QTreeWidgetItem([sc_track.title, sc_track.stream_url])
                    item.setData(0, Qt.UserRole, self.track_counter)

                    self.track_counter += 1
                    self.tree.addTopLevelItem(item)

                    self.tracks.append(sc_track)
                    self.urls.append(sc_track.stream_url)
        except Exception as e:
            errormsg = qtw.QMessageBox(self)
            errormsg.setText(str(e))
            errormsg.exec()
        
        self.url_entry.setText("")

    def download_all_tracks(self) -> bool:
        print("downloading all tracks")
        dst: str = qtw.QFileDialog.getExistingDirectory()
        dst = str(dst) # ???
        print(dst)
        if len(dst) > 0:
            if len(self.tracks) == 0:
                info = qtw.QMessageBox(self)
                info.setWindowTitle("no tracks")
                info.setText("ermmmm")
                info.exec()
                return False
            for track in self.tracks:
                try:
                    dl = track.stream_download(self.cfg['metadata'])
                    dl.write_to_file(dst)
                except Exception as e:
                    errormsg = qtw.QMessageBox(self)
                    errormsg.setText(str(e))
                    errormsg.exec()

            success = qtw.QMessageBox(self)
            success.setWindowTitle("downloaded all tracks")
            success.setText("all tracks saved to {}".format(dst))
            success.exec()
            return True
        else:
            info = qtw.QMessageBox(self)
            info.setWindowTitle("cancelled")
            info.setText("title")
            info.exec()
            return False

    def open_player(self) -> None:
        print("opening player")
        cmd = [self.cfg['player_cmd']]
        cmd.extend(self.urls)
        print(cmd)
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL)

    def tree_item_clicked(self, item: qtw.QTreeWidgetItem, column: int) -> None:
        """when u double click a tree item, should open pygame window"""
        idx = item.data(0, Qt.UserRole)
        try:
            from pyperclip import copy
            copy(self.urls[idx])
            success = qtw.QMessageBox(self)
            success.setWindowTitle("copied")
            success.setText("copied {} to clipboard".format(self.urls[idx]))
            success.exec()
        except ImportError as e:
            error = qtw.QMessageBox(self)
            error.setWindowTitle("pyperclip not found")
            error.setText("ermm guys this is awkward")
            error.exec()
        except Exception as e:
            error = qtw.QMessageBox(self)
            error.setWindowTitle("error")
            error.setText(str(e))
            error.exec()

    
    def delete_all_tracks(self) -> None:
        if len(self.tracks) > 0:
            confirm = qtw.QMessageBox(self)
            confirm.setWindowTitle("are u sure")
            confirm.setText(f"this will remove all tracks")

            confirm.setStandardButtons(qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.No)
            button = confirm.exec()

            if button == qtw.QMessageBox.StandardButton.Yes:
                self.tree.clear()
                self.tracks = []
                self.urls = []
            elif button == qtw.QMessageBox.StandardButton.No:
                pass
        else:
            info = qtw.QMessageBox(self)
            info.setWindowTitle("yo")
            info.setText("no tracks loaded")
            info.exec()

    def open_settings(self) -> None:
        settings_dialog = SCASettingsDialog(self, self.cfg)
        if settings_dialog.exec():
            self.cfg = settings_dialog.get_cfg()
            with open('cfg.json', 'w+') as h:
                json.dump(self.cfg, h)


if __name__ == "__main__":
    if not os.path.exists('cfg.json'):
        with open('cfg.json', 'w+') as h:
            json.dump(DEFAULT_CFG, h)
    app = qtw.QApplication(sys.argv)
    launcher = SCBatchLoader(cid)
    launcher.show()
    sys.exit(app.exec())
