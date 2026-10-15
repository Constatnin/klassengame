# Klassengame / Neon Arena

Ein lokales 2D-Arena-Spiel mit Pygame. Du kannst solo gegen Bots kämpfen oder
mit bis zu vier weiteren Personen im selben WLAN im LAN gegeneinander antreten.

## Überblick

- 5 spielbare Brawler mit unterschiedlicher Geschwindigkeit, Health und Damage
- Einzelspieler gegen KI-Bots
- LAN-Mehrspieler für bis zu 5 Personen (Host plus vier Mitspieler)
- Zwei auswählbare Arenen mit unterschiedlichen Hindernissen und Farben
- Freie Fenstergröße und umschaltbarer Vollbildmodus
- Power Cubes, Super-Attacken, Dash und Gegner-Spawn-System
- Einfache, feste Steuerung ohne externe Abhängigkeiten außer Pygame

## Voraussetzungen

- Python 3.10 oder neuer
- Windows, Linux oder macOS
- Für LAN-Modus: dasselbe lokale Netzwerk wie der andere Spieler

## Installation

Im Projektordner:

```powershell
python -m pip install -r requirements.txt
```

Falls `python` nicht gefunden wird, nutze unter Windows stattdessen:

```powershell
py -m pip install -r requirements.txt
```

## Spiel starten

```powershell
python main.py
```

Alternativ unter Windows:

```powershell
py main.py
```

## Spielmodi

### Solo

1. Wähle einen Brawler im Menü aus.
2. Wähle mit den Schaltflächen `<` und `>` neben dem Arena-Namen oder mit `Q`/`E` eine Map aus.
3. Klicke auf `SOLO SPIELEN`.
4. Besiege 10 Gegner und sammle die Power Cubes ein.

### LAN-Multiplayer

1. Der Host wählt die Arena aus und erstellt eine Lobby (`LAN-MATCH HOSTEN`).
2. Der Host teilt die im Menü angezeigte IPv4-Adresse mit.
3. Der zweite Spieler klickt auf `HOST-IP`, gibt die IPv4-Adresse ein und klickt auf
   `LAN-MATCH BEITRETEN`.
4. Mit dem ersten Mitspieler beginnt das Match. Insgesamt können Host und bis zu
   vier Clients mitspielen; weitere Clients können auch während des Matches
   beitreten.

Beide Geräte müssen im selben lokalen Netzwerk sein. `127.0.0.1` funktioniert
nur, wenn Host und Client auf demselben Rechner laufen. Die Verbindung nutzt
TCP-Port `50505`; der Host muss Python gegebenenfalls in der Windows-Firewall
für private Netzwerke zulassen.

## Steuerung

| Taste / Eingabe | Aktion |
| --- | --- |
| `W`, `A`, `S`, `D` | Bewegen |
| Pfeiltasten | Alternative Bewegung |
| Linke Maustaste gedrückt halten | Zielen und Schießen |
| `Leertaste` | Dash / Super-Attacke |
| `Esc` | Zurück ins Menü; im Menü beendet es das Spiel |
| `F11` | Vollbild ein-/ausschalten |
| `R` | Nach dem Sieg oder Verlust neu starten |
| `1` bis `5` | Brawler im Menü auswählen |
| `Q` / `E` | Arena im Menü wechseln |
| `Enter` | Im Menü starten |

## Brawler

- `NOVA`: ausgewogen, stabiler Energieschuss
- `VOLT`: schnell, hohe Feuerrate, agiler Bewegungsstil
- `BRUTUS`: langsam aber robust mit starkem Schaden
- `LYNX`: wendig und präzise
- `ORBIT`: ausgewogen mit starkem Plasmaschuss

Jeder Brawler hat eine eigene Superkraft. Die geladene Superkraft wird mit
`Leertaste` aktiviert; wenn die Superanzeige noch nicht voll ist, löst die Taste
stattdessen den Dash aus.

