from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp
from qtpy import QtCore


class MyApp(CustomApp):
    params = [
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False,
         'children': [
             {'title': 'Wait time step (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0,
              'tip': 'Wait time in ms after each step of acquisition (move and grab)'},
             {'title': 'Wait time between (ms)', 'name': 'wait_time_between', 'type': 'int',
              'value': 0,
              'tip': 'Wait time in ms between move and grab processes'},
         ]}]
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setup_ui()

    def setup_docks_and_widgets(self):
        self.mainwindow.setCentralWidget(self.settings_tree)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        if menubar is None:
            menubar = self.menubar
        self.create_object_toolbar(add_break=True)
        self.add_menu('file', QtCore.QCoreApplication.translate('MyApp', 'File'), parent_menu=menubar)
        self.add_menu('tools', QtCore.QCoreApplication.translate('MyApp', 'Tools'), parent_menu=menubar)
        self.add_menu('subtools', QtCore.QCoreApplication.translate('MyApp', 'SubTools'), parent_menu='tools')
        self.add_toolbar('file', 'file', parent_menu=self.mainwindow, add_break=False)


    def setup_actions(self):
        self.add_action('new', QtCore.QCoreApplication.translate('MyApp', 'New File'), 'draft', QtCore.QCoreApplication.translate('MyApp', 'Create a new file'),
                        toolbar='file', menu='file')
        self.add_action('save', QtCore.QCoreApplication.translate('MyApp', 'Save File'), 'file_save', QtCore.QCoreApplication.translate('MyApp', 'Save file as'),
                        toolbar='file', menu='file')
        self.add_action('load', QtCore.QCoreApplication.translate('MyApp', 'Load File'), 'file_open', QtCore.QCoreApplication.translate('MyApp', 'Load file '),
                        toolbar='file', menu='file')

        self.add_action('tool1', QtCore.QCoreApplication.translate('MyApp', 'Erase'), 'ink_eraser', 'ink_eraser',
                        menu='tools')
        self.add_action('tool2', QtCore.QCoreApplication.translate('MyApp', 'Erase off'), 'ink_eraser_off', 'ink_eraser_off',
                        menu='subtools')
        self.add_action('tool3', 'input', 'input', 'input',
                        menu='subtools')

    def connect_things(self):
        pass


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq_gui.utils.widgets.window import make_window
    from pymodaq_gui.utils.shared_ui import SharedUI

    qtapp = mkQApp('SharedUI')
    window, dockarea = make_window(area=False, title='SharedUiExample')
    app = MyApp(window)

    shared_ui = SharedUI(window)
    shared_ui.affect_application(app)

    qtapp.exec()

if __name__ == '__main__':
    main()



