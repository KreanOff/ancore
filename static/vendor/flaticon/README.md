# Flaticon UIcons

Lokalny podzbiór **UIcons Regular Rounded** i pełna gwiazdka **Solid Rounded** z oficjalnej paczki
[`@flaticon/flaticon-uicons` 3.3.1](https://www.npmjs.com/package/@flaticon/flaticon-uicons/v/3.3.1).
Źródło: [Freepik / Flaticon](https://github.com/freepik-company/flaticon-uicons).
Warunki dostawcy są zachowane w [LICENSE](LICENSE).

Kontury glifów oficjalnego pliku WOFF przekształcono do SVG o `viewBox="0 0 24 24"`.
Kształty pochodzą z Flaticon; aplikacja nie potrzebuje fontu ikon, npm ani CDN.
`uicons.js` zawiera tylko używane ikony i mapowanie stabilnych nazw aplikacji.
Osobne SVG służą checkboxom, strzałkom selectów, maskom statusów i krzyżykom
zamykania okien (`x-mask.svg`) w CSS.

Oznaczenie „Ikony UIcons: Flaticon” znajduje się w Ustawieniach.
[Instrukcja atrybucji](https://www.flaticon.com/uicons/get-started).

## Odtworzenie zestawu

Narzędzie budujące wymaga `fonttools` (wyłącznie podczas regenerowania).
Pobierz oficjalne archiwum:

```sh
curl -fL https://registry.npmjs.org/@flaticon/flaticon-uicons/-/flaticon-uicons-3.3.1.tgz -o /tmp/flaticon-uicons-3.3.1.tgz
python scripts/assets/build_flaticon_icons.py /tmp/flaticon-uicons-3.3.1.tgz
```

SHA256 archiwum: `2c7b6e3725241d3f00ad6345e6eed66b5b3625ff201fbb5bd14acbc057acc05f`.
Nazwy aplikacji i odpowiadające im ikony Flaticon definiuje
[`scripts/assets/flaticon-icon-map.json`](../../../scripts/assets/flaticon-icon-map.json).
Wartości bez prefiksu wskazują Regular Rounded; prefiks `solid:` wybiera
Solid Rounded (`star-filled` → `solid:star`).
Po zmianie mapowania odtwórz zasoby i podbij wersję ich importu w obu bazowych
szablonach. Nie edytuj ręcznie wygenerowanych ścieżek.
