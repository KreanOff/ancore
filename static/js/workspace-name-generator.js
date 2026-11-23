(function () {
    const workspaceNames = [
        'Biuro Latających Pierogów',
        'Sztab Kofeinowych Pingwinów',
        'Baza Turboślimaków',
        'Królestwo Zaginionych Długopisów',
        'Departament Dzielnych Kapibar',
        'Fabryka Genialnych Wymówek',
        'Centrum Dowodzenia Chomików',
        'Agencja Kosmicznych Ogórków',
        'Pracownia Tańczących Ziemniaków',
        'Klub Bardzo Zajętych Kotów',
        'Bunkier Ostatniego Ciastka',
        'Akademia Drzemek Strategicznych',
        'Liga Nieustraszonych Naleśników',
        'Biuro Spraw Prawie Pilnych',
        'Sztab Gumowych Kaczek',
        'Baza Tajnych Skarpetek',
        'Królestwo Wiecznej Przerwy',
        'Departament Kawy i Chaosu',
        'Fabryka Pomysłów z Kosmosu',
        'Centrum Dowodzenia Kanapek',
        'Agencja Sprytnych Leniwców',
        'Pracownia Mruczących Silników',
        'Klub Wędrujących Kubków',
        'Bunkier Zapomnianych Haseł',
        'Awaryjny Zapas Kawy',
        'Spółka z Ograniczoną Drzemką',
        'Narada u Wydry',
        'Biuro Poważnych Królików',
        'Komisja do Spraw Ciastek',
        'Piwnica Wielkich Planów',
        'Kwatera Sów po Godzinach',
        'Kawiarnia na Produkcji',
        'Pingwin w Marynarce',
        'Wydra z Kalendarzem',
        'Stacja po Drugiej Kawie',
        'Żółw przed Terminem',
        'Dział Krótkich Spotkań',
        'Pokój Cichego Chrupania',
        'Centrala Tajnych Tostów',
        'Turboherbata i Spółka',
        'Punkt Obsługi Kocyków',
        'Wąsaty Komitet',
        'Baza Podwodnych Pączków',
        'Hala Startowa Herbaty',
        'Orkiestra Myszek i Klawiatur',
        'Chomik na Dyżurze',
        'Rada Nadzorcza Szopów',
        'Słonie z Notatnikami',
        'Biuro Zapasowej Marchewki',
        'Klub Planowania na Serwetce',
        'Międzygalaktyczny Bufet',
        'Archiwum Zgubionych Wątków',
        'Studio Krzywych Wykresów',
        'Zajezdnia Pomysłów',
        'Port Wesołych Meduz',
        'Naleśnik na Orbicie',
        'Projekt Kawa na Wynos',
        'Ministerstwo Długich Przerw',
        'Tajny Związek Herbatników',
        'Panda od Pilnych Spraw',
        'Żaby na Wideokonferencji',
        'Pierogi w Delegacji',
        'Kalendarz Pełen Pączków',
        'Marchewka na Poniedziałek',
        'Ekipa od Drugiej Środy',
        'Wyprawa po Segregator',
        'Misja Ciepły Kaloryfer',
        'Poczta Szybkich Ślimaków',
        'Stół Okrągłych Gąbek',
        'Magazyn Pomysłów z Szuflady',
        'Awaria Kontrolowana',
        'Koło Wzajemnej Kofeiny',
        'Strażnicy Zapasowego Markera',
        'Cebule w Garniturach',
        'Ministerstwo Zbędnych Spotkań',
        'Instytut Znikających Zakładek',
        'Ośrodek Szkolenia Ośmiornic',
        'Orbitalna Stacja Ksero',
        'Kolektyw Kocich Klawiatur',
        'Ekspres do Rozwiązań',
        'Związek Zawodowy Kaktusów',
        'Kuratorium Puszystych Pomysłów',
        'Laboratorium Szalonych Tosterów',
        'Galeria Niedokończonych Slajdów',
        'Punkt Odbioru Dobrych Wieści',
        'Biuro Wczorajszego Jutra',
        'Naczelna Rada Niespodzianek',
        'Towarzystwo Radosnych Rabarbarów',
        'Tajna Siedziba Przecinków',
        'Gabinet Leczenia Poniedziałków',
        'Operacja Pusty Kalendarz',
        'Stołówka dla Robotów',
        'Zespół Obcych w Windzie',
        'Sejmik Krótkich Wiadomości',
        'Mistrzowie Pustej Skrzynki',
        'Misja Odzyskania Ładowarki',
        'Rezerwat Wolnych Kwadransów',
        'Dyrekcja Wielkiego Zszywacza',
        'Chór Zaspanych Robotów',
        'Izba Gospodarcza Wiewiórek',
    ];

    function suggest(currentName) {
        const name = currentName.trim();
        const suggestions = workspaceNames.filter((suggestion) => suggestion !== name);
        return suggestions[Math.floor(Math.random() * suggestions.length)];
    }

    function showButtons() {
        document.querySelectorAll('[data-workspace-name-generator][hidden]').forEach((button) => {
            button.hidden = false;
        });
    }

    window.AncoreWorkspaceNames = { suggest };

    // Uncontrolled fields keep their native input and validation listeners.
    document.addEventListener('click', (event) => {
        const button = event.target instanceof Element
            ? event.target.closest('[data-workspace-name-generator]')
            : null;
        if (!button || button.matches(':disabled')) return;
        const input = document.getElementById(button.getAttribute('aria-controls'));
        if (!(input instanceof HTMLInputElement) || input.matches(':disabled') || input.readOnly) return;

        input.value = suggest(input.value);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus({ preventScroll: true });
    });

    document.addEventListener('ancore:content-loaded', showButtons);
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showButtons, { once: true });
    } else {
        showButtons();
    }
})();
