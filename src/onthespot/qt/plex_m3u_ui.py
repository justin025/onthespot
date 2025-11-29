import os
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
                             QHeaderView, QComboBox, QScrollArea, QMessageBox, QFormLayout)
from ..api.plex import (plex_test_connection, plex_get_library_sections,
                        plex_import_m3u, plex_save_settings, plex_get_m3u_files)
from ..otsconfig import config
from ..runtimedata import get_logger

logger = get_logger('gui.plex_m3u_ui')


class PlexConnectionWorker(QThread):
    """Worker thread for testing Plex connection"""
    finished = pyqtSignal(bool, object)

    def __init__(self, server_url, token):
        super().__init__()
        self.server_url = server_url
        self.token = token

    def run(self):
        success = plex_test_connection(self.server_url, self.token)
        sections = None
        if success:
            sections = plex_get_library_sections(self.server_url, self.token)
        self.finished.emit(success, sections)


class PlexImportWorker(QThread):
    """Worker thread for importing M3U to Plex"""
    finished = pyqtSignal(bool, str)

    def __init__(self, server_url, token, library_section_id, m3u_path):
        super().__init__()
        self.server_url = server_url
        self.token = token
        self.library_section_id = library_section_id
        self.m3u_path = m3u_path

    def run(self):
        success = plex_import_m3u(self.server_url, self.token,
                                   self.library_section_id, self.m3u_path)
        filename = os.path.basename(self.m3u_path)
        self.finished.emit(success, filename)


def add_plex_settings_to_settings_tab(main_window):
    """
    Add Plex settings section to the settings scroll area
    """
    try:
        # Find the settings scroll area content widget
        scroll_area = main_window.settings_scroll_area
        scroll_content = scroll_area.widget()
        scroll_layout = scroll_content.layout()

        # Create Plex Settings GroupBox
        plex_group = QGroupBox("Plex Settings")
        plex_group.setObjectName("gb_plex_settings")
        plex_layout = QVBoxLayout()

        # Server URL
        url_layout = QHBoxLayout()
        url_label = QLabel("Plex Server URL:")
        url_label.setMinimumWidth(150)
        main_window.plex_server_url = QLineEdit()
        main_window.plex_server_url.setPlaceholderText("http://127.0.0.1:32400")
        url_layout.addWidget(url_label)
        url_layout.addWidget(main_window.plex_server_url)
        plex_layout.addLayout(url_layout)

        # Token
        token_layout = QHBoxLayout()
        token_label = QLabel("Plex Token:")
        token_label.setMinimumWidth(150)
        main_window.plex_token = QLineEdit()
        main_window.plex_token.setPlaceholderText("Your X-Plex-Token")
        main_window.plex_token.setEchoMode(QLineEdit.EchoMode.Password)
        token_layout.addWidget(token_label)
        token_layout.addWidget(main_window.plex_token)
        plex_layout.addLayout(token_layout)

        # Library Section ID
        section_layout = QHBoxLayout()
        section_label = QLabel("Library Section ID:")
        section_label.setMinimumWidth(150)
        main_window.plex_library_section_id = QLineEdit()
        main_window.plex_library_section_id.setPlaceholderText("e.g., 5")
        section_layout.addWidget(section_label)
        section_layout.addWidget(main_window.plex_library_section_id)
        plex_layout.addLayout(section_layout)

        # Test Connection Button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(lambda: test_plex_connection(main_window))
        plex_layout.addWidget(test_btn)

        # Help Text
        help_text = QLabel(
            "<small>To get your Plex token:<br>"
            "1. Open a media file in Plex Web App<br>"
            "2. Click '...' → 'Get Info' → 'View XML'<br>"
            "3. Copy the 'X-Plex-Token' from the URL<br>"
            "4. Copy the 'librarySectionID' for your music library</small>"
        )
        help_text.setWordWrap(True)
        plex_layout.addWidget(help_text)

        plex_group.setLayout(plex_layout)

        # Insert before the save button (which is at the end)
        scroll_layout.insertWidget(scroll_layout.count() - 1, plex_group)

        logger.info("Plex settings section added to Settings tab")

    except Exception as e:
        logger.error(f"Error adding Plex settings to Settings tab: {str(e)}")


