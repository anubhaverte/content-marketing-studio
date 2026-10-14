# Test data

Generate the fixtures from the repository root:

```powershell
python studio\design_tools\make_test_photos.py
python studio\design_tools\make_test_csv.py
```

`test_people.csv` has exactly 250 deterministic records and is saved as UTF-8
with BOM for spreadsheet compatibility. Its columns (`name`, `role`, `id`,
`team`, `photo`, `email`) exercise missing optional values, misspelled roles,
duplicate identifiers, multilingual text, and very short and long names.

## Tricky cases by teammate

| Fixture case | What it tests | Teammate |
| --- | --- | --- |
| Long, short, Devanagari, Gujarati, French, German, and Spanish names | Validation accepts text content; card renderer measures and fits varied names | Person 1: validation; Person 2: text fit |
| 8 unknown or misspelled role values | Role validation and graceful handling of unsupported roles | Person 1: validation |
| 5 duplicate ID pairs and 10 empty IDs | Uniqueness and required-field validation | Person 1: validation |
| 10 empty teams and 15 empty photo values | Optional-field and missing-photo handling | Person 1: validation; Person 2: photo handling |
| 20 normal portraits reused by CSV rows | Standard photo loading and rendering | Person 2: photo handling |
| 2 tiny portraits | Minimum image dimensions and upscaling behavior | Person 2: photo handling |
| 2 high-compression 4000x5000 portraits | Large-dimension decoding and memory/resource handling | Person 2: photo handling |
| 2 square and 2 landscape portraits | Unexpected aspect ratios and crop behavior | Person 2: photo handling |
| `broken.jpg` contains plain text, not image data | Corrupt/unreadable image error handling | Person 2: photo handling |

All valid photo references use filenames generated in `photos/`. The
intentional `broken.jpg` is also referenced so unreadable-image behavior can be
tested. Placeholder images contain only colored backgrounds and short labels;
they do not depict real people. The photo generator enforces a total size below
5 MiB.
