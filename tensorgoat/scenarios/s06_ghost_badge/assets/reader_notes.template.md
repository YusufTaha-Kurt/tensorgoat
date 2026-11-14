# Lobby badge reader: technician's notes

Halcyon Labs, facilities team. Internal.

## Badges

A badge is a punch card with {{GRID}} x {{GRID}} cells ({{CELLS}} in total).
Every cell is either punched or blank. Your badge is `{{HOLDER_ID}}`; its
pattern is in `my_badge.txt` (`#` punched, `.` blank, one line per row).

## How the reader sees a badge

The optical sensor does not see clean cells. It reports one brightness value
per cell, row by row from the top left:

- `1.0`  clearly punched
- `0.0`  clearly blank
- anything in between: a worn, dirty or half-covered cell

## Recognition model

The reader does not compare scans with stored patterns. A small model was
trained on a few dozen scans of every badge and answers with a confidence per
badge holder. It copes well with worn badges.

Diagnostic mode is still enabled from the installation week. In that mode the
reader accepts any scan over HTTP and returns all confidences, four decimals
each. Remember to switch it off.

## Vault door

The vault door is stricter than the lobby reader. It compares the presented
badge with the keyholder's enrolled pattern cell by cell and opens when at most
{{TOLERANCE}} cells differ (badges wear out).
