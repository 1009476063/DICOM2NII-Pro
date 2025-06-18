from dataclasses import dataclass, field
from typing import Optional, Tuple, Literal

# Type definitions for clarity
Modality = Literal["CT", "MRI", "Mammography", "Ultrasound"]
Interpolator = Literal["sitkLinear", "sitkNearestNeighbor", "sitkBSpline"]
NormalizationMethod = Literal["None", "ZScore", "WhiteStripe", "HistogramMatching"]

@dataclass
class BaseConversionConfig:
    """Base class for conversion settings."""
    input_dir: str
    output_dir: str
    modality: Modality

@dataclass
class CTConversionConfig(BaseConversionConfig):
    """Configuration specific to CT scans."""
    modality: Modality = "CT"
    
    # RT options
    convert_rtstruct: bool = True
    convert_rtdose: bool = False
    anonymize_rtplan: bool = False
    
    # Radiomics preprocessing
    resample: bool = False
    new_voxel_size: Optional[Tuple[float, float, float]] = (1.0, 1.0, 1.5)
    interpolator: Interpolator = "sitkLinear"
    discretize: bool = False
    discretization_type: Literal["FixedBinWidth", "FixedBinCount"] = "FixedBinWidth"
    discretization_value: float = 25.0
    
    # Metadata overrides
    override_spacing: bool = False
    new_spacing: Optional[Tuple[float, float]] = None
    override_orientation: bool = False
    new_orientation: Optional[str] = None
    
@dataclass
class MRIConversionConfig(BaseConversionConfig):
    """Configuration specific to MRI scans."""
    modality: Modality = "MRI"
    
    # MRI specific preprocessing
    n4_bias_correction: bool = True
    skull_stripping: bool = False
    normalization_method: NormalizationMethod = "None"

    # Radiomics
    discretize: bool = False
    discretization_type: Literal["FixedBinWidth", "FixedBinCount"] = "FixedBinWidth"
    discretization_value: float = 0.5

@dataclass
class MammographyConversionConfig(BaseConversionConfig):
    """Configuration specific to Mammography scans."""
    modality: Modality = "Mammography"
    
    # Mammography specific processing
    correct_orientation: bool = True
    remove_edge_info: bool = False

@dataclass
class UltrasoundConversionConfig(BaseConversionConfig):
    """Configuration specific to Ultrasound scans."""
    modality: Modality = "Ultrasound"
    # Placeholder for future ultrasound-specific settings
    ... 