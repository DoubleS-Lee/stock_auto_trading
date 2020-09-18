from kiwoom.kiwoom import *

import sys
from PyQt5.QtWidgets import *

class Ui_class():
    def __init__(self):
        print("Ui 클래스 입니다")

        self.app = QApplication(sys.argv)

        self.kiwoom = Kiwoom()

        # 프로그램이 종료되는 것을 방지
        self.app.exec_()