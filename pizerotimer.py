#!/usr/bin/python3
import board, digitalio
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789

import threading, sys, time, sqlite3, signal, os, pprint
from datetime import datetime, timedelta


# Setup the screen and buttons
background_under40 = color565(0, 0, 255)
background_over40 = color565(255, 0, 0)
background = background_under40
foreground = color565(255, 255, 255)
screen_delay = 10
now = datetime.now()
timeout = now.timestamp()+screen_delay
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000
display = st7789.ST7789(
    board.SPI(),
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=240,
    height=240,
    x_offset=0,
    y_offset=80,
)
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
buttonA = digitalio.DigitalInOut(board.D23)
buttonB = digitalio.DigitalInOut(board.D24)
buttonA.switch_to_input()
buttonB.switch_to_input()

# Database
conn = sqlite3.connect('pizerotimer.db')
db = conn.cursor()

# The timer
elapsed_seconds = 0

def quit(signum, frame):
    print("Exiting...")
    sys.stdout.flush()
    stop_timer()
    conn.close()
    global timeout
    timeout = 0
    backlight.value = False
    sys.exit(0)

def backlight_timer(name):
    global backlight

    while True:
        now = datetime.now()
        if timeout > now.timestamp():
            backlight.value = True        
            sys.stdout.flush()
        else:
            backlight.value = False
        time.sleep(0.1)

def display_timer(name):
    global background
    global timeout
    while True:
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        text = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
        if hours > 40 and background != background_over40:
            background = background_over40
            screen_setup()
            timeout = now.timestamp() + screen_delay
        if hours < 40 and background != background_under40:
            background = background_under40
            screen_setup()
        display_digit(10, 10, text[0])
        display_digit(40, 10, text[1])
        display_digit(80, 10, text[3])
        display_digit(110, 10, text[4])
        display_digit(150, 10, text[6])
        display_digit(180, 10, text[7])

def screen_setup():
    display.fill(background)
    display.fill_rectangle(70, 30, 5, 5, foreground)
    display.fill_rectangle(70, 60, 5, 5, foreground)
    display.fill_rectangle(140, 30, 5, 5, foreground)
    display.fill_rectangle(140, 60, 5, 5, foreground)

def display_digit(x, y, number):
    display.fill_rectangle(x+5, y+0, 15, 5, (foreground if number in ['2','3','5','6','7','8','9','0'] else background)) # top bar
    display.fill_rectangle(x+0, y+5, 5, 30, (foreground if number in ['4','5','6','8','9','0'] else background)) # top left
    display.fill_rectangle(x+20, y+5, 5, 30, (foreground if number in ['1','2','3','4','7','8','9','0'] else background)) # top right
    display.fill_rectangle(x+5, y+35, 15, 5, (foreground if number  in ['2','3','4','5','6','8','9'] else background)) # center bar
    display.fill_rectangle(x+0, y+40, 5, 30, (foreground if number in ['2','6','8','0'] else background)) # bottom left
    display.fill_rectangle(x+20, y+40, 5, 30, (foreground if number in ['1','3','4','5','6','7','8','9','0'] else background)) # bottom right
    display.fill_rectangle(x+5, y+70, 15, 5, (foreground if number in ['2','3','5','6','8','9','0'] else background)) # bottom bar

def database_setup():
    for row in db.execute("select sql from sqlite_master where type = 'table' and name = 'time_log'").fetchall():
        return True

    db.execute('''CREATE TABLE time_log (dt_start text, dt_finish text)''')
    conn.commit()
    return True

def start_stop_timer(signum=None, frame=None):
    for row in db.execute("select dt_start, dt_finish from time_log where dt_finish is NULL").fetchall():
        db.execute("update time_log set dt_finish = datetime('now') where dt_finish is NULL")
        conn.commit()
        return True
    db.execute("insert into time_log(dt_start) values(datetime('now'))")
    conn.commit()
    return True

def stop_timer():
    db.execute("update time_log set dt_finish = datetime('now') where dt_finish is NULL")
    conn.commit()
    return True

def time_this_week():
    now = datetime.now()
    day_of_week = now.weekday()
    start_of_week = now - timedelta(days=day_of_week, seconds=now.second, microseconds=now.microsecond, minutes=now.minute, hours=now.hour)
    start_of_week_string = start_of_week.strftime('%Y-%m-%d %H:%M:%S')
    sys.stdout.flush()
    elapsed_time = 0
    for row in db.execute("select strftime('%s',ifnull(dt_finish,'now'))-strftime('%s',dt_start) from time_log where dt_start>=?", (start_of_week_string,)).fetchall():
        elapsed_time += row[0]
    return elapsed_time

if __name__ == "__main__":

    signal.signal(signal.SIGTERM, quit)
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGHUP, start_stop_timer)

    database_setup()
    screen_setup()

    # backlight monitoring thread
    x = threading.Thread(target=backlight_timer, args=(1,), daemon=True)
    x.start()

    # timer display thread
    y = threading.Thread(target=display_timer, args=(1,), daemon=True)
    y.start()


    # FIXME: This is pegging the CPU waiting for a button press. We should
    # make this more reactive instead and hopefully eliminate the 0.1 sleep
    # after responding to a button press
    while True:
        time.sleep(0.1)
        now = datetime.now()
        elapsed_seconds = time_this_week()

        if not (buttonA.value and buttonB.value):
            # Either button is pressed
            timeout = now.timestamp() + screen_delay
        if buttonB.value and not buttonA.value:  # just button A pressed
            start_stop_timer()
        #if buttonA.value and not buttonB.value:  # just button B pressed
        #    display.fill(color565(0, 0, 255))  # blue
        #if not buttonA.value and not buttonB.value:  # none pressed
        #    display.fill(color565(0, 255, 0))  # green
