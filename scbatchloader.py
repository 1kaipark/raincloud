from raincloud import SCTrack, SCSet
from raincloud.shared import scrape_client_id, test_client_id
from raincloud.exceptions import TrackSetMismatchError

from PySide6 import QtWidgets as qtw
from PySide6.QtCore import Qt, QSize, QPoint
import PySide6.QtGui as qtg

import pandas as pd

import sys
import subprocess
import json
import os

from typing import Any, Iterator, Generator


if os.path.exists('client_id.txt'):
    cid = open('client_id.txt').read()
    if not test_client_id(cid):
        cid = scrape_client_id()
else:
    cid = scrape_client_id()

with open('client_id.txt', 'w+') as h:
    h.write(cid)



DEFAULT_CFG: dict = {
    'metadata': True,
    'player_cmd': 'audacious'
}

class SCASettingsDialog(qtw.QDialog):
    def __init__(self, parent: qtw.QWidget | None = None, cfg: dict = DEFAULT_CFG) -> None:
        super().__init__(parent)
        
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

class ResolvedViewer(qtw.QDialog):
    def __init__(self, parent: qtw.QWidget = None, text: str = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.text_view = qtw.QPlainTextEdit(text)
        self.text_view.setReadOnly(True)
        self.text_view.setMinimumSize(QSize(200, 200))
        self.close_button = qtw.QPushButton("close")
        self.close_button.clicked.connect(self.accept)

        lt = qtw.QVBoxLayout()
        lt.addWidget(self.text_view)
        lt.addWidget(self.close_button)

        self.setLayout(lt)

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
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_tree_cx_menu)

        self.download_button = qtw.QPushButton("download all tracks")
        self.player_button = qtw.QPushButton("open music player")

        self.download_button.clicked.connect(self.download_all_tracks)
        self.player_button.clicked.connect(self.open_player)


        btns_lt = qtw.QHBoxLayout()
        btns_lt.addWidget(self.player_button)
        btns_lt.addWidget(self.download_button)

        main_lt = qtw.QVBoxLayout()
        main_lt.addLayout(url_entry_lt)
        main_lt.addWidget(self.tree)
        main_lt.addLayout(btns_lt)

        self.setLayout(main_lt)

        # menu bar
        menubar = qtw.QMenuBar(self)
        file_menu = qtw.QMenu("file", self)

        delete_all_action = qtg.QAction("delete all tracks", self)
        delete_all_action.triggered.connect(self.delete_all_tracks)
        file_menu.addAction(delete_all_action)

        file_menu.addSeparator()

        settings_action = qtg.QAction("settings", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        refresh_streams_action = qtg.QAction("refresh streams", self)
        refresh_streams_action.triggered.connect(self.refresh_streams)
        file_menu.addAction(refresh_streams_action)

        file_menu.addSeparator()

        exit_action = qtg.QAction("exit", self)
        exit_action.triggered.connect(qtw.QApplication.instance().quit)
        file_menu.addAction(exit_action)

        file_menu.addSeparator()
        about_action = qtg.QAction("what is this?", self)
        about_action.triggered.connect(self.show_about)
        file_menu.addAction(about_action)

        menubar.addMenu(file_menu)
        main_lt.setMenuBar(menubar)

        self.setFixedSize(self.sizeHint())

    def add_url(self) -> None:
        url: str = self.url_entry.text()
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
            tracks = SCSet(self.client_id, url).tracks
            for sc_track in tracks:
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
        dst: str = qtw.QFileDialog.getExistingDirectory()
        dst = str(dst) # ???
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
        try:
            cmd = [self.cfg['player_cmd']]
            cmd.extend(self.urls)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL)
        except Exception as e:
            errormsg = qtw.QMessageBox(self)
            errormsg.setText(str(e))
            errormsg.exec()

    def tree_item_clicked(self, item: qtw.QTreeWidgetItem, column: int) -> None:
        idx = item.data(0, Qt.UserRole)
        try:
            ResolvedViewer(self, str(self.tracks[idx].resolved)).exec()
        #     from pyperclip import copy
        #     copy(self.urls[idx])
        #     success = qtw.QMessageBox(self)
        #     success.setWindowTitle("copied")
        #     success.setText("copied {} to clipboard".format(self.urls[idx]))
        #     success.exec()
        # except ImportError as e:
        #     error = qtw.QMessageBox(self)
        #     error.setWindowTitle("pyperclip not found")
        #     error.setText("ermm guys this is awkward")
        #     error.exec()
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
                self.track_counter = 0
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

    def open_tree_cx_menu(self, position: QPoint) -> None:

        # Should add option to copy permalink url, and download individual track.
        
        item = self.tree.itemAt(position)
        if item is not None:
            menu = qtw.QMenu()
            delete_action = qtg.QAction("delete", self)
            delete_action.triggered.connect(lambda _: self.delete_track(item))

            copy_action = qtg.QAction("copy stream URL", self)
            copy_action.triggered.connect(lambda _: self.copy_stream_url(item))

            copy_permalink_action = qtg.QAction("copy permalink URL", self)
            copy_permalink_action.triggered.connect(lambda _: self.copy_permalink_url(item))

            download_action = qtg.QAction("download single", self)
            download_action.triggered.connect(lambda _: self.download_single(item))

            menu.addAction(delete_action)
            menu.addAction(copy_action)
            menu.addAction(copy_permalink_action)
            menu.addAction(download_action)

            menu.exec(self.tree.viewport().mapToGlobal(position))

    def delete_track(self, item: qtw.QTreeWidgetItem) -> None:
        idx = item.data(0, Qt.UserRole)
        del self.tracks[idx]
        del self.urls[idx]
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

        # recalculate index
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setData(0, Qt.UserRole, i)
        
        self.track_counter -= 1

    def copy_stream_url(self, item: qtw.QTreeWidgetItem) -> None:
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

    def copy_permalink_url(self, item: qtw.QTreeWidgetItem) -> None:
        idx = item.data(0, Qt.UserRole)
        try:
            from pyperclip import copy
            permalink = self.tracks[idx].resolved['permalink_url']
            copy(permalink)
            success = qtw.QMessageBox(self)
            success.setWindowTitle("copied")
            success.setText("copied {} to clipboard".format(permalink))
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


    def download_single(self, item: qtw.QTreeWidgetItem) -> None:
        idx = item.data(0, Qt.UserRole)

        sc_track = self.tracks[idx]
        dst: str = qtw.QFileDialog.getExistingDirectory()
        dst = str(dst) # ???

        try:
            dl = sc_track.stream_download(self.cfg['metadata'])
            dl.write_to_file(dst)
            success = qtw.QMessageBox(self)
            success.setWindowTitle("downloaded track")
            success.setText("{} saved to {}".format(sc_track.title, dst))
            success.exec()
        except Exception as e:
            errormsg = qtw.QMessageBox(self)
            errormsg.setText(str(e))
            errormsg.exec()

    def refresh_streams(self) -> None:
        self.urls = [t.stream_url for t in self.tracks]
        info = qtw.QMessageBox(self)
        info.setWindowTitle("streams refreshed")
        info.setText("streaming URLs should be updated.") # How to refresh the tree view as well iteratively
        info.exec()

    def show_about(self) -> None:
        info = qtw.QMessageBox(self)
        info.setWindowTitle("about")
        info.setText("a simple Qt frontend for the raincloud SC api.")
        info.exec()



if __name__ == "__main__":
    if not os.path.exists('cfg.json'):
        with open('cfg.json', 'w+') as h:
            json.dump(DEFAULT_CFG, h)
    app = qtw.QApplication(sys.argv)
    launcher = SCBatchLoader(cid)
    launcher.show()
    sys.exit(app.exec())
