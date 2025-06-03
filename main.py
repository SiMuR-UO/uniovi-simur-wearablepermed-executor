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
        "-di",
        "--docker-image",
        required=True,
        dest="docker_image",
        help="Docker image",
    )
    parser.add_argument(
        "-rb",
        "--root-bin-folder",
        required=True,
        dest="root_bin_folder",
        help="Root BIN files folder",
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

def filter_files_export(args):
    for root, dirs, files in os.walk(args.root_bin_folder):
        for file in files:
            # get participant name           
            _, ext = os.path.splitext(file)         

            # get only activity registers
            if ext == ".BIN":
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
                    'python', 'converter.py',
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
        
_logger.info("Starting docker executor ...")

args = parse_args(sys.argv[1:])
setup_logging(args.loglevel)

_logger.info("Filering files to be export ...")
files_to_export = filter_files_export(args)

_logger.info("Execute Docker export ...")
execute_container(args, files_to_export)

_logger.info("Ending docker executor ...")