import time
from .base_converter import BaseConverter

class CTConverter(BaseConverter):
    """
    Converter for CT data.
    """
    def run(self):
        """
        Simulates the CT conversion process.
        """
        self.progress.emit(0, "Starting CT conversion...")
        
        if self.config.convert_rtstruct:
            self.progress.emit(10, "RTSTRUCT detected. Preparing to convert masks...")
            time.sleep(1)
        
        self.progress.emit(30, "Converting main CT series...")
        time.sleep(1)

        if self.config.resample:
            self.progress.emit(60, f"Resampling to {self.config.new_voxel_size} with {self.config.interpolator}...")
            time.sleep(1.5)

        if self.config.convert_rtdose:
            self.progress.emit(85, "Converting and aligning RTDOSE...")
            time.sleep(1)
            
        self.progress.emit(100, "CT conversion complete.")
        self.finished.emit(True, "Successfully converted CT data.") 