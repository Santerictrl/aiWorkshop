#!/usr/bin/env python3
"""
Simple Domain Resolver CLI App

This command-line application prompts the user for domain names and checks
if they resolve to IP addresses using socket.gethostbyname. Results are logged
to a file with timestamp and user information.
"""

import json
import os
import socket
import getpass
from datetime import datetime

HISTORY_FILENAME = "domain_check_history.json"


def validate_domain(domain: str) -> str:
    """
    Validate the domain name input.

    Args:
        domain (str): The domain name to validate.

    Returns:
        str: Empty string if valid, otherwise an error message.
    """
    if not domain:
        return "Error: Domain name cannot be empty. Please enter a valid domain name."
    if ' ' in domain:
        return "Error: Domain name cannot contain spaces. Please enter a valid domain name."
    if '.' not in domain:
        return "Error: Domain name must contain at least one dot (e.g., example.com). Please enter a valid domain name."
    # Additional check: only allow alphanumeric, dots, hyphens
    if not all(c.isalnum() or c in '.-' for c in domain):
        return "Error: Domain name contains invalid characters. Only letters, numbers, dots, and hyphens are allowed."
    return ""


def resolve_domain(domain: str) -> str:
    """
    Attempt to resolve a domain name to an IPv4 address.

    Args:
        domain (str): The domain name to resolve.

    Returns:
        str: The resolved IP address or an error message.
    """
    try:
        ip_address = socket.gethostbyname(domain)
        return f"Domain '{domain}' resolves to: {ip_address}"
    except socket.gaierror as e:
        return f"Error: Domain '{domain}' could not be resolved. DNS lookup failed."
    except Exception as e:
        return f"Unexpected error during DNS lookup: {e}"


def load_history() -> list:
    """Load persistent domain check history from disk."""
    if not os.path.exists(HISTORY_FILENAME):
        return []

    try:
        with open(HISTORY_FILENAME, 'r', encoding='utf-8') as history_file:
            return json.load(history_file)
    except Exception:
        return []


def save_history(history: list) -> None:
    """Save the full persistent domain check history to disk."""
    try:
        with open(HISTORY_FILENAME, 'w', encoding='utf-8') as history_file:
            json.dump(history, history_file, indent=2)
    except Exception as e:
        print(f"Warning: Could not save history file: {e}")


def format_history_entry(entry: dict) -> str:
    return (
        f"Date: {entry['timestamp']}\n"
        f"User: {entry['user']}\n"
        f"Domain: {entry['domain']}\n"
        f"Result: {entry['result']}\n"
        + "-" * 60
    )


def print_last_check(history: list) -> None:
    if not history:
        return

    last_entry = history[-1]
    print("Last domain check:")
    print(f"  Domain: {last_entry['domain']}")
    print(f"  Date:   {last_entry['timestamp']}")
    print(f"  User:   {last_entry['user']}")
    print()


def print_history_entries(entries: list) -> None:
    if not entries:
        print("No history to display.")
        return

    for entry in entries:
        print(format_history_entry(entry))
    print()


def search_history(history: list) -> None:
    query = input("Enter a domain substring to search for: ").strip().lower()
    if not query:
        print("Search query cannot be empty.")
        return

    matches = [entry for entry in history if query in entry['domain'].lower()]
    if not matches:
        print(f"No history entries found for '{query}'.")
        return

    print(f"Found {len(matches)} matching entries:")
    print_history_entries(matches)


def extract_ip_from_result(result: str) -> str:
    """
    Extract IP address from a domain resolution result string.

    Args:
        result (str): The result string from resolve_domain function.

    Returns:
        str: The IP address if found, otherwise empty string.
    """
    if "resolves to:" in result:
        # Extract IP from "Domain 'domain' resolves to: IP"
        parts = result.split("resolves to:")
        if len(parts) == 2:
            return parts[1].strip()
    return ""


