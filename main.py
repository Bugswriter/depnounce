import os
import sys
import argparse
import requests
import json
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
            choice = int(input("(^__^) Select a monitor by number: "))
            if 1 <= choice <= len(monitors):
                return monitors[choice - 1]['id'], monitors[choice - 1]['name']
            else:
                print("Invalid choice. Please select a valid monitor number.")
        except ValueError:
            print("Please enter a number.")


def send_slack_notification(webhook_url, header, msg):
    slack_message = {
        "text": f"{header} \n\n 🚧 🚧 🚧 🚧 🚧  \n\n {msg} \n\n <!channel>",
        "mrkdwn": True  # Enable markdown for formatting
    }

    response = requests.post(
        webhook_url,
        data=json.dumps(slack_message),
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        print("Notification sent successfully!")
    else:
        print(f"Failed to send notification. Status code: {response.status_code}, Response: {response.text}")

def create_maintenance(api, monitor_id, monitor_name, description):
    now = datetime.now()
    res = api.add_maintenance(
        title=f"Maintenance for monitor - {monitor_name}",
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
    print(f"Monitor {monitor_name} is now under maintenance with ID {res['maintenanceID']}")

    # Add the maintenance to all status pages
    status_pages = api.get_status_pages()
    status_page_ids = [{"id": page['id']} for page in status_pages]

    if status_page_ids:
        response = api.add_status_page_maintenance(res["maintenanceID"], status_page_ids)
        print(f"Maintenance added to all status pages: {response['msg']}")
    else:
        print("No status pages found.")

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

    return maintenance_id


def save_token(token, filename=".token"):
    with open(filename, "w") as file:
        file.write(token)

def load_token(filename=".token"):
    with open(filename, "r") as file:
        return file.read().strip()

def capture_multiline_input():
    print("Enter a description for the maintenance: (press Ctrl+D or Ctrl+Z on Windows to finish):")
    input_lines = sys.stdin.read()  # Read until EOF (Ctrl+D or Ctrl+Z)
    return input_lines

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Manage Uptime Kuma monitors.")
    parser.add_argument('--remove', action='store_true', help="Remove a maintenance.")

    args = parser.parse_args()
    kuma_host = os.getenv('KUMA_HOST')
    kuma_user = os.getenv('KUMA_USER')
    kuma_pass = os.getenv('KUMA_PASS')
    slack_hook = os.getenv('SLACK_HOOK')

    api = UptimeKumaApi(kuma_host)

    if os.path.exists(".token"):
        # Load and use the saved token
        token = load_token(".token")
        login_response = api.login_by_token(token)
        if not login_response:  # If the response is an empty dictionary, login was successful
            print("Re-logged in with saved token.")
        else:
            print("Failed to login with saved token. Please delete the .token file and try again.")
            return

    else:
        # Perform the initial login with username, password, and TOTP
        res = api.login(kuma_user, kuma_pass)

        if res.get('tokenRequired'):
            totp_token= str(input("(^__^) Enter your TOTP secret: "))
            res = api.login(kuma_user, kuma_pass, totp_token)

            if 'token' in res:
                # Save the token to a file
                print(res['token'])
                save_token(res['token'])
                print("(^__^) Login successful and token saved.")
            else:
                print("(;__;) Failed to login with TOTP.")
                return

    if args.remove:
        print("\n (^__^) Listing all maintenances...")
        list_maintenances(api)
        _id = remove_maintenance(api)
        send_slack_notification(slack_hook, "🚀 *Deployment Done*" , f"Maintenance ID: {_id}")
    else:
        print("(^__^) Fetching monitors...")
        monitors = list_monitors(api)
        monitor_id, monitor_name = select_monitor(monitors)
        title = f"🚀 *Deployment Announce* -\n\n *{monitor_name}* is now under maintenance"
        description = capture_multiline_input()
        print("(^__^) wait...")

        print("(^__^) notifying...")
        send_slack_notification(slack_hook, title, description)
        print("(^__^) putting maintenance...")
        create_maintenance(api, monitor_id, monitor_name, description)

    api.disconnect()

if __name__ == "__main__":
    main()
