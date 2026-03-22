---
title: "Read Your Card"
description: "Supported smart cards, auto-detection, and how LibreCelik displays card data"
---

LibreCelik automatically detects the type of card you insert and displays the appropriate data. No manual configuration is required — just insert your card and the application handles the rest.

## Supported cards

| Card | Data shown |
|------|-----------|
| Serbian eID (Gemalto / IF2020) | Personal data, document info, digital signature certificates, PIN management |
| Vehicle registration | All fields including owner, vehicle, and registration dates |
| Health insurance card | Insured person, employer, insurance details |
| PKS Chamber of Commerce | Qualified signature certificates, PIN management |

Support for additional card types is planned through the plugin architecture.

---

## How auto-detection works

When a card is inserted into the reader, LibreCelik:

1. Detects the card event via PC/SC polling
2. Queries the card to determine its type (by ATR or AID)
3. Loads the appropriate card plugin to read the data
4. Displays the data using the matching GUI plugin

If no plugin recognizes the card, LibreCelik shows a message indicating the card type is not supported.

---

## Language

LibreCelik supports English and Serbian (Cyrillic). Change the language via the menu in the top-right corner. Card data is displayed as stored on the card — typically in the language of the issuing country.

---

## Printing

All card data views support printing. Use **File** > **Print** or the print button to generate a formatted printout of the displayed card data.
