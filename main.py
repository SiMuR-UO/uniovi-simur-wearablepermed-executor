import sys
import os
import argparse
import logging
from enum import Enum
from collections import defaultdict
import unicodedata
import pandas as pd
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

def to_ascii(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()

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
        dest="ml_models",
        help=f"Available ML models: {[c.value for c in ML_Model]}."
    )
    parser.add_argument(
        "-ml-sensors",
        "--ml-sensors",
        dest="ml_sensors",
        help=f"Available ML sensors: {[c.value for c in ML_Sensor]}."
    ) 
    parser.add_argument(
        "-participants-file",
        "--participants-file",
        dest="participants_file",
        help="Choose the dataset participant text file"
    )
    parser.add_argument(
        "-csv-participants-not-time-off-file",
        "--csv-participants-not-time-off-file",
        dest="csv_participants_not_time_off_file",
        help="csv Participants not time off file"
    )    
    parser.add_argument(
        "-case-id-folder",
        "--case-id-folder",
        dest="case_id_folder",
        help="Choose the case id root folder."
    )  
    parser.add_argument(
        "-training-percent",
        "--training-percent",        
        dest="training_percent",
        default="70",        
        help="Choose the training percent."
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

def filter_windowed_mets_files(args):
    for root, dirs, files in os.walk(args.dataset_folder):
        for file in files:
            # get files tokens
            _, ext = os.path.splitext(file)         

            # get only files for windowed step
            if "_features.npz" in file or "_REPOSO_" in file or "_TREADMILL_" in file or "_STS_" in file or "_GXT_" in file:
                files_to_export.append((root, file))

    files_to_export_ordered = sorted(files_to_export)

    return files_to_export_ordered

def execute_container_by_converter(args, input_files):
    client = docker.from_env()

    for file in input_files:
        _logger.info('Executing file: ' + file[1])

        # Define the container volume mapping
        volumes = {
            file[0]: {
                'bind': '/app/data',
                'mode': 'rw'
            }
        }

        # Define the container command
        command = [
            'python', args.python_module,
            '--bin-matrix-PMP', 'data/' + file[1]
        ]

        # Run the container from volume and command
        try:
            container = client.containers.run(
                name = os.path.splitext(file[1])[0],
                image = args.docker_image,
                user = '1000:1000',
                command = command,
                volumes = volumes,
                working_dir = '/app',         
                detach = True,
                stdout = True,
                stderr = True,
            )

            # stream logs live
            for line in container.logs(stream=True):
                _logger.info(line.decode(), end='')

            # remove the container and volume attached
            container.remove(v=True, force=True)          
        except docker.errors.ContainerError as e:
            _logger.error("Container failed:", e.stderr.decode())
        except docker.errors.ImageNotFound:
            _logger.error("Image not found.")
        except Exception as e:
            _logger.error("Unexpected error:", str(e))

def execute_container_by_windowed(args, input_files):
    # load the csv not time off file to detect imcompleted participants        
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "participants_not_time_off.csv")

    df_participants_not_time_off = pd.read_csv(csv_path, dtype=str)

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
                _logger.info(f"{activity_file} with {csv_file}")

                # get name and extension from input csv file
                name, extension = os.path.splitext(csv_file)

                # check if the participant has not time off issue                
                participant_code = name.split('_')[0]
                participant_id = participant_code[3:]
                sensor_id = name.split('_')[2]

                # Define the container volume mapping
                volumes = {
                    participant_path: {
                        'bind': '/app/data',
                        'mode': 'rw'
                    }
                }

                # Define the container command        
                command = [
                    'python', args.python_module,
                    '--csv-matrix-PMP', 'data/' + csv_file,
                    '--activity-PMP', 'data/' + activity_file,
                    #'--export-folder-name', 'data/' + name + '.npz',
                    '--export-folder-name', 'data/' + 'data_' + participant_id + '_tot_' + sensor_id + '.npz',
                ]

                if args.make_feature_extractions == True:
                    command.append('--make-feature-extractions')

                participant_not_time_off = df_participants_not_time_off[(df_participants_not_time_off.iloc[:, 0] == participant_code) & (df_participants_not_time_off.iloc[:, 1] == sensor_id)]

                if not participant_not_time_off.empty:
                    command.append('--has-timeoff')
                    command.append('False')
                    command.append('--calibrate-with-start-WALKING-USUAL-SPEED')
                    command.append(participant_not_time_off.iloc[0]['sample'])
                    command.append('--start-time-WALKING-USUAL-SPEED')
                    command.append(participant_not_time_off.iloc[0]['time'])

                # Run the container from volume and command
                try:
                    container = client.containers.run(
                        name = to_ascii(name),
                        image = args.docker_image,
                        user = '1000:1000',
                        command = command,
                        volumes = volumes,
                        working_dir = '/app',
                        detach = True,
                        stdout = True,
                        stderr = True,
                    )

                    # stream logs live
                    for line in container.logs(stream=True):
                        _logger.info(line.decode(), end='')

                    # remove the container and volume attached
                    container.remove(v=True, force=True)
                except docker.errors.ContainerError as e:
                    _logger.error("Container failed:", e.stderr.decode())
                except docker.errors.ImageNotFound:
                    _logger.error("Image not found.")
                except Exception as e:
                    _logger.error("Unexpected error:", str(e))

