#!/usr/bin/python3
import board, digitalio
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789

import threading, sys, time, sqlite3, signal, os, pprint, yaml, pytz, os
from datetime import datetime, timedelta

# Setup the screen and buttons
now = datetime.now()
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

# Status Bar globals
status_bar_width = 220
status_bar_height = 10

# The timer
elapsed_seconds = 0

def quit(signum=None, frame=None, shutdown=False):
    print("Exiting...")
    sys.stdout.flush()
    stop_timer()
    conn.close()
    global timeout
    timeout = 0
    backlight.value = False
    if shutdown:
        os.system('/bin/systemctl poweroff')
        sys.exit(0)
    else:
        sys.exit(0)

def backlight_timer(name):
    global backlight

    while True:
        now = datetime.now()
        if timeout > now.timestamp():
            backlight.value = True        
        else:
            backlight.value = False
        time.sleep(0.1)

def display_timer(name):
    global background_color
    global timeout
    force_redraw = False
    text = 'aa:aa:aa'
    day_of_week = -1
    first_time_through = True
    while True:
        now = datetime.now()
        last_day = day_of_week
        day_of_week = now.weekday()
        if last_day != day_of_week:
            draw_days(day_of_week)
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        last_text = text
        text = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
        if ( hours >= int(config['options']['background_threshold'])
             and background_color != background_over_threshold ):
            background_color = background_over_threshold
            force_redraw = True
            screen_setup()
            turn_on_backlight()
        if ( hours < int(config['options']['background_threshold'])
             and background_color != background_under_threshold ):
            background_color = background_under_threshold
            force_redraw = True
            screen_setup()
        if ( minutes == 0 and seconds < 5
             and text != last_text
             and text != '00:00:00'):
            turn_on_backlight()

        # Update any digits that have changed since last screen update
        if (last_text[0] != text[0] or force_redraw):
            display_digit(10, 10, text[0], foreground_color, background_color)
        if (last_text[1] != text[1] or force_redraw):
            display_digit(44, 10, text[1], foreground_color, background_color)
        if (last_text[3] != text[3] or force_redraw):
            display_digit(88, 10, text[3], foreground_color, background_color)
        if (last_text[4] != text[4] or force_redraw):
            display_digit(122, 10, text[4], foreground_color, background_color)
        if (last_text[6] != text[6] or force_redraw):
            display_digit(166, 10, text[6], foreground_color, background_color)
        if (last_text[7] != text[7] or force_redraw):
            display_digit(200, 10, text[7], foreground_color, background_color)
        if first_time_through or (seconds == 0 and last_text != text):
            display_bar()
        first_time_through = False
        force_redraw = False
        time.sleep(0.1)

def display_bar():
    bar_complete = (status_bar_width-2) * (elapsed_seconds / (config['options']['status_bar_max']*60*60))
    if bar_complete > (status_bar_width-2):
       bar_complete = status_bar_width-2
    display.fill_rectangle(11, 91, int(bar_complete), status_bar_height-2, status_bar_color)
    display.fill_rectangle(11+int(bar_complete)+1 , 91, (status_bar_width-2)-int(bar_complete), status_bar_height-2, status_bar_outline_color)
    if (config['options']['status_bar_segments'] > 0):
        display_bar_segments()

def display_bar_segments():
    spacing = int(status_bar_width/config['options']['status_bar_segments'])
    xpos = 0
    while (xpos <= status_bar_width):
        display.fill_rectangle(10+xpos , 88, 1, status_bar_height+4, status_bar_outline_color)
        xpos += spacing

def screen_setup():
    """ Draw background, colons, and outline of status bar """
    global timeout
    display.fill(background_color)
    display.fill_rectangle(78 , 30, 5, 5, foreground_color) # left colon top
    display.fill_rectangle(78 , 60, 5, 5, foreground_color) # left colon bottom
    display.fill_rectangle(156, 30, 5, 5, foreground_color) # right colon top
    display.fill_rectangle(156, 60, 5, 5, foreground_color) # right colon bottom
    display.fill_rectangle(10 , 90, 1, status_bar_height, status_bar_outline_color)
    display.fill_rectangle(230, 90, 1, status_bar_height, status_bar_outline_color)
    display.fill_rectangle(10 , 90, status_bar_width, 1, status_bar_outline_color)
    display.fill_rectangle(10 , 90+status_bar_height-1, status_bar_width, 1, status_bar_outline_color)
    draw_days()

def draw_days(day_of_week=-1):
    display_dow(15 , 190, 'S', active_day_color if day_of_week == 6 else inactive_day_color, background_color)
    display_dow(47 , 190, 'M', active_day_color if day_of_week == 0 else inactive_day_color, background_color)
    display_dow(79 , 190, 'T', active_day_color if day_of_week == 1 else inactive_day_color, background_color)
    display_dow(111, 190, 'W', active_day_color if day_of_week == 2 else inactive_day_color, background_color)
    display_dow(143, 190, 'T', active_day_color if day_of_week == 3 else inactive_day_color, background_color)
    display_dow(175, 190, 'F', active_day_color if day_of_week == 4 else inactive_day_color, background_color)
    display_dow(207, 190, 'S', active_day_color if day_of_week == 5 else inactive_day_color, background_color)

