import time
from .base_converter import BaseConverter

class MRIConverter(BaseConverter):
    """
    Converter for MRI data.
    """
    def run(self):
        """
        Simulates the MRI conversion process.
        """
        self.progress.emit(0, "Starting MRI conversion...")
        
        if self.config.n4_bias_correction:
            self.progress.emit(20, "Applying N4 Bias Field Correction...")
            time.sleep(2) # N4 can be slow
        
        self.progress.emit(70, f"Applying {self.config.normalization_method} intensity normalization...")
        time.sleep(1)

        self.progress.emit(100, "MRI conversion complete.")
        self.finished.emit(True, "Successfully converted MRI data.") 