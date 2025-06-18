import time
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool
from .conversion_config import *
from ..converters.dicom_converter import DicomConverter
from ..auth.license_manager import IGPSLicenseManager
from typing import Optional

# Placeholder for actual converter implementations
# from ..converters.ct_converter import CTConverter
# from ..converters.mri_converter import MRIConverter
# from ..converters.mammography_converter import MammographyConverter

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished: No data
    error: tuple (exctype, value, traceback.format_exc())
    progress: int indicating % progress, str for message
    """
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    progress = pyqtSignal(int, str)

class PreprocessingWorker(QRunnable):
    """
    Worker thread for running a preprocessing task.
    Inherits from QRunnable to handle worker thread setup, signals, and wrap-up.
    """
    def __init__(self, config: BaseConversionConfig):
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()

    def run(self):
        """Execute the preprocessing task."""
        try:
            # 1. Initialize the main converter
            converter = DicomConverter()

            # 2. Connect the converter's progress signal to this worker's signal
            #    This allows relaying progress from the converter to the UI
            converter.set_progress_callback(
                lambda p_int, p_str: self.signals.progress.emit(p_int, p_str)
            )

            # 3. Run the main processing function
            #    This function will contain the logic to scan directories and apply
            #    all the preprocessing steps based on the config.
            converter.process_directory_with_config(self.config)

        except Exception as e:
            # Pass exceptions to the main thread
            self.signals.error.emit(e)
        finally:
            self.signals.finished.emit()


class ProcessingController(QObject):
    """
    Controls the preprocessing pipeline.
    It takes requests from the UI and runs them in a background thread pool.
    """
    def __init__(self, license_manager: Optional[IGPSLicenseManager] = None):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.license_manager = license_manager or IGPSLicenseManager()
        # You can set the max thread count if needed
        # self.thread_pool.setMaxThreadCount(1) 
        self.worker = None

    def get_license_manager(self) -> IGPSLicenseManager:
        """Returns the instance of the license manager."""
        return self.license_manager

    def run_preprocessing(self, config):
        """
        Creates and runs a worker for the given configuration.
        """
        # Pass the function to execute
        self.worker = PreprocessingWorker(config)
        # Any other args, kwargs are passed to the run function
        # Execute
        self.thread_pool.start(self.worker)
        return self.worker.signals 