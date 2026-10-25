# Pflanzenschutz: Daten erweitern

Die Anwendung läuft ohne Build-Schritt als statische App. HTML/CSS/JavaScript
und strukturierte JSON-Daten sind getrennt. Keine Supabase-Migration nötig.

## Schadbild ergänzen

In `data/diseases.json` unter `diseases` ein bestehendes Profil kopieren.
`id` dauerhaft eindeutig halten, beispielsweise `neues-schadbild`.

Erforderliche Felder:

| Feld | Inhalt |
| --- | --- |
| `name`, `scientific`, `summary` | Anzeigename, Fachbezeichnung, Kurzbeschreibung |
| `category` | `pilze`, `schaedlinge`, `naehrstoffe`, `umwelt`, `sonstige` |
| `organs` | Auswahl aus Blatt, Traube, Geschein, Trieb, Holz, Wurzel, Tier |
| `symptoms`, `confusions`, `prevention` | Listen kurzer Aussagen |
| `cause`, `weather` | Ursache und begünstigende Umstände |
| `bio`, `conventional` | Getrennte Maßnahmen; keine unbestätigte Mittelzulassung behaupten |
| `bioSubstances`, `substances` | Verfahren/Wirkstoffe für BIO bzw. Konventionell |
| `sources` | Liste aus `title` und offizieller `url` |
| `images` | Bilder mit Quelle, Urheber und Lizenz; leere Liste ist zulässig |
| `reviewed` | Datum der redaktionellen Prüfung als YYYY-MM-DD |

Die Suche umfasst Name, Fachbezeichnung, Kurzbeschreibung, Merkmale und Bildtitel.
Die Kategorieauswahl und die Bilderübersicht übernehmen neue Profile automatisch.

## Fotos ergänzen

Nur echte, eindeutig zugeordnete Vergleichsaufnahmen mit geklärten Rechten
verwenden. Die Standorte des eigenen Betriebs können später gezielt mit eigenen
Fotos ergänzt werden. Keine fremden Bilder einfach von Suchmaschinen kopieren.

Die Bilddatei unter `assets/photos/` speichern. Im Profil unter `images`:

```json
{
  "src": "assets/photos/neues-schadbild-blatt.jpg",
  "caption": "Präzise Beschreibung der Aufnahme",
  "credit": "Name des Fotografen / der Institution",
  "license": "Eigene Aufnahme, Veröffentlichung freigegeben",
  "licenseUrl": "",
  "source": "https://offizielle-quellseite.example/",
  "original": "https://offizielle-quellseite.example/bild.jpg",
  "organs": ["Blatt"],
  "modified": false
}
```

Dasselbe Bild auch in `data/credits.json` aufnehmen. Bei eigenen Bildern ohne
Webquelle sollte eine geeignete öffentliche Nachweisseite angegeben werden;
die Anwendung verlinkt nur gültige https-Adressen. Bilder möglichst kleiner als
1 MB und mindestens etwa 1000 Pixel an der längeren Seite halten. Bildnachweise,
Wasserzeichen und diagnostische Details erhalten. Bearbeitungen kennzeichnen.

## Mittel aktualisieren

`data/products.json` enthält den am 25.10.2026 recherchierten BVL-Monatsbestand
vom 01.10.2026 für 18 ausgewählte Handelsprodukte. Es findet keine automatische
Nachprüfung statt. Neue Produkte nicht allein aus alten PDF-Tabellen oder
aufgrund eines Wirkstoffnamens hinzufügen.

1. Aktuellen BVL-Eintrag einschließlich Anwendungsnummer prüfen.
2. Kultur, Verwendungszweck (Kelter-/Tafeltrauben), Freiland und berufliche
   Anwendung prüfen. Anwendungsende und aktuelle Widerrufe berücksichtigen.
3. Pro `applications`-Eintrag Aufwandmenge, Einheit, Entwicklungsstadium,
   Wasseraufwand, Wartezeit, Häufigkeit und sämtliche Auflagen zusammenhalten.
4. `diseaseIds` nur bei tatsächlich passender Indikation setzen.
5. `modes: ["bio","konventionell"]` nur als begründeten Öko-Kandidaten verwenden,
   `bioCandidate`, `bioStatus` und `bioSource` nachvollziehbar setzen. BIO-Recht,
   Verband und Kontrollstelle bleiben eine zusätzliche Prüfung.
6. BVL- und PS-Info-Originallinks sowie Daten-/Abrufdatum aktualisieren.
7. Keine Tagesaktualität behaupten, wenn nur ein Monatsdatenbestand vorliegt.

Die Mengenangaben dienen dem Nachschlagen, nicht als Dosierrechner. Einheiten je
Laubwandfläche keinesfalls automatisch in Mengen je Hektar Grundfläche umdeuten.

## Prüfen und veröffentlichen

Mit Python 3 (keine Zusatzpakete):

```sh
python3 tools/validate.py
```

Vor dem Hochladen außerdem die geänderten Profile im Browser prüfen.
Bei Änderungen `VERSION` in `service-worker.js` erhöhen, etwa von
`pflanzenschutz-v1` auf `pflanzenschutz-v2`. Der Cache ist ausschließlich für
Pflanzenschutz zuständig; andere App-Caches werden nicht gelöscht.
Beim Öffnen werden aktuelle Dateien bevorzugt über das Netz geladen,
bei fehlender Verbindung dienen bereits geladene Dateien als Rückfall.
Es gibt keine Garantie, dass sämtliche Bilder nach einem ersten kurzen Besuch
offline vorliegen; Fotos werden erst nach ihrem Aufruf zwischengespeichert.

Das Manifest verwendet relative Start- und Scope-Adressen. Deshalb kann der
Ordnerinhalt in einem eigenen Repository veröffentlicht werden. App-Links in
der Haupt-App müssen zur tatsächlichen Veröffentlichungsadresse passen.
