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
$ deactivate
```

 ## Python Module Description

1. To run the python module to **parse** bin to csv accelerometer files we have these arguments:

    - **docker-image**: is the docker image to be used for parse BIN IMUs file to CSV files.
    - **python-module**: is the python module inside the docker image to be executed.
    - **data-folder**: the root data folder where the executor will parse these BIN files from each participant.

    To convert all BIN files for all participants root data folder `/mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/input` using the docker image `ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0` execute this command:

    Using python command:
    ```
    $ python3 main.py \
    -vv \
    --docker-image ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0 \
    --python-module converter.py \
    --data-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/input
    ```

    Using docker image:

    ```
    $ docker run \
    --rm \
    -v /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data:/app/data \
    uniovi-simur-wearablepermed-hmc:1.0.0 \
    python converter.py \
    --data-folder data/input
    ```

2. To run the python module to **windowed datasets** from previous csv files and activity registers for each participant we have these arguments:

    - **docker-image**: is the docker image to be used for aggregate BIN and activity registers.
    - **python-module**: is the python module inside the docker image to be executed.
    - **dataset-folder**: the root data folder where the windowed will generate the final datasets to be used to aggregate for our machine learning models: convolutional and reinforced machine learning. By default only the dataset to train convolutional machine learning models will be created.
    - **make-feature-extractions**: this optional argument permit create also the feature extractions dataset to train reinforced machine learning models.

    To generate datasets for all participants root data folder `/mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/input` using the docker image `ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0` to create datasets to train convolutional and reinforced machine learning, execute this command:

    Using python command:
    ```
    $ python3 main.py \
    --docker-image ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0 \
    --python-module windowed.py \
    --dataset-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/input
    --make-feature-extractions
    ```

    Using docker image:

    ```
    $ docker run \
    --rm \
    -v /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data:/app/data \
    uniovi-simur-wearablepermed-hmc:1.0.0 \
    python windowed.py \
    --dataset-folder data/input \
    --make-feature-extractions
    ```

3. To run the python module to **aggregator** from previous datasets to be aggregated for final trianing:

    Using python command:

    ```
    $ python3 main.py \
    --docker-image uniovi-simur-wearablepermed-hmc:1.0.0 \
    --python-module aggregator.py \
    --case-id case_05 \
    --ml-models CAPTURE24 \
    --dataset-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/input \
    --participants-file participants.txt \
    --ml-sensors thigh,wrist \
    --case-id-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/output
    ```

    Using docker image:

    ```
    $ docker run \
    --rm \
    -v /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data:/app/data \
    -v /home/simur/git/uniovi-simur-wearablepermed-executor/participants.txt:/app/participants.txt \
    uniovi-simur-wearablepermed-hmc:1.0.0 \
    python aggregator.py \
    --case-id case_05 \
    --ml-models CAPTURE24 \
    --dataset-folder data/input \
    --participants-file participants.txt \
    --ml-sensors thigh,wrist \
    --case-id-folder data/output
    ```

4. To run the python module to **trainer** from previous Datasets:

    Using python command:

    ```
    $ python3 main.py \
    --docker-image uniovi-simur-wearablepermed-ml:1.0.0 \
    --python-module trainer.py \
    --case-id case_06 \
    --case-id-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/output \
    --ml-models RandomForest \
    --dataset-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/input \
    --training-percent 70
    ```

    Using docker image:

    ```
    $ docker run \
    --rm \
    -v /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data:/app/data \
    uniovi-simur-wearablepermed-ml:1.0.0 \
    python trainer.py \
    --case-id case_06 \
    --case-id-folder data/output \
    --ml-models RandomForest \
    --dataset-folder data/input \
    --training-percent 70  
    ```

5. To run the python module to **tester** from previous ML:

    Using python command:

    ```
    $ python3 main.py \
    --docker-image uniovi-simur-wearablepermed-ml:1.0.0 \
    --python-module tester.py \
    --case-id case_06 \
    --ml-models RandomForest \
    --case-id-folder /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data/output \        
    ```

    Using docker image:

    ```
    $ docker run \
    --rm \
    -v /mnt/nvme1n2/git/uniovi-simur-wearablepermed-data:/app/data \
    uniovi-simur-wearablepermed-ml:1.0.0 \
    python tester.py \
    --case-id case_06 \
    --ml-models RandomForest \
    --case-id-folder data/output    
    ```