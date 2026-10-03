# Auftragswartezeit

Man misst den Zeitabstand zwischen dem Auftrag und dem ccu-request.

```text
Auftragswartezeit =
Zeitpunkt des ersten Modul-/FTS-Auftrags - ccu/order/request.payload.timestamp
```

Hier würde man je nach Auftragstyp unterscheiden.

# FTS

## Auslesen, ob der FTS am Fahren ist

Hier ist es am Zuverlässigsten den Boolean-Wert `driving` aus dem FTS-State zu verwenden, um festzustellen, ob der FTS fährt oder nicht. Da dieser Wert jedoch nur in bestimmten Intervallen gemessen wird, kann es zu Ungenauigkeiten von mehreren Sekunden kommen.

## Wann wurde der Auftrag erstellt

Weiterhin kann `fts/order` betrachtet werden, um weitere Hinweise auf Wartezeiten etc zu erhalten. Dies muss jedoch weiter analysiert werden.

## Wartezeit für Be- und Entladen

Bei dem FTS-State existiert der Boolean-Wert `waitingForLoadHandling`.

# Werkstückübergabe zwischen FTS und Modul

Ka ob das überhaupt geht

# Fehler getrennt Analysieren

Modul-State

- `payload.errors[].timestamp`
- `payload.errors[].errorType`
- `payload.errors[].errorLevel`
- `payload.errors[].errorReferences[]`
