from PyQt6.QtCore import QObject, pyqtSignal

class BaseConverter(QObject):
    """
    Base class for all DICOM converters.
    It's a QObject to support signals in a threaded environment.
    """
    progress = pyqtSignal(int, str)  # percentage, message
    finished = pyqtSignal(bool, str) # success, final message
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        """
        The main method to run the conversion.
        This should be implemented by subclasses.
        """
        raise NotImplementedError("The 'run' method must be implemented by a subclass.")

    def check_dependencies(self):
        """
        Checks if all necessary external tools (like dcm2niix) are available.
        """
        # Subclasses can implement this
        return True