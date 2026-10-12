# Klassengame / Neon Arena

Ein lokales 2D-Arena-Spiel mit Pygame. Du kannst solo gegen Bots kämpfen oder
mit einer zweiten Person im selben WLAN über LAN duellieren.

## Überblick

- 3 spielbare Brawler mit unterschiedlicher Geschwindigkeit, Health und Damage
- Einzelspieler gegen KI-Bots
- Mehrspieler-Modus über TCP im lokalen Netzwerk
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
2. Klicke auf `ALLEIN SPIELEN`.
3. Besiege 10 Gegner und sammle die Power Cubes ein.

### LAN-Multiplayer

1. Ein Spieler startet als Host (`LAN SPIEL HOSTEN`).
2. Der Host teilt die im Menü angezeigte lokale IP-Adresse mit.
3. Der zweite Spieler gibt diese IP in `HOST-IP` ein und klickt auf
   `LAN SPIEL BEITRETEN`.
4. Sobald beide verbunden sind, beginnt das Match.

Hinweis: Die Verbindung nutzt TCP-Port `50505`. Der Host muss möglicherweise die
Windows-Firewall für private Netzwerke erlauben.

## Steuerung

| Taste / Eingabe | Aktion |
| --- | --- |
| `W`, `A`, `S`, `D` | Bewegen |
| Pfeiltasten | Alternative Bewegung |
| Linke Maustaste gedrückt halten | Zielen und Schießen |
| `Leertaste` | Dash / Super-Attacke |
| `Esc` | Spiel beenden |
| `R` | Nach dem Sieg oder Verlust neu starten |
| `1`, `2`, `3` | Brawler im Menü auswählen |
| `Enter` | Im Menü starten |

## Brawler

- `NOVA`: ausgewogen, stabiler Energieschuss
- `VOLT`: schnell, hohe Feuerrate, agiler Bewegungsstil
- `BRUTUS`: langsam aber robust mit starkem Schaden

## Power Cubes

Besiegte Gegner lassen grüne Power Cubes fallen. Wenn du einen Cube sammelst,
werden deine maximale Gesundheit und dein Angriff verstärkt. Treffer auf Gegner
laden außerdem die Superanzeige auf.

## Projektstruktur

- `main.py` – Spiel-Logik, Grafik, Steuerung, Bots und LAN-Verbindung
- `requirements.txt` – Python-Abhängigkeiten
- `README.md` – Installations- und Bedienungsanleitung

## Verifikation

Das Projekt wurde mit einem kurzen Smoke-Test geprüft:

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
