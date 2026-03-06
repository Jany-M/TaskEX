# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash_screen.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QLabel, QLayout, QLineEdit, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_SplashScreen(object):
    def setupUi(self, SplashScreen):
        if not SplashScreen.objectName():
            SplashScreen.setObjectName(u"SplashScreen")
        SplashScreen.setWindowModality(Qt.WindowModality.WindowModal)
        SplashScreen.resize(695, 470)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SplashScreen.sizePolicy().hasHeightForWidth())
        SplashScreen.setSizePolicy(sizePolicy)
        SplashScreen.setMinimumSize(QSize(0, 0))
        SplashScreen.setMaximumSize(QSize(16777215, 16777215))
        SplashScreen.setStyleSheet(u"QMainWindow { border: none; margin: 0px; padding: 0px; }\n"
"\n"
"QFrame {	\n"
"	background-color:  rgba(40,44,52,255);	\n"
"	color: rgb(220, 220, 220);\n"
"	border-radius: 10px;\n"
"}\n"
"\n"
"/* /////////////////////////////////////////////////////////////////////////////////////////////////\n"
"LineEdit */\n"
"QLineEdit {\n"
"	background-color: rgb(33, 37, 43);\n"
"	border-radius: 5px;\n"
"	border: 2px solid rgb(33, 37, 43);\n"
"	padding-left: 10px;\n"
"	selection-color: rgb(255, 255, 255);\n"
"	selection-background-color: rgb(255, 121, 198);\n"
"}\n"
"QLineEdit:hover {\n"
"	border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"QLineEdit:focus {\n"
"	border: 2px solid rgb(91, 101, 124);\n"
"}\n"
"\n"
"/* /////////////////////////////////////////////////////////////////////////////////////////////////\n"
"CheckBox */\n"
"QCheckBox::indicator {\n"
"    border: 3px solid rgb(52, 59, 72);\n"
"	width: 15px;\n"
"	height: 15px;\n"
"	border-radius: 10px;\n"
"    background: rgb(44, 49, 60);\n"
"}\n"
"QCheckBox::indicator:ho"
                        "ver {\n"
"    border: 3px solid rgb(58, 66, 81);\n"
"}\n"
"QCheckBox::indicator:checked {\n"
"    background: 3px solid rgb(52, 59, 72);\n"
"	border: 3px solid rgb(52, 59, 72);	\n"
"	background-image: url(:/icons/images/icons/cil-check-alt.png);\n"
"}\n"
"\n"
"/* /////////////////////////////////////////////////////////////////////////////////////////////////\n"
"Button */\n"
"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        self.centralwidget = QWidget(SplashScreen)
        self.centralwidget.setObjectName(u"centralwidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.dropShadowFrame = QFrame(self.centralwidget)
        self.dropShadowFrame.setObjectName(u"dropShadowFrame")
        sizePolicy1.setHeightForWidth(self.dropShadowFrame.sizePolicy().hasHeightForWidth())
        self.dropShadowFrame.setSizePolicy(sizePolicy1)
        self.dropShadowFrame.setMaximumSize(QSize(16777215, 16777215))
        self.dropShadowFrame.setStyleSheet(u"")
        self.dropShadowFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.dropShadowFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.dropShadowFrame)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.header_frame = QFrame(self.dropShadowFrame)
        self.header_frame.setObjectName(u"header_frame")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.header_frame.sizePolicy().hasHeightForWidth())
        self.header_frame.setSizePolicy(sizePolicy2)
        self.header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.header_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.header_frame)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label_title_version = QLabel(self.header_frame)
        self.label_title_version.setObjectName(u"label_title_version")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(40)
        self.label_title_version.setFont(font)
        self.label_title_version.setStyleSheet(u"color: rgb(254, 121, 199);")
        self.label_title_version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.label_title_version)

        self.label_description = QLabel(self.header_frame)
        self.label_description.setObjectName(u"label_description")
        font1 = QFont()
        font1.setFamilies([u"Segoe UI"])
        font1.setPointSize(14)
        self.label_description.setFont(font1)
        self.label_description.setStyleSheet(u"color: rgb(98, 114, 164);")
        self.label_description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.label_description)


        self.verticalLayout_4.addWidget(self.header_frame, 0, Qt.AlignmentFlag.AlignBottom)

        self.action_frame = QFrame(self.dropShadowFrame)
        self.action_frame.setObjectName(u"action_frame")
        sizePolicy1.setHeightForWidth(self.action_frame.sizePolicy().hasHeightForWidth())
        self.action_frame.setSizePolicy(sizePolicy1)
        self.action_frame.setMaximumSize(QSize(16777215, 16777215))
        self.action_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.action_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.action_frame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.horizontalSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer, 0, 2, 1, 1)

        self.btn_startup = QPushButton(self.action_frame)
        self.btn_startup.setObjectName(u"btn_startup")
        self.btn_startup.setEnabled(False)
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.btn_startup.sizePolicy().hasHeightForWidth())
        self.btn_startup.setSizePolicy(sizePolicy3)
        self.btn_startup.setMinimumSize(QSize(180, 45))

        self.gridLayout_2.addWidget(self.btn_startup, 3, 0, 1, 1)

        self.startup_field_1 = QLineEdit(self.action_frame)
        self.startup_field_1.setObjectName(u"startup_field_1")
        self.startup_field_1.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.startup_field_1.sizePolicy().hasHeightForWidth())
        self.startup_field_1.setSizePolicy(sizePolicy3)
        self.startup_field_1.setMinimumSize(QSize(300, 45))

        self.gridLayout_2.addWidget(self.startup_field_1, 0, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)

        self.startup_field_2 = QLineEdit(self.action_frame)
        self.startup_field_2.setObjectName(u"startup_field_2")
        self.startup_field_2.setEnabled(False)
        self.startup_field_2.setMinimumSize(QSize(300, 45))
        self.startup_field_2.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.startup_field_2.setEchoMode(QLineEdit.EchoMode.Password)

        self.gridLayout_2.addWidget(self.startup_field_2, 1, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)

        self.startup_option = QCheckBox(self.action_frame)
        self.startup_option.setObjectName(u"startup_option")
        self.startup_option.setEnabled(False)
        self.startup_option.setMinimumSize(QSize(0, 40))

        self.gridLayout_2.addWidget(self.startup_option, 2, 0, 1, 1)

        self.line = QFrame(self.action_frame)
        self.line.setObjectName(u"line")
        sizePolicy.setHeightForWidth(self.line.sizePolicy().hasHeightForWidth())
        self.line.setSizePolicy(sizePolicy)
        self.line.setStyleSheet(u"background-color: rgb(33, 37, 43);")
        self.line.setFrameShadow(QFrame.Shadow.Raised)
        self.line.setLineWidth(1)
        self.line.setMidLineWidth(0)
        self.line.setFrameShape(QFrame.Shape.VLine)

        self.gridLayout_2.addWidget(self.line, 0, 3, 4, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_2, 0, 4, 1, 1)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_3, 0, 6, 1, 1)

        self.btn_continue = QPushButton(self.action_frame)
        self.btn_continue.setObjectName(u"btn_continue")
        self.btn_continue.setMinimumSize(QSize(150, 45))

        self.gridLayout_2.addWidget(self.btn_continue, 0, 5, 1, 1)

        self.btn_exit = QPushButton(self.action_frame)
        self.btn_exit.setObjectName(u"btn_exit")
        self.btn_exit.setMinimumSize(QSize(150, 45))
        self.btn_exit.setMaximumSize(QSize(16777215, 16777215))

        self.gridLayout_2.addWidget(self.btn_exit, 1, 5, 1, 1)


        self.verticalLayout_4.addWidget(self.action_frame, 0, Qt.AlignmentFlag.AlignBottom)

        self.progress_frame = QFrame(self.dropShadowFrame)
        self.progress_frame.setObjectName(u"progress_frame")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.progress_frame.sizePolicy().hasHeightForWidth())
        self.progress_frame.setSizePolicy(sizePolicy4)
        self.progress_frame.setMaximumSize(QSize(16777215, 0))
        self.progress_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.progress_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.progress_frame)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.progressBar = QProgressBar(self.progress_frame)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setStyleSheet(u"QProgressBar {\n"
"	\n"
"	background-color: rgb(98, 114, 164);\n"
"	color: transparent;\n"
"	border-style: none;\n"
"	border-radius: 10px;\n"
"	text-align: center;\n"
"}\n"
"QProgressBar::chunk{\n"
"	border-radius: 10px;\n"
"	background-color: qlineargradient(spread:pad, x1:0, y1:0.511364, x2:1, y2:0.523, stop:0 rgba(254, 121, 199, 255), stop:1 rgba(170, 85, 255, 255));\n"
"}")
        self.progressBar.setValue(0)

        self.verticalLayout_5.addWidget(self.progressBar)

        self.label_loading = QLabel(self.progress_frame)
        self.label_loading.setObjectName(u"label_loading")
        font2 = QFont()
        font2.setFamilies([u"Segoe UI"])
        font2.setPointSize(12)
        self.label_loading.setFont(font2)
        self.label_loading.setStyleSheet(u"color: rgb(98, 114, 164);")
        self.label_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_5.addWidget(self.label_loading)


        self.verticalLayout_4.addWidget(self.progress_frame, 0, Qt.AlignmentFlag.AlignBottom)

        self.credits_frame = QFrame(self.dropShadowFrame)
        self.credits_frame.setObjectName(u"credits_frame")
        self.credits_frame.setMinimumSize(QSize(0, 0))
        self.credits_frame.setMaximumSize(QSize(16777215, 40))
        self.credits_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.credits_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.credits_frame)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label_credits = QLabel(self.credits_frame)
        self.label_credits.setObjectName(u"label_credits")
        font3 = QFont()
        font3.setFamilies([u"Segoe UI"])
        font3.setPointSize(10)
        self.label_credits.setFont(font3)
        self.label_credits.setStyleSheet(u"color: rgb(98, 114, 164);")
        self.label_credits.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_6.addWidget(self.label_credits)


        self.verticalLayout_4.addWidget(self.credits_frame)


        self.verticalLayout.addWidget(self.dropShadowFrame)

        SplashScreen.setCentralWidget(self.centralwidget)

        self.retranslateUi(SplashScreen)

        QMetaObject.connectSlotsByName(SplashScreen)
    # setupUi

    def retranslateUi(self, SplashScreen):
        SplashScreen.setWindowTitle(QCoreApplication.translate("SplashScreen", u"TaskEX", None))
        self.label_title_version.setText(QCoreApplication.translate("SplashScreen", u"<html><head/><body><p>TaskEnforcerX <span style=\" font-size:12pt;\">v</span><span style=\" font-size:16pt;\">0.0.1</span></p></body></html>", None))
        self.label_description.setText(QCoreApplication.translate("SplashScreen", u"<html><head/><body><p>Ultimate Edition</p></body></html>", None))
        self.btn_startup.setText(QCoreApplication.translate("SplashScreen", u"Start", None))
        self.startup_field_1.setPlaceholderText(QCoreApplication.translate("SplashScreen", u"Field 1", None))
        self.startup_field_2.setPlaceholderText(QCoreApplication.translate("SplashScreen", u"Field 2", None))
        self.startup_option.setText(QCoreApplication.translate("SplashScreen", u"Option", None))
        self.btn_continue.setText(QCoreApplication.translate("SplashScreen", u"Continue", None))
        self.btn_exit.setText(QCoreApplication.translate("SplashScreen", u"Exit", None))
        self.label_loading.setText(QCoreApplication.translate("SplashScreen", u"Setting up TaskEnforcerX...", None))
        self.label_credits.setText(QCoreApplication.translate("SplashScreen", u"<html><head/><body><p>By: MwoNuZzz & TheAnt</p></body></html>", None))
    # retranslateUi

