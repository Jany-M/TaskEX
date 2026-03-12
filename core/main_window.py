import logging

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QShortcut, QKeySequence, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QScrollArea, QFrame

from config.settings import TITLE, TITLE_DESCRIPTION, CREDITS, VERSION
from core.app_settings import Settings
from core.controllers.emulator_controller import handle_scan_general_button
from core.instance_manager import setup_port_display_table, reload_ports
from core.menu_button import connect_buttons, initialize_instances
from core.ui_functions import UIFunctions
from db.db_setup import init_db, get_session
from db.models import Instance
from features.ui.join_rally_ui import refresh_join_rally_monsters_for_all_instances
from gui.controllers.bm_blackmarket_controller import init_bm_blackmarket_ui
from gui.controllers.bm_bubbles_controller import init_bm_bubbles_ui
from gui.controllers.bm_monsters_controller import init_bm_monster_ui
from gui.controllers.bm_scan_generals_controller import init_scan_general_ui, update_scan_console
from gui.generated.ui_main import Ui_MainWindow
from utils.adb_manager import ADBManager
from utils.image_recognition_utils import setup_tesseract


# os.environ["QT_FONT_DPI"] = "96" # FIX Problem for High DPI and Scale above 100%


class MainWindow(QMainWindow):
    # Define Signals
    scan_general_console = Signal(str)
    def __init__(self, splash_screen):
        super(MainWindow, self).__init__()


        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.widgets = self.ui
        self.worker_refs = {} # Store references to profile workers here

        # Start initialization when splash screen emits the startup signal.
        splash_screen.load_signal.connect(lambda: self.perform_initialization(splash_screen))

    def perform_initialization(self, splash_screen):
        # print("Loading...")
        # List of initialization steps with corresponding messages
        init_steps = [
            ("Loading Configurations", self.load_configurations),
            ("Loading UI Settings",self.load_ui_settings),
            ("Initializing Instances", self.init_instance),
            ("Initializing ADB", self.init_adb),
            ("Finalizing Setup", self.finalize_setup)
        ]

        splash_screen.ui.progressBar.setMaximum(len(init_steps))


        for i, (message, function) in enumerate(init_steps):
            QTimer.singleShot(i * 1000,
                              lambda msg=message, func=function, idx=i + 1: self.load_step(splash_screen, msg, func,
                                                                                        idx))

    def load_configurations(self):
        # Initialize the database and create tables
        init_db()


    def load_ui_settings(self):
        # USE CUSTOM TITLE BAR | USE AS "False" FOR MAC OR LINUX
        # ///////////////////////////////////////////////////////////////
        Settings.ENABLE_CUSTOM_TITLE_BAR = True

        # APPLY TEXTS
        # ///////////////////////////////////////////////////////////////
        self.setWindowTitle(TITLE)
        self.widgets.titleLeftApp.setText(TITLE)
        self.widgets.titleLeftDescription.setText(TITLE_DESCRIPTION)
        # widgets.titleRightInfo.setText(Settings.DESCRIPTION)
        self.widgets.creditsLabel.setText(CREDITS)
        self.widgets.version.setText(VERSION)

        # Create a scroll area for the topMenu
        self.scroll_area = QScrollArea(self.widgets.leftMenuFrame)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        # self.scroll_area.setFrameShadow(QFrame.Plain)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("background-color: rgb(37, 41, 48);")
        self.scroll_area.setWidget(self.widgets.topMenu)

        # Get the layout of leftMenuFrame
        layout = self.widgets.leftMenuFrame.layout()
        self.widgets.topMenu.layout().setAlignment(Qt.Alignment.AlignTop)

        # Add widgets to the layout in the desired order
        layout.addWidget(self.widgets.toggleBox)  # Toggle box at the top
        layout.addWidget(self.scroll_area)  # Scroll area next
        # layout.addStretch()
        layout.addWidget(self.widgets.bottomMenu)  # Instance Manager at the bottom

        # Setup BM Scan Generals UI
        init_scan_general_ui(self)

        # Setup BM Monsters UI
        init_bm_monster_ui(self)

        # Setup BM BlackMarket UI
        init_bm_blackmarket_ui(self)

        # Setup BM Bubbles UI
        init_bm_bubbles_ui(self)


        # TOGGLE MENU
        # ///////////////////////////////////////////////////////////////
        self.widgets.toggleButton.clicked.connect(lambda: UIFunctions.toggleMenu(self, True))

        # SET UI DEFINITIONS
        # ///////////////////////////////////////////////////////////////
        UIFunctions.uiDefinitions(self)

        # Setup the Screen DPI
        UIFunctions.setup_screen_dpi_ui(self)

        # LEFT MENUS
        # Connect buttons directly to click events
        connect_buttons(self)

        # EXTRA LEFT BOX
        def openCloseLeftBox():
            UIFunctions.toggleLeftBox(self, True)

        self.widgets.toggleLeftBox.clicked.connect(openCloseLeftBox)
        self.widgets.extraCloseColumnBtn.clicked.connect(openCloseLeftBox)

        # EXTRA RIGHT BOX
        def openCloseRightBox():
            UIFunctions.toggleRightBox(self, True)

        self.widgets.settingsTopBtn.clicked.connect(openCloseRightBox)


        # SCREEN SIZE
        UIFunctions.screen_size(self)

        # Load Active Ports UI Setup
        setup_port_display_table(self)

        # Load Open Emulator Ports
        reload_ports(self)

        # Connect the scan general signals
        self.widgets.scan_generals_btn.clicked.connect(lambda : handle_scan_general_button(self))
        self.scan_general_console.connect(lambda message: update_scan_console(self,message))

        # Global template manager shortcuts
        self.shortcut_bubble_templates = QShortcut(QKeySequence("Ctrl+Shift+B"), self)
        self.shortcut_bubble_templates.activated.connect(self.open_bubble_template_dialog)

        self.shortcut_resource_templates = QShortcut(QKeySequence("Ctrl+Shift+G"), self)
        self.shortcut_resource_templates.activated.connect(self.open_resource_template_dialog)


    def init_adb(self):

        # call the iniitializer for adb
        ADBManager.initialize_adb()


    def init_instance(self):

        session = get_session()
        # Query all instances from the database
        instances = session.query(Instance).all()

        if not instances:
            # Load the Default Instances when no data found in db
            initialize_instances(self)
        else:
            # Load the instance from db when there are some data in db
            for instance in instances:
                initialize_instances(self,instance)

        session.close()


    def finalize_setup(self):
        # SET HOME PAGE AND SELECT MENU
        # ///////////////////////////////////////////////////////////////
        self.widgets.stackedWidget.setCurrentWidget(self.widgets.home)
        self.widgets.btn_home.setStyleSheet(UIFunctions.selectMenu(self.widgets.btn_home.styleSheet()))

        # Ensure sidebars are open by default at startup.
        self.widgets.leftMenuBg.setMinimumWidth(Settings.MENU_WIDTH)
        self.widgets.leftMenuBg.setMaximumWidth(Settings.MENU_WIDTH)
        self.widgets.extraLeftBox.setMinimumWidth(Settings.LEFT_BOX_WIDTH)
        self.widgets.extraLeftBox.setMaximumWidth(Settings.LEFT_BOX_WIDTH)
        self.widgets.toggleLeftBox.setStyleSheet(
            self.widgets.toggleLeftBox.styleSheet() + Settings.BTN_LEFT_BOX_COLOR
        )

        # Refresh Join Rally monster UI for all loaded instances (ensures UI is up-to-date with DB)
        refresh_join_rally_monsters_for_all_instances(self)

        # Setup Pytesseract
        setup_tesseract()

    def open_bubble_template_dialog(self):
        from gui.widgets.BubbleConfigDialog import BubbleConfigDialog
        dlg = BubbleConfigDialog(self)
        dlg.exec()

    def open_resource_template_dialog(self):
        from gui.widgets.ResourceConfigDialog import ResourceConfigDialog
        dlg = ResourceConfigDialog(self)
        dlg.exec()


    def load_step(self, splash_screen, message, function, index):
        splash_screen.ui.progressBar.setValue(index)
        splash_screen.ui.label_loading.setText(message)
        try:
            function()  # Execute the initialization function
        except Exception:
            logging.getLogger("taskex_boot").exception("Initialization step failed: %s", message)
            splash_screen.ui.label_loading.setText(f"Initialization failed: {message}")
            raise

        if index == splash_screen.ui.progressBar.maximum():
            splash_screen.close()
            # SHOW MAIN APP
            # ///////////////////////////////////////////////////////////////
            self.show()

    def closeEvent(self, event: QCloseEvent):
        """Persist current instance control state before application closes."""
        try:
            from core.menu_button import get_active_instance_indexes
            from gui.controllers.run_tab_controller import save_profile_controls
            from features.logic.auto_bubble import reset_auto_bubble_state

            for instance_index in get_active_instance_indexes(self):
                profile_combo = getattr(self.widgets, f"emu_profile_{instance_index}", None)
                profile_id = profile_combo.currentData() if profile_combo is not None else None
                if profile_id is None:
                    continue
                save_profile_controls(self, instance_index, profile_id=profile_id)

                emulator_thread = getattr(self.widgets, f"emulator_thread_{instance_index}", None)
                if emulator_thread is not None:
                    reset_auto_bubble_state(emulator_thread, reason="app close")
        except Exception:
            logging.getLogger("taskex_boot").exception("Failed to persist controls on application close")
        super().closeEvent(event)


    # RESIZE EVENTS
    # ///////////////////////////////////////////////////////////////
    def resizeEvent(self, event):
        # Update Size Grips
        UIFunctions.resize_grips(self)

    # MOUSE CLICK EVENTS
    # ///////////////////////////////////////////////////////////////
    def mousePressEvent(self, event):
        # SET DRAG POS WINDOW
        self.dragPos = event.globalPos()

        # # PRINT MOUSE EVENTS
        # if event.buttons() == Qt.LeftButton:
        #     print('Mouse click: LEFT CLICK')
        # if event.buttons() == Qt.RightButton:
        #     print('Mouse click: RIGHT CLICK')

