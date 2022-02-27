import displayio
import rgbmatrix
import board
import framebufferio
import terminalio
from adafruit_display_text import label
from adafruit_datetime import datetime
import time
import digitalio
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import busio
import rtc
import supervisor

def updateBootScreen(credentialsState, wifiState, clockState):
    if credentialsState == "ok":
        bitmap_check_mark = displayio.OnDiskBitmap("bitmaps/Checkmark_ok.bmp")
    elif credentialsState == "warning":
        bitmap_check_mark = displayio.OnDiskBitmap("bitmaps/Checkmark_warning.bmp")
    else:
        bitmap_check_mark = displayio.OnDiskBitmap("bitmaps/Checkmark_default.bmp")

    if wifiState == "ok":
        bitmap_wifi = displayio.OnDiskBitmap("bitmaps/WiFi_ok.bmp")
    elif wifiState == "warning":
        bitmap_wifi = displayio.OnDiskBitmap("bitmaps/WiFi_warning.bmp")
    else:
        bitmap_wifi = displayio.OnDiskBitmap("bitmaps/WiFi_default.bmp")

    if clockState == "ok":
        bitmap_clock = displayio.OnDiskBitmap("bitmaps/Clock_ok.bmp")
    elif clockState == "warning":
        bitmap_clock = displayio.OnDiskBitmap("bitmaps/Clock_warning.bmp")
    else:
        bitmap_clock = displayio.OnDiskBitmap("bitmaps/Clock_default.bmp")

    item_bitmap_check_mark = displayio.TileGrid(
        bitmap_check_mark,
        pixel_shader=bitmap_check_mark.pixel_shader
    )

    item_bitmap_check_mark.x = 3
    item_bitmap_check_mark.y = 9

    item_bitmap_wifi = displayio.TileGrid(
        bitmap_wifi,
        pixel_shader=bitmap_wifi.pixel_shader
    )

    item_bitmap_wifi.x = 25
    item_bitmap_wifi.y = 9

    item_bitmap_clock = displayio.TileGrid(
        bitmap_clock,
        pixel_shader=bitmap_clock.pixel_shader
    )

    item_bitmap_clock.x = 47
    item_bitmap_clock.y = 9

    group_bitmaps = displayio.Group()

    group_bitmaps.append(item_bitmap_check_mark)
    group_bitmaps.append(item_bitmap_wifi)
    group_bitmaps.append(item_bitmap_clock)

    # Add the Group to the Display
    display.show(group_bitmaps)

def alertClock():
    # Count time for a specific time in different colours
    print("Alarm display triggered.")
    start_time = datetime.now()
    while True:
        timer = datetime.now() - start_time

        if str(timer) < time_exit:
            if str(timer) < "0:04:00":
                alert_color = 0x00CC00
            elif str(timer) >= "0:04:00" and str(timer) < "0:06:00":
                alert_color = 0xFFFF00
            elif str(timer) >= "0:06:00" and str(timer) < "1:00:00":
                alert_color = 0xFF0000
            else:
                alert_color = 0xFFFFFF
            alert_text = str(timer)

            line_alert = label.Label(font, text=alert_text, color=alert_color, scale=2)
            line_alert.x = -21
            line_alert.y = 14

            alert_group = displayio.Group()
            alert_group.append(line_alert)
            display.show(alert_group)
        else:
            clearDisplay()
            print("Alarm display deactivated.")
            break

def realtimeClock():
    # Display the real time
    clock_color = 0x070973
    clock_text = datetime.now()
    line_clock = label.Label(font, text=str(clock_text), color=clock_color, scale=2)
    line_clock.x = -130
    line_clock.y = 14
    clock_group = displayio.Group()
    clock_group.append(line_clock)
    display.show(clock_group)


def getRTC():
    # Get the real time via API
    updateBootScreen("default", "default", "default")

    try:
        from secrets import secrets
    except ImportError:
        print("WiFi secrets are kept in secrets.py, please add them there!")
        updateBootScreen("warning", "default", "default")
        raise
    updateBootScreen("ok", "default", "default")
    print("ESP32 SPI webclient test")

    TIME_API_IO = "https://timeapi.io/api/Time/current/zone?timeZone=Europe/Berlin"

    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    requests.set_socket(socket, esp)

    if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
        print("ESP32 found and in idle mode")
    print("Firmware vers.", esp.firmware_version)
    print("MAC addr:", [hex(i) for i in esp.MAC_address])

    for ap in esp.scan_networks():
        print("\t%s\t\tRSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))

    print("Connecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(secrets["ssid"], secrets["password"])
        except RuntimeError as e:
            print("could not connect to AP, retrying: ", e)
            updateBootScreen("ok", "warning", "default")
            continue
    updateBootScreen("ok", "ok", "default")
    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

    print("My IP address is", esp.pretty_ip(esp.ip_address))
    print(
        "IP lookup adafruit.com: %s" %
        esp.pretty_ip(esp.get_host_by_name("adafruit.com"))
    )
    print("Ping google.com: %d ms" % esp.ping("google.com"))

    print()
    print("Fetching json from", TIME_API_IO)
    request = requests.get(TIME_API_IO)
    print("-" * 40)
    HTTP_ANSWER = request.json()
    print(HTTP_ANSWER['dateTime'])
    print("-" * 40)
    request.close()
    updateBootScreen("ok", "ok", "ok")
    r = rtc.RTC()
    r.datetime = time.struct_time((
        HTTP_ANSWER['year'],
        HTTP_ANSWER['month'],
        HTTP_ANSWER['day'],
        HTTP_ANSWER['hour'],
        HTTP_ANSWER['minute'],
        HTTP_ANSWER['seconds'],
        0,
        -1,
        -1
    ))
    esp.disconnect()
    return HTTP_ANSWER

def clearDisplay():
    # Clear the whole display
    clear_text = ""
    clear_color = 0x000000
    line_clear = label.Label(font, text=clear_text, color=clear_color, scale=1)
    clear_group = displayio.Group()
    clear_group.append(line_clear)
    display.show(clear_group)
    print("Display cleared successfully.")

# Print general board informations
print(board.board_id)


triggered = False
switch_A4 = digitalio.DigitalInOut(board.A4)
switch_A4.pull = digitalio.Pull.UP

time_exit = "0:15:00"
font = terminalio.FONT

restart_time = "0:20:00"

# Initialize display
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, bit_depth=4,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE
)

display = framebufferio.FramebufferDisplay(matrix)

clearDisplay()

rtcData = getRTC()
r = rtc.RTC()
r.datetime = time.struct_time((
    rtcData['year'],
    rtcData['month'],
    rtcData['day'],
    rtcData['hour'],
    rtcData['minute'],
    rtcData['seconds'],
    0,
    -1,
    -1
))

boot_time = datetime.now()
if not switch_A4.value and not triggered:
   triggered = True
while True:
    if (str(datetime.now() - boot_time)) >= restart_time:
        print(str(datetime.now() - boot_time))
        supervisor.reload()
    if (not switch_A4.value and not triggered) or (triggered and switch_A4.value):
        if not switch_A4.value and not triggered:
            print("Auslösung [Quittiert]")
            triggered = True
        elif triggered and switch_A4.value:
            print("Auslösung [Nicht Quittiert]")
        else:
            print("Auslösung [Ohne Grund]")
        print(triggered)
        alertClock()
    else:
        realtimeClock()
