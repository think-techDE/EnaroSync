# Enaro Shopping Home Assistant Integration

Diese Custom Integration stellt pro Enaro-Haushalt automatisch eine eigene
Home-Assistant-To-do-Liste bereit.

Beispiel:

- `todo.enaro_zuhause_einkauf`
- `todo.enaro_ferienwohnung_einkauf`

Damit ist kein manuelles Mapping auf vorhandene HA-To-do-Listen noetig.

## Installation

1. Add-on-Repository `https://github.com/think-techDE/EnaroSync` in Home Assistant
   hinzufuegen.
2. Add-on **Enaro Shopping Integration** installieren und starten.
3. Home Assistant neu starten.
4. **Einstellungen > Geraete & Dienste > Integration hinzufuegen**.
5. `Enaro Shopping` auswaehlen.
6. Enaro-API-URL, E-Mail und Passwort eintragen.

Fuer lokale Entwicklung kann dieser Ordner alternativ direkt nach
`config/custom_components/enaro_shopping` kopiert werden.

## Verhalten

- Die Integration laedt alle Haushalte des Enaro-Nutzers.
- Fuer jeden Haushalt wird eine eigene `todo.*`-Entitaet angelegt.
- Artikel hinzufuegen, erledigen, wieder oeffnen, umbenennen und loeschen wird
  nach Enaro synchronisiert.
- Enaro bleibt die Quelle fuer Einkaufslisten und Haushaltsrechte.
- Die Integration pollt aktuell alle 60 Sekunden.

## Warum Add-on plus Integration?

Home-Assistant-To-do-Listen sind Entitaeten, die von Integrationen
bereitgestellt werden. Ein Add-on allein kann keine nativen `todo.*`-Entitaeten
registrieren. Das Add-on installiert deshalb diese Integration aus derselben
Quelle.
