## USAGE ##

`squash.py` contains the SQLite interface, through the `sqlite3` module.

`formats.py` defines the database entry formats (`DataFormat.structure`), along
with a parser function to process ADC pedestal/gain calibration test data.

`helper.py` connects the SQLite interface and the database format, and provides
a few convenience functions that can be used to script access to the database.

`pumpkin.py` is the `tkinter` graphical interface.

        python pumpkin.py

`analysis.py` contains examples of how to process data files and draw various
plots independent of the graphical interface.

## REQUIREMENTS ##

`python` version 3.6 and above is required to interact with the database
(including running analysis scripts), while version 3.7 and above is required
to use the `pumpkin.py` `tkinter` interface.

### SETTING UP A VIRTUAL ENVIRONMENT ###

Setting up a python virtual environment is recommended, to avoid module version
conflicts with the default environment.

        ENV_DIR=<path to working directory>
        python -m venv $ENV_DIR

The virtual environment can be activated,

        cd $ENV_DIR
        source bin/activate

and deactivated (the `$ENV_DIR/bin` directory is placed into the `$PATH` upon
activation):

        deactivate

### INSTALLING MODULES ###

With the virtual environment activated,

        pip install -r requirements.txt
