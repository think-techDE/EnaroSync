# Enaro Shopping Integration

Dieses Add-on ist der einzige Installationspunkt fuer die Enaro-Einkaufslisten
in Home Assistant.

Es installiert oder aktualisiert die Custom Integration `enaro_shopping` unter
`/config/custom_components/enaro_shopping`. Die Integration stellt danach pro
Enaro-Haushalt automatisch eine eigene Home-Assistant-To-do-Liste bereit.

Beispiele:

- `todo.enaro_zuhause_einkauf`
- `todo.enaro_ferienwohnung_einkauf`

## Installation

1. Home Assistant: **Einstellungen > Add-ons > Add-on-Store**.
2. Oben rechts **Repositorys** oeffnen.
3. Repository-URL eintragen:
   `https://github.com/think-techDE/EnaroSync`
4. Add-on **Enaro Shopping Integration** installieren.
5. Add-on starten.
6. Home Assistant neu starten, falls `restart_homeassistant` nicht aktiviert war.
7. **Einstellungen > Geraete & Dienste > Integration hinzufuegen**.
8. `Enaro Shopping` auswaehlen und Enaro-API-URL, E-Mail und Passwort eintragen.

Danach erscheinen automatisch eigene To-do-Entitaeten fuer alle Enaro-Haushalte,
auf die dieser Enaro-Nutzer Zugriff hat.

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
- Enaro bleibt Quelle fuer Haushalte, Rechte und Einkaufslisten.
- Die Integration pollt aktuell alle 60 Sekunden.

## Warum Add-on plus Integration?

Home-Assistant-To-do-Listen sind Entitaeten und muessen von einer Integration
bereitgestellt werden. Ein Add-on allein kann keine nativen `todo.*`-Entitaeten
registrieren. Dieses Add-on sorgt deshalb fuer die einfache Installation aus
einer Quelle und installiert die eigentliche Integration automatisch.
