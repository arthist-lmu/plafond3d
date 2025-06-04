import json
import xml.etree.ElementTree as ET
from datetime import datetime

def load_json(filename):
    """Load JSON data from a file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def timestamp_to_iso(ts):
    """Convert a millisecond timestamp to ISO format."""
    try:
        return datetime.fromtimestamp(ts / 1000).isoformat()
    except Exception:
        return ""

def main():
    # Load JSON data
    entities = load_json('dumps/deckenmalerei.eu/2025_02/entities.json')
    try:
        relations = load_json('dumps/deckenmalerei.eu/2025_02/relations.json')
    except FileNotFoundError:
        relations = []
    try:
        resources = load_json('dumps/deckenmalerei.eu/2025_02/resources.json')
    except FileNotFoundError:
        resources = []

    # Build a lookup of entities by ID (to resolve linked authors, etc.)
    entities_by_id = {entity["ID"]: entity for entity in entities}

    # Create the XML root element with required attributes.
    # Adjust datenpaket_name and schema_version as needed.
    root = ET.Element("bavarikonDatenlieferung", {
        "datenpaket_name": "ExampleDatenpaket",
        "export_zeitstempel": datetime.now().isoformat(),
        "schema_version": "1.0.0"
    })

    # For each entity, create a Kulturobjekt element.
    for entity in entities:
        kulturobjekt = ET.SubElement(root, "Kulturobjekt")
        
        # bav01_bavarikonProjektnummer: use a default 4-digit project number.
        bav01 = ET.SubElement(kulturobjekt, "bav01_bavarikonProjektnummer")
        bav01.text = "0001"
        
        # bav02_LieferID: use the entity’s ID and add attribute typ="Datensatznummer"
        bav02 = ET.SubElement(kulturobjekt, "bav02_LieferID", {"typ": "Datensatznummer"})
        bav02.text = entity.get("ID", "")
        
        # bav03_AnzeigeID: (optional) – not used here.
        
        # bav04_DatenlieferndeInstitution: default value with required attribute.
        bav04 = ET.SubElement(kulturobjekt, "bav04_DatenlieferndeInstitution", {"gnd-id": "default_gnd"})
        bav04.text = "DefaultInstitution"
        
        # bav05_BestandshaltendeInstitution: default value.
        bav05 = ET.SubElement(kulturobjekt, "bav05_BestandshaltendeInstitution", {"gnd-id": "default_gnd"})
        bav05.text = "DefaultInstitution"
        
        # bav06_BeteiligteInstitution: (optional) – omitted in this example.
        
        # bav07_Titel_Name_Objektbezeichnung: map from the JSON appellation.
        bav07 = ET.SubElement(kulturobjekt, "bav07_Titel_Name_Objektbezeichnung")
        bav07.text = entity.get("appellation", "")
        
        # bav08_Alternativtitel: (optional) – omitted.
        
        # bav09_Beschreibungstext: (optional) – omitted.
        
        # bav10_Objektkategorie: assign a default category from the allowed enumeration.
        bav10 = ET.SubElement(kulturobjekt, "bav10_Objektkategorie")
        bav10.text = "Datensatz"
        
        # bav11_Schlagwort_Thema: use the JSON sType (or other field) with attribute typ="undefined" (as a fallback).
        bav11 = ET.SubElement(kulturobjekt, "bav11_Schlagwort_Thema", {"typ": "undefined"})
        bav11.text = entity.get("sType", "")
        
        # bav12_Ereignis: create an event element.
        # Here we use a default event typ "Entstehung" and add a Zeit element using the creationDate.
        bav12 = ET.SubElement(kulturobjekt, "bav12_Ereignis", {"typ": "Entstehung"})
        
        # Optionally, if a relation of type "AUTHORS" exists for this entity,
        # look up the related entity and add a Hauptverantwortlichkeit element.
        for rel in relations:
            if rel.get("ID") == entity.get("ID") and rel.get("sType") == "AUTHORS":
                related = entities_by_id.get(rel.get("relTar"))
                if related:
                    haupt = ET.SubElement(bav12, "Hauptverantwortlichkeit", {"typ": "Person"})
                    haupt.text = related.get("appellation", "")
                    break
        
        # Always add a Zeit element with the entity's creation date.
        zeit = ET.SubElement(bav12, "Zeit")
        zeit.text = timestamp_to_iso(entity.get("creationDate", 0))
        
        # bav13_Sprache: assign a default language.
        bav13 = ET.SubElement(kulturobjekt, "bav13_Sprache")
        bav13.text = "de"
        
        # bav14_Material: assign a default material description.
        bav14 = ET.SubElement(kulturobjekt, "bav14_Material")
        bav14.text = "unbekannt"
        
        # bav15_Umfang_Abmessungen_Laufzeit: (optional) – omitted.
        # bav16_Bemerkung: (optional) – omitted.
        
        # bav17_RechtedeklarationMetadaten: fixed value "CC0".
        bav17 = ET.SubElement(kulturobjekt, "bav17_RechtedeklarationMetadaten")
        bav17.text = "CC0"
        
        # bav18_RechtedeklarationBeschreibungstext: (optional) – omitted.
        # bav19_RechtedeklarationDigitalisat: (optional) – omitted.
        
        # bav20_Permalink_DigitalesObjekt and bav21_Dateinamen_Bilddateien:
        # If a resource (e.g. an image) exists, use its information.
        resource = next((res for res in resources if res.get("sType") == "IMAGE"), None)
        bav20 = ET.SubElement(kulturobjekt, "bav20_Permalink_DigitalesObjekt")
        bav20.text = resource.get("resProvider", "") if resource else ""
        bav21 = ET.SubElement(kulturobjekt, "bav21_Dateinamen_Bilddateien")
        bav21.text = resource.get("ID", "") if resource else ""
    
    # Build the ElementTree and write to file with XML declaration.
    tree = ET.ElementTree(root)
    tree.write("output.xml", encoding="UTF-8", xml_declaration=True)

if __name__ == '__main__':
    main()
