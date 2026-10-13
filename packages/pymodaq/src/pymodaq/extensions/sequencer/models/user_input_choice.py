from qtpy import QtWidgets
from pymodaq_data import DataToExport
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase
from qtpy import QtCore


@ChoiceModelFactory.register_choice()
class UserInput(ChoiceModelBase):
    model_name = 'user_input'

    params = []

    def execute(self, dte: DataToExport):

        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(QtCore.QCoreApplication.translate('UserInput', "Previous steps are finished"))
        msgBox.setInformativeText(QtCore.QCoreApplication.translate('UserInput', "Are you ok to proceed or go back?"))
        button_proceed = msgBox.addButton(QtCore.QCoreApplication.translate('UserInput', 'Proceed'), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        button_goback = msgBox.addButton(QtCore.QCoreApplication.translate('UserInput', 'Go back'), QtWidgets.QMessageBox.ButtonRole.RejectRole)
        msgBox.setDefaultButton(button_proceed)
        msgBox.exec()

        self.parent_elt.go_to_signal.emit(msgBox.clickedButton() == button_proceed)