def execute_container_by_windowed_mets(args, input_files):
    client = docker.from_env()

    # group input files in participant groups from activity excel and csv input files
    participants = defaultdict(list)

    for participant, filename in input_files:
        participants[participant].append(filename)

    # create the container from participant groups
    for participant_path, files in participants.items():
        _logger.info('Executing participant: ' + participant_path)

        # Identify the .xlsx file
        activity_reposo_files = [f for f in files if "_REPOSO_" in f]
        activity_treadmill_files = [f for f in files if "_TREADMILL_" in f]
        activity_sts_files = [f for f in files if "_STS_" in f]
        activity_gxt_files = [f for f in files if "_GXT_" in f]

        npz_files = [f for f in files if f.endswith('features.npz')]

        if len(activity_reposo_files) == 1 and len(activity_treadmill_files) == 1 and len(activity_sts_files) == 1 and len(activity_gxt_files) == 1 and len(npz_files) > 0:
            for npz_file in npz_files:
                _logger.info(f"{npz_file}")

                # get name and extension from input csv file
                name, extension = os.path.splitext(npz_file)

                # Define the container volume mapping
                volumes = {
                    participant_path: {
                        'bind': '/app/data',
                        'mode': 'rw'
                    }
                }

                # Define the container command        
                command = [
                    'python', args.python_module,
                    '--ruta-datos-features', 'data/' + npz_file,
                    '--ruta-excel-fase-reposo', 'data/' + activity_reposo_files[0],
                    '--ruta-excel-tapiz-rodante', 'data/' + activity_treadmill_files[0],            
                    '--ruta-excel-sts', 'data/' + activity_sts_files[0],            
                    '--ruta-excel-incremental', 'data/' + activity_gxt_files[0],            
                ]

                # Run the container from volume and command
                try:
                    container = client.containers.run(
                        name = to_ascii(name),
                        image = args.docker_image,
                        user = '1000:1000',
                        command = command,
                        volumes = volumes,
                        working_dir = '/app',
                        detach = True,
                        stdout = True,
                        stderr = True,
                    )

                    # stream logs live
                    for line in container.logs(stream=True):
                        _logger.info(line.decode(), end='')

                    # remove the container and volume attached
                    container.remove(v=True, force=True)
                except docker.errors.ContainerError as e:
                    _logger.error("Container failed:", e.stderr.decode())
                except docker.errors.ImageNotFound:
                    _logger.error("Image not found.")
                except Exception as e:
                    _logger.error("Unexpected error:", str(e))

def execute_container_by_agregator(args):
    client = docker.from_env()

    # get container volume paths
    dataset_folder_path = args.dataset_folder
    participant_file_path = os.path.join(os.getcwd(), 'participants.txt')        
    case_id_folder_path = args.case_id_folder

    # Define the container volume mapping
    volumes = {
        dataset_folder_path: {
            'bind': '/app/data/input',
            'mode': 'rw'
        },
        participant_file_path: {
            'bind': '/app/participants.txt',
            'mode': 'rw'
        },
        case_id_folder_path: {
            'bind': '/app/data/output',
            'mode': 'rw'
        }
    }

    # Define the container command
    command = [
        'python', args.python_module,
        '--case-id', args.case_id,
        '--ml-models', args.ml_models,
        '--dataset-folder', 'data/input',
        '--participants-file', 'participants.txt',
        '--ml-sensors', args.ml_sensors,
        '--case-id-folder', 'data/output'
    ]

    try:
        # Run the container
        container = client.containers.run(
            name = 'aggregator',
            image = args.docker_image,
            user = '1000:1000',
            command = command,
            volumes = volumes,
            working_dir = '/app',            
            detach = True,
            stdout = True,
            stderr = True,
        )

        # Stream logs live
        for line in container.logs(stream=True):
            _logger.info(line.decode(), end='')
    except docker.errors.ContainerError as e:
        _logger.error("Container failed:", e.stderr.decode())
    except docker.errors.ImageNotFound:
        _logger.error("Image not found.")
    except Exception as e:
        _logger.error("Unexpected error:", str(e))
    finally:
        # remove the container and volume attached                
        container.remove(v=True, force=True)

