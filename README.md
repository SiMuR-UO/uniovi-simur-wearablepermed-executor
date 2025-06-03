# Description

Uniovi Simur WearablePerMed Docker Executor

 ## Execute

To run the executos we must pass two arguments to our python module `main.py`

- **docker-image**: represente the docker image to be used for parse BIN IMUs file to CSV files
- **root-bin-folder**: the folder where the executor will parse these BIN files. The CSVs parsed will be saved in the same folder of the original BIN one.

```
python3 main.py -vv --docker-image ofertoio/uniovi-simur-wearablepermed-hmc:1.0.0 --root-bin-folder /home/simur/git/uniovi-simur-wearablepermed-data
```