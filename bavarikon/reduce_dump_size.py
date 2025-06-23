import json
import logging


def remove_keys_from_entities(input_file, output_file, keys_to_remove):
    logging.info(f"Loading JSON data from {input_file}")
    with open(input_file, "r") as infile:
        data = json.load(infile)

    ids_to_extract = getattr(remove_keys_from_entities, "ids_to_extract", None)
    if ids_to_extract is not None:
        logging.info(f"Filtering entities by {len(ids_to_extract)} IDs...")
        before_count = len(data)
        data = [entity for entity in data if entity.get("ID") in ids_to_extract]
        logging.info(f"Filtered {before_count} entities down to {len(data)}.")
    else:
        logging.info(f"Processing all {len(data)} entities.")

    logging.info(f"Removing keys: {keys_to_remove}")
    for entity in data:
        for key in keys_to_remove:
            entity.pop(key, None)

    logging.info(f"Saving {len(data)} entities to {output_file}")
    with open(output_file, "w") as outfile:
        json.dump(data, outfile, indent=2)
    logging.info("Done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    keys_to_remove = ["shortText", "text", "bibliography"]
    # Example: set ids_to_extract to a list of IDs, or leave as None to process all
    # remove_keys_from_entities.ids_to_extract = ['id1', 'id2', ...]
    remove_keys_from_entities.ids_to_extract = [
        "0c728050-c5af-11e9-893a-a37e5cdc9651",
        "46d47900-c5ab-11e9-b229-6b499a37f581",
        "277fbb40-c5ac-11e9-893a-a37e5cdc9651",
    ]
    # For the full dataset
    # remove_keys_from_entities('dumps/deckenmalerei.eu/2025_02/entities.json', 'bavarikon/entities small.json', keys_to_remove)
