#!/usr/bin/env python3
"""
General-purpose segmentation script using TotalSegmentator.

This script processes all sub-subfolders in a given directory and performs
segmentation on medical images using TotalSegmentator. It's designed to be
flexible and reusable for different structures and directory layouts.

Usage:
    python segment_structures.py --config config.yaml
    
    Or with command-line arguments:
    python segment_structures.py --input-dir /path/to/data --structures skin aorta
"""

import argparse
import json
import logging
import sys
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import nibabel as nib
import numpy as np
from totalsegmentator.python_api import totalsegmentator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('segmentation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SegmentationConfig:
    """Configuration for segmentation tasks."""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        structures: List[str] = None,
        input_filename: str = "CT.nii.gz",
        model: str = "3d_fullres",
        device: str = "gpu",
        device_id: Optional[int] = None,
        fast: bool = False,
        export_label_stats: bool = False,
        skip_existing: bool = True,
    ):
        """
        Initialize segmentation configuration.
        
        Args:
            input_dir: Root directory containing sub-subfolders with images
            output_dir: Output directory (if None, saves in same location as input)
            structures: List of structures to segment (TotalSegmentator labels)
            input_filename: Name of the input CT image file
            model: TotalSegmentator model to use ("3d_fullres", "3d_lowres")
            device: Device to use ("gpu" or "cpu")
            device_id: CUDA device ID to use (e.g., 0, 1, 2, 3 for cuda:0, cuda:1, etc.)
            fast: Use fast mode (lower resolution, faster)
            export_label_stats: Export statistics for each label
            skip_existing: Skip folders where output already exists
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir
        self.structures = structures or ["skin"]
        self.input_filename = input_filename
        self.model = model
        self.device = device
        self.device_id = device_id
        self.fast = fast
        self.export_label_stats = export_label_stats
        self.skip_existing = skip_existing
        
        # Validate
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'input_dir': str(self.input_dir),
            'output_dir': str(self.output_dir),
            'structures': self.structures,
            'input_filename': self.input_filename,
            'model': self.model,
            'device': self.device,
            'device_id': self.device_id,
            'fast': self.fast,
            'export_label_stats': self.export_label_stats,
            'skip_existing': self.skip_existing,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'SegmentationConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)


class MedicalImageSegmentor:
    """Handle medical image segmentation using TotalSegmentator."""
    
    # TotalSegmentator label mapping (common structures)
    LABEL_MAPPING = {
        "skin": 1,
        "aorta": 16,
        "pulmonary_artery": 75,
        "lung_upper_lobe_left": 20,
        "lung_lower_lobe_left": 21,
        "lung_upper_lobe_right": 22,
        "lung_middle_lobe_right": 23,
        "lung_lower_lobe_right": 24,
        "heart": 26,
        "kidney_left": 29,
        "kidney_right": 30,
        "spleen": 34,
        "liver": 35,
        "stomach": 36,
        "pancreas": 37,
        "brain": 2,
    }
    
    def __init__(self, config: SegmentationConfig):
        """Initialize segmentor with configuration."""
        self.config = config
        logger.info(f"Initialized segmentor with config: {config.to_dict()}")
    
    def find_all_subfolders(self) -> List[Path]:
        """
        Find all sub-subfolders containing input images.
        
        Returns:
            List of paths to folders containing input images
        """
        subfolders = []
        
        # Walk through the directory structure
        for level1_dir in self.config.input_dir.iterdir():
            if not level1_dir.is_dir():
                continue
            
            for level2_dir in level1_dir.iterdir():
                if not level2_dir.is_dir():
                    continue
                
                input_file = level2_dir / self.config.input_filename
                if input_file.exists():
                    subfolders.append(level2_dir)
        
        logger.info(f"Found {len(subfolders)} folders to process")
        return sorted(subfolders)
    
    def segment_folder(self, folder_path: Path) -> bool:
        """
        Segment all structures in a single folder.
        
        Args:
            folder_path: Path to folder containing input image
            
        Returns:
            True if successful, False otherwise
        """
        input_file = folder_path / self.config.input_filename
        
        if not input_file.exists():
            logger.warning(f"Input file not found: {input_file}")
            return False
        
        # Check if outputs already exist
        if self.config.skip_existing:
            if self._outputs_exist(folder_path):
                logger.info(f"Output already exists for {folder_path.name}, skipping")
                return True
        
        logger.info(f"Processing: {folder_path}")
        
        try:
            # Set CUDA device if specified
            if self.config.device == "gpu" and self.config.device_id is not None:
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.set_device(self.config.device_id)
                        logger.info(f"Using CUDA device: cuda:{self.config.device_id}")
                    else:
                        logger.warning("GPU requested but no CUDA devices available")
                except Exception as e:
                    logger.warning(f"Could not set CUDA device: {e}")
            
            # Run TotalSegmentator
            logger.info(f"Running TotalSegmentator on {input_file}")
            
            # Temporary directory for full segmentation
            temp_output_dir = folder_path / ".temp_totalseg"
            temp_output_dir.mkdir(exist_ok=True)
            
            # Check if we need skin (requires body task instead of total)
            needs_skin = "skin" in self.config.structures
            needs_other = any(s != "skin" for s in self.config.structures)
            
            # Run segmentation for non-skin structures
            if needs_other:
                other_structures = [s for s in self.config.structures if s != "skin"]
                totalsegmentator(
                    str(input_file),
                    str(temp_output_dir),
                    task="total",
                    device=self.config.device,
                    fast=self.config.fast,
                )
                self._extract_from_task_output(temp_output_dir, folder_path, structures=other_structures)
            
            # Run segmentation for skin (uses body task)
            if needs_skin:
                with tempfile.TemporaryDirectory() as body_temp:
                    body_output = Path(body_temp)
                    totalsegmentator(
                        str(input_file),
                        str(body_output),
                        task="body",
                        device=self.config.device,
                        fast=self.config.fast,
                    )
                    # Extract body_trunc as skin
                    body_seg_file = body_output / "body_trunc.nii.gz"
                    if body_seg_file.exists():
                        skin_file = folder_path / "skin.nii.gz"
                        shutil.copy2(body_seg_file, skin_file)
                        logger.info(f"Saved skin to {skin_file}")
                    else:
                        logger.warning(f"body_trunc.nii.gz not found in {body_output}")
            
            # Clean up temporary directory
            if temp_output_dir.exists():
                shutil.rmtree(temp_output_dir)
            
            logger.info(f"Successfully processed: {folder_path}")
            return True
            
        except KeyboardInterrupt:
            print(f"\n⚠ Processing interrupted by user at: {folder_path}")
            return False
        except Exception as e:
            error_msg = f"Error processing {folder_path}: {type(e).__name__}: {str(e)}"
            print(f"ERROR: {error_msg}", flush=True)
            try:
                logger.error(error_msg)
            except KeyboardInterrupt:
                pass  # Ignore interruption during logging
            return False
    
    def _outputs_exist(self, folder_path: Path) -> bool:
        """Check if output files already exist."""
        for structure in self.config.structures:
            output_file = folder_path / f"{structure}.nii.gz"
            if not output_file.exists():
                return False
        return True
    
    def _extract_from_task_output(self, output_dir: Path, save_dir: Path, structures: List[str] = None):
        """
        Extract individual structure files from TotalSegmentator task output.
        
        Args:
            output_dir: Directory containing TotalSegmentator output files
            save_dir: Directory where to save/copy extracted structures
            structures: List of structures to extract
        """
        if structures is None:
            structures = self.config.structures
        
        for structure in structures:
            # TotalSegmentator outputs individual .nii.gz files per structure
            structure_file = output_dir / f"{structure}.nii.gz"
            
            if not structure_file.exists():
                logger.warning(f"Structure file not found: {structure_file}")
                continue
            
            # Copy the structure file to output directory
            output_file = save_dir / f"{structure}.nii.gz"
            shutil.copy2(structure_file, output_file)
            logger.info(f"Saved {structure} to {output_file}")
    
    def _extract_structures(self, temp_output_dir: Path, output_dir: Path, structures: List[str] = None):
        """
        Extract requested structures from TotalSegmentator output.
        
        Args:
            temp_output_dir: Directory containing full TotalSegmentator output
            output_dir: Directory where to save extracted structures
            structures: List of structures to extract (defaults to self.config.structures)
        """
        if structures is None:
            structures = self.config.structures
        
        # TotalSegmentator outputs segmentations.nii.gz with all labels
        segmentation_file = temp_output_dir / "segmentations.nii.gz"
        
        if not segmentation_file.exists():
            logger.warning(f"TotalSegmentator output not found: {segmentation_file}")
            return
        
        # Load the full segmentation
        logger.info(f"Loading segmentation from {segmentation_file}")
        img = nib.load(segmentation_file)
        seg_data = img.get_fdata()
        
        # Extract each requested structure
        for structure in structures:
            label_id = self.LABEL_MAPPING.get(structure)
            
            if label_id is None:
                logger.warning(f"Unknown structure: {structure}. Skipping.")
                continue
            
            # Extract mask for this structure
            mask = (seg_data == label_id).astype(np.uint8)
            
            # Create new image with the extracted structure
            structure_img = nib.Nifti1Image(mask, img.affine, img.header)
            
            # Save the structure
            output_file = output_dir / f"{structure}.nii.gz"
            nib.save(structure_img, output_file)
            logger.info(f"Saved {structure} to {output_file}")
    
    def process_all(self, max_workers: int = 1) -> Dict[str, int]:
        """
        Process all folders.
        
        Args:
            max_workers: Number of parallel workers (currently sequential)
            
        Returns:
            Dictionary with processing statistics
        """
        folders = self.find_all_subfolders()
        
        if not folders:
            logger.warning("No folders found to process")
            return {'total': 0, 'successful': 0, 'failed': 0}
        
        successful = 0
        failed = 0
        
        try:
            for i, folder_path in enumerate(folders, 1):
                logger.info(f"Processing folder {i}/{len(folders)}: {folder_path}")
                if self.segment_folder(folder_path):
                    successful += 1
                else:
                    failed += 1
        except KeyboardInterrupt:
            print("\n\n⚠ Processing interrupted by user")
            print(f"Progress: {successful} successful, {failed} failed, {len(folders) - successful - failed} remaining\n")
        
        stats = {
            'total': len(folders),
            'successful': successful,
            'failed': failed,
        }
        
        logger.info(f"Processing complete. Stats: {stats}")
        return stats


def load_config_from_file(config_file: str) -> SegmentationConfig:
    """Load configuration from JSON or YAML file."""
    config_path = Path(config_file)
    
    if config_file.endswith('.json'):
        with open(config_path) as f:
            config_dict = json.load(f)
    elif config_file.endswith(('.yaml', '.yml')):
        import yaml
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported config file format: {config_file}")
    
    return SegmentationConfig.from_dict(config_dict)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Segment medical images using TotalSegmentator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Segment skin in all folders
  python segment_structures.py --input-dir /path/to/RSNApe/RSNApe --structures skin
  
  # Segment multiple structures
  python segment_structures.py --input-dir /path/to/data --structures skin aorta pulmonary_artery
  
  # Use GPU and fast mode
  python segment_structures.py --input-dir /path/to/data --structures skin --device gpu --fast
  
  # Load from config file
  python segment_structures.py --config config.json
        """
    )
    
    # Config file option
    parser.add_argument('--config', type=str, 
                        help='Path to configuration file (JSON or YAML)')
    
    # Command-line options (override config file)
    parser.add_argument('--input-dir', type=str,
                        help='Input directory containing sub-subfolders')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory (default: same as input)')
    parser.add_argument('--structures', nargs='+', default=None,
                        help='Structures to segment (default: skin)')
    parser.add_argument('--input-filename', type=str, default='CT.nii.gz',
                        help='Input image filename')
    parser.add_argument('--model', type=str, default='3d_fullres',
                        choices=['3d_fullres', '3d_lowres'],
                        help='TotalSegmentator model')
    parser.add_argument('--device', type=str, default='gpu',
                        choices=['gpu', 'cpu'],
                        help='Device to use')
    parser.add_argument('--device-id', type=int, default=None,
                        help='CUDA device ID (0, 1, 2, 3, etc. for cuda:0, cuda:1, cuda:2, cuda:3, etc.)')
    parser.add_argument('--fast', action='store_true',
                        help='Use fast mode')
    parser.add_argument('--export-label-stats', action='store_true',
                        help='Export label statistics')
    parser.add_argument('--no-skip', action='store_true',
                        help='Do not skip existing outputs')
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
        # Override config with command-line arguments if explicitly provided
        if args.input_dir:
            config.input_dir = Path(args.input_dir)
        if args.output_dir:
            config.output_dir = Path(args.output_dir)
        if args.structures is not None:  # User explicitly provided --structures
            config.structures = args.structures
        if args.input_filename != 'CT.nii.gz':
            config.input_filename = args.input_filename
        if args.model != '3d_fullres':
            config.model = args.model
        if args.device != 'gpu':
            config.device = args.device
        if args.device_id is not None:
            config.device_id = args.device_id
        if args.fast:
            config.fast = args.fast
        if args.export_label_stats:
            config.export_label_stats = args.export_label_stats
        if args.no_skip:
            config.skip_existing = not args.no_skip
    else:
        if not args.input_dir:
            parser.error("Either --config or --input-dir must be specified")
        
        config = SegmentationConfig(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            structures=args.structures or ['skin'],  # Default to skin if not provided
            input_filename=args.input_filename,
            model=args.model,
            device=args.device,
            device_id=args.device_id,
            fast=args.fast,
            export_label_stats=args.export_label_stats,
            skip_existing=not args.no_skip,
        )
    
    # Run segmentation
    segmentor = MedicalImageSegmentor(config)
    stats = segmentor.process_all()
    
    # Print summary
    logger.info("="*50)
    logger.info("SEGMENTATION SUMMARY")
    logger.info("="*50)
    logger.info(f"Total folders processed: {stats['total']}")
    logger.info(f"Successful: {stats['successful']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info("="*50)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