- `NOVA` – Nova-Impuls: trifft Gegner im Umkreis
- `VOLT` – Blitzsalve: feuert fünf schnelle Schüsse nach vorn
- `BRUTUS` – Bodenbrecher: hoher Schaden in einem großen Nahbereich
- `LYNX` – Phasensprung: stürmt vor und rammt Gegner am Zielpunkt
- `ORBIT` – Gravitationsfeld: zieht nahe Gegner heran und verletzt sie

Normale Angriffe verbrauchen Munition. Ist das Magazin leer, wird automatisch
nachgeladen. Die Magazingröße hängt vom Brawler ab:

| Brawler | Schüsse pro Magazin |
| --- | ---: |
| `NOVA` | 8 |
| `VOLT` | 12 |
| `BRUTUS` | 5 |
| `LYNX` | 7 |
| `ORBIT` | 6 |

VOLT verbraucht für seinen Doppelschuss jeweils zwei Schüsse. Superkräfte
verbrauchen keine normale Munition.

Das Spielfenster lässt sich an den Rändern größer oder kleiner ziehen. Mit
`F11` wechselst du zwischen Fenster- und Vollbildmodus; die zuletzt genutzte
Fenstergröße bleibt beim Zurückwechseln erhalten.

## Power Cubes

Grüne Power Cubes liegen in Holzkisten. Schieße auf eine Kiste, um sie zu
zerstören und den Cube freizulegen. Besiegte Gegner lassen ebenfalls Cubes
fallen. Wenn du einen Cube sammelst, werden deine maximale Gesundheit und dein
Angriff verstärkt. Treffer auf Gegner laden außerdem die Superanzeige auf.

## Arenen

- **Neon-Arena:** offene Wege und versetzte Deckungen.
- **Kristall-Labor:** kompaktere Korridore und geschützte Seitenwege.

Die Map wird im Hauptmenü mit den Schaltflächen `<` und `>` neben dem Namen oder
mit `Q`/`E` gewechselt. Im LAN bestimmt der Host die Arena; alle Mitspieler
erhalten dieselbe Map.

## Extras und Arena-Ereignisse

In der Arena erscheinen regelmäßig Bonus-Extras:

- **Heilung (`+`, grün):** stellt bis zu 35 Gesundheit wieder her.
- **Schild (`S`, blau):** verringert erlittenen Schaden für 7 Sekunden.
- **Schnellfeuer (`>>`, gelb):** verkürzt die Schusswartezeit für 8 Sekunden.

Die Sturmzone wird angekündigt, bevor sie aktiv wird. Während des Ereignisses
verursacht der rote Bereich regelmäßig Schaden; weiche ihm aus. Treffer werden
zusätzlich durch einen kurzen Bildschirmblitz und leichtes Bildschirmwackeln
hervorgehoben.

## Projektstruktur

- `main.py` – Spiel-Logik, Grafik, Steuerung, Bots und LAN-Verbindung
- `requirements.txt` – Python-Abhängigkeiten
- `README.md` – Installations- und Bedienungsanleitung

## Verifikation

Das Projekt kann mit der Syntaxprüfung und headless Regressionstests für Menü,
beide Arenen, Textboxen, Fenstergröße, Brawler, Munition, Kisten, Power-ups,
Sturmzone und LAN-Synchronisierung geprüft werden:

```powershell
python -m py_compile main.py
```

Zusätzlich wurde die Pygame-Initialisierung mit einem Dummy-Display validiert,
damit die Anwendung ohne sichtbare GUI gestartet werden kann.

## Troubleshooting

- Falls `pygame` nicht gefunden wird: `python -m pip install -r requirements.txt`
- Falls das Spiel im LAN-Modus nicht verbindet: prüfe Firewall und private
  Netzwerkeinstellung
- Falls das Fenster nicht angezeigt wird: prüfe, ob eine grafische Oberfläche
  verfügbar ist, oder starte den Spiel-Start in einer GUI-Umgebung
