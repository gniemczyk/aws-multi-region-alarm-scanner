# Skaner Alarmów Chmury AWS (Multi-Region)

Lekki, bez-dependency skrypt Python, który wykorzystuje AWS CLI i wielowątkowość do szybkiego skanowania wszystkich aktywnych regionów AWS pod kątem alarmów CloudWatch w stanie `ALARM` — zapewniający wysokowydajne, współbieżne monitorowanie bez zewnętrznych zależności.

---

## 📌 Problem

Alarmy CloudWatch są **lokalizowane regionalnie**, co oznacza, że każde odpytanie musi być wykonane osobno dla każdego regionu. Ręczne sprawdzanie wielu regionów w konsoli AWS jest uciążliwe, a synchroniczne wywołania CLI (`for region in $(aws ec2 describe-regions ...)`) są wolne i niewygodne dla kont z 20+ regionami. To opóźnienie może znacząco wpłynąć na czas reakcji na incydenty — zwłaszcza gdy potrzebujesz kompletnego obrazu całego zasobu AWS w kilka sekund.

---

## 🚀 Kluczowe Funkcje

- **Brak Zależności**  
  Wykorzystuje tylko bibliotekę standardową Pythona (`subprocess`, `json`, `concurrent.futures`, `logging`, `os`). Nie wymaga instalacji `pip`.

- **Wysoka Wydajność dzięki Wielowątkowości**  
  Wykonuje współbieżne skanowanie regionów przy użyciu `ThreadPoolExecutor`, drastycznie skracając czas skanowania (złożoność O(1) vs O(n) czasu rzeczywistego).

- **Obsługa Wielu Profili**  
  Automatycznie wykrywa wszystkie profile AWS z `~/.aws/config` i pozwala na interaktywny wybór z fallbackiem do domyślnego. Obsługuje flagę `--profile`.

- **Bezpieczeństwo od Podstaw**  
  Opiera się na lokalnie skonfigurowanych poświadczeniach AWS CLI (`~/.aws/credentials`), unikając hardkodowanych sekretów lub zewnętrznych SDK.

- **Elastyczne Filtrowanie**  
  Skanuj wszystkie regiony lub filtruj do wybranego za pomocą `--region`.

- **Odporna Obsługa Błędów**  
  Zwinie radzi sobie z brakiem AWS CLI, błędami uprawnień IAM i uszkodzonymi odpowiedziami JSON — logując działające diagnozy bez awarii.

---

## 🛠️ Wymagania

- Python 3.6+ (z obsługą `subprocess` i `concurrent.futures`)
- AWS CLI (`aws`) zainstalowane i skonfigurowane przez `aws configure`
- Prawidłowe poświadczenia AWS z uprawnieniami `cloudwatch:DescribeAlarms` i `ec2:DescribeRegions`

---

## 💻 Użycie

```bash
# Klonowanie repozytorium
git clone https://github.com/<username>/aws-multi-region-alarm-scanner.git
cd aws-multi-region-alarm-scanner

# Uruchomienie skanera (brak zależności!)
python3 alarm-scanner.py
```

### Dostępne Argumenty

```bash
# Interaktywny wybór profilu (domyślnie)
python3 alarm-scanner.py

# Użycie konkretnego profilu (bez interakcji)
python3 alarm-scanner.py --profile prod
python3 alarm-scanner.py -p prod

# Skanowanie tylko wybranego regionu
python3 alarm-scanner.py --region us-east-1
python3 alarm-scanner.py -r eu-west-1

# Wyjście w formacie JSON
python3 alarm-scanner.py --json

# Pomiń wyświetlanie regionów bez alarmów
python3 alarm-scanner.py --no-ok

# Kombinacja: konkretny profil, jeden region, bez "OK"
python3 alarm-scanner.py --profile prod --region us-east-1 --no-ok
```

---

## Przykład Wyjścia

### Tryb Tabelaryczny (domyślny)

```
Dostępne profile AWS:
  1. default (domyślny: eu-central-1)

Wybierz numer profilu (Enter = domyślny): 

Sprawdzanie 17 regionów (Wielkowątkowość)...
Profil: default
---------------------------------------------------------------------------
REGION          | STAN       | NAZWA ALARMU
---------------------------------------------------------------------------
us-east-1       | ALARM      | high-cpu-alarm-prod
us-west-2       | ALARM      | disk-space-critical
eu-west-1       | OK         | Brak aktywnych alarmów
ap-southeast-1  | ERROR      | Błąd CLI: An error occurred (UnauthorizedOperation)
...
---------------------------------------------------------------------------

[ALERT] Znaleziono łącznie 2 aktywnych alarmów!
```

### Tryb JSON

```bash
$ python3 alarm-scanner.py --json --profile prod
```

```json
[
  {
    "region": "us-east-1",
    "status": "ALARM",
    "alarms": [
      {
        "name": "high-cpu-alarm-prod",
        "state": "ALARM"
      }
    ],
    "error": null
  },
  {
    "region": "us-west-2",
    "status": "OK",
    "alarms": [],
    "error": null
  }
]
```

---

## 🔮 Przyszłe Ulepszenia

- Filtrowanie po nazwach alarmów (regex)
- Integracja z webhookami Slack/Teams dla natychmiastowych alertów
- Eksport wyników do CSV dla raportowania i CI/CD
- Dodanie kontroli timeout i logiki retry dla niestabilnych połączeń
- Walidacja uprawnień IAM przed skanowaniem

---

## 📄 Licencja

Licencja MIT — szczegóły w pliku [LICENSE](LICENSE).
