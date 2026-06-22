# Enaro Integration

Dieses Add-on ist der einzige Installationspunkt fuer die Enaro-Funktionen in
Home Assistant.

Es installiert oder aktualisiert die Custom Integration `enaro_shopping` unter
`/config/custom_components/enaro_shopping`. Die Integration stellt danach pro
Enaro-Haushalt automatisch eine eigene Home-Assistant-To-do-Liste bereit und
kann aus Home-Assistant-Sensorzustaenden automatisch Enaro-Aufgaben erstellen.

Beispiele:

- `todo.enaro_zuhause_einkauf`
- `todo.enaro_ferienwohnung_einkauf`
- Rauchmelder `unavailable` -> wichtige Enaro-Aufgabe fuer eine Person

## Installation

1. Home Assistant: **Einstellungen > Add-ons > Add-on-Store**.
2. Oben rechts **Repositorys** oeffnen.
3. Repository-URL eintragen:
   `https://github.com/think-techDE/EnaroSync`
4. Add-on **Enaro Integration** installieren.
5. Add-on starten.
6. Home Assistant neu starten, falls `restart_homeassistant` nicht aktiviert war.
7. **Einstellungen > Geraete & Dienste > Integration hinzufuegen**.
8. `Enaro Integration` auswaehlen und Enaro-API-URL, E-Mail und Passwort eintragen.

Danach erscheinen automatisch eigene To-do-Entitaeten fuer alle Enaro-Haushalte,
auf die dieser Enaro-Nutzer Zugriff hat.

Das Add-on beendet sich nach dem Kopieren der Integration absichtlich. Es muss
nicht dauerhaft laufen und wird nur fuer Installation oder Updates erneut
gestartet.

## Add-on-Optionen

```yaml
log_level: info
restart_homeassistant: false
```

- `restart_homeassistant`: Wenn `true`, loest das Add-on nach dem Kopieren der
  Integration einen Home-Assistant-Neustart aus. Standard bleibt `false`, damit
  nichts unerwartet neu startet.

## Verhalten der Integration

- Ein Enaro-Haushalt = eine HA-To-do-Entitaet.
- Artikel in HA anlegen, erledigen, wieder oeffnen, umbenennen und loeschen
  wird nach Enaro synchronisiert.
- Sensorregeln werden unter **Geraete & Dienste > Enaro Integration > Optionen**
  gepflegt.
- Pro Sensorregel wird nach 5 Minuten stabilem Zielzustand genau eine
  Enaro-Aufgabe fuer den gewaehlten Stoerfall erstellt.
- Enaro bleibt Quelle fuer Haushalte, Rechte, Einkaufslisten und Aufgaben.
- Die Einkaufslisten-Integration pollt aktuell alle 60 Sekunden.

## Sensorregeln

Eine Regel besteht aus:

- Home-Assistant-Entity, z. B. Rauchmelder-Sensor
- Zielzustand aus den fuer diese Entity beobachteten Zustaenden, z. B.
  `unavailable`
- Enaro-Haushalt
- Enaro-Mitglied als Zuständiger
- optional `Wichtig`
- Aufgabentitel und Notiz-Vorlage

Beim Anlegen einer Regel prueft die Integration zuerst den aktuellen Zustand der
ausgewaehlten Entity. Wenn Home Assistant Recorder/History aktiv ist, werden
zusaetzlich die in den letzten 14 Tagen gespeicherten Zustaende ausgewertet und
als Auswahl angeboten. Falls keine Historie vorhanden ist, bleibt eine freie
Eingabe moeglich.

Vorlagen koennen diese Platzhalter nutzen:

- `{entity_id}`
- `{entity_name}`
- `{state}`
- `{triggered_at}`

## Warum Add-on plus Integration?

Home-Assistant-To-do-Listen sind Entitaeten und muessen von einer Integration
bereitgestellt werden. Ein Add-on allein kann keine nativen `todo.*`-Entitaeten
registrieren. Dieses Add-on sorgt deshalb fuer die einfache Installation aus
einer Quelle und installiert die eigentliche Integration automatisch.