def test_plex_connection(main_window):
    """Test Plex connection and update UI"""
    server_url = main_window.plex_server_url.text()
    token = main_window.plex_token.text()

    if not server_url or not token:
        main_window.show_popup_dialog("Please enter both Plex Server URL and Token")
        return

    main_window.show_popup_dialog("Testing Plex connection...", btn_hide=True)

    worker = PlexConnectionWorker(server_url, token)
    worker.finished.connect(lambda success, sections: on_connection_tested(
        main_window, success, sections))
    worker.start()

    # Store worker to prevent garbage collection
    main_window._plex_connection_worker = worker


def on_connection_tested(main_window, success, sections):
    """Handle Plex connection test result"""
    if success:
        if sections:
            section_names = [f"{s['title']} (ID: {s['id']})" for s in sections]
            msg = "✓ Connected to Plex successfully!\n\nMusic Libraries:\n• " + "\n• ".join(section_names)
        else:
            msg = "✓ Connected to Plex successfully!\n\nNo music libraries found."
        main_window.show_popup_dialog(msg)
    else:
        main_window.show_popup_dialog("✗ Failed to connect to Plex.\n\nPlease check your Server URL and Token.")


def create_m3u_import_tab(main_window):
    """
    Create and add M3U Import tab to the main window
    """
    try:
        # Create the M3U Import tab widget
        m3u_tab = QWidget()
        m3u_tab.setObjectName("m3u_import_tab")
        main_layout = QVBoxLayout()

        # Top section with controls
        controls_group = QGroupBox("Import Settings")
        controls_layout = QVBoxLayout()

        # Library Section Selection
        section_layout = QHBoxLayout()
        section_label = QLabel("Library Section ID:")
        section_label.setMinimumWidth(120)
        main_window.m3u_library_section = QLineEdit()
        main_window.m3u_library_section.setPlaceholderText("Enter Plex library section ID")
        section_layout.addWidget(section_label)
        section_layout.addWidget(main_window.m3u_library_section)
        controls_layout.addLayout(section_layout)

        # Buttons row
        buttons_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh M3U List")
        refresh_btn.setIcon(main_window.get_icon('retry'))
        refresh_btn.clicked.connect(lambda: refresh_m3u_list(main_window))
        import_all_btn = QPushButton("Import All to Plex")
        import_all_btn.setIcon(main_window.get_icon('download'))
        import_all_btn.clicked.connect(lambda: import_all_m3u_files(main_window))
        buttons_layout.addWidget(refresh_btn)
        buttons_layout.addWidget(import_all_btn)
        buttons_layout.addStretch()
        controls_layout.addLayout(buttons_layout)

        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        # M3U Files Table
        main_window.tbl_m3u_files = QTableWidget()
        main_window.tbl_m3u_files.setColumnCount(3)
        main_window.tbl_m3u_files.setHorizontalHeaderLabels(["Playlist Name", "File Path", "Actions"])
        main_window.tbl_m3u_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        main_window.tbl_m3u_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        main_window.tbl_m3u_files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        main_window.tbl_m3u_files.setColumnWidth(2, 100)
        main_window.tbl_m3u_files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        main_layout.addWidget(main_window.tbl_m3u_files)

        m3u_tab.setLayout(main_layout)

        # Add the tab to the main tab widget
        main_window.tabview.insertTab(3, m3u_tab, "M3U Import")

        # Load initial data
        refresh_m3u_list(main_window)

        logger.info("M3U Import tab created and added")

    except Exception as e:
        logger.error(f"Error creating M3U Import tab: {str(e)}")


