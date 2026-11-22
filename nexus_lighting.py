
import argparse
import time
import hid


# ==========================================
# NEXUS LIGHTING - ROBOBLOQ USBHID
# ==========================================

VID = 0x1A86
PID = 0xFE07

USAGE_PAGE = 0xFF00
INTERFACE = 0

REPORT_LEN = 65

ACT_READ_DEVICE_INFO = 0x82
ACT_SET_SECTION_LED = 0x86
ACT_SET_BRIGHTNESS = 0x87
ACT_TURN_OFF_LIGHT = 0x97

_sequence = 1


# ==========================================
# DEVICE
# ==========================================

def open_device():
    devices = hid.enumerate(VID, PID)

    target = next(
        (
            d for d in devices
            if d.get("usage_page") == USAGE_PAGE
            and d.get("interface_number") == INTERFACE
        ),
        None
    )

    if not target:
        raise RuntimeError("ROBOBLOQ controller not found.")

    device = hid.device()
    device.open_path(target["path"])

    return device


# ==========================================
# PROTOCOL
# ==========================================

def next_sequence():
    global _sequence

    _sequence += 1

    if _sequence >= 255:
        _sequence = 1

    return _sequence


def build_packet(action, payload=None):
    if payload is None:
        payload = []

    length = 6 + len(payload)

    packet = [
        ord("R"),
        ord("B"),
        length,
        next_sequence(),
        action
    ]

    packet.extend(payload)

    checksum = sum(packet) & 0xFF
    packet.append(checksum)

    return packet


def send_packet(device, packet):
    report = [0] + packet
    report += [0] * (REPORT_LEN - len(report))

    written = device.write(report)

    if written != REPORT_LEN:
        raise RuntimeError(
            f"HID write failed: {written} bytes."
        )


def read_device_info(device):
    packet = build_packet(ACT_READ_DEVICE_INFO)
    expected_sequence = packet[3]

    send_packet(device, packet)

    for _ in range(8):
        response = device.read(64, 400)

        if (
            len(response) >= 24
            and response[0] == ord("R")
            and response[1] == ord("B")
            and response[3] == expected_sequence
            and response[4] == ACT_READ_DEVICE_INFO
        ):
            return {
                "device_id": bytes(response[5:8]).hex(),
                "display_size": response[8],
                "led_count": response[11],
                "uuid": bytes(response[12:20]).hex(),
                "firmware": tuple(response[21:24])
            }

    raise RuntimeError(
        "Controller did not respond to device information request."
    )


# ==========================================
# COLOR
# ==========================================

def compress_rgb(red, green, blue):
    total = red + green + blue

    if total > 255:
        factor = total / 255.0

        red = int(red / factor)
        green = int(green / factor)
        blue = int(blue / factor)

    return red, green, blue


def set_color_packet(device, rgb, led_count):
    red = (rgb >> 16) & 0xFF
    green = (rgb >> 8) & 0xFF
    blue = rgb & 0xFF

    red, green, blue = compress_rgb(
        red, green, blue
    )

    payload = [
        1,
        red,
        green,
        blue
    ]

    if 0 < led_count < 254:
        payload.extend([
            led_count,
            led_count + 1,
            0, 0, 0,
            254
        ])
    else:
        payload.append(254)

    packet = build_packet(
        ACT_SET_SECTION_LED,
        payload
    )

    send_packet(device, packet)


# ==========================================
# BRIGHTNESS
# ==========================================

def set_brightness_packet(device, brightness):
    if not 1 <= brightness <= 100:
        raise ValueError(
            "Brightness must be between 1 and 100."
        )

    value = max(
        5,
        int(255 * (brightness / 100.0))
    )

    packet = build_packet(
        ACT_SET_BRIGHTNESS,
        [value]
    )

    send_packet(device, packet)


# ==========================================
# PUBLIC FUNCTIONS
# ==========================================

def get_info():
    device = open_device()

    try:
        return read_device_info(device)
    finally:
        device.close()


def set_color(rgb, brightness=100):
    if not 0 <= rgb <= 0xFFFFFF:
        raise ValueError("Invalid RGB color.")

    if not 1 <= brightness <= 100:
        raise ValueError("Brightness must be 1-100.")

    device = open_device()

    try:
        try:
            info = read_device_info(device)
            led_count = info["led_count"]
        except RuntimeError:
            led_count = 0

        set_brightness_packet(device, brightness)

        time.sleep(0.22)

        set_color_packet(
            device,
            rgb,
            led_count
        )

        return True

    finally:
        device.close()


def turn_off():
    device = open_device()

    try:
        try:
            info = read_device_info(device)
            firmware = info["firmware"]
            led_count = info["led_count"]
        except RuntimeError:
            firmware = (0, 0, 0)
            led_count = 0

        version = (
            firmware[0] * 10000
            + firmware[1] * 100
            + firmware[2]
        )

        for _ in range(4):
            if version >= 10800:
                packet = build_packet(
                    ACT_TURN_OFF_LIGHT
                )
            else:
                payload = [1, 0, 0, 0]

                if 0 < led_count < 254:
                    payload.extend([
                        led_count,
                        led_count + 1,
                        0, 0, 0,
                        254
                    ])
                else:
                    payload.append(254)

                packet = build_packet(
                    ACT_SET_SECTION_LED,
                    payload
                )

            send_packet(device, packet)
            time.sleep(0.02)

        return True

    finally:
        device.close()


# ==========================================
# COMMAND LINE
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="NEXUS LIGHTING - ROBOBLOQ controller"
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--info",
        action="store_true"
    )

    group.add_argument(
        "--set",
        type=str,
        metavar="RRGGBB"
    )

    group.add_argument(
        "--off",
        action="store_true"
    )

    parser.add_argument(
        "--brightness",
        type=int,
        default=100
    )

    args = parser.parse_args()

    try:
        if args.info:
            info = get_info()

            print("\n[NEXUS LIGHTING] DEVICE INFO")
            print("Device ID:", info["device_id"])
            print("Display:", info["display_size"], "inch")
            print("LED count:", info["led_count"])
            print(
                "Firmware:",
                ".".join(map(str, info["firmware"]))
            )

        elif args.set:
            color = args.set.strip().lstrip("#")

            if len(color) != 6:
                raise ValueError(
                    "Color must contain 6 hexadecimal digits."
                )

            rgb = int(color, 16)

            set_color(
                rgb,
                args.brightness
            )

            print(
                f"[SUCCESS] Color #{color.upper()} "
                f"applied at {args.brightness}%."
            )

        elif args.off:
            turn_off()
            print("[SUCCESS] Lighting turned off.")

    except Exception as error:
        print(f"[NEXUS LIGHTING ERROR] {error}")


if __name__ == "__main__":
    main()
