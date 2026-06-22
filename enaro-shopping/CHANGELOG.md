# Changelog

## 0.2.5

- Sensorregeln erscheinen jetzt als Home-Assistant-Entitaeten unter der Enaro
  Integration.
- Pro Sensorregel gibt es eine Status-Entitaet und einen Schalter zum
  Aktivieren oder Deaktivieren.
- Sensorregel-Status zeigt Zielzustand, aktuellen Zustand, letzte erzeugte
  Aufgabe und Stoerfallstatus als Attribute.

## 0.2.4

- Sensorregeln senden bei Automations-Aufgaben jetzt auch dann eine
  Enaro-Benachrichtigung, wenn der technische Enaro-Account selbst zustaendig
  ist.
- Home Assistant zeigt nach erfolgreicher oder fehlgeschlagener
  Sensorregel-Ausloesung eine persistente Enaro-Meldung an.

## 0.2.3

- Add-on und Integration enthalten jetzt Enaro-Icon und Enaro-Logo fuer eine
  professionellere Darstellung in Home Assistant.

## 0.2.2

- Sensorregeln beruecksichtigen jetzt auch Zielzustaende, die beim Einrichten
  oder Neustart bereits bestehen.
- Wenn der Zustand schon laenger als die Debounce-Zeit besteht, wird die
  Enaro-Aufgabe direkt nach dem Laden der Integration erstellt; sonst nach der
  verbleibenden Debounce-Zeit.

## 0.2.1

- Sensorregeln schlagen Zielzustaende jetzt aus den zuletzt beobachteten
  Home-Assistant-Zustaenden der gewaehlten Entity vor.
- Die aktuelle Entity-State wird immer beruecksichtigt; bei aktiviertem Recorder
  werden zusaetzlich die letzten 14 Tage ausgewertet.

## 0.2.0

- Sichtbare Umbenennung zu **Enaro Integration** bei kompatiblem internen Slug.
- Neue Sensorregeln erstellen nach stabilem Home-Assistant-Zielzustand
  automatisch Enaro-Aufgaben fuer ausgewaehlte Haushaltsmitglieder.
- Bestehende Einkaufslisten-To-do-Entitaeten bleiben erhalten.

## 0.1.0

- Erstes Add-on fuer Enaro-Einkaufslisten in Home Assistant.
- Installiert die Custom Integration `enaro_shopping` aus einer Quelle.
- Die Integration stellt pro Enaro-Haushalt automatisch eine eigene
  Home-Assistant-To-do-Entitaet bereit.
- Artikel anlegen, bearbeiten, erledigen, wieder oeffnen und loeschen wird nach
  Enaro synchronisiert.