def refresh_m3u_list(main_window):
    """Refresh the list of M3U files"""
    try:
        # Clear the table
        main_window.tbl_m3u_files.setRowCount(0)

        # Get M3U files
        m3u_files = plex_get_m3u_files()

        if not m3u_files:
            logger.info("No M3U files found")
            return

        # Populate the table
        for m3u_path in m3u_files:
            row = main_window.tbl_m3u_files.rowCount()
            main_window.tbl_m3u_files.insertRow(row)

            # Playlist name (from filename)
            filename = os.path.basename(m3u_path)
            playlist_name = os.path.splitext(filename)[0]
            main_window.tbl_m3u_files.setItem(row, 0, QTableWidgetItem(playlist_name))

            # File path
            main_window.tbl_m3u_files.setItem(row, 1, QTableWidgetItem(m3u_path))

            # Import button
            import_btn = QPushButton("Import")
            import_btn.setIcon(main_window.get_icon('download'))
            import_btn.clicked.connect(lambda checked, path=m3u_path: import_single_m3u(main_window, path))
            main_window.tbl_m3u_files.setCellWidget(row, 2, import_btn)

        logger.info(f"Loaded {len(m3u_files)} M3U files")

    except Exception as e:
        logger.error(f"Error refreshing M3U list: {str(e)}")
        main_window.show_popup_dialog(f"Error loading M3U files: {str(e)}")


def import_single_m3u(main_window, m3u_path):
    """Import a single M3U file to Plex"""
    try:
        server_url = config.get("plex_server_url")
        token = config.get("plex_token")
        library_section_id = main_window.m3u_library_section.text() or config.get("plex_library_section_id")

        if not server_url or not token:
            main_window.show_popup_dialog("Please configure Plex settings first (Settings tab)")
            main_window.tabview.setCurrentIndex(2)  # Switch to Settings tab
            return

        if not library_section_id:
            main_window.show_popup_dialog("Please enter a Library Section ID")
            return

        filename = os.path.basename(m3u_path)
        main_window.show_popup_dialog(f"Importing {filename} to Plex...", btn_hide=True)

        worker = PlexImportWorker(server_url, token, library_section_id, m3u_path)
        worker.finished.connect(lambda success, name: on_import_finished(main_window, success, name))
        worker.start()

        # Store worker to prevent garbage collection
        main_window._plex_import_worker = worker

    except Exception as e:
        logger.error(f"Error importing M3U: {str(e)}")
        main_window.show_popup_dialog(f"Error: {str(e)}")


def import_all_m3u_files(main_window):
    """Import all M3U files to Plex"""
    try:
        m3u_files = plex_get_m3u_files()
        if not m3u_files:
            main_window.show_popup_dialog("No M3U files found")
            return

        server_url = config.get("plex_server_url")
        token = config.get("plex_token")
        library_section_id = main_window.m3u_library_section.text() or config.get("plex_library_section_id")

        if not server_url or not token:
            main_window.show_popup_dialog("Please configure Plex settings first (Settings tab)")
            main_window.tabview.setCurrentIndex(2)  # Switch to Settings tab
            return

        if not library_section_id:
            main_window.show_popup_dialog("Please enter a Library Section ID")
            return

        main_window.show_popup_dialog(f"Importing {len(m3u_files)} playlists to Plex...", btn_hide=True)

        success_count = 0
        fail_count = 0

        for m3u_path in m3u_files:
            if plex_import_m3u(server_url, token, library_section_id, m3u_path):
                success_count += 1
            else:
                fail_count += 1

        msg = f"Import completed!\n\nSuccessful: {success_count}\nFailed: {fail_count}"
        main_window.show_popup_dialog(msg)

    except Exception as e:
        logger.error(f"Error importing all M3U files: {str(e)}")
        main_window.show_popup_dialog(f"Error: {str(e)}")


def on_import_finished(main_window, success, filename):
    """Handle import completion"""
    if success:
        main_window.show_popup_dialog(f"✓ Successfully imported:\n{filename}")
    else:
        main_window.show_popup_dialog(f"✗ Failed to import:\n{filename}")