def display_dow(x, y, letter, fg_color, bg_color):
    bar_width = 3
    hbar_length = 14
    vbar_length = 15

    display.fill_rectangle(x+bar_width                     , y                            , hbar_length  , bar_width    , (fg_color if letter in ['S','M','T','F'] else bg_color)) # top bar
    display.fill_rectangle(x+bar_width-1                   , y+1                          , hbar_length+2, 1            , (fg_color if letter in ['S','M','T','F'] else bg_color)) # top bar
    display.fill_rectangle(x                               , y+bar_width                  , bar_width    , vbar_length  , (fg_color if letter in ['S','M','W','F'] else bg_color)) # top left
    display.fill_rectangle(x+1                             , y+bar_width-1                , 1            , vbar_length+2, (fg_color if letter in ['S','M','W','F'] else bg_color)) # top left
    display.fill_rectangle(x+int((hbar_length+bar_width)/2), y+bar_width                  , bar_width    , vbar_length  , (fg_color if letter in ['M','T'] else bg_color)) # top center
    display.fill_rectangle(x+hbar_length+bar_width         , y+bar_width                  , bar_width    , vbar_length  , (fg_color if letter in ['M','W'] else bg_color)) # top right
    display.fill_rectangle(x+hbar_length+bar_width+1       , y+bar_width-1                , 1            , vbar_length+2, (fg_color if letter in ['M','W'] else bg_color)) # top right
    display.fill_rectangle(x+bar_width                     , y+vbar_length+bar_width      , hbar_length  , bar_width    , (fg_color if letter in ['S','F'] else bg_color)) # center bar
    display.fill_rectangle(x+bar_width-1                   , y+vbar_length+bar_width+1    , hbar_length+2, 1            , (fg_color if letter in ['S','F'] else bg_color)) # center bar
    display.fill_rectangle(x                               , y+vbar_length+2*bar_width    , bar_width    , vbar_length  , (fg_color if letter in ['M','W','F'] else bg_color)) # bottom left
    display.fill_rectangle(x+1                             , y+vbar_length+2*bar_width-1  , 1            , vbar_length+2, (fg_color if letter in ['M','W','F'] else bg_color)) # bottom left
    display.fill_rectangle(x+int((hbar_length+bar_width)/2), y+vbar_length+2*bar_width    , bar_width    , vbar_length  , (fg_color if letter in ['W','T'] else bg_color)) # bottom center
    display.fill_rectangle(x+hbar_length+bar_width         , y+vbar_length+2*bar_width    , bar_width    , vbar_length  , (fg_color if letter in ['S','M','W'] else bg_color)) # bottom right
    display.fill_rectangle(x+hbar_length+bar_width+1       , y+vbar_length+2*bar_width-1  , 1            , vbar_length+2, (fg_color if letter in ['S','M','W'] else bg_color)) # bottom right
    display.fill_rectangle(x+bar_width                     , y+2*vbar_length+2*bar_width  , hbar_length  , bar_width    , (fg_color if letter in ['S','W'] else bg_color)) # bottom bar
    display.fill_rectangle(x+bar_width-1                   , y+2*vbar_length+2*bar_width+1, hbar_length+2, 1            , (fg_color if letter in ['S','W'] else bg_color)) # bottom bar

