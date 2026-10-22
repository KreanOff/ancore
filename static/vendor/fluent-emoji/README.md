# Fluent Emoji 3D — lokalna biblioteka Ancore

3145 emoji i wariantów, 9 kategorii, 13 arkuszy WebP po 16×16 kafelków 64px.
Katalog i obrazy zajmują łącznie ok. 5 MiB. Aplikacja nie używa CDN; katalog
jest pobierany dopiero po otwarciu pickera. Wygląd pochodzi z tych samych
obrazów na każdym systemie. Obrazy źródłowe przeskalowano i spakowano do atlasów.

- Obrazy i metadane: [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji),
  commit `1ffb34c752ecf5d402f04cfb4b392c77f57c54bc`, licencja MIT w `LICENSE-MICROSOFT`.
- Polskie nazwy i słowa kluczowe: [Unicode CLDR 48](https://github.com/unicode-org/cldr/tree/release-48/common),
  `annotations/pl.xml` i `annotationsDerived/pl.xml`, licencja w `LICENSE-UNICODE`.

Generator: `scripts/assets/build_fluent_emoji.py`. Wymaga Pillow tylko podczas
generowania; aplikacja nie ma nowej zależności wykonawczej. Wejścia i SHA-256
są przypięte w generatorze. Pobierz archiwum przypiętego commita Microsoftu,
dwa pliki CLDR oraz jego `LICENSE`, a następnie uruchom:

```sh
python scripts/assets/build_fluent_emoji.py fluent.tar.gz pl.xml pl-derived.xml CLDR-LICENSE
```

Wartości Unicode są trwałymi identyfikatorami wyborów. Wiersze `sheet/x/y`
określają pozycję grafiki; nie są zapisywane w rekordach użytkownika.
Aktualizacja biblioteki musi zachować zapisane wartości lub dodać ich aliasy.
