from enum import Enum
import sys
import os
import argparse
import logging
import docker
from collections import defaultdict
import unicodedata

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

def to_ascii(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()

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

def execute_container_by_converter(args, input_files):
    client = docker.from_env()

    for file in input_files:
        _logger.info('Executing file: ' + file[1])

        # Define the volume mapping
        volumes = {
            file[0]: {
                'bind': '/app/data',
                'mode': 'rw'
            }
        }

        # Define the container command
        commands = [
            'python', args.python_module,
            '--bin-matrix-PMP', 'data/' + file[1]
        ]

        # Run the container from volume and command
        try:
            container = client.containers.run(
                name = os.path.splitext(file[1])[0],
                image = args.docker_image,
                user = '1000:1000',
                command = commands,
                volumes = volumes,
                working_dir = '/app',         
                detach = True,
                stdout = True,
                stderr = True,
            )

            # Stream logs live
            for line in container.logs(stream=True):
                print(line.decode(), end='')

            # Optionally remove the container and volumes attached
            container.remove(v=True, force=True)          
        except docker.errors.ContainerError as e:
            _logger.error("Container failed:", e.stderr.decode())
        except docker.errors.ImageNotFound:
            _logger.error("Image not found.")
        except Exception as e:
            _logger.error("Unexpected error:", str(e))

def execute_container_by_windowed(args, input_files):
    client = docker.from_env()

    # group input files in participant groups from activity excel and csv input files
    participants = defaultdict(list)

    for participant, filename in input_files:
        participants[participant].append(filename)

    # create the container from participant groups
    for participant_path, files in participants.items():
        _logger.info('Executing participant: ' + participant_path)

        # Identify the .xlsx file
        activity_files = [f for f in files if f.endswith('.xlsx')]
        csv_files = [f for f in files if f.endswith('.csv')]

        if len(activity_files) == 1 and len(csv_files) > 0:
            activity_file = activity_files[0]

            for csv_file in csv_files:
                print(f"{activity_file} with {csv_file}")

                # get name and extension from input csv file
                name, extension = os.path.splitext(csv_file)

                # Define the volume mapping
                volumes = {
                    participant_path: {
                        'bind': '/app/data',
                        'mode': 'rw'
                    }
                }

                # Define the container command        
                commands = [
                    'python', args.python_module,
                    '--csv-matrix-PMP', 'data/' + csv_file,
                    '--activity-PMP', 'data/' + activity_file,
                    '--export-folder-name', 'data/' + name + '.npz',            
                ]

                if args.make_feature_extractions == True:
                    commands.append('--make-feature-extractions')

                # Run the container from volume and command
                try:
                    container = client.containers.run(
                        name = to_ascii(name),
                        image = args.docker_image,
                        user = '1000:1000',
                        command = commands,
                        volumes = volumes,
                        working_dir = '/app',
                        detach = True,
                        stdout = True,
                        stderr = True,
                    )

                    # Stream logs live
                    for line in container.logs(stream=True):
                        print(line.decode(), end='')

                    # Optionally remove the container and volumne attached
                    container.remove(v=True, force=True)
                except docker.errors.ContainerError as e:
                    _logger.error("Container failed:", e.stderr.decode())
                except docker.errors.ImageNotFound:
                    _logger.error("Image not found.")
                except Exception as e:
                    _logger.error("Unexpected error:", str(e))

def execute_container_by_agregator(args, input_files):
    client = docker.from_env()

    for file in input_files:
        _logger.info('Executing file: ' + file[1])

        # Define the volume mapping
        volumes = {
            file[0]: {
                'bind': '/app/data',
                'mode': 'rw'
            }
        }

        # Define the container command
        commands = [
            'python', args.python_module,
            '--bin-matrix-PMP', 'data/' + file[1]
        ]

        try:
            # Run the container
            container = client.containers.run(
                name = os.path.splitext(file[1])[0],
                image = args.docker_image,
                user = '1000:1000',
                command = commands,
                volumes = volumes,
                working_dir = '/app',            
                detach = True,
                stdout = True,
                stderr = True,
            )

            # Stream logs live
            for line in container.logs(stream=True):
                print(line.decode(), end='')

            # Optionally remove the container
            container.remove(v=True, force=True)
        except docker.errors.ContainerError as e:
            _logger.error("Container failed:", e.stderr.decode())
        except docker.errors.ImageNotFound:
            _logger.error("Image not found.")
        except Exception as e:
            _logger.error("Unexpected error:", str(e))

_logger.info("Starting executor python module ...")

args = parse_args(sys.argv[1:])
setup_logging(args.loglevel)

if args.python_module == "converter.py":
    _logger.info("Filtering files ...")
    input_files = filter_conveter_files(args)

    _logger.info("Execute Docker Python module ...")
    execute_container_by_converter(args, input_files)    
elif args.python_module == "windowed.py":
    _logger.info("Filtering files ...")
    input_files = filter_windowed_files(args)

    _logger.info("Execute Docker Python module ...")
    execute_container_by_windowed(args, input_files) 
elif args.python_module == "aggregator.py":
    _logger.info("Filtering files ...")
    input_files = filter_aggregator_files(args)

    _logger.info("Execute Docker Python module ...")
    execute_container_by_agregator(args, input_files) 

else:
    raise Exception("Python module not implemented")   

_logger.info("Ending executor python module ...")