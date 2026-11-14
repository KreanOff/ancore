# Tapeta aplikacji, baner profilu i wcześniejsze warianty

## Tapeta aplikacji: biel, czerwień i czerń

`wallpaper-red-black-white.png` jest tapetą wspólnej powłoki aplikacji
i stron logowania, rejestracji, tworzenia oraz wyboru Workspace, podłączoną przez
`--app-shell-wallpaper-image`. Te ekrany korzystają z lokalnego aliasu `--app-wallpaper-image` na
`body.auth-page--wallpaper`, dodawanym przez ich szablony.
Tapeta zachowuje abstrakcyjne fałdy
poprzedniej tapety, z przewagą bieli, czerwonymi wstęgami i czarnymi akcentami.
Jasna górna część zapewnia czytelne tło ciemnych kontrolek. Obraz skaluje się
przez `cover` i jest wyrównany do lewej i środka. Panele pozostają białe.

Wariant utworzono wbudowanym Image Gen na podstawie
`wallpaper-fluent-bloom-light-4k.webp`. Zachowano natywny wynik PNG
o wymiarach **1672 × 941 pikseli**, bez zmiany rozdzielczości.
Poprzedni obraz pozostaje domyślnym banerem profilu. Dołączanie do
Workspace oraz karty zespołów bez zdjęcia zachowują
jednolite tło, bez tapety i matowego szkła.

Prompt użyty we wbudowanym Image Gen:

> Use case: style-transfer. Asset type: full-screen wallpaper behind a light productivity application. Edit target: the referenced existing abstract folded-satin bloom wallpaper. Preserve its sculptural flowing folds, soft 3D material, broad elegant curves, wide 16:9 composition and overall placement. Change the color palette only to WHITE, RED and BLACK, with white and pearl-gray dominant, a few confident saturated Ancore red (#df2b2b) ribbons, and restrained deep charcoal/black folds and shadows. Remove every blue, violet, lavender and pink hue. Keep the upper 15% of the entire image light white or pale gray and visually quiet so dark toolbar icons remain legible on desktop and mobile; concentrate red and black sculptural folds lower down and along the left/middle. Bright diffuse studio lighting, refined matte satin finish, no harsh glare. Output a clean full-bleed landscape wallpaper, ideally 3840x2160 if supported. No text, no logos, no letters, no UI, no border or watermark. Opaque background.

## Domyślny baner profilu i poprzednia tapeta: jasne fałdy

`wallpaper-fluent-bloom-light-4k.webp` pozostaje domyślnym osobistym banerem
profilu użytkownika bez własnego obrazu. Adres przekazuje
[`backend/accounts/frontend.py`](../../../backend/accounts/frontend.py).
Wspólna powłoka aplikacji korzysta teraz z osobnego wariantu
biało-czerwono-czarnego opisanego powyżej.

To autorska, abstrakcyjna kompozycja błękitno-lawendowych fałd inspirowana
tapetami Windows 11. Nie zawiera logo, tekstu ani elementów interfejsu.
Baner profilu kadruje obraz przez `object-fit: cover` w proporcjach 4:1;
logo i formularze pozostają osobnymi elementami HTML/React.

Grafikę wygenerowano wbudowanym Image Gen. Źródło ma 1672 × 941 pikseli;
eksport WebP ma dokładnie **3840 × 2160 pikseli**, 2 642 594 bajty
i bezstratne kodowanie. Użyto powiększenia Lanczos3 z minimalnym dopasowaniem
do 16:9. To plik o wymiarach 4K, a nie natywna generacja szczegółów w 4K.

Historyczny prompt użyty we wbudowanym Image Gen, opisujący pierwotne
przeznaczenie obrazu jako tapety:

> Use case: stylized-concept. Asset type: full-screen desktop wallpaper for Ancore, shared by a
> light login screen and translucent application navigation. Primary request: an original elegant
> abstract wallpaper inspired by the soft sculptural bloom and folded ribbons of Windows 11 desktop
> backgrounds. Create a completely new composition of broad flowing folded translucent satin /
> frosted glass sheets, curling organically into a graceful sculptural bloom on the left and center,
> with generous calm negative space on the right for a login form. The folds must read as a refined
> dimensional abstract material, with smooth continuous ridges, softly lit overlapping layers, no
> landscape or dunes. Color palette: luminous icy blue, periwinkle, soft cobalt, lavender and a
> restrained purple center, fading into a very light pearl blue background. Keep the overall image
> bright and airy, with rich enough blue-violet fold definition to remain beautiful through a white
> frosted glass overlay. Soft diffuse daylight, subtle ambient shadows and reflections, polished
> premium operating-system wallpaper quality, no harsh glare or neon. Keep the upper-left region
> light enough for a dark gray wordmark. Composition must work as a full-bleed 16:9 landscape
> wallpaper at 3840 x 2160 UHD; request that exact size when available. No text, no letters, no
> logos, no Windows symbol, no interface, no border, no watermark.

## Poprzednie warianty: wydmy

`wallpaper-violet-dunes-light-4k.webp` zachowuje poprzednią jasną tapetę
w perłowej bieli, chłodnej szarości i bladej lawendzie.
`wallpaper-violet-dunes-4k.webp` to wcześniejsza ciemna wersja.
Oba warianty powstały przez edycję we wbudowanym Image Gen, który zwrócił
obrazy 1672 × 941 pikseli. Eksporty 3840 × 2160 przygotowano przez
powiększenie filtrem Lanczos3 i bezstratne kodowanie WebP.
Są to pliki o wymiarach 4K, a nie natywna generacja szczegółów w 4K.

Prompt jasnego wariantu użyty we wbudowanym Image Gen:

> Edit target: supplied Ancore dark purple dunes wallpaper. Create its LIGHT
> MODE counterpart. Preserve the same dune contours, arrangement of low
> sweeping horizontal layered waves, delicate fine matte texture, calm negative
> space in the upper half, and exact wide 16:9 composition. Change only the
> lighting and palette: high-key pearl white, very light cool gray and pale
> lavender, with restrained soft violet shadows on the dune slopes. The whole
> wallpaper must be bright and airy, including the top and right side; no
> midnight navy, black or dark purple regions. Keep enough subtle lavender
> shape definition to remain an elegant wallpaper behind a white login form
> panel. Quiet studio daylight, smooth tonal transitions, no glare or glowing
> neon edges. No text, logos, UI, stars or extra objects. Output at 3840 x 2160
> UHD 4K if available. This is the same scene in daylight, not a new scene.

Prompt wcześniejszej ciemnej wersji:

> Edit target: the supplied violet/navy dunes wallpaper. Change ONLY output
> resolution and fine detail. Deliver a true UHD 4K image at EXACTLY 3840 pixels
> wide by 2160 pixels tall (16:9), not a small preview. Regenerate the fine matte
> surface texture and delicate lavender rim lighting at 4K detail. Preserve the
> same dune contours, the same low horizontal layered waves across the lower
> left, midnight navy upper negative space, rich aubergine/lavender palette,
> dark quiet right side for the login panel, and the original calm lighting.
> Accommodate the wider 16:9 aspect by extending the scene naturally at the
> sides; do not crop away the important dunes or add new objects. No interface,
> no text, no logo, no stars, no watermark. Required final raster dimensions:
> 3840 x 2160 pixels, full image at UHD 4K resolution.
