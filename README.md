# Description

Python module to:

- **Parse** recursively a folder with telemetry (accelerometer) BIN files to CSV format files using the accelerometers Python propietary module.
- **Generate datasets and graphical analysis** from IMUs CSV telemetry (accelerometer) and activity register files from several participants to be used to train machine learning models.

## Prepare environment

To activate virtual enviroment
```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

To deactivate virtual enviroment
```
$ deact

 ## Python Module Description

1. To run the python module to **parse** bin to csv accelerometer files we have these arguments:

    - **docker-image**: is the docker image to be used for parse BIN IMUs file to CSV files.
    - **python-module**: is the python module inside the docker image to be executed.
    - **root-data-folder**: the root data folder where the executor will parse these BIN files from each participant.

    To convert all BIN files for all participants root data folder `/home/simur/git/uniovi-simur-wearablepermed-data` using the docker image `ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0` execute this command:

    ```
    python3 main.py \
    -vv \
    --docker-image ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0 \
    --python-module converter.py \
    --data-folder /home/simur/git/uniovi-simur-wearablepermed-data
    ```

2. To run the python module to **generate datasets** from previous csv files and activity registers for each participant we have these arguments:


    - **docker-image**: is the docker image to be used for aggregate BIN and activity registers.
    - **python-module**: is the python module inside the docker image to be executed.
    - **root-data-folder**: the root data folder where the aggregator will generage the final datasets to be used to train our machine learning models: convolutional and reinforced machine learning. By default only the dataset to train convolutional machine learning models will be created.
    - **make-feature-extractions**: this optional argument permit create also the feature extractions dataset to train reinforced machine learning models.

    To generate datasets for all participants root data folder `/home/simur/git/uniovi-simur-wearablepermed-data` using the docker image `ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0` to create datasets to train convolutional and reinforced machine learning, execute this command:

    ```
    python3 main.py \
    -vv \
    --docker-image ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0 \
    --python-module aggregator.py \
    --bin-folder /home/simur/git/uniovi-simur-wearablepermed-data
    --make-feature-extractions
    ```