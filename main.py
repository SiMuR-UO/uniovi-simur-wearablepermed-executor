from enum import Enum
import sys
import os
import argparse
import logging
import docker

__author__ = "Miguel Angel Salinas Gancedo"
__copyright__ = "Simur"
__license__ = "MIT"

_logger = logging.getLogger(__name__)

files_to_export = []

class ML_Model(Enum):
    ESANN = 'ESANN'
    CAPTURE24 = 'CAPTURE24'
    RANDOM_FOREST = 'RandomForest'
    XGBOOST = 'XGBoost'

class ML_Sensor(Enum):
    PI = 'thigh'
    M = 'wrist'
    C = 'hip'

def parse_ml_model(value):
    try:
        """Parse a comma-separated list of CML Models lor values into a list of ML_Sensor enums."""
        values = [v.strip() for v in value.split(',') if v.strip()]
        result = []
        invalid = []
        for v in values:
            try:
                result.append(ML_Model(v))
            except ValueError:
                invalid.append(v)
        if invalid:
            valid = ', '.join(c.value for c in ML_Model)
            raise argparse.ArgumentTypeError(
                f"Invalid color(s): {', '.join(invalid)}. "
                f"Choose from: {valid}"
            )
        return result
    except ValueError:
        valid = ', '.join(ml_model.value for ml_model in ML_Model)
        raise argparse.ArgumentTypeError(f"Invalid ML Model '{value}'. Choose from: {valid}")
    
def parse_ml_sensor(value):
    try:
        """Parse a comma-separated list of CML Models lor values into a list of ML_Sensor enums."""
        values = [v.strip() for v in value.split(',') if v.strip()]
        result = []
        invalid = []
        for v in values:
            try:
                result.append(ML_Sensor(v))
            except ValueError:
                invalid.append(v)
        if invalid:
            valid = ', '.join(c.value for c in ML_Sensor)
            raise argparse.ArgumentTypeError(
                f"Invalid color(s): {', '.join(invalid)}. "
                f"Choose from: {valid}"
            )
        return result
    except ValueError:
        valid = ', '.join(ml_model.value for ml_model in ML_Sensor)
        raise argparse.ArgumentTypeError(f"Invalid ML Model '{value}'. Choose from: {valid}")
   
def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="BIN to CSV Converter")

    parser.add_argument(
        "-rd",
        "--dataset-folder",
        required=True,
        dest="dataset_folder",
        help="Root Participant data folder",
    )
    parser.add_argument(
        "-di",
        "--docker-image",
        required=True,
        dest="docker_image",
        help="Docker image with Python modules implemented",
    )    
    parser.add_argument(
        "-md",
        "--python-module",
        required=True,
        dest="python_module",
        help="Python module to be execute",
    )
    parser.add_argument(
        "-make-feature-extractions",
        "--make-feature-extractions",
        dest="make_feature_extractions",
        action='store_true',
        help="make feature extractions?.")
    parser.add_argument(
        "-case-id",
        "--case-id",
        dest="case_id",
        help="Case unique identifier."
    )
    parser.add_argument(
        "-ml-models",
        "--ml-models",
        type=parse_ml_model,
        nargs='+',
        dest="ml_models",
        help=f"Available ML models: {[c.value for c in ML_Model]}."
    )
    parser.add_argument(
        "-ml-sensors",
        "--ml-sensors",
        type=parse_ml_sensor,
        nargs='+',
        dest="ml_sensors",
        help=f"Available ML sensors: {[c.value for c in ML_Sensor]}."
    ) 
    parser.add_argument(
        "-participants-file",
        "--participants-file",
        type=argparse.FileType("r"),
        help="Choose the dataset participant text file"
    )
    parser.add_argument(
        "-case-id-folder",
        "--case-id-folder",
        dest="case_id_folder",
        help="Choose the case id root folder."
    )                                 
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )

    return parser.parse_args(args)

def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )

def filter_conveter_files(args):
    for root, dirs, files in os.walk(args.dataset_folder):
        for file in files:
            # get files tokens         
            _, ext = os.path.splitext(file)         

            # get only files for converter step
            if ext == ".BIN":
                files_to_export.append((root, file))

    files_to_export_ordered = sorted(files_to_export)

    return files_to_export_ordered

def filter_windowed_files(args):
    for root, dirs, files in os.walk(args.dataset_folder):
        for file in files:
            # get files tokens
            _, ext = os.path.splitext(file)         

            # get only files for windowed step
            if ext == ".csv" or "_RegistroActividades.xlsx" in file:
                files_to_export.append((root, file))

    files_to_export_ordered = sorted(files_to_export)

    return files_to_export_ordered

def filter_aggregator_files(args):
    for root, dirs, files in os.walk(args.dataset_folder):
        for file in files:
            # get files tokens
            _, ext = os.path.splitext(file)         

            # get only files for windowed step
            if ext == ".npz" and "_all.npz" not in file:
                files_to_export.append((root, file))

    files_to_export_ordered = sorted(files_to_export)

    return files_to_export_ordered

def execute_container(args, files_to_export):
    client = docker.from_env()

    for file in files_to_export:
        _logger.info('Export BIN file: ' + file[1])

        # Define the volume mapping
        volumes = {
            file[0]: {
                'bind': '/app/data',
                'mode': 'rw'
            }
        }

        try:
            # Run the container
            container = client.containers.run(
                name=os.path.splitext(file[1])[0],
                image=args.docker_image,
                command=[
                    'python', args.python_module,
                    '--bin-matrix-PMP',
                    'data/' + file[1]
                ],
                volumes=volumes,
                working_dir='/app',
                #remove=True,                
                detach=True,
                stdout=True,
                stderr=True,
            )

            # Stream logs live
            for line in container.logs(stream=True):
                print(line.decode(), end='')

            # Optionally remove the container
            container.remove()          
        except docker.errors.ContainerError as e:
            _logger.error("Container failed:", e.stderr.decode())
        except docker.errors.ImageNotFound:
            _logger.error("Image not found.")
        except Exception as e:
            _logger.error("Unexpected error:", str(e))
        
_logger.info("Starting executor python module ...")

args = parse_args(sys.argv[1:])
setup_logging(args.loglevel)

_logger.info("Filtering files to be used ...")
if args.python_module == "converter.py":
    files_to_export = filter_conveter_files(args)
elif args.python_module == "windowed.py":
    files_to_export = filter_windowed_files(args)
elif args.python_module == "aggregator.py":
    files_to_export = filter_aggregator_files(args)
else:
    raise Exception("Python module not implemented")   

_logger.info("Execute Docker collector python module ...")
execute_container(args, files_to_export)

_logger.info("Ending executor python module ...")