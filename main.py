import os
import sys
import argparse
import requests
import json
from dotenv import load_dotenv
from uptime_kuma_api import UptimeKumaApi, MaintenanceStrategy, UptimeKumaException
from datetime import datetime, timedelta

def login(api, kuma_user, kuma_pass, token_file=".token"):
    if os.path.exists(token_file):
        token = load_token(token_file)
        login_response = api.login_by_token(token)
        if not login_response:  # Successful login if response is empty
            print("Re-logged in with saved token.")
        else:
            print("Failed to login with saved token. Deleting token file.")
            os.remove(token_file)
            return login(api, kuma_user, kuma_pass, token_file)  # Retry login without token
    else:
        res = api.login(kuma_user, kuma_pass)
        if res.get('tokenRequired'):
            totp_token = input("(^__^) Enter your TOTP secret: ")
            res = api.login(kuma_user, kuma_pass, totp_token)
            if 'token' in res:
                save_token(res['token'], token_file)
                print("(^__^) Login successful and token saved.")
            else:
                print("(;__;) Failed to login with TOTP.")
                sys.exit(1)  # Exit if login fails

def retry_on_unauthenticated(api_func):
    """Decorator to retry API call on 'You are not logged in' exception."""
    def wrapper(api, *args, **kwargs):
        try:
            return api_func(api, *args, **kwargs)
        except UptimeKumaException as e:
            if 'You are not logged in' in str(e):
                print("Session expired. Re-authenticating...")
                login(api, os.getenv('KUMA_USER'), os.getenv('KUMA_PASS'))
                return api_func(api, *args, **kwargs)
            else:
                raise e
    return wrapper

@retry_on_unauthenticated
def list_monitors(api):
    monitors = api.get_monitors()
    for idx, monitor in enumerate(monitors, start=1):
        print(f"{idx}. {monitor['name']}")
    return monitors

@retry_on_unauthenticated
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

    status_pages = api.get_status_pages()
    status_page_ids = [{"id": page['id']} for page in status_pages]

    if status_page_ids:
        response = api.add_status_page_maintenance(res["maintenanceID"], status_page_ids)
        print(f"Maintenance added to all status pages: {response['msg']}")
    else:
        print("No status pages found.")

@retry_on_unauthenticated
def remove_maintenance(api):
    maintenance_id = input("Enter the maintenance ID to remove: ")
    try:
        api.delete_maintenance(int(maintenance_id))
        print(f"Maintenance with ID {maintenance_id} removed.")
    except ValueError:
        print("Invalid ID. Please enter a valid maintenance ID.")
    return maintenance_id

def send_slack_notification(webhook_url, header, msg):
    slack_message = {
        "text": f"{header} \n\n 🚧 🚧 🚧 🚧 🚧  \n\n {msg} \n\n <!channel>",
        "mrkdwn": True
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

def save_token(token, filename=".token"):
    with open(filename, "w") as file:
        file.write(token)

def load_token(filename=".token"):
    with open(filename, "r") as file:
        return file.read().strip()

def capture_multiline_input():
    print("Enter a description for the maintenance: (press Ctrl+D or Ctrl+Z on Windows to finish):")
    input_lines = sys.stdin.read()
    return input_lines

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Manage Uptime Kuma monitors.")
    parser.add_argument('--remove', action='store_true', help="Remove a maintenance.")
    args = parser.parse_args()

    api = UptimeKumaApi(os.getenv('KUMA_HOST'))
    login(api, os.getenv('KUMA_USER'), os.getenv('KUMA_PASS'))

    if args.remove:
        print("\n (^__^) Listing all maintenances...")
        list_maintenances(api)
        _id = remove_maintenance(api)
        send_slack_notification(os.getenv('SLACK_HOOK'), "🚀 *Deployment Done*", f"Maintenance ID: {_id}")
    else:
        print("(^__^) Fetching monitors...")
        monitors = list_monitors(api)
        monitor_id, monitor_name = select_monitor(monitors)
        description = capture_multiline_input()
        print("(^__^) wait...")

        print("(^__^) putting maintenance...")
        create_maintenance(api, monitor_id, monitor_name, description)

        print("(^__^) notifying...")
        send_slack_notification(os.getenv('SLACK_HOOK'), f"🚀 *Deployment Announce* -\n\n *{monitor_name}*", description)

    api.disconnect()

if __name__ == "__main__":
    main()
