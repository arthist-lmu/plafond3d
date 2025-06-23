
# CbDD to Bavarikon Export

This project converts the existing CbDD dump into a format readable by Bavarikon, following the [Bavarikon-Lieferformat.xsd](bavarikon-Lieferformat.xsd) schema.

---

## Table of Contents

- [Overview](#overview)
- [Libraries Used](#libraries-used)
- [Code Structure](#code-structure)
- [Workflow](#workflow)
- [Example Output](#example-output)

---

## Overview

The workflow consists of two main steps:

1. **Reduce the size of the CbDD dump** (see [`reduce_dump_size.py`](reduce_dump_size.py))
2. **Convert the reduced JSON to the required XML format** (see [`map_to_xml.py`](map_to_xml.py))

---

## Libraries Used

- **Python Standard Library**: `json`, `os`, `logging`, etc.
- **lxml**: For XML generation and validation (install with `poetry add lxml`)

---

## Code Structure

- [`reduce_dump_size.py`](reduce_dump_size.py):
  - Removes large or unnecessary fields from the original JSON dump.
  - Optionally filters entities by a list of IDs.
- [`map_to_xml.py`](map_to_xml.py):
  - Converts the reduced JSON to XML according to the Bavarikon schema.
- [`bavarikon-Lieferformat.xsd`](bavarikon-Lieferformat.xsd):
  - The XML Schema Definition (XSD) describing the required output format.
- [`test.xsd`](test.xsd):
  - Example/test file for schema and output structure.

---

## Workflow

1. **Reduce the JSON dump:**

   ```bash
   poetry run python reduce_dump_size.py
   # Output: entities small.json
   ```

2. **Convert to XML:**

   ```bash
   poetry run python map_to_xml.py
   # Output: bavarikon.xml
   ```

---

## Example Output

Below is an example of a `<Kulturobjekt>` element as required by Bavarikon:

```xml
<Kulturobjekt>
  <bav01_bavarikonProjektnummer>1234</bav01_bavarikonProjektnummer>
  <bav02_LieferID typ="Datensatznummer">277fbb40-c5ac-11e9-893a-a37e5cdc9651</bav02_LieferID>
  <bav03_AnzeigeID typ="Inventarnummer">A-001</bav03_AnzeigeID>
  <bav04_DatenlieferndeInstitution gnd-id="GND-0001">Staatliche Museen</bav04_DatenlieferndeInstitution>
  <bav05_BestandshaltendeInstitution gnd-id="GND-0002">Kunstsammlung</bav05_BestandshaltendeInstitution>
  <bav06_BeteiligteInstitution gnd-id="GND-0003">Restaurierungswerkstatt</bav06_BeteiligteInstitution>
  <bav07_Titel_Name_Objektbezeichnung>Landschaftsdarstellungen u.a. mit Jagdszenen und Jahreszeitenzyklus</bav07_Titel_Name_Objektbezeichnung>
  <bav08_Alternativtitel>Jahreszeiten und Jagd</bav08_Alternativtitel>
  <bav09_Beschreibungstext>
    <deutsch>Wandmalerei mit verschiedenen Landschaftsdarstellungen, Jagdszenen und einem Zyklus der Jahreszeiten.</deutsch>
    <englisch>Wall painting with various landscapes, hunting scenes, and a cycle of the seasons.</englisch>
    <Autorenangabe>Dr. Mustermann</Autorenangabe>
  </bav09_Beschreibungstext>
  <bav10_Objektkategorie>Malerei</bav10_Objektkategorie>
  <bav11_Schlagwort_Thema typ="Sachbegriff">Wandmalerei</bav11_Schlagwort_Thema>
  <bav12_Ereignis typ="Entstehung">
    <Zeit>1776-1778</Zeit>
  </bav12_Ereignis>
  <bav13_Sprache>de</bav13_Sprache>
  <bav14_Material>Farbe auf Putz</bav14_Material>
  <bav15_Umfang_Abmessungen_Laufzeit>ca. 3 x 5 m</bav15_Umfang_Abmessungen_Laufzeit>
  <bav16_Bemerkung>Teilweise restauriert</bav16_Bemerkung>
  <bav17_RechtedeklarationMetadaten>CC0</bav17_RechtedeklarationMetadaten>
  <bav18_RechtedeklarationBeschreibungstext>CC BY 4.0</bav18_RechtedeklarationBeschreibungstext>
  <bav19_RechtedeklarationDigitalisat>CC BY 4.0</bav19_RechtedeklarationDigitalisat>
  <bav20_Permalink_DigitalesObjekt>https://www.example.org/objekt/277fbb40-c5ac-11e9-893a-a37e5cdc9651</bav20_Permalink_DigitalesObjekt>
  <bav21_Dateinamen_Bilddateien>bild1.jpg bild2.jpg</bav21_Dateinamen_Bilddateien>
</Kulturobjekt>
```
