#!/usr/bin/env python3
import argparse
import configparser
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Optional, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_aws_environment(profile: Optional[str] = None):
    """Sprawdza czy AWS CLI jest dostępne i czy poświadczenia są poprawne."""
    try:
        # Sprawdzenie dostępności aws cli
        subprocess.run(["aws", "--version"], capture_output=True, check=True, timeout=30)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("Błąd: AWS CLI nie jest zainstalowane lub nie ma go w PATH.")
        sys.exit(1)

    # Sprawdzenie poświadczeń
    cmd = ["aws", "sts", "get-caller-identity"]
    if profile:
        cmd.extend(["--profile", profile])
    
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    except subprocess.CalledProcessError:
        print(f"Błąd: Nie udało się uwierzytelnić w AWS. Sprawdź poświadczenia dla profilu '{profile or 'default'}'")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"Błąd: Timeout podczas uwierzytelniania w AWS.")
        sys.exit(1)


def get_aws_profiles() -> Dict[str, str]:
    """Pobiera listę konfigurowanych profili AWS z ~/.aws/config."""
    config_path = os.path.expanduser("~/.aws/config")
    profiles = {}
    
    if not os.path.exists(config_path):
        return profiles
    
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
        for section in config.sections():
            if section == "default":
                profile_name = "default"
            elif section.startswith("profile "):
                profile_name = section[8:]
            else:
                continue
            
            profiles[profile_name] = config.get(section, "region", fallback="")
    except configparser.Error as e:
        logger.warning(f"Błąd podczas parsowania ~/.aws/config: {e}")
    
    return profiles


def select_profile(profiles: Dict[str, str]) -> Optional[str]:
    """Zaprasza użytkownika do wyboru profilu AWS."""
    if not profiles:
        return None
    
    profile_list = list(profiles.keys())
    
    print("\nDostępne profile AWS:")
    for idx, profile in enumerate(profile_list, 1):
        region_hint = f" (domyślny: {profiles[profile]})" if profiles[profile] else ""
        print(f"  {idx}. {profile}{region_hint}")
    
    try:
        user_input = input(f"\nWybierz numer profilu (Enter = domyślny, Ctrl+C = Wyjście): ").strip()
        
        if user_input == "":
            for profile in profile_list:
                if "default" in profile.lower():
                    return profile
            return profile_list[0] if profile_list else None
        
        choice = int(user_input)
        if 1 <= choice <= len(profile_list):
            return profile_list[choice - 1]
        
        print(f"Nieprawidłowy wybór, używam domyślnego profilu.")
        return profile_list[0] if profile_list else None
        
    except KeyboardInterrupt:
        print("\nWyjście.")
        sys.exit(0)
    except ValueError:
        print(f"Błąd wejścia, używam domyślnego profilu.")
        return profile_list[0] if profile_list else None


class AWSClient:
    """Klasa do komunikacji z AWS CLI."""
    
    @staticmethod
    def _build_cmd(base_cmd: List[str], profile: Optional[str] = None, **kwargs) -> List[str]:
        """Buduje komendę AWS CLI z opcjonalnym profilem."""
        cmd = ["aws"] + base_cmd
        if profile:
            cmd.insert(1, "--profile")
            cmd.insert(2, profile)
        for key, value in kwargs.items():
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        return cmd
    
    @classmethod
    def get_regions(cls, profile: Optional[str] = None) -> List[str]:
        """Pobiera listę aktywnych regionów przy użyciu AWS CLI."""
        cmd = cls._build_cmd(
            ["ec2", "describe-regions", "--query", "Regions[].RegionName", "--output", "json"],
            profile=profile
        )
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            return json.loads(result.stdout)
        except FileNotFoundError:
            logger.critical("Błąd: Narzędzie 'aws' (AWS CLI) nie jest zainstalowane w systemie lub nie ma go w PATH.")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Błąd AWS CLI podczas pobierania regionów: {e.stderr.strip()}")
            return []
        except subprocess.TimeoutExpired:
            logger.error("Timeout podczas pobierania regionów.")
            return []
        except json.JSONDecodeError:
            logger.error("Nie udało się sparsować odpowiedzi JSON dla regionów.")
            return []
    
    @classmethod
    def check_region_alarms(cls, region: str, profile: Optional[str] = None) -> Tuple[str, List[dict], Optional[str]]:
        """Odpytuje konkretny region o wszystkie alarmy przy użyciu AWS CLI."""
        cmd = cls._build_cmd(
            ["cloudwatch", "describe-alarms", "--region", region, "--output", "json"],
            profile=profile
        )
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            data = json.loads(result.stdout)
            alarms = data.get('MetricAlarms', [])
            return region, alarms, None
        except subprocess.CalledProcessError as e:
            return region, [], f"Błąd CLI: {e.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return region, [], f"Timeout dla regionu {region}"
        except json.JSONDecodeError:
            return region, [], "Błąd formatu JSON z API"


def print_table_header() -> None:
    """Drukuje nagłówek tabeli wyników."""
    print("-" * 75)
    print(f"{'REGION':<15} | {'STAN':<10} | {'NAZWA ALARMU'}")
    print("-" * 75)


