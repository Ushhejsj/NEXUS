
import hid

VID = 0x1A86
PID = 0xFE07

REPORT_LEN = 65
SEQ = 2


def main():
    print("[NEXUS LIGHTING] Searching for ROBOBLOQ...")

    devices = hid.enumerate(VID, PID)

    target = next(
        (
            d for d in devices
            if d.get("usage_page") == 0xFF00
            and d.get("interface_number") == 0
        ),
        None
    )

    if not target:
        print("[ERROR] ROBOBLOQ control interface not found.")
        return

    print("[FOUND] ROBOBLOQ USBHID detected.")

    device = hid.device()

    try:
        device.open_path(target["path"])
        print("[OPEN] Interface opened.")

        # Build device information request
        packet = [
            ord("R"),
            ord("B"),
            6,
            SEQ,
            0x82
        ]

        checksum = sum(packet) & 0xFF
        packet.append(checksum)

        # HID output report: Report ID + 64 bytes
        report = [0] + packet
        report += [0] * (REPORT_LEN - len(report))

        written = device.write(report)
        print("[WRITE] Bytes written:", written)

        print("[READ] Waiting for controller...")

        for attempt in range(8):
            response = device.read(REPORT_LEN - 1, 400)

            if not response:
                print(f"[READ {attempt + 1}] Timeout")
                continue

            print(
                f"[READ {attempt + 1}] "
                f"HEX: {bytes(response).hex(' ')}"
            )

            # hidapi returns 64 bytes without Report ID
            if (
                len(response) >= 24
                and response[0] == ord("R")
                and response[1] == ord("B")
                and response[3] == SEQ
                and response[4] == 0x82
            ):
                print("\n[SUCCESS] Controller verified!")

                print(
                    "Device ID:",
                    bytes(response[5:8]).hex()
                )

                print("Display size:", response[8])
                print("LED count:", response[11])

                print(
                    "Firmware:",
                    ".".join(map(str, response[21:24]))
                )

                return

        print("\n[ERROR] No valid device information response.")

    except Exception as e:
        print("[ERROR]", e)

    finally:
        device.close()
        print("[CLOSE] Device closed.")


if __name__ == "__main__":
    main()


