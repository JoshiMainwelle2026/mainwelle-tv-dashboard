# Mainwelle Regional-Dashboard

Ein sich selbst aktualisierendes TV-Dashboard mit den aktuellen
Regional-Nachrichten von mainwelle.de – im Mainwelle-Design, gedacht für
den Redaktionsfernseher.

Wie es funktioniert:
- Ein Python-Script (`scraper/scrape_news.py`) liest alle 15 Minuten
  automatisch über GitHub Actions die Regional-Nachrichten-Seite von
  mainwelle.de aus und schreibt sie nach `docs/news.json`.
- `docs/index.html` ist die eigentliche Anzeigeseite. Sie lädt `news.json`
  alle 2 Minuten neu, zeigt die Schlagzeilen groß im Wechsel an und lässt
  unten einen Nachrichtenticker durchlaufen.
- GitHub Pages veröffentlicht den Ordner `docs/` als ganz normale Webseite,
  die der Fernseher später einfach aufruft.

Es läuft kein eigener Server bei euch – GitHub übernimmt kostenlos das
regelmäßige Abrufen und Hosten. Es ist kein bezahlter Drittanbieter
involviert.

## 1. Einrichtung (einmalig)

1. Erstellt ein neues, öffentliches GitHub-Repository (z. B.
   `mainwelle-tv-dashboard`). Es muss öffentlich sein, damit GitHub Pages
   und die kostenlosen Actions-Minuten ohne Limit funktionieren.
2. Ladet den kompletten Inhalt dieses Ordners in das Repo hoch (z. B. per
   `git push` oder Drag & Drop im Browser).
3. Unter **Settings → Actions → General → Workflow permissions**:
   *"Read and write permissions"* aktivieren (damit die Action
   `docs/news.json` committen darf).
4. Unter **Settings → Pages**: als Quelle *"Deploy from a branch"*,
   Branch `main`, Ordner `/docs` auswählen und speichern.
5. Unter dem Reiter **Actions** den Workflow *"Mainwelle Dashboard
   aktualisieren"* einmal manuell starten (Button *"Run workflow"*), damit
   `news.json` gleich mit echten Daten gefüllt wird, statt auf die nächste
   15-Minuten-Marke zu warten.
6. Nach 1–2 Minuten ist die Seite erreichbar unter:
   `https://<euer-github-name>.github.io/<repo-name>/`

Das ist die URL, die ihr auf dem Fernseher öffnet.

## 2. Falls der Scraper einmal leer läuft

Die Nachrichtenseite von mainwelle.de lädt ihre Inhalte per JavaScript
nach, deshalb nutzt der Scraper einen Headless-Browser (Playwright) statt
eines einfachen HTTP-Requests. Ändert sich der Aufbau der Seite einmal
grundlegend, kann es sein, dass keine Meldungen mehr gefunden werden.
Erkennbar ist das an einer Warnung im Log des jeweiligen Action-Laufs
(Reiter *Actions*). In dem Fall:

```
pip install -r scraper/requirements.txt
python -m playwright install chromium
python scraper/scrape_news.py --debug
```

Das erzeugt eine `debug_page.html`, an der man sehen kann, wie die Seite
aktuell aufgebaut ist, und die Selektoren in `scrape_news.py` entsprechend
anpassen kann.

## 3. Automatisches Öffnen auf dem Samsung-Fernseher

Wichtig zu wissen: Der eingebaute Tizen-Browser von Samsung-Fernsehern hat
**keine echte Zeitplan-Funktion** für "öffne diese URL um 18:00 Uhr" – das
ist eine reine Betriebssystem-Einschränkung, kein Problem der Webseite
selbst. Es gibt zwei Bausteine, die zusammen nah an das gewünschte
Verhalten herankommen:

**a) Immer auf der richtigen Seite starten**
- Fernseher-Browser öffnen → die Dashboard-URL aufrufen.
- Falls euer Modell eine Startseiten-Einstellung im Browser hat
  (Browser-Menü → Einstellungen), dort die Dashboard-URL als Startseite
  eintragen.
- Unter **Einstellungen → Allgemein → Smart-Funktionen → "Letzte App
  automatisch ausführen"** aktivieren. Dann öffnet der Fernseher nach
  jedem Ein-/Ausschalten wieder die zuletzt genutzte App – lasst dafür den
  Browser beim Ausschalten einfach auf der Dashboard-Seite geöffnet.

**b) Zeitgesteuertes Umschalten, während der Fernseher schon läuft**
- Das geht nur über die **SmartThings-App** (Smartphone), *nicht* über das
  TV-Menü selbst: SmartThings → Gerät (euer Fernseher) → Routinen → "Wenn
  Uhrzeit X erreicht ist" → Aktion. Ob dort eine Aktion wie "App öffnen"
  für den Browser mit fester URL zur Verfügung steht, hängt vom TV-Modell
  und der SmartThings-Version ab – das müsst ihr direkt an eurem Gerät
  ausprobieren, das kann ich von hier aus nicht für ein bestimmtes Modell
  garantieren.
- Falls das an eurem Modell nicht klappt: Da der Fernseher ohnehin
  durchgehend läuft, ist die robusteste Lösung, den Browser-Tab dauerhaft
  auf der Dashboard-Seite offen zu lassen – sie aktualisiert sich ja von
  allein. Für ein zuverlässiges *zeitgesteuertes Umschalten* zwischen
  mehreren Quellen bräuchtet ihr eigentlich ein kleines Zusatzgerät (z. B.
  Fire TV Stick), das per Kiosk-Browser und Cronjob exakt das kann – das
  hattet ihr aber bewusst ausgeschlossen, deshalb hier nur als Hinweis für
  später, falls es doch nicht zuverlässig klappt.
