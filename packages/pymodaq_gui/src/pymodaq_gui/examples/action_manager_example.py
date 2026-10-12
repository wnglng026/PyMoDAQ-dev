"""
Action Manager Menu and Toolbar Example

Demonstrates the menu and toolbar capabilities of ActionManager including:
- Creating submenus within submenus (multiple levels)
- Adding actions to nested submenus
- Creating and managing multiple toolbars
- Adding actions to both menus and toolbars
- Using icons for both actions and submenus
- Shared actions across menus and toolbars
"""

import sys
from qtpy import QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from qtpy import QtCore


class ActionManagerExample(QtWidgets.QMainWindow, ActionManager):
    """Example application demonstrating nested menus and multiple toolbars with ActionManager"""

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        ActionManager.__init__(self, menu=self.menuBar())
        self.setWindowTitle(QtCore.QCoreApplication.translate('ActionManagerExample', "ActionManager Menu and Toolbar Example"))
        self.resize(1000, 700)

        # Create central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Add info label
        info_label = QtWidgets.QLabel(
            "<h2>ActionManager Menu and Toolbar Example</h2>"
            "<p>This example demonstrates ActionManager capabilities:</p>"
            "<ul>"
            "<li><b>Multiple menu levels</b> - Submenus within submenus</li>"
            "<li><b>Multiple toolbars</b> - File, Edit, View, and Tools toolbars</li>"
            "<li><b>Icons</b> - Both menus and actions can have icons</li>"
            "<li><b>Flexible organization</b> - Group related actions logically</li>"
            "<li><b>Shared submenus</b> - 'Recent Files' appears in both File and Edit menus</li>"
            "<li><b>Shared actions</b> - Actions appear in multiple menus AND toolbars</li>"
            "<li><b>Toolbar management</b> - Create, retrieve, and populate toolbars dynamically</li>"
            "</ul>"
            "<p>Try clicking any menu item or toolbar button to see action details!</p>",
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Status display
        self.status_display = QtWidgets.QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumHeight(300)
        layout.addWidget(QtWidgets.QLabel("<b>Action Log:</b>"))
        layout.addWidget(self.status_display)

        # Setup all menus and actions
        self.setup_actions()

        self.log_message("Application started. Click any menu item or toolbar button to see action details!")

    def setup_actions(self):
        """Create nested menu structure with actions and multiple toolbars"""

        # ========== Create Multiple Toolbars ==========
        # Create toolbars first so they can be referenced when adding actions
        file_toolbar = self.add_toolbar('file_toolbar', 'File Toolbar', parent=self)
        self.addToolBar(file_toolbar)

        edit_toolbar = self.add_toolbar('edit_toolbar', 'Edit Toolbar', parent=self)
        self.addToolBar(edit_toolbar)

        view_toolbar = self.add_toolbar('view_toolbar', 'View Toolbar', parent=self)
        self.addToolBar(view_toolbar)

        tools_toolbar = self.add_toolbar('tools_toolbar', 'Tools Toolbar', parent=self)
        self.addToolBar(tools_toolbar)

        # ========== File Menu ==========
        file_menu = self.add_menu('file', QtCore.QCoreApplication.translate('ActionManagerExample', 'File'), icon_name='Folder')

        # Add simple actions to File menu AND File toolbar
        self.add_action('new', QtCore.QCoreApplication.translate('ActionManagerExample', 'New'), icon_name='NewFile',
                       menu='file', toolbar=file_toolbar, shortcut='Ctrl+N', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Create new file'))
        self.add_action('open', QtCore.QCoreApplication.translate('ActionManagerExample', 'Open...'), icon_name='Open',
                       menu='file', toolbar=file_toolbar, shortcut='Ctrl+O', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Open existing file'))
        self.add_action('save', QtCore.QCoreApplication.translate('ActionManagerExample', 'Save'), icon_name='SaveAs',
                       menu='file', toolbar=file_toolbar, shortcut='Ctrl+S', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Save current file'))

        # Create "Recent Files" menu within File menu
        recent_menu = self.add_menu('recent', QtCore.QCoreApplication.translate('ActionManagerExample', 'Recent Files'),
                                   menu=file_menu, icon_name='Folder')

        # Add recent file actions
        for i in range(1, 4):
            self.add_action(f'recent_{i}', QtCore.QCoreApplication.translate('ActionManagerExample', 'Project_{}.py').format(i),
                          menu=recent_menu)

        # Add separator to file toolbar
        file_toolbar.addSeparator()

        # Create "Export" menu within File menu
        export_menu = self.add_menu('export', QtCore.QCoreApplication.translate('ActionManagerExample', 'Export'),
                                   menu=file_menu, icon_name='SaveAs')

        # Add export format actions (menu only, not in toolbar)
        self.add_action('export_pdf', QtCore.QCoreApplication.translate('ActionManagerExample', 'Export as PDF'), menu=export_menu, auto_toolbar=False)
        self.add_action('export_png', QtCore.QCoreApplication.translate('ActionManagerExample', 'Export as PNG'), menu=export_menu, auto_toolbar=False)
        self.add_action('export_svg', QtCore.QCoreApplication.translate('ActionManagerExample', 'Export as SVG'), menu=export_menu, auto_toolbar=False)

        # ========== Edit Menu ==========
        edit_menu = self.add_menu('edit', QtCore.QCoreApplication.translate('ActionManagerExample', 'Edit'))

        # Add edit actions to both menu and edit toolbar
        self.add_action('undo', QtCore.QCoreApplication.translate('ActionManagerExample', 'Undo'), icon_name='go-previous', menu='edit',
                       toolbar=edit_toolbar, shortcut='Ctrl+Z', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Undo last action'))
        self.add_action('redo', QtCore.QCoreApplication.translate('ActionManagerExample', 'Redo'), icon_name='go-next', menu='edit',
                       toolbar=edit_toolbar, shortcut='Ctrl+Y', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Redo last action'))

        edit_toolbar.addSeparator()

        self.add_action('cut', QtCore.QCoreApplication.translate('ActionManagerExample', 'Cut'), menu='edit', toolbar=edit_toolbar,
                       shortcut='Ctrl+X', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Cut selection'))
        self.add_action('copy', QtCore.QCoreApplication.translate('ActionManagerExample', 'Copy'), menu='edit', toolbar=edit_toolbar,
                       shortcut='Ctrl+C', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Copy selection'))
        self.add_action('paste', QtCore.QCoreApplication.translate('ActionManagerExample', 'Paste'), menu='edit', toolbar=edit_toolbar,
                       shortcut='Ctrl+V', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Paste from clipboard'))

        # ========== View Menu with Deep Nesting ==========
        view_menu = self.add_menu('view', QtCore.QCoreApplication.translate('ActionManagerExample', 'View'))

        # Level 1: Panels menu
        panels_menu = self.add_menu('panels', QtCore.QCoreApplication.translate('ActionManagerExample', 'Panels'), parent_menu=view_menu)

        # Level 2: Left Panel menu
        left_panel_menu = self.add_menu('left_panel', QtCore.QCoreApplication.translate('ActionManagerExample', 'Left Panel'),
                                       parent_menu=panels_menu)
        self.add_action('left_files', QtCore.QCoreApplication.translate('ActionManagerExample', 'File Explorer'), icon_name='Folder',
                       menu=left_panel_menu, toolbar=view_toolbar,
                       checkable=True, checked=True, tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Toggle file explorer panel'))
        self.add_action('left_search', QtCore.QCoreApplication.translate('ActionManagerExample', 'Search'),
                       menu=left_panel_menu, checkable=True, tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Toggle search panel'))
        self.add_action('left_git', QtCore.QCoreApplication.translate('ActionManagerExample', 'Git'),
                       menu=left_panel_menu, checkable=True, tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Toggle git panel'))

        # Level 2: Right Panel menu
        right_panel_menu = self.add_menu('right_panel', QtCore.QCoreApplication.translate('ActionManagerExample', 'Right Panel'),
                                        parent_menu=panels_menu)
        self.add_action('right_outline', QtCore.QCoreApplication.translate('ActionManagerExample', 'Outline'),
                       menu=right_panel_menu, checkable=True)
        self.add_action('right_terminal', QtCore.QCoreApplication.translate('ActionManagerExample', 'Terminal'),
                       menu=right_panel_menu, checkable=True, checked=True)

        # Level 2: Bottom Panel menu
        bottom_panel_menu = self.add_menu('bottom_panel', QtCore.QCoreApplication.translate('ActionManagerExample', 'Bottom Panel'),
                                         parent_menu=panels_menu)
        self.add_action('bottom_console', QtCore.QCoreApplication.translate('ActionManagerExample', 'Console'),
                       menu=bottom_panel_menu, checkable=True, checked=True)
        self.add_action('bottom_problems', QtCore.QCoreApplication.translate('ActionManagerExample', 'Problems'),
                       menu=bottom_panel_menu, checkable=True)
        self.add_action('bottom_output', QtCore.QCoreApplication.translate('ActionManagerExample', 'Output'),
                       menu=bottom_panel_menu, checkable=True)

        # Add separator to view toolbar
        view_toolbar.addSeparator()

        # Add appearance menu to View
        appearance_menu = self.add_menu('appearance', QtCore.QCoreApplication.translate('ActionManagerExample', 'Appearance'),
                                       parent_menu=view_menu)

        # Theme menu (3 levels deep!)
        theme_menu = self.add_menu('theme', QtCore.QCoreApplication.translate('ActionManagerExample', 'Theme'), parent_menu=appearance_menu)
        self.add_action('theme_light', QtCore.QCoreApplication.translate('ActionManagerExample', 'Light'), menu=theme_menu, tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Switch to light theme'))
        self.add_action('theme_dark', QtCore.QCoreApplication.translate('ActionManagerExample', 'Dark'), menu=theme_menu, tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Switch to dark theme'))
        self.add_action('theme_auto', QtCore.QCoreApplication.translate('ActionManagerExample', 'Auto'), menu=theme_menu, toolbar=view_toolbar,
                       tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Auto-detect theme based on system'))

        # Font size menu (3 levels deep!)
        font_menu = self.add_menu('font', QtCore.QCoreApplication.translate('ActionManagerExample', 'Font Size'), parent_menu=appearance_menu)
        self.add_action('font_small', QtCore.QCoreApplication.translate('ActionManagerExample', 'Small'), menu=font_menu)
        self.add_action('font_medium', QtCore.QCoreApplication.translate('ActionManagerExample', 'Medium'), menu=font_menu)
        self.add_action('font_large', QtCore.QCoreApplication.translate('ActionManagerExample', 'Large'), menu=font_menu)

        # ========== Tools Menu ==========
        tools_menu = self.add_menu('tools', QtCore.QCoreApplication.translate('ActionManagerExample', 'Tools'))

        # Add tools with nested settings
        self.add_action('tool_format', QtCore.QCoreApplication.translate('ActionManagerExample', 'Format Document'), icon_name='Params',
                       menu='tools', toolbar=tools_toolbar, tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Format current document'))

        settings_menu = self.add_menu('settings', QtCore.QCoreApplication.translate('ActionManagerExample', 'Settings'),
                                     parent_menu=tools_menu, icon_name='Params')

        # General settings
        general_settings = self.add_menu('general_settings',
                                        QtCore.QCoreApplication.translate('ActionManagerExample', 'General'), parent_menu=settings_menu)
        self.add_action('auto_save', QtCore.QCoreApplication.translate('ActionManagerExample', 'Auto Save'),
                       menu=general_settings, checkable=True, checked=True)
        self.add_action('show_tooltips', QtCore.QCoreApplication.translate('ActionManagerExample', 'Show Tooltips'),
                       menu=general_settings, checkable=True, checked=True)

        # Advanced settings
        advanced_settings = self.add_menu('advanced_settings',
                                         QtCore.QCoreApplication.translate('ActionManagerExample', 'Advanced'), parent_menu=settings_menu)
        self.add_action('debug_mode', QtCore.QCoreApplication.translate('ActionManagerExample', 'Debug Mode'),
                       menu=advanced_settings, checkable=True)
        self.add_action('verbose_logging', QtCore.QCoreApplication.translate('ActionManagerExample', 'Verbose Logging'),
                       menu=advanced_settings, checkable=True)

        # ========== Help Menu ==========
        help_menu = self.add_menu('help', QtCore.QCoreApplication.translate('ActionManagerExample', 'Help'))
        self.add_action('docs', QtCore.QCoreApplication.translate('ActionManagerExample', 'Documentation'), menu='help')
        self.add_action('about', QtCore.QCoreApplication.translate('ActionManagerExample', 'About'), menu='help')

        # ========== Demonstration of Shared Menus ==========
        # You can add the same menu to multiple parent menus!
        # Let's add the "Recent Files" menu to the Edit menu as well
        edit_menu_obj = self.get_menu('edit')
        recent_menu_obj = self.get_menu('recent')
        edit_menu_obj.addMenu(recent_menu_obj)
        # Now "Recent Files" appears in both File and Edit menus,
        # but it's the same menu instance - changes appear everywhere!

        # ========== Demonstration of Shared Actions ==========
        # The 'save' action can be added to multiple menus/toolbars
        tools_menu_obj = self.get_menu('tools')
        self.affect_to('save', tools_menu_obj)
        # Now "Save" appears in File and Tools menus

        # ========== Demonstration of Toolbar Retrieval and Management ==========
        # You can retrieve toolbars by name and add actions to them later
        retrieved_file_toolbar = self.get_toolbar('file_toolbar')
        # Let's add the 'new' action to the tools toolbar as well
        retrieved_tools_toolbar = self.get_toolbar('tools_toolbar')
        tools_toolbar.addSeparator()
        self.affect_to('new', retrieved_tools_toolbar)
        # Now "New" appears in the File toolbar AND the Tools toolbar

        # Add a widget to the tools toolbar to demonstrate widget support
        self.add_widget('search_box', 'QLineEdit', tip=QtCore.QCoreApplication.translate('ActionManagerExample', 'Search in document'),
                       toolbar=tools_toolbar, visible=True)
        self.get_action('search_box').setPlaceholderText('Search...')
        self.get_action('search_box').setMaximumWidth(200)

        # Log toolbar information
        self.log_message(f"<b>Created {len(self.toolbars)} toolbars:</b> {', '.join(self.toolbars_names)}")

        # Connect all actions to the same handler that shows the info
        for action_name in self.actions_names:
            if action_name != 'search_box':  # Skip the widget
                self.connect_action(action_name, lambda checked=False, name=action_name:
                                  self.on_action_triggered(name))

    def on_action_triggered(self, action_name):
        """Handle action triggered - display action info"""
        action = self.get_action(action_name)

        # Build status message
        message = f"<b>Action:</b> {action.text()}"
        message += f"<br><b>Internal Name:</b> {action_name}"

        # Find which toolbars contain this action
        toolbars_with_action = []
        for toolbar_name in self.toolbars_names:
            toolbar = self.get_toolbar(toolbar_name)
            if action in toolbar.actions():
                toolbars_with_action.append(toolbar_name)

        if toolbars_with_action:
            message += f"<br><b>In Toolbars:</b> {', '.join(toolbars_with_action)}"

        if action.isCheckable():
            state = "Checked" if action.isChecked() else "Unchecked"
            message += f"<br><b>State:</b> {state}"

        if action.shortcut().toString():
            message += f"<br><b>Shortcut:</b> {action.shortcut().toString()}"

        if action.toolTip():
            message += f"<br><b>Tooltip:</b> {action.toolTip()}"

        self.log_message(message)

    def log_message(self, message):
        """Add message to status display"""
        self.status_display.append(message)
        self.status_display.append("<hr>")
        # Scroll to bottom
        scrollbar = self.status_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    """Run the example application"""
    app = QtWidgets.QApplication(sys.argv)

    window = ActionManagerExample()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
