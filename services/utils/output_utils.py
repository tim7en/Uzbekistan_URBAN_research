"""
Output directory and file management utilities
"""

from pathlib import Path
from typing import Dict
from datetime import datetime


def create_output_directories(base_name: str = "suhi_analysis_output") -> Dict[str, Path]:
    """
    Create organized output directory structure
    """
    try:
        base_root = Path(__file__).parent.parent.parent
    except NameError:
        base_root = Path.cwd()
    
    base_dir = base_root / base_name
    
    # Define subdirectories
    subdirs = [
        "data",
        "classification", 
        "temperature",
        "vegetation",
        "visualizations",
        "reports",
        "error_analysis",
        "raster_outputs",  # For raster files (SUHI maps, landcover maps)
        "night_lights",    # For night lights analysis
        "urban_expansion", # For urban expansion analysis
        "statistical"      # For statistical analysis outputs
    ]
    
    dirs = {'base': base_dir}
    dirs.update({k: base_dir / k for k in subdirs})
    
    # Create all directories
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directories created: {base_dir}")
    return dirs


def get_output_filename(base_name: str, city: str = None, year: int = None, 
                       extension: str = "json", timestamp: bool = True) -> str:
    """
    Generate standardized output filename
    """
    parts = [base_name]
    
    if city:
        parts.append(city.lower().replace(" ", "_"))
    
    if year:
        parts.append(str(year))
    
    if timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(ts)
    
    filename = "_".join(parts) + f".{extension}"
    return filename


def save_analysis_metadata(output_dir: Path, metadata: Dict) -> Path:
    """
    Save analysis metadata to JSON file
    """
    import json
    
    metadata_file = output_dir / "analysis_metadata.json"
    metadata['generated_at'] = datetime.now().isoformat()
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata_file