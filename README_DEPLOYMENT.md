# Geister Custom Catalog Generator — Deployment Guide

## Überblick

Web-App zur Erstellung kundenspezifischer Geister Produktkatalog-PDFs.
Extrahiert originale Katalogseiten mit allen Bildern und hebt gewünschte
Artikel hervor.

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `webapp.py` | Flask Web-App (UI + API) |
| `geister_custom_catalog.py` | PDF-Generator (Kernlogik) |
| `Dockerfile` | Docker-Container für Deployment |
| `*.pdf` | Geister Produktkatalog-Quelldateien |
| `article_index_cache.json` | Gecachter Artikel-Index (wird auto-generiert) |

## Schnellstart (Lokal)

```bash
# Python 3.10+ erforderlich
pip install flask pypdf pdfplumber reportlab

# Starten
python3 webapp.py

# Öffnen: http://localhost:5000
```

## Deployment mit Docker

```bash
# Image bauen (im Ordner mit allen PDFs + Skripten)
docker build -t geister-catalog .

# Container starten
docker run -d -p 5000:5000 --name geister-catalog geister-catalog

# Öffnen: http://localhost:5000
```

## Cloud Deployment

### Option A: Railway.app (einfachstes Deployment)

1. Repository auf GitHub erstellen mit allen Dateien
2. Auf [railway.app](https://railway.app) einloggen
3. "New Project" → "Deploy from GitHub repo"
4. Railway erkennt das Dockerfile automatisch
5. Port 5000 konfigurieren → fertig, Link wird generiert

### Option B: Hetzner VPS

1. VPS bestellen (CX22 reicht, ~4€/Monat)
2. Docker installieren: `apt install docker.io`
3. Dateien hochladen (scp/rsync)
4. `docker build` + `docker run` (siehe oben)
5. Nginx als Reverse-Proxy mit SSL (Let's Encrypt)

### Option C: Fly.io

```bash
fly launch
fly deploy
```

## Neue Kataloge hinzufügen

1. Neue PDF-Datei in den App-Ordner legen
2. `article_index_cache.json` löschen
3. App neu starten (Index wird automatisch neu aufgebaut)

Bei Docker: Image neu bauen und deployen.

## Technische Details

- **24 Kataloge**, ~6785 Artikel indexiert
- **Index-Aufbau**: ~10 Minuten (einmalig, wird gecached)
- **PDF-Generierung**: 2-10 Sekunden pro Katalog
- **Speicherbedarf**: ~500MB (hauptsächlich die Quell-PDFs)
- **Python-Dependencies**: flask, pypdf, pdfplumber, reportlab