def show_ip_change_history(history: list) -> None:
    """
    Show IP address change history for a specific domain.
    """
    domain = input("Enter domain name to check IP change history: ").strip().lower()
    if not domain:
        print("Domain name cannot be empty.")
        return

    # Filter history for this domain (case-insensitive)
    domain_entries = [entry for entry in history if entry['domain'].lower() == domain]

    if not domain_entries:
        print(f"No history found for domain '{domain}'.")
        return

    # Extract IP addresses with timestamps
    ip_history = []
    for entry in sorted(domain_entries, key=lambda x: x['timestamp'], reverse=True):
        ip = extract_ip_from_result(entry['result'])
        if ip:  # Only include successful resolutions
            ip_history.append({
                'timestamp': entry['timestamp'],
                'ip': ip,
                'user': entry['user']
            })

    if not ip_history:
        print(f"No successful IP resolutions found for '{domain}'.")
        return

    # Group by IP address to find changes
    ip_groups = {}
    for entry in ip_history:
        ip = entry['ip']
        if ip not in ip_groups:
            ip_groups[ip] = []
        ip_groups[ip].append(entry)

    # Display results
    print(f"\nIP Change History for '{domain}':")
    print("=" * 60)

    # Show current IP first
    current_ip = ip_history[0]['ip']
    current_timestamp = ip_history[0]['timestamp']
    print(f"Current IP: {current_ip} (as of {current_timestamp})")
    print()

    # Show all unique IPs with their first and last seen dates
    unique_ips = list(ip_groups.keys())
    if len(unique_ips) == 1:
        print("No IP changes detected - domain has always resolved to the same IP.")
        print(f"First seen: {ip_groups[unique_ips[0]][-1]['timestamp']}")
        print(f"Last checked: {ip_groups[unique_ips[0]][0]['timestamp']}")
        print(f"Total checks: {len(ip_groups[unique_ips[0]])}")
    else:
        print("IP Address Changes:")
        for i, ip in enumerate(unique_ips):
            entries = ip_groups[ip]
            first_seen = entries[-1]['timestamp']  # Oldest first (reverse sorted)
            last_seen = entries[0]['timestamp']   # Newest first
            check_count = len(entries)

            status = "(current)" if ip == current_ip else "(previous)"
            print(f"{i+1}. {ip} {status}")
            print(f"   First seen: {first_seen}")
            print(f"   Last seen:  {last_seen}")
            print(f"   Check count: {check_count}")
            print()

        # Show timeline of changes
        print("Timeline of Changes:")
        print("-" * 30)
        prev_ip = None
        for entry in reversed(ip_history):  # Show chronological order (oldest first)
            if prev_ip and prev_ip != entry['ip']:
                print(f"  ↳ Changed to {entry['ip']} on {entry['timestamp']}")
            elif prev_ip is None:
                print(f"  ↳ First recorded: {entry['ip']} on {entry['timestamp']}")
            prev_ip = entry['ip']

    print("=" * 60)
    print(f"Total successful checks: {len(ip_history)}")
    print(f"Unique IP addresses: {len(unique_ips)}")


def main():
    """Main function to run the domain checker with history and file logging."""
    print("Domain Resolver CLI")
    print()

    username = getpass.getuser()
    persistent_history = load_history()

    if persistent_history:
        print_last_check(persistent_history)

        show_recent = input("Show the last 10 domain checks? (y/n): ").strip().lower()
        if show_recent == 'y':
            print_history_entries(persistent_history[-10:])

        if len(persistent_history) > 10:
            search_prompt = input("Search history for a domain? (y/n): ").strip().lower()
            if search_prompt == 'y':
                search_history(persistent_history)

        # New feature: IP change history
        if persistent_history:
            ip_history_prompt = input("Check IP change history for a domain? (y/n): ").strip().lower()
            if ip_history_prompt == 'y':
                show_ip_change_history(persistent_history)
                print()

    session_history = []

    while True:
        domain_input = input("Enter a domain name to check (or q to quit): ").strip()

        if domain_input.lower() == 'q':
            if session_history:
                persistent_history.extend(session_history)
                save_history(persistent_history)
                print(f"Saved {len(session_history)} new check(s) to history.")
            print("Goodbye!")
            return

        validation_error = validate_domain(domain_input)
        if validation_error:
            print(validation_error)
            print()
            continue

        result = resolve_domain(domain_input)
        print(result)
        print()

        session_history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': username,
            'domain': domain_input,
            'result': result,
        })

        while True:
            continue_prompt = input("Check another domain? (y/n): ").strip().lower()
            if continue_prompt == 'y':
                print()
                break
            elif continue_prompt == 'n':
                if session_history:
                    persistent_history.extend(session_history)
                    save_history(persistent_history)
                    print(f"Saved {len(session_history)} new check(s) to history.")
                print("Goodbye!")
                return
            else:
                print("Invalid input. Please enter 'y' or 'n'.")


if __name__ == "__main__":
    main()