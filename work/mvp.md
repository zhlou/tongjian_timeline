# Goal
The purpose of this project is to generate a MVP interactive web app that allow browsing Zizhi Tongjian using multiple index.

## Multi index
The web app needs to support at least the following indices
- dynasty name: e.g. 周
- volume name: e.g. 周纪一
- era name: e.g. 威烈王
- era name + year: e.g. 威烈王二十三年, 建武元年 (include era name if there is no regin title)
- western year: e.g. 123 AD
The data structure should be flexible so we can add other index later.

## Data
The data to get started is in `semantic_json`. But it needs some ETL.

## Web app
- The backend should use python
- The front end should be straight html, css, javascript, with minimal dependencies
- The indices are long, so make sure we can easily scroll and jump through these

## Open Questions
- Do we need some kind of database? Or should we load everything into client side? Or serve json files on demand?
- 