def execute_container_by_trainer(args):
    client = docker.from_env()

    # get container volume paths
    dataset_folder_path = args.dataset_folder    
    case_id_folder_path = args.case_id_folder

    # Define the container volume mapping
    volumes = {
        dataset_folder_path: {
            'bind': '/app/data/input',
            'mode': 'rw'
        },
        case_id_folder_path: {
            'bind': '/app/data/output',
            'mode': 'rw'
        }
    }

    # Define the container command
    command = [
        'python', args.python_module,
        '--case-id', args.case_id,
        '--dataset-folder', 'data/input',        
        '--ml-models', args.ml_models,
        '--case-id-folder', 'data/output',        
        "--training-percent", args.training_percent    
    ]

    try:
        # Run the container
        container = client.containers.run(
            name = 'trainer',
            image = args.docker_image,
            user = '1000:1000',
            command = command,
            volumes = volumes,
            working_dir = '/app',            
            detach = True,
            stdout = True,
            stderr = True,
        )

        # Stream logs live
        for line in container.logs(stream=True):
            _logger.info(line.decode(), end='')
    except docker.errors.ContainerError as e:
        _logger.error("Container failed:", e.stderr.decode())
    except docker.errors.ImageNotFound:
        _logger.error("Image not found.")
    except Exception as e:
        _logger.error("Unexpected error:", str(e))
    finally:
        # remove the container and volume attached                
        container.remove(v=True, force=True)

def execute_container_by_tester(args):
    client = docker.from_env()

    # get container volume paths    
    case_id_folder_path = args.case_id_folder

    # Define the container volume mapping
    volumes = {
        case_id_folder_path: {
            'bind': '/app/data/output',
            'mode': 'rw'
        }
    }

    # Define the container command
    command = [
        'python', args.python_module,
        '--case-id', args.case_id,
        '--case-id-folder', 'data/output',        
        '--ml-models', args.ml_models,
        "--training-percent", args.training_percent    
    ]

    try:
        # Run the container
        container = client.containers.run(
            name = 'tester',
            image = args.docker_image,
            user = '1000:1000',
            command = command,
            volumes = volumes,
            working_dir = '/app',            
            detach = True,
            stdout = True,
            stderr = True,
        )

        # Stream logs live
        for line in container.logs(stream=True):
            _logger.info(line.decode(), end='')
    except docker.errors.ContainerError as e:
        _logger.error("Container failed:", e.stderr.decode())
    except docker.errors.ImageNotFound:
        _logger.error("Image not found.")
    except Exception as e:
        _logger.error("Unexpected error:", str(e))
    finally:
        # remove the container and volume attached                
        container.remove(v=True, force=True)

args = parse_args(sys.argv[1:])
setup_logging(args.loglevel)

_logger.info("Starting executor python module ...")

if args.python_module == "converter.py":
    _logger.info("Filtering files ...")
    input_files = filter_conveter_files(args)

    _logger.info("Execute Docker Python converter module ...")
    execute_container_by_converter(args, input_files)    
elif args.python_module == "windowed.py":
    _logger.info("Filtering files ...")
    input_files = filter_windowed_files(args)

    _logger.info("Execute Docker Python windowed module ...")
    execute_container_by_windowed(args, input_files) 
elif args.python_module == "windowing_mets.py":
    _logger.info("Filtering Mets files ...")
    input_files = filter_windowed_mets_files(args)

    _logger.info("Execute Docker Python windowed module ...")
    execute_container_by_windowed_mets(args, input_files)     
elif args.python_module == "aggregator.py":
    _logger.info("Execute Docker Python aggregator module ...")
    execute_container_by_agregator(args) 
elif args.python_module == "trainer.py":
    _logger.info("Execute Docker Python trainer module ...")
    execute_container_by_trainer(args) 
elif args.python_module == "tester.py":
    _logger.info("Execute Docker Python tester module ...")
    execute_container_by_tester(args) 
else:
    raise Exception("Python module not implemented")   

_logger.info("Ending executor python module ...")