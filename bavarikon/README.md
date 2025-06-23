# Export the CbDD data to Bavarikon

This project tries to convert the exsiting CbDD dump into a format readable by bavarikon, according to this [example](bavarikon-Lieferformat.xsd).

We first reduce the size of the dump (plafond3d/dumps/deckenmalerei.eu/2025_02) using [this method](reduce_dump_size.py), then convert the json into the required xml.
