import sys
from pathlib import Path
from config.config import load_detector_config
from detector.structure_detector import StructureDetector

if __name__ == "__main__":
    config = load_detector_config()
    
    detector = StructureDetector(config=config)
    detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/structure.md")

