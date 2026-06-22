# Enaro Home Assistant Integration

Diese Custom Integration verbindet Home Assistant mit Enaro.

Aktueller Umfang:

- pro Enaro-Haushalt automatisch eine eigene Home-Assistant-To-do-Liste
- Einkaufsartikel zwischen Home Assistant und Enaro synchronisieren
- Home-Assistant-Sensorregeln erstellen automatisch Enaro-Aufgaben

Beispiele:

- `todo.enaro_zuhause_einkauf`
- `todo.enaro_ferienwohnung_einkauf`
- Rauchmelder `unavailable` -> wichtige Enaro-Aufgabe

## Installation

1. Add-on-Repository `https://github.com/think-techDE/EnaroSync` in Home Assistant
   hinzufuegen.
2. Add-on **Enaro Integration** installieren und starten.
3. Home Assistant neu starten.
4. **Einstellungen > Geraete & Dienste > Integration hinzufuegen**.
5. `Enaro Integration` auswaehlen.
6. Enaro-API-URL, E-Mail und Passwort eintragen.

Fuer lokale Entwicklung kann dieser Ordner alternativ direkt nach
`config/custom_components/enaro_shopping` kopiert werden.

## Einkaufslisten

- Die Integration laedt alle Haushalte des Enaro-Nutzers.
- Fuer jeden Haushalt wird eine eigene `todo.*`-Entitaet angelegt.
- Artikel hinzufuegen, erledigen, wieder oeffnen, umbenennen und loeschen wird
  nach Enaro synchronisiert.

## Sensorregeln

Sensorregeln werden unter **Geraete & Dienste > Enaro Integration > Optionen**
verwaltet.
Jede Sensorregel erscheint zusaetzlich als eigene Home-Assistant-Entitaet: ein
Status-Sensor und ein Schalter zum Aktivieren oder Deaktivieren.
Fuer uebersichtliche Geraete- und Entitaetslisten kann jede Sensorregel einen
Anzeigenamen/Alias bekommen.

Pro Regel werden konfiguriert:

- HA-Entity
- Anzeigename/Alias
- Zielzustand aus den fuer diese Entity beobachteten Zustaenden, z. B.
  `unavailable`
- Enaro-Haushalt
- Enaro-Mitglied als Zuständiger
- ob die Aufgabe wichtig ist
- Aufgabentitel und Notiz

Beim Anlegen einer Regel wird zuerst die HA-Entity gewaehlt. Danach zeigt die
Integration die aktuellen und, falls Recorder/History aktiv ist, die in den
letzten 14 Tagen beobachteten Zustaende dieser Entity als Auswahl an. Wenn keine
Historie vorhanden ist, bleibt eine freie Eingabe moeglich.

Die Integration erstellt erst nach 5 Minuten stabilem Zielzustand eine Aufgabe
und nur einmal pro Stoerfall. Eine neue Aufgabe entsteht erst wieder, nachdem
die Entity den Zielzustand verlassen und spaeter erneut erreicht hat.

Wenn die Entity beim Einrichten oder Neustart bereits im Zielzustand ist, wird
`last_changed` beruecksichtigt. Besteht der Zustand schon laenger als 5 Minuten,
wird die Aufgabe direkt erstellt; andernfalls nach der verbleibenden Wartezeit.

## Warum Add-on plus Integration?

Home-Assistant-To-do-Listen sind Entitaeten, die von Integrationen
bereitgestellt werden. Ein Add-on allein kann keine nativen `todo.*`-Entitaeten
registrieren. Das Add-on installiert deshalb diese Integration aus derselben
Quelle.
