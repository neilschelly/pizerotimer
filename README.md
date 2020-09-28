# PiZeroTimer

I made this timer application to help me keep track of how much I'm working. I
lose track of time too much when I'm working from home. This helps me. 

## How To Use The Tool

### Startup

```bash
sudo ./pizerotimer.py
```

* Upon startup, it will create a sqlite DB file `pizerotimer.db` in the current
  working directory to store the time ranges that you're working.
* It will initialize and turn on the display to start showing your counter.
* After 10 seconds, the backlight will go off if no buttons are pressed. It will
  come back on every time a button is pressed.

### Interaction

* Press the top-right button to just see the current elapsed time for this week.
* Press the bottom-right button to start/stop the timer. If you're in a work
  period that hasn't been stopped, it will stop it. If you're not in a unstopped
  work period, it will start a new one, and the timer will start counting up.
* The time shown on the screen will be the number of hours:minutes:seconds that
  have accumulated of work time since 00:00 midnight on Monday of the current
  week.
* When the time exceeds 40 hours, the screen background will turn red, and the
  backlight will turn on so you see it.
* `Ctrl-C` (or sending a `KILL` or `TERM` signal) will close the database, stop
  any outstanding timers, turn off the backlight, and exit.
* Sending a `HUP` signal to the application will start/stop the timer, just like
  hitting the bottom-right button.

## Hardware

![PiZeroTimer](/docs/device.jpg)

I run it on a [Raspberry Pi Zero WH](https://www.adafruit.com/product/3708) with
a [Mini PiTFT screen](https://www.adafruit.com/product/4484) attached with
Python3. It'll probably run on any Pi and the GPIO headers (optional on the Pi
Zero) are necessary to attach the screen that I chose. You can add headers to a
Pi Zero without them with simple soldering skills.

## Installation

Use raspi-config to enable both the SPI and I2C interfaces via the
`raspi-config` tool and reboot. 

```bash
sudo apt-get install python3 pip3 sqlite3
sudo pip3 install -r requirements.txt
sudo ./pizerotimer.py
```

Put the `pizerotimer.yml` file at `/etc/pizerotimer.yml` and create the
directory that your SQLite database will be kept in.

## FIXMEs

* It'd be nice not to have to run as root.
* A systemd unit file to run it as a service is coming soon.
* Provide some simple web UI to see/edit the database time range entries
* Clean up old database time range entries automatically
* If it crashes for some reason, any existing timers won't get stopped. Should
  they?
* Maybe the screen should blink on whenever the elapsed_time crosses an hour?
