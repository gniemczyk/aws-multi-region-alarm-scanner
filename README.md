# AWS CloudWatch Skaner Alarmów (Multi-Region)

Lekki skrypt Python bez zależności, który wykorzystuje AWS CLI i wielowątkowość do szybkiego skanowania wszystkich aktywnych regionów AWS pod kątem alarmów CloudWatch.

---

## 📌 Problem

Alarmy CloudWatch są lokalizowane regionalnie — każde odpytanie musi być wykonane osobno. Sprawdzanie wielu regionów ręcznie jest uciążliwe, a synchroniczne skrypty są wolne. Potrzebujesz kompletnego obrazu całego zasobu AWS w kilka sekund.

---

## 🚀 Kluczowe Funkcje

- **Brak Zależności** — tylko biblioteka standardowa Pythona
- **Wielowątkowość** — skanuje wszystkie regiony współbieżnie
- **Wszystkie Stany** — wyświetla OK, ALARM, INSUFFICIENT_DATA
- **Elastyczne Filtrowanie** — `--skip-ok`, `--skip-alarm`, `--only-state`, itp.
- **Bezpieczeństwo** — używa lokalnych poświadczeń AWS CLI
- **Odporna Obsługa Błędów** — bez awarii przy błędach uprawnień

---

## 🛠️ Wymagania

- Python 3.6+
- AWS CLI skonfigurowany (`aws configure`)
- Uprawnienia: `cloudwatch:DescribeAlarms` i `ec2:DescribeRegions`

---

## 🧪 Testy

```bash
pytest tests/test-alarm-scanner.py
```

---

## 💻 Szybki Start

```bash
python3 alarm-scanner.py
```

### Argumenty

```bash
python3 alarm-scanner.py --profile prod          # Konkretny profil
python3 alarm-scanner.py --region us-east-1      # Jeden region
python3 alarm-scanner.py --skip-ok                # Pokaż tylko problemy
python3 alarm-scanner.py --only-state ALARM      # Tylko ALARM
python3 alarm-scanner.py --json                  # Format JSON
```

---

## Przykład Wyjścia

### Tabelarycznie

```
Sprawdzanie 17 regionów (Wielkowątkowość)...
Profil: default
---------------------------------------------------------------------------
REGION          | STAN       | NAZWA ALARMU
---------------------------------------------------------------------------
us-east-1       | ALARM      | high-cpu-alarm-prod
us-west-2       | OK         | disk-space-monitor
eu-west-1       | OK         | Brak alarmów
---------------------------------------------------------------------------

[ALERT] Znaleziono łącznie 1 alarm w stanie ALARM!
```

### JSON

```bash
$ python3 alarm-scanner.py --json
```

```json
[
  {
    "region": "eu-central-1",
    "status": "ALARM",
    "alarms": [{"name": "high-cpu-alarm-prod", "state": "ALARM"}],
    "error": null
  }
]
```
---
**Autor:** Grzegorz N  
**Data:** Czerwiec 2026