def display_digit(x, y, number, fg_color, bg_color):
    bar_width = 5
    hbar_length = 15
    vbar_length = 30

    display.fill_rectangle(x+bar_width              , y                            , hbar_length  , bar_width    , (fg_color if number in ['2','3','5','6','7','8','9','0'] else bg_color)) # top bar
    display.fill_rectangle(x+bar_width-1            , y+1                          , hbar_length+2, bar_width-2  , (fg_color if number in ['2','3','5','6','7','8','9','0'] else bg_color)) # top bar
    display.fill_rectangle(x                        , y+bar_width                  , bar_width    , vbar_length  , (fg_color if number in ['4','5','6','8','9','0'] else bg_color)) # top left
    display.fill_rectangle(x+1                      , y+bar_width-1                , bar_width-2  , vbar_length+2, (fg_color if number in ['4','5','6','8','9','0'] else bg_color)) # top left
    display.fill_rectangle(x+bar_width+hbar_length  , y+bar_width                  , bar_width    , vbar_length  , (fg_color if number in ['1','2','3','4','7','8','9','0'] else bg_color)) # top right
    display.fill_rectangle(x+bar_width+hbar_length+1, y+bar_width-1                , bar_width-2  , vbar_length+2, (fg_color if number in ['1','2','3','4','7','8','9','0'] else bg_color)) # top right
    display.fill_rectangle(x+bar_width              , y+vbar_length+bar_width      , hbar_length  , bar_width    , (fg_color if number in ['2','3','4','5','6','8','9'] else bg_color)) # center bar
    display.fill_rectangle(x+bar_width-1            , y+vbar_length+bar_width+1    , hbar_length+2, bar_width-2  , (fg_color if number in ['2','3','4','5','6','8','9'] else bg_color)) # center bar
    display.fill_rectangle(x                        , y+vbar_length+2*bar_width    , bar_width    , vbar_length  , (fg_color if number in ['2','6','8','0'] else bg_color)) # bottom left
    display.fill_rectangle(x+1                      , y+vbar_length+2*bar_width-1  , bar_width-2  , vbar_length+2, (fg_color if number in ['2','6','8','0'] else bg_color)) # bottom left
    display.fill_rectangle(x+bar_width+hbar_length  , y+vbar_length+2*bar_width    , bar_width    , vbar_length  , (fg_color if number in ['1','3','4','5','6','7','8','9','0'] else bg_color)) # bottom right
    display.fill_rectangle(x+bar_width+hbar_length+1, y+vbar_length+2*bar_width-1  , bar_width-2  , vbar_length+2, (fg_color if number in ['1','3','4','5','6','7','8','9','0'] else bg_color)) # bottom right
    display.fill_rectangle(x+bar_width              , y+2*(vbar_length+bar_width)  , hbar_length  , bar_width    , (fg_color if number in ['2','3','5','6','8','9','0'] else bg_color)) # bottom bar
    display.fill_rectangle(x+bar_width-1            , y+2*(vbar_length+bar_width)+1, hbar_length+2, bar_width-2  , (fg_color if number in ['2','3','5','6','8','9','0'] else bg_color)) # bottom bar

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
    timezone_delta = local_tz.localize(now) - pytz.utc.localize(now)
    start_of_week = now - timedelta(days=day_of_week, seconds=now.second, microseconds=now.microsecond, minutes=now.minute, hours=now.hour) + timezone_delta
    start_of_week_string = start_of_week.strftime('%Y-%m-%d %H:%M:%S')
    elapsed_time = 0
    for row in db.execute("select strftime('%s',ifnull(dt_finish,'now'))-strftime('%s',dt_start) from time_log where dt_start>=?", (start_of_week_string,)).fetchall():
        elapsed_time += row[0]
    return elapsed_time

def turn_on_backlight():
    global timeout
    now = datetime.now()
    timeout = now.timestamp() + 2 * int(config['options']['display_timeout'])

if __name__ == "__main__":

    signal.signal(signal.SIGTERM, quit)
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGHUP, start_stop_timer)

    with open(r'/etc/pizerotimer.yml') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    # date/times in database will be UTC - need this for determining "local"
    # start of week.
    local_tz = pytz.timezone(config['options']['local_tz'])

    # Database Setup
    conn = sqlite3.connect(config['options']['database'])
    db = conn.cursor()
    database_setup()

    # Setup screen
    (r, g, b) = config['colors']['background_under_threshold'].split(',')
    background_under_threshold = color565(int(r), int(g), int(b))
    (r, g, b) = config['colors']['background_over_threshold'].split(',')
    background_over_threshold = color565(int(r), int(g), int(b))
    (r, g, b) = config['colors']['status_bar_color'].split(',')
    status_bar_color = color565(int(r), int(g), int(b))
    (r, g, b) = config['colors']['status_bar_outline_color'].split(',')
    status_bar_outline_color = color565(int(r), int(g), int(b))
    (r, g, b) = config['colors']['foreground_color'].split(',')
    foreground_color = color565(int(r), int(g), int(b))
    (r, g, b) = config['colors']['active_day_color'].split(',')
    active_day_color = color565(int(r), int(g), int(b))
    (r, g, b) = config['colors']['inactive_day_color'].split(',')
    inactive_day_color = color565(int(r), int(g), int(b))
    test_color = color565(0,0,0)
    background_color = background_under_threshold
    turn_on_backlight()
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
    poweroff_cycles = 0
    skip_button_a = False
    while True:
        time.sleep(0.1)
        now = datetime.now()
        elapsed_seconds = time_this_week()
        
        if not (buttonA.value and buttonB.value):    # Either button is pressed
            turn_on_backlight()
        if not skip_button_a and buttonB.value and not buttonA.value:      # just button A pressed
            start_stop_timer()
            skip_button_a = True # Ignore additoinal Button A hits until nothing
        if buttonA.value and not buttonB.value:      # just button B pressed
            poweroff_cycles += 1
        if not buttonA.value and not buttonB.value:  # none pressed
            poweroff_cycles = 0
            skip_button_a = False

        if poweroff_cycles > 50:
            break
    quit(shutdown=True)
