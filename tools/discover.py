"""Listen for Tuya announcements; omit keys and never poll device controls."""

import json

import tinytuya


def main():
    devices = tinytuya.deviceScan(verbose=False, maxretry=10, color=False, poll=False, forcescan=False)
    print(
        json.dumps(
            [
                {
                    "address": ip,
                    "device_id": device.get("gwId", device.get("id")),
                    "protocol": device.get("version"),
                }
                for ip, device in devices.items()
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
