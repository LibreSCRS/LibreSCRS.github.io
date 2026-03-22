---
layout: "simple"
title: "Read Your Card"
description: "Supported smart cards, auto-detection, and how LibreCelik displays card data"
---

LibreCelik automatically detects the type of card you insert and displays the appropriate data. No manual configuration is required — just insert your card and the application handles the rest.

## Supported cards

| Card | Data shown |
|------|-----------|
| Serbian eID (Gemalto 2014+ / IF2020 Foreigner) | Personal data, document info, photo, digital signature certificates, PIN management |
| Vehicle registration (EU Directive 2003/127/EC) | Owner, vehicle data, registration dates — core fields interoperable across EU-compliant cards |
| Health insurance card (RFZO) | Insured person, employer, insurance details |
| PKS Chamber of Commerce | Qualified signature certificates, PIN management |
| eMRTD e-passports | Personal data, photo, MRZ, data groups — requires BAC or PACE authentication |

The plugin architecture makes it straightforward to add support for new card types — both at the middleware level (card communication) and GUI level (data display).

---

## How auto-detection works

When a card is inserted into the reader, LibreCelik:

1. Detects the card event via `smartcard::Monitor` (PC/SC polling in LibreMiddleware)
2. Queries all middleware plugins — first by ATR, then by live connection probe
3. The highest-ranked plugin reads the card data
4. Displays the data using the matching GUI plugin

If no plugin recognizes the card, LibreCelik shows a message indicating the card type is not supported.

---

## Language

LibreCelik supports English and Serbian (Cyrillic). Change the language via the menu in the top-right corner. Card data is displayed as stored on the card — typically in the language of the issuing country.

---

## Printing

All card data views support printing. Use **File** > **Print** or the print button to generate a formatted printout of the displayed card data.