def print_result(region: str, alarms: List[dict], error: Optional[str], show_ok: bool = True, skip_states: Optional[List[str]] = None, only_state: Optional[str] = None) -> int:
    """Drukuje wynik dla jednego regionu. Zwraca liczbę znalezionych alarmów w stanie ALARM.
    
    Args:
        skip_states: Lista stanów do pominięcia (OK, ALARM, INSUFFICIENT_DATA)
        only_state: Pokaż tylko alarmy w wybranym stanie
    """
    if skip_states is None:
        skip_states = []
    
    if error:
        print(f"{region:<15} | ERROR      | {error[:45]}")
        return 0
    
    if not alarms:
        if show_ok:
            print(f"{region:<15} | OK         | Brak alarmów")
        return 0
    
    alarm_count = 0
    for alarm in alarms:
        state = alarm.get('StateValue', 'UNKNOWN')
        
        # Filtrowanie po stanach
        if only_state and state != only_state:
            continue
        if state in skip_states:
            continue
        
        print(f"{region:<15} | {state:<10} | {alarm['AlarmName']}")
        if state == 'ALARM':
            alarm_count += 1
    return alarm_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Skaner alarmów CloudWatch w wielu regionach AWS")
    parser.add_argument("--profile", "-p", help="Nazwa profilu AWS do użycia (domyślny: domyślny)")
    parser.add_argument("--region", "-r", help="Filtruj tylko do wybranego regionu")
    parser.add_argument("--skip-no-alarm", action="store_true", help="Pomiń regiony bez alarmów")
    parser.add_argument("--skip-ok", action="store_true", help="Ukryj alarmy w stanie OK")
    parser.add_argument("--skip-alarm", action="store_true", help="Ukryj alarmy w stanie ALARM")
    parser.add_argument("--skip-insufficient", action="store_true", help="Ukryj alarmy w stanie INSUFFICIENT_DATA")
    parser.add_argument("--only-state", choices=["OK", "ALARM", "INSUFFICIENT_DATA"], 
                       help="Pokaż tylko alarmy w wybranym stanie")
    parser.add_argument("--json", action="store_true", help="Wydajność JSON zamiast tabeli")
    args = parser.parse_args()
    
    # Proaktywne sprawdzenie środowiska
    check_aws_environment(args.profile)
    
    profiles = get_aws_profiles()
    
    if args.profile:
        selected_profile = args.profile
        if selected_profile not in profiles and selected_profile != "default":
            logger.warning(f"Profil '{selected_profile}' nie istnieje, używam domyślnego.")
            selected_profile = None
    else:
        # Sprawdź AWS_PROFILE env var
        env_profile = os.getenv('AWS_PROFILE')
        if env_profile:
            selected_profile = env_profile
        elif not profiles:
            print("Używam domyślnego profilu.")
            selected_profile = None
        else:
            selected_profile = select_profile(profiles)
    
    if not selected_profile:
        print("Brak wybranego profilu. Przerywam działanie.")
        return
    
    regions = AWSClient.get_regions(selected_profile)
    if not regions:
        print("Brak dostępu do regionów lub błąd konfiguracji. Przerywam działanie.")
        return
    
    if args.region:
        if args.region in regions:
            regions = [args.region]
        else:
            logger.warning(f"Region '{args.region}' nie istnieje lub nie jest aktywny.")
            return
    
    # Budowanie listy stanów do pominięcia
    skip_states = []
    if args.skip_ok:
        skip_states.append("OK")
    if args.skip_alarm:
        skip_states.append("ALARM")
    if args.skip_insufficient:
        skip_states.append("INSUFFICIENT_DATA")
    
    # Gatheruj wyniki z wszystkich regionów
    print(f"\nSprawdzanie {len(regions)} regionów...")
    print(f"Profil: {selected_profile or 'default'}")
    
    region_data = []
    with ThreadPoolExecutor(max_workers=min(10, len(regions))) as executor:
        region_results = executor.map(lambda r: AWSClient.check_region_alarms(r, selected_profile), regions)
        
        for region, alarms, error in region_results:
            region_data.append((region, alarms, error))
    
    # Printuj w wybranym formacie
    if args.json:
        results = []
        for region, alarms, error in region_data:
            if error:
                status = "ERROR"
            elif not alarms:
                status = "OK"
            else:
                status = next((a.get("StateValue", "UNKNOWN") for a in alarms if a.get("StateValue") == "ALARM"), "OK")
            
            result_entry = {
                "region": region,
                "status": status,
                "alarms": [{"name": a["AlarmName"], "state": a.get("StateValue", "UNKNOWN")} for a in alarms] if not error else None,
                "error": error
            }
            results.append(result_entry)
        
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_table_header()
        total_alarms = 0
        
        for region, alarms, error in region_data:
            total_alarms += print_result(region, alarms, error, show_ok=not args.skip_no_alarm, skip_states=skip_states, only_state=args.only_state)
        
        print("-" * 75)
        if total_alarms == 0:
            print("\n[INFO] Brak alarmów w stanie ALARM.")
        else:
            print(f"\n[ALERT] Znaleziono łącznie {total_alarms} alarmów w stanie ALARM!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSkrypt przerwany przez użytkownika.")
        sys.exit(0)
