import argparse
from dotenv import load_dotenv
from uptime_kuma_api import UptimeKumaApi, MaintenanceStrategy
from datetime import datetime, timedelta

def list_monitors(api):
    monitors = api.get_monitors()
    for idx, monitor in enumerate(monitors, start=1):
        print(f"{idx}. {monitor['name']}")
    return monitors

def select_monitor(monitors):
    while True:
        try:
            choice = int(input("Select a monitor by number: "))
            if 1 <= choice <= len(monitors):
                return monitors[choice - 1]['id']
            else:
                print("Invalid choice. Please select a valid monitor number.")
        except ValueError:
            print("Please enter a number.")

def create_maintenance(api, monitor_id, description):
    now = datetime.now()
    res = api.add_maintenance(
        title=f"Maintenance for monitor {monitor_id}",
        description=description,
        strategy=MaintenanceStrategy.SINGLE,
        active=True,
        intervalDay=1,
        dateRange=[
            now.strftime('%Y-%m-%d %H:%M:%S'),
            (now + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        ],
        weekdays=[],
        daysOfMonth=[],
        cron=None,
        durationMinutes=120,
        timezoneOption="UTC"
    )
    api.add_monitor_maintenance(res["maintenanceID"], [{"id": monitor_id}])
    print(f"Monitor {monitor_id} is now under maintenance with ID {res['maintenanceID']}")

def list_maintenances(api):
    maintenances = api.get_maintenances()
    for maintenance in maintenances:
        print(f"ID: {maintenance['id']}, Title: {maintenance['title']}, Active: {maintenance['active']}")

def remove_maintenance(api):
    maintenance_id = input("Enter the maintenance ID to remove: ")
    try:
        api.delete_maintenance(int(maintenance_id))
        print(f"Maintenance with ID {maintenance_id} removed.")
    except ValueError:
        print("Invalid ID. Please enter a valid maintenance ID.")

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Manage Uptime Kuma monitors.")
    parser.add_argument('--remove', action='store_true', help="Remove a maintenance.")

    args = parser.parse_args()
    kuma_host = os.getenv('KUMA_HOST')
    kuma_user = os.getenv('KUMA_USER')
    kuma_pass = os.getenv('KUMA_PASS')

    api = UptimeKumaApi(kuma_host)
    api.login(kuma_user, kuma_pass)

    if args.remove:
        print("\nListing all maintenances...")
        list_maintenances(api)
        remove_maintenance(api)
    else:
        print("Fetching monitors...")
        monitors = list_monitors(api)
        monitor_id = select_monitor(monitors)
        description = input("Enter a description for the maintenance: ")
        create_maintenance(api, monitor_id, description)

    api.disconnect()

if __name__ == "__main__":
    main()
