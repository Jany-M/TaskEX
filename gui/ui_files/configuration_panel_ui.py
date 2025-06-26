# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'configuration_panel.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QSizePolicy,
    QWidget)

class Ui_ConfigurationPanel(object):
    def setupUi(self, ConfigurationPanel):
        if not ConfigurationPanel.objectName():
            ConfigurationPanel.setObjectName(u"ConfigurationPanel")
        ConfigurationPanel.resize(342, 665)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ConfigurationPanel.sizePolicy().hasHeightForWidth())
        ConfigurationPanel.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(ConfigurationPanel)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.config_panel_frame_ = QFrame(ConfigurationPanel)
        self.config_panel_frame_.setObjectName(u"config_panel_frame_")
        self.config_panel_frame_.setFrameShape(QFrame.Shape.NoFrame)
        self.config_panel_frame_.setFrameShadow(QFrame.Shadow.Raised)

        self.horizontalLayout.addWidget(self.config_panel_frame_)


        self.retranslateUi(ConfigurationPanel)

        QMetaObject.connectSlotsByName(ConfigurationPanel)
    # setupUi

    def retranslateUi(self, ConfigurationPanel):
        ConfigurationPanel.setWindowTitle(QCoreApplication.translate("ConfigurationPanel", u"Form", None))
    # retranslateUi

