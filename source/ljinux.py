# -----------------
#      Ljinux
# Coded on a Raspberry Pi 400
# Ma'am I swear we are alright in the head
# -----------------

# Some important vars
Version = "0.4.0"
Circuitpython_supported = [(7, 3), (8, 0)]  # don't bother with last digit
dmesg = []
access_log = []

# Core board libs
try:
    import gc

    gc.enable()
    usable_ram = gc.mem_alloc() + gc.mem_free()

    import board
    import digitalio
except ImportError:
    print("FATAL: Core libraries loading failed")
    from sys import exit

    exit(1)

print("[    0.00000] Core libs loaded")
dmesg.append("[    0.00000] Core libs loaded")

# Pin allocation tables
pin_alloc = set()
gpio_alloc = {}

# Default password, aka the password if no /LjinuxRoot/etc/passwd is found
dfpasswd = "Ljinux"

# Exit code holder, has to be global for everyone to be able to see it.
Exit = False
Exit_code = 0

# Hardware autodetect vars, starts assuming everything is missing
sdcard_fs = False
print("[    0.00000] Sys vars loaded")
dmesg.append("[    0.00000] Sys vars loaded")

import time

print("[    0.00000] Timing libraries done")
dmesg.append("[    0.00000] Timing libraries done")
uptimee = (
    -time.monotonic()
)  # using uptimee as an offset, this way uptime + time.monotonic = 0 at this very moment and it goes + from here on out
print("[    0.00000] Got time zero")
dmesg.append("[    0.00000] Got time zero")

# dmtex previous end holder
oend = "\n"  # needed to mask print

try:
    from jcurses import jcurses

    term = jcurses()  # the main curses entity, used primarily for based.shell()
    print("[    0.00000] Loaded jcurses")
    dmesg.append("[    0.00000] Loaded jcurses")
except ImportError:
    print("FATAL: FAILED TO LOAD JCURSES")
    exit(0)


def dmtex(texx=None, end="\n", timing=True, force=False):
    # Persistent offset, Print "end=" preserver

    # current time since ljinux start rounded to 5 digits
    ct = "%.5f" % (uptimee + time.monotonic())

    # used to disable the time print
    strr = (
        "[{u}{upt}] {tx}".format(
            u="           ".replace(" ", "", len(ct)), upt=str(ct), tx=texx
        )
        if timing
        else texx
    )

    if (not term.dmtex_suppress) or force:
        print(strr, end=end)  # using the provided end

    global oend
    """
    if the oend of the last print is a newline we add a new entry
    otherwise we go to the last one and we add it along with the old oend
    """
    if "\n" == oend:
        dmesg.append(strr)
    elif (len(oend.replace("\n", "")) > 0) and (
        "\n" in oend
    ):  # there is hanging text in old oend
        dmesg[-1] += oend.replace("\n", "")
        dmesg.append(strr)
    else:
        dmesg[-1] += oend + strr
    oend = end  # oend for next

    del ct, strr


print("[    0.00000] Timings reset")
dmesg.append("[    0.00000] Timings reset")

# Now we can use this function to get a timing
dmtex("Basic Libraries loading")

# Basic absolutely needed libs
from sys import (
    implementation,
    platform,  # needed for neofetch btw
    modules,
    exit,
    stdout,
)

dmtex("System libraries loaded")

try:
    import busio

    from microcontroller import cpu

    from storage import remount, VfsFat, mount, getmount

    from os import chdir, rmdir, mkdir, sync, getcwd, listdir, remove, sync

    from io import StringIO
    from usb_cdc import console
    from getpass import getpass
    import json
    from traceback import print_exception
    from math import trunc

    dmtex("Basic libraries loaded")
except ImportError:
    dmtex("FATAL: BASIC LIBRARIES LOAD FAILED")
    exit(0)

try:
    from neopixel_write import neopixel_write

    try:  # we can't fail this part though
        from neopixel_colors import neopixel_colors as nc
    except ImportError:
        dmtex("FATAL: FAILED TO LOAD NEOPIXEL_COLORS")
        exit(1)
except ImportError:
    pass  # no big deal, this just isn't a neopixel board

# Kernel cmdline.txt
try:

    with open("/config.json") as config_file:
        dmtex("Loaded /config.json")
        configg = json.load(config_file)
        del config_file

    for i in configg:
        if i.startswith("_"):
            del configg[i]

except (ValueError, OSError):
    configg = {}
    dmtex("Kernel config could not be found / parsed, applying defaults")

try:
    from lj_colours import lJ_Colours as colors

    print(colors.reset_s_format, end="")
    dmtex("Loaded lj_colours")
except ImportError:
    dmtex(f"{colors.error}FATAL:{colors.endc} FAILED TO LOAD LJ_COLOURS")
    dmtex(
        "If you intented to disable colors, just rename lj_colours_placebo -> lj_colours"
    )
    exit(0)

dmtex("Options applied:")

defaultoptions = {  # default configuration, in line with the manual (default value, type, allocates pin bool)
    "led": (0, int, True),
    "ledtype": ("generic", str, False),
    "SKIPCP": (False, bool, False),
    "DEBUG": (False, bool, False),
    "sd_SCLK": (-1, int, True),
    "sd_SCSn": (-1, int, True),
    "sd_MISO": (-1, int, True),
    "sd_MOSI": (-1, int, True),
}

# pintab
try:
    from pintab import pintab
except:
    dmtex(
        f"{colors.error}ERROR:{colors.endc} Board pintab cannot be loaded!\n\nCannot continue."
    )
    exit(1)

# General options
for optt in list(defaultoptions.keys()):
    try:
        if isinstance(configg[optt], defaultoptions[optt][1]):
            dmtex(
                "\t"
                + colors.green_t
                + "√"
                + colors.endc
                + " "
                + optt
                + "="
                + str(configg[optt]),
                timing=False,
            )
        else:
            raise KeyError
    except KeyError:
        configg.update({optt: defaultoptions[optt][0]})
        dmtex(
            f'Missing / Invalid value for "{optt}" applied: {configg[optt]}',
            timing=False,
        )
    if defaultoptions[optt][2]:
        pin = configg[optt]
        if pin in pin_alloc:
            dmtex("PIN ALLOCATED, EXITING")
            exit(0)
        elif pin == -1:
            pass
        else:
            pin_alloc.add(pin)
        del pin

dmtex("Total pin alloc: ", end="")
for pin in pin_alloc:
    dmtex(str(pin), timing=False, end=" ")
dmtex("", timing=False)

if configg["led"] == -1:
    boardLED = board.LED
else:
    boardLED = pintab[configg["led"]]

del defaultoptions

# basic checks
if not configg["SKIPCP"]:  # beta testing
    good = False
    for i in Circuitpython_supported:
        if implementation.version[:2] == i:
            good = True
            break
    if good:
        dmtex("Running on supported implementation")
    else:
        dmtex(
            "-" * 42
            + "\n"
            + " " * 14
            + "WARNING: Unsupported CircuitPython version\n"
            + " " * 14
            + "-" * 42
        )
        for i in range(10, 0):
            print(f"WARNING: Unsupported CircuitPython version (Continuing in {i})")
            time.sleep(1)
    del good
else:
    print("Skipped CircuitPython version checking, happy beta testing!")

dmtex((f"Board memory: {usable_ram} bytes"))
dmtex((f"Memory free: {gc.mem_free()} bytes"))
dmtex("Basic checks done")

# audio
NoAudio = False  # used to ensure audio will NOT be used in case of libs missing
try:
    from audiomp3 import MP3Decoder
    from audiopwmio import PWMAudioOut
    from audiocore import WaveFile

    dmtex("Audio libraries loaded")
except ImportError:
    NoAudio = True
    dmtex(colors.error + "Notice: " + colors.endc + "Audio libraries loading failed")

# sd card
try:
    import adafruit_sdcard

    dmtex("Sdcard libraries loaded")
except ImportError:
    dmtex(colors.error + "Notice: " + colors.endc + "SDcard libraries loading failed")

dmtex("Imports complete")


def systemprints(mod, tx1, tx2=None):
    dmtex("[ ", timing=False, end="")

    mods = {
        1: lambda: dmtex(colors.green_t + "OK", timing=False, end=""),
        2: lambda: dmtex(colors.magenta_t + "..", timing=False, end=""),
        3: lambda: dmtex(colors.red_t + "FAILED", timing=False, end=""),
    }
    mods[mod]()
    dmtex(colors.endc + " ] " + tx1, timing=False)
    if tx2 is not None:
        dmtex("           -> " if mod is 3 else "       -> ", timing=False, end="")
        dmtex(tx2, timing=False)


dmtex("Additional loading done")


class ljinux:
    modules = dict()

    class api:
        def var(var, data=None, system=False):
            """
            Set a ljinux user variable without mem leaks
            No handbreak installed.
            data=None deletes
            """
            if not system:
                if var in ljinux.based.user_vars.keys():
                    del ljinux.based.user_vars[var]
                if data is not None:
                    ljinux.based.user_vars.update({var: data})
            else:
                if var in ljinux.based.system_vars.keys():
                    del ljinux.based.system_vars[var]
                if data is not None:
                    ljinux.based.system_vars.update({var: data})
            del var, data, system

        def xarg(rinpt=None, fn=False):
            """
            Proper argument parsing for ljinux, send your input stream to here and you will receive a dict in return

            The return dict contains 3 items:
                "w" for the words that don't belong to a specific option. Example: "ls /bin", "/bin" is gonna be returned in "w"
                "hw" for the words, that were hidden due to an option. Example "ls -a /bin", "/bin" is
                 not gonna be in "w" as it is a part of "o" but will be in "hw".
                "o" for all the options, with their respective values. Example: "ls -a /bin", {"a": "/bin"} is gonna be in "o"
                "n" if False is passed to fn, contains the filename

            Variables automatically translated.
            GPIO excluded.
            """

            if rinpt is None:
                rinpt = ljinux.based.user_vars["argj"]

            inpt = rinpt.split(" ")
            del rinpt

            options = dict()
            words = list()
            hidwords = list()

            n = False  # in keyword
            s = False  # in string
            temp_s = None  # temporary string
            entry = None  # keyword

            r = 0 if fn else 1
            del fn

            for i in range(r, len(inpt)):
                if inpt[i].startswith("$"):  # variable
                    if not s:
                        inpt[i] = ljinux.api.adv_input(inpt[i][1:])
                    elif inpt[i].endswith('"'):
                        temp_s += ljinux.api.adv_input(inpt[i][:-1])
                        words.append(temp_s)
                        s = False
                    elif '"' not in inpt[i]:
                        temp_s += " " + ljinux.api.adv_input(inpt[i][1:])
                        continue
                    else:
                        temp_s += " " + ljinux.api.adv_input(
                            inpt[i][1 : inpt[i].find('"')]
                        )
                        words.append(temp_s)
                        s = False
                        inpt[i] = inpt[i][inpt[i].find('"') + 1 :]
                elif (not s) and inpt[i].startswith('"$'):
                    if inpt[i].endswith('"'):
                        inpt[i] = ljinux.api.adv_input(inpt[i][2:-1])
                    else:
                        temp_s = ljinux.api.adv_input(inpt[i][2:])
                        s = True
                        continue
                if not n:
                    if (not s) and inpt[i].startswith("-"):
                        if inpt[i].startswith("--"):
                            entry = inpt[i][2:]
                        else:
                            entry = inpt[i][1:]
                        n = True
                    elif (not s) and inpt[i].startswith('"'):
                        if not inpt[i].endswith('"'):
                            temp_s = inpt[i][1:]
                            s = True
                        else:
                            words.append(inpt[i][1:-1])
                    elif s:
                        if inpt[i].endswith('"'):
                            temp_s += " " + inpt[i][:-1]
                            words.append(temp_s)
                            s = False
                        else:
                            temp_s += " " + inpt[i]
                    else:
                        words.append(inpt[i])
                else:  # in keyword
                    if (not s) and inpt[i].startswith('"'):
                        if not inpt[i].endswith('"'):
                            temp_s = inpt[i][1:]
                            s = True
                        else:
                            options.update({entry: inpt[i][1:-1]})
                            hidwords.append(inpt[i][1:-1])
                            n = False
                    elif s:
                        if inpt[i].endswith('"'):
                            temp_s += " " + inpt[i][:-1]
                            options.update({entry: temp_s})
                            hidwords.append(temp_s)
                            n = False
                            s = False
                        else:
                            temp_s += " " + inpt[i]
                    elif inpt[i].startswith("-"):
                        options.update({entry: None})  # no option for the previous one
                        if inpt[i].startswith("--"):
                            entry = inpt[i][2:]
                        else:
                            entry = inpt[i][1:]
                        # leaving n = True
                    else:
                        options.update({entry: inpt[i]})
                        hidwords.append(inpt[i])
                        n = False
            if n:  # we have incomplete keyword
                # not gonna bother if s is True
                options.update({entry: None})
                hidwords.append(inpt[i])

            del n, entry, s, temp_s

            argd = {
                "w": words,
                "hw": hidwords,
                "o": options,
            }

            if r is 1:  # add the filename
                argd.update({"n": inpt[0]})
            del options, words, hidwords, inpt, r
            return argd

        class fopen(object):
            def __init__(self, fname, mod="r", ctx=None):
                self.fn = fname
                self.mod = mod

            def __enter__(self):
                try:
                    global sdcard_fs
                    rm = False  # remount
                    if "w" in self.mod or "a" in self.mod:
                        rm = True
                    if rm and not sdcard_fs:
                        remount("/", False)
                    self.file = open(ljinux.api.betterpath(self.fn), self.mod)
                    if rm and not sdcard_fs:
                        remount("/", True)
                    del rm
                except RuntimeError:
                    return None
                return self.file

            def __exit__(self, typee, value, traceback):
                self.file.flush()
                self.file.close()
                del self.file, self.fn, self.mod

        def isdir(dirr, rdir=None):
            """
            Checks if given item is file (returns 0) or directory (returns 1).
            Returns 2 if it doesn't exist.
            """
            dirr = ljinux.api.betterpath(dirr)
            rdir = ljinux.api.betterpath(rdir)
            cddd = getcwd() if rdir is not None else rdir

            res = 2

            try:
                chdir(dirr)
                chdir(cddd)
                res = 1
            except OSError:
                rr = "/"
                try:
                    # browsing deep
                    if dirr.count(rr) not in [0, 1] and dirr[
                        dirr.rfind(rr) + 1 :
                    ] in listdir(dirr[: dirr.rfind(rr)]):
                        res = 0
                    elif dirr.count(rr) is 1 and dirr.startswith(rr):
                        # browsing root
                        if dirr[1:] in listdir(rr):
                            res = 0
                    else:
                        # browsing dum
                        if dirr[dirr.rfind(rr) + 1 :] in listdir(
                            dirr[: dirr.rfind(rr)]
                        ):
                            res = 0
                        else:
                            raise OSError

                except OSError:
                    try:
                        if dirr in (
                            listdir(cddd) + (listdir(rdir) if rdir is not None else [])
                        ):
                            res = 0
                    except OSError:
                        res = 2  # we have had enough
                del rr
            del cddd
            return res

        def betterpath(back=None):
            """
            Removes /LjinuxRoot from path and puts it back
            """
            res = ""
            userr = ljinux.based.system_vars["USER"].lower()
            if userr != "root":
                hd = "/LjinuxRoot/home/" + ljinux.based.system_vars["USER"].lower()
            else:
                hd = "/"
            del userr
            if back is None:
                a = getcwd()
                if a.startswith(hd):
                    res = "~" + a[len(hd) :]
                elif a == "/":
                    res = "&/"
                elif a == "/LjinuxRoot":
                    res = "/"
                elif a.startswith("/LjinuxRoot"):
                    res = a[11:]
                else:
                    res = "&" + a
                del a
            else:  # resolve path back to normal
                if back in ["&/", "&"]:  # board root
                    res = "/"
                elif back.startswith("&/"):
                    res = back[1:]
                elif back.startswith("/LjinuxRoot"):
                    res = back  # already good
                elif back[0] == "/":
                    # This is for absolute paths
                    res = "/LjinuxRoot"
                    if back != "/":
                        res += back
                elif back[0] == "~":
                    res = hd
                    if back != "~":
                        res += back[1:]
                else:
                    res = back
            del back, hd
            return res

        def adv_input(whatever, _type=str):
            """
            Universal variable request
            Returns the variable's value in the specified type
            Parameters:
                whatever : The name of the variable
                _type : The type in which it should be returned
            Returns:
                The result of the variable in the type
                specified if found
                Otherwise, it returns the input
            """
            res = None
            if whatever.isdigit():
                res = int(whatever)
            elif whatever in ljinux.based.user_vars:
                res = ljinux.based.user_vars[whatever]
            elif whatever in ljinux.based.system_vars:
                res = ljinux.based.system_vars[whatever]
            elif whatever in ljinux.io.sys_getters:
                res = ljinux.io.sys_getters[whatever]()
            else:
                res = whatever
            return _type(res)

    class history:
        historyy = []
        nav = [0, 0, ""]
        sz = 50

        def load(filen):
            ljinux.history.historyy = list()
            try:
                with open(filen, "r") as historyfile:
                    for line in historyfile:
                        ljinux.io.ledset(3)  # act
                        ljinux.history.historyy.append(line.strip())
                        ljinux.io.ledset(1)  # idle
                        del line

            except OSError:
                try:
                    if not sdcard_fs:
                        remount("/", False)
                    with open(filen, "w") as historyfile:
                        pass
                    if not sdcard_fs:
                        remount("/", True)
                except RuntimeError:
                    ljinux.based.error(4, filen)
                ljinux.io.ledset(1)  # idle

        def appen(itemm):  # add to history, but don't save to file
            if (
                len(ljinux.history.historyy) > 0 and itemm != ljinux.history.gett(1)
            ) or len(ljinux.history.historyy) is 0:
                if len(ljinux.history.historyy) < ljinux.history.sz:
                    ljinux.history.historyy.append(itemm)
                elif len(ljinux.history.historyy) is ljinux.history.sz:
                    ljinux.history.shift(itemm)
                else:
                    ljinux.history.historyy = ljinux.history.historyy[
                        -(ljinux.history.sz - 1) :
                    ] + [itemm]

        def shift(itemm):
            ljinux.history.historyy.reverse()
            ljinux.history.historyy.pop()
            ljinux.history.historyy.reverse()
            ljinux.history.historyy.append(itemm)
            del itemm

        def save(filen):
            try:
                if not sdcard_fs:
                    remount("/", False)
                with open(filen, "w") as historyfile:
                    for item in ljinux.history.historyy:
                        historyfile.write(item + "\n")
                if not sdcard_fs:
                    remount("/", True)
            except (OSError, RuntimeError):
                ljinux.based.error(7, filen)

        def clear(filen):
            try:
                # deletes all history, from ram and storage
                a = open(filen, "r")
                a.close()
                del a
                if not sdcard_fs:
                    remount("/", False)
                with open(filen, "w") as historyfile:
                    historyfile.flush()
                if not sdcard_fs:
                    remount("/", True)
                ljinux.history.historyy.clear()
            except (OSError, RuntimeError):
                ljinux.based.error(4, filen)

        def gett(whichh):  # get a specific history item, from loaded history
            obj = len(ljinux.history.historyy) - whichh
            if obj < 0:
                raise IndexError
            return str(ljinux.history.historyy[obj])

        def getall():  # get the whole history, numbered, line by line
            for index, item in enumerate(ljinux.history.historyy):
                print(f"{index + 1}: {item}")
                del index, item

    class io:
        # activity led

        ledcases = {
            0: nc.off,
            1: nc.idle,
            2: nc.idletype,
            3: nc.activity,
            4: nc.waiting,
            5: nc.error,
            6: nc.killtheuser,
            7: nc.waiting2,
        }

        getled = 0

        led = digitalio.DigitalInOut(boardLED)
        led.direction = digitalio.Direction.OUTPUT
        if configg["ledtype"] == "generic":
            led.value = True
        elif configg["ledtype"] == "generic_invert":
            led.value = False
        elif configg["ledtype"] == "neopixel":
            neopixel_write(led, nc.idle)

        def ledset(state):
            """
            Set the led to a state.
            state can be int with one of the predifined states,
            or a tuple like (10, 40, 255) for a custom color
            """
            if isinstance(state, int):
                ## use preconfigured led states
                if configg["ledtype"] in ["generic", "generic_invert"]:
                    if state in [0, 3, 4, 5]:  # close tha led
                        ljinux.io.led.value = (
                            False if configg["ledtype"] == "generic" else True
                        )
                    else:
                        ljinux.io.led.value = (
                            True if configg["ledtype"] == "generic" else False
                        )
                elif configg["ledtype"] == "neopixel":
                    neopixel_write(ljinux.io.led, ljinux.io.ledcases[state])
            elif isinstance(state, tuple):
                # a custom color
                if configg["ledtype"] in ["generic", "generic_invert"]:
                    if not (state[0] == 0 and state[1] == 0 and state[2] == 0):
                        # apply 1 if any of tuple >0
                        ljinux.io.led.value = (
                            True if configg["ledtype"] == "generic" else False
                        )
                    else:
                        ljinux.io.led.value = (
                            False if configg["ledtype"] == "generic" else True
                        )
                elif configg["ledtype"] == "neopixel":
                    neopixel_write(ljinux.io.led, bytearray(state))
            else:
                raise TypeError
            ljinux.io.getled = state

        def get_static_file(filename, m="rb"):
            "Static file generator"
            try:
                with open(filename, m) as f:
                    b = None
                    while b is None or len(b) == 2048:
                        b = f.read(2048)
                        yield b
            except OSError:
                yield f"Error: File '{filename}' Not Found"

        def start_sdcard():
            global sdcard_fs
            if (
                configg["sd_SCLK"] != -1
                and configg["sd_SCSn"] != -1
                and configg["sd_MISO"] != -1
                and configg["sd_MOSI"] != -1
            ):
                spi = busio.SPI(board.GP2, MOSI=board.GP3, MISO=board.GP4)
                cs = digitalio.DigitalInOut(board.GP5)
            else:
                sdcard_fs = False
                dmtex("No pins for sdcard, skipping setup")
                return
            dmtex("SD bus ready")
            try:
                sdcard = adafruit_sdcard.SDCard(spi, cs)
                vfs = VfsFat(sdcard)
                dmtex("SD mount attempted")
                mount(vfs, "/LjinuxRoot")
                sdcard_fs = True
            except NameError:
                dmtex("SD libraries not present, aborting.")
            del spi
            del cs
            try:
                del sdcard
                del vfs
            except NameError:
                pass

        sys_getters = {
            "sdcard": lambda: str(sdcard_fs),
            "uptime": lambda: str("%.5f" % (uptimee + time.monotonic())),
            "temperature": lambda: str("%.2f" % cpu.temperature),
            "memory": lambda: str(gc.mem_free()),
            "implementation_version": lambda: ljinux.based.system_vars[
                "IMPLEMENTATION"
            ],
            "implementation": lambda: implementation.name,
            "frequency": lambda: str(cpu.frequency),
            "voltage": lambda: str(cpu.voltage),
        }

    class based:
        silent = False
        olddir = None
        pled = False  # persistent led state for nested exec
        alias_dict = {}
        raw_command_input = ""

        user_vars = {
            "history-file": "/LjinuxRoot/home/board/.history",
            "history-size": "10",
            "return": "0",
        }

        system_vars = {
            "USER": "root",
            "SECURITY": "off",
            "Init-type": "oneshot",
            "HOSTNAME": "ljinux",
            "TERM": "xterm-256color",
            "LANG": "en_GB.UTF-8",
            "BOARD": board.board_id,
            "IMPLEMENTATION": ".".join(map(str, list(implementation.version))),
        }

        def get_bins():
            try:
                return [
                    dirr[:-4]
                    for dirr in listdir("/LjinuxRoot/bin")
                    if dirr.endswith(".lja") and not dirr.startswith(".")
                ]
            except OSError:  # Yea no root, we cope
                return list()

        def error(wh=3, f=None, prefix=f"{colors.magenta_t}Based{colors.endc}"):
            """
            The different errors used by the based shell.
            CODE:
                ljinux.based.error([number])
                where [number] is one of the error below
            """
            ljinux.io.ledset(5)  # error
            time.sleep(0.1)
            errs = {
                1: "Syntax Error",
                2: "Input Error",
                3: "Error",
                4: f'"{f}": No such file or directory',
                5: "Network unavailable",
                6: "Display not attached",
                7: "Filesystem unwritable, board in developer mode",
                8: "Missing files",
                9: "Missing arguments",
                10: "File exists",
                11: "Not enough system memory",
                12: "Based: Error, variable already used",
                13: f"Terminal too small, minimum size: {f}",
                14: "Is a file",
                15: "Is a directory",
            }
            print(f"{prefix}: {errs[wh]}")
            ljinux.io.ledset(1)
            del errs

        def autorun():
            ljinux.io.ledset(3)  # act
            global Exit
            global Exit_code
            global Version

            ljinux.based.system_vars["VERSION"] = Version

            print(
                "\nWelcome to ljinux wannabe Kernel {}!\n\n".format(
                    ljinux.based.system_vars["VERSION"]
                ),
                end="",
            )

            try:
                systemprints(2, "Mount /LjinuxRoot")
                ljinux.io.start_sdcard()
                systemprints(1, "Mount /LjinuxRoot")
            except OSError:
                systemprints(
                    3,
                    "Mount /LjinuxRoot",
                    "Error: sd card not available, assuming built in fs",
                )
                del modules["adafruit_sdcard"]
                dmtex("Unloaded sdio libraries")
            ljinux.io.ledset(1)  # idle
            systemprints(
                2,
                "Running Init Script",
            )
            systemprints(
                2,
                "Attempting to open /LjinuxRoot/boot/Init.lja..",
            )
            lines = None
            Exit_code = 0  # resetting, in case we are the 2nd .shell
            try:
                ljinux.io.ledset(3)  # act
                ljinux.based.command.execc(["/LjinuxRoot/boot/Init.lja"])
                systemprints(1, "Running Init Script")
            except OSError:
                systemprints(3, "Running Init Script")
            ljinux.history.load(ljinux.based.user_vars["history-file"])
            try:
                ljinux.history.sz = int(ljinux.based.user_vars["history-size"])
            except:
                pass
            systemprints(1, "History Reload")
            if ljinux.based.system_vars["Init-type"] == "oneshot":
                systemprints(1, "Init complete")
            elif ljinux.based.system_vars["Init-type"] == "reboot-repeat":
                Exit = True
                Exit_code = 245
                print(
                    f"{colors.magenta_t}Based{colors.endc}: Init complete. Restarting"
                )
            elif ljinux.based.system_vars["Init-type"] == "delayed-reboot-repeat":
                try:
                    time.sleep(float(ljinux.based.user_vars["repeat-delay"]))
                except IndexError:
                    print(
                        f"{colors.magenta_t}Based{colors.endc}: No delay specified! Waiting 60s."
                    )
                    time.sleep(60)
                    Exit = True
                    Exit_code = 245
                    print(
                        f"{colors.magenta_t}Based{colors.endc}: Init complete and delay finished. Restarting"
                    )
            elif ljinux.based.system_vars["Init-type"] == "oneshot-quit":
                Exit = True
                Exit_code = 244
                print(f"{colors.magenta_t}Based{colors.endc}: Init complete. Halting")
            elif ljinux.based.system_vars["Init-type"] == "repeat":
                try:
                    while not Exit:
                        for commandd in lines:
                            ljinux.based.shell(commandd)

                except KeyboardInterrupt:
                    print(f"{colors.magenta_t}Based{colors.endc}: Caught Ctrl + C")
            elif ljinux.based.system_vars["Init-type"] == "delayed-repeat":
                try:
                    time.sleep(float(ljinux.based.user_vars["repeat-delay"]))
                except IndexError:
                    print(
                        f"{colors.magenta_t}Based{colors.endc}: No delay specified! Waiting 60s."
                    )
                    time.sleep(60)
                try:
                    while not Exit:
                        for commandd in lines:
                            ljinux.based.shell(commandd)

                except KeyboardInterrupt:
                    print(f"{colors.magenta_t}Based{colors.endc}: Caught Ctrl + C")
            else:
                print(
                    f"{colors.magenta_t}Based{colors.endc}: Init-type specified incorrectly, assuming oneshot"
                )
            ljinux.io.ledset(1)  # idle
            while not Exit:
                try:
                    ljinux.based.shell()
                except KeyboardInterrupt:
                    stdout.write("^C\n")
            Exit = False  # to allow ljinux.based.shell to be rerun
            return Exit_code

        class command:
            def not_found(errr):  # command not found
                print(
                    f"{colors.magenta_t}Based{colors.endc}: '{errr[0]}': command not found"
                )
                ljinux.based.user_vars["return"] = "1"

            def execc(argj):
                global Exit
                global Exit_code

                if argj[0] == "exec":
                    argj = argj[1:]

                try:
                    with open(argj[0], "r") as filee:
                        ljinux.based.olddir = getcwd()
                        mine = False
                        if not ljinux.based.pled:
                            ljinux.based.pled = True
                            ljinux.io.ledset(3)
                            mine = True
                        else:
                            old = ljinux.io.getled
                            ljinux.io.ledset(3)
                            time.sleep(0.03)
                            ljinux.io.ledset(old)
                            del old
                        for j in filee:
                            j = j.strip()

                            ljinux.based.shell(
                                'argj = "{}"'.format(" ".join([str(i) for i in argj])),
                                led=False,
                            )

                            ljinux.based.shell(j, led=False)

                            del j
                        if ljinux.based.olddir != getcwd():
                            chdir(ljinux.based.olddir)
                        if mine:
                            ljinux.io.ledset(1)
                        del mine
                except OSError:
                    ljinux.based.error(4, argj[0])

            def helpp(dictt):
                print(
                    f"LNL {colors.magenta_t}based\nThese shell commands are defined internally or are in PATH.\nType 'help' to see this list.\n"
                )  # shameless, but without rgb spam

                l = ljinux.based.get_bins() + list(dictt.keys())

                lenn = 0
                for i in l:
                    if len(i) > lenn:
                        lenn = len(i)
                lenn += 2

                for index, tool in enumerate(l):
                    print(
                        colors.green_t + tool + colors.endc,
                        end=(" " * lenn).replace(" ", "", len(tool)),
                    )
                    if index % 4 == 3:
                        stdout.write("\n")  # stdout faster than print cuz no logic
                stdout.write("\n")

                del l
                del lenn

            def var(inpt):  # variables setter / editor
                valid = True
                if inpt[0] == "var":  # check if the var is passed and trim it
                    temp = inpt
                    del inpt
                    inpt = []
                    for i in range(len(temp) - 1):
                        inpt.append(temp[i + 1])
                try:
                    # basic checks, if any of this fails, quit
                    for chh in inpt[0]:
                        if not (chh.islower() or chh.isupper() or chh == "-"):
                            valid = False
                            break
                    if inpt[1] != "=" or not (
                        inpt[2].startswith('"')
                        or inpt[2].isdigit()
                        or inpt[2].startswith("/")
                        or inpt[2].startswith("GP")
                        or inpt[2] in gpio_alloc
                    ):
                        valid = False
                    if valid:  # if the basic checks are done we can procceed to work
                        new_var = ""
                        if inpt[2].startswith('"'):
                            countt = len(inpt)
                            if inpt[2].endswith('"'):
                                new_var = str(inpt[2])[1:-1]
                            elif (countt > 3) and (inpt[countt - 1].endswith('"')):
                                new_var += str(inpt[2])[1:] + " "
                                for i in range(3, countt - 1):
                                    new_var += inpt[i] + " "
                                new_var += str(inpt[countt - 1])[:-1]
                            else:
                                ljinux.based.error(1)
                                valid = False
                        elif inpt[2].startswith("GP"):  # gpio allocation
                            if len(inpt[2]) > 2 and len(inpt[2]) <= 4:
                                gpp = int(inpt[2][2:])
                            else:
                                ljinux.based.error(2)
                                return "1"
                            if gpp in pin_alloc:
                                dmtex("PIN ALLOCATED, ABORT", force=True)
                                return "1"
                            else:
                                if ljinux.api.adv_input(inpt[0], str) == inpt[0]:
                                    gpio_alloc.update(
                                        {
                                            inpt[0]: [
                                                digitalio.DigitalInOut(pintab[gpp]),
                                                gpp,
                                            ]
                                        }
                                    )
                                    gpio_alloc[inpt[0]][0].switch_to_input(
                                        pull=digitalio.Pull.DOWN
                                    )
                                    pin_alloc.add(gpp)
                                else:
                                    ljinux.based.error(12)
                            del gpp
                            valid = False  # skip the next stuff

                        elif inpt[0] in gpio_alloc:
                            if inpt[2].isdigit():
                                if (
                                    gpio_alloc[inpt[0]][0].direction
                                    != digitalio.Direction.OUTPUT
                                ):
                                    gpio_alloc[inpt[0]][
                                        0
                                    ].direction = digitalio.Direction.OUTPUT
                                gpio_alloc[inpt[0]][0].value = int(inpt[2])
                                valid = False  # skip the next stuff
                        elif inpt[2] in gpio_alloc:
                            pass  # yes we really have to pass
                        else:
                            new_var += str(inpt[2])
                    else:
                        ljinux.based.error(1)
                        valid = False
                    if valid:  # now do the actual set
                        if inpt[0] in ljinux.based.system_vars:
                            if not (ljinux.based.system_vars["SECURITY"] == "on"):
                                ljinux.based.system_vars[inpt[0]] = new_var
                            else:
                                print(
                                    colors.error
                                    + "Cannot edit system variables, security is enabled."
                                    + colors.endc
                                )
                        elif (
                            inpt[0] == ljinux.api.adv_input(inpt[0], str)
                            or inpt[0] in ljinux.based.user_vars
                        ):
                            if inpt[2] in gpio_alloc:  # if setting value is gpio
                                if (
                                    gpio_alloc[inpt[2]][0].direction
                                    != digitalio.Direction.INPUT
                                ):
                                    gpio_alloc[inpt[2]][
                                        0
                                    ].direction = digitalio.Direction.INPUT
                                    gpio_alloc[inpt[2]][0].switch_to_input(
                                        pull=digitalio.Pull.DOWN
                                    )
                                ljinux.based.user_vars[inpt[0]] = str(
                                    int(gpio_alloc[inpt[2]][0].value)
                                )
                            else:
                                ljinux.based.user_vars[inpt[0]] = new_var
                        else:
                            ljinux.based.error(12)
                except IndexError:
                    ljinux.based.error(1)

            def dell(inpt):  # del variables, and dell computers
                try:
                    a = inpt[1]
                    if a == ljinux.api.adv_input(a, str) and a not in gpio_alloc:
                        ljinux.based.error(2)
                    else:
                        if a in gpio_alloc:
                            gpio_alloc[a][0].deinit()
                            pin_alloc.remove(gpio_alloc[a][1])
                            del gpio_alloc[a]
                        elif a in ljinux.based.system_vars:
                            if not (ljinux.based.system_vars["SECURITY"] == "on"):
                                del ljinux.based.system_vars[a]
                            else:
                                print(
                                    colors.error
                                    + "Cannot edit system variables, security is enabled."
                                    + colors.endc
                                )
                        elif a in ljinux.based.user_vars:
                            del ljinux.based.user_vars[a]
                        else:
                            raise IndexError
                    del a
                except IndexError:
                    ljinux.based.error(1)

            def suuu(inpt):  # su command but worse
                global dfpasswd
                passwordarr = {}
                try:
                    try:
                        with open("/LjinuxRoot/etc/passwd", "r") as data:
                            for line in data:
                                dt = line.split()
                                passwordarr[dt[0]] = dt[1]
                                del dt, line
                    except OSError:
                        pass
                    ljinux.io.ledset(2)
                    if passwordarr["root"] == getpass():
                        ljinux.based.system_vars["SECURITY"] = "off"
                        print("Authentication successful. Security disabled.")
                    else:
                        ljinux.io.ledset(3)
                        time.sleep(2)
                        print(
                            colors.error + "Authentication unsuccessful." + colors.endc
                        )

                    try:
                        del passwordarr
                    except NameError:
                        pass

                except (KeyboardInterrupt, KeyError):  # I betya some cve's cover this

                    try:
                        del passwordarr
                    except NameError:
                        pass

                    if dfpasswd == getpass():
                        ljinux.based.system_vars["security"] = "off"
                        print("Authentication successful. Security disabled.")
                    else:
                        print(
                            colors.error + "Authentication unsuccessful." + colors.endc
                        )
                try:
                    del passwordarr
                except NameError:
                    pass

            def historgf(inpt):  # history frontend
                try:
                    if inpt[1] == "clear":
                        ljinux.history.clear(ljinux.based.user_vars["history-file"])
                    elif inpt[1] == "load":
                        ljinux.history.load(ljinux.based.user_vars["history-file"])
                        try:
                            ljinux.history.sz = int(
                                ljinux.based.user_vars["history-size"]
                            )
                        except:
                            pass
                    elif inpt[1] == "save":
                        ljinux.history.save(ljinux.based.user_vars["history-file"])
                    else:
                        print(f"{colors.magenta_t}Based{colors.endc}: Invalid option")
                except IndexError:
                    ljinux.history.getall()

            def iff(inpt):  # the if, the pinnacle of ai WIP
                condition = []
                complete = False
                next_part = None
                if inpt[1] == "[":
                    for i in range(2, len(inpt)):
                        if inpt[i] == "]":
                            complete = True
                            next_part = i + 1
                            break
                        else:
                            condition.append(inpt[i])
                    if complete:
                        try:
                            val = False
                            need_new_cond = False
                            i = 0
                            while i < len(condition) - 1:
                                if condition[i] == "argj":  # this is an argument check
                                    i += 1  # we can move on as we know of the current situation
                                    if (
                                        condition[i] == "has"
                                    ):  # check if condition is present
                                        i += 1  # we have to keep moving
                                        if (
                                            condition[i]
                                            in ljinux.based.user_vars["argj"]
                                        ):  # it's in!
                                            val = True
                                        else:
                                            val = False
                                        need_new_cond = True
                                    elif (
                                        condition[i].startswith('"')
                                        and condition[i].endswith('"')
                                    ) and (
                                        (condition[i + 1] == "is")
                                        or (condition[i + 1] == "==")
                                        or (condition[i + 1] == "=")
                                    ):  # check next arg for name and the one ahead of it for value
                                        namee = condition[i][1:-1]  # remove ""
                                        i += 2
                                        try:
                                            if (
                                                namee in ljinux.based.user_vars["argj"]
                                            ):  # it's in!
                                                pos = ljinux.based.user_vars[
                                                    "argj"
                                                ].find(namee)
                                                sz = len(namee)
                                                nextt = ljinux.based.user_vars["argj"][
                                                    pos + sz + 1 :
                                                ]
                                                cut = nextt.find(" ") + 1
                                                del sz
                                                del pos
                                                if cut is not 0:
                                                    nextt = nextt[: nextt.find(" ") + 1]
                                                del cut
                                                if nextt == condition[i][1:-1]:
                                                    val = True
                                                    need_new_cond = True
                                                else:
                                                    val = False
                                                    need_new_cond = True
                                                i += 1
                                            else:
                                                raise KeyError
                                            del namee
                                        except KeyError:
                                            print(
                                                f"{colors.magenta_t}Based{colors.endc}: Arg not in argj"
                                            )
                                elif condition[i] == "and":  # and what
                                    i += 1  # just read the argj, i'm not gonna copy the comments
                                    if val == 0:  # no need to keep goin, just break;
                                        break
                                    else:
                                        need_new_cond = False
                                elif condition[i] == "or":  # or what
                                    i += 1
                                    if val == 1:  # no need to keep goin, just break;
                                        break
                                    else:
                                        need_new_cond = False
                                elif condition[i].isdigit():  # meth
                                    i += 1  # todo
                                else:
                                    print(
                                        f"{colors.magenta_t}Based{colors.endc}: Invalid action type: "
                                        + condition[i]
                                    )
                                    break
                            if val == 1:
                                ljinux.based.shell(
                                    " ".join(inpt[next_part:]), led=False
                                )
                            del next_part
                            del val
                        except KeyError:
                            print(
                                f"{colors.magenta_t}Based{colors.endc}: Invalid condition type"
                            )
                    else:
                        print(
                            f"{colors.magenta_t}Based{colors.endc}: Incomplete condition"
                        )
                else:
                    ljinux.based.error(1)
                del need_new_cond
                del complete
                del condition

            def pexecc(inpt):  # filtered & true source
                global Version
                pcomm = ljinux.based.raw_command_input.lstrip(
                    ljinux.based.raw_command_input.split()[0]
                ).replace(" ", "", 1)
                try:
                    exec(pcomm)  # Vulnerability.exe
                    del pcomm
                except Exception as err:
                    print(
                        "Traceback (most recent call last):\n\t"
                        + str(type(err))[8:-2]
                        + ": "
                        + str(err)
                    )
                    del err

            def fpexecc(inpt):  # file pexec
                global Version
                fpargs = list()
                offs = 1

                try:
                    while inpt[offs].startswith("-"):
                        fpargs += list(inpt[offs][1:])
                        offs += 1
                except IndexError:
                    ljinux.based.error(9)
                    ljinux.based.user_vars["return"] = "1"
                    return

                try:
                    a = open(ljinux.api.betterpath(inpt[offs])).read()
                    if not ("t" in fpargs or "l" in fpargs):
                        exec(a)
                    elif "i" in fpargs:
                        exec(a, dict(), dict())
                    elif "l" in fpargs:
                        exec(a, locals())
                    del a
                except Exception as err:
                    print(
                        "Traceback (most recent call last):\n\t"
                        + str(type(err))[8:-2]
                        + ": "
                        + str(err)
                    )
                    del err
                del offs, fpargs

        # the shell function, do not poke, it gets angry
        def shell(inp=None, led=True, args=None, nalias=False):

            global Exit
            if inp is not None and args is not None:
                for i in args:
                    inp += f" {i}"
            del args
            function_dict = {
                # holds all built-in commands. The plan is to move as many as possible externally
                # yea, hello 9/6/22 here, we keepin bash-like stuff in, but we have to take the normal
                # ones out, we almost there
                "error": ljinux.based.command.not_found,
                "exec": ljinux.based.command.execc,
                "help": ljinux.based.command.helpp,
                "var": ljinux.based.command.var,
                "unset": ljinux.based.command.dell,
                "su": ljinux.based.command.suuu,
                "history": ljinux.based.command.historgf,
                "if": ljinux.based.command.iff,
                "pexec": ljinux.based.command.pexecc,
                "fpexec": ljinux.based.command.fpexecc,
            }
            command_input = False
            if not term.enabled:
                ljinux.io.ledset(4)  # waiting for serial
                term.start()
                ljinux.io.ledset(1)  # idle
                term.trigger_dict = {
                    "enter": 0,
                    "ctrlC": 1,
                    "ctrlD": 2,
                    "ctrlL": 13,
                    "tab": 3,
                    "up": 4,
                    "down": 7,
                    "pgup": 11,
                    "pgdw": 12,
                    "overflow": 14,
                    "rest": "stack",
                    "rest_a": "common",
                    "echo": "common",
                }
            if not Exit:
                while (
                    (command_input == False) or (command_input == "\n")
                ) and not Exit:
                    term.trigger_dict["prefix"] = (
                        "["
                        + colors.cyan_t
                        + ljinux.based.system_vars["USER"]
                        + colors.endc
                        + "@"
                        + colors.cyan_t
                        + ljinux.based.system_vars["HOSTNAME"]
                        + colors.endc
                        + "| "
                        + colors.yellow_t
                        + ljinux.api.betterpath()
                        + colors.endc
                        + "]"
                        + colors.blue_t
                        + "> "
                        + colors.endc
                    )
                    if inp is None:
                        command_input = False
                        while (command_input in [False, ""]) and not Exit:
                            try:
                                term.program()
                                if term.buf[0] is 0:
                                    ljinux.history.nav[0] = 0
                                    command_input = term.buf[1]
                                    term.buf[1] = ""
                                    term.focus = 0
                                    stdout.write("\n")
                                elif term.buf[0] is 1:
                                    ljinux.io.ledset(2)  # keyact
                                    print("^C")
                                    term.buf[1] = ""
                                    term.focus = 0
                                    term.clear_line()
                                    ljinux.io.ledset(1)  # idle
                                elif term.buf[0] is 2:
                                    ljinux.io.ledset(2)  # keyact
                                    print("^D")
                                    global Exit
                                    global Exit_code
                                    Exit = True
                                    Exit_code = 0
                                    ljinux.io.ledset(1)  # idle
                                    break
                                elif term.buf[0] is 3:  # tab key
                                    ljinux.io.ledset(2)  # keyact
                                    tofind = term.buf[
                                        1
                                    ]  # made into var for speed reasons
                                    candidates = []
                                    slicedd = tofind.split()
                                    lent = len(slicedd)
                                    if lent > 1:  # suggesting files
                                        files = listdir()
                                        for i in files:
                                            if i.startswith(
                                                slicedd[lent - 1]
                                            ):  # only on the arg we are in
                                                candidates.append(i)
                                        del files
                                    else:  # suggesting bins
                                        bins = ljinux.based.get_bins()
                                        for i in [function_dict, bins]:
                                            for j in i:
                                                if j.startswith(tofind):
                                                    candidates.append(j)
                                        del bins
                                    if len(candidates) > 1:
                                        stdout.write("\n")
                                        minn = 100
                                        for i in candidates:
                                            if not i.startswith("_"):  # discard those
                                                minn = min(minn, len(i))
                                                print("\t" + i)
                                        letters_match = 0
                                        isMatch = True
                                        while isMatch:
                                            for i in range(0, minn):
                                                for j in range(1, len(candidates)):
                                                    try:
                                                        if (
                                                            not candidates[j][
                                                                letters_match
                                                            ]
                                                            == candidates[j - 1][
                                                                letters_match
                                                            ]
                                                        ):
                                                            isMatch = False
                                                            break
                                                        else:
                                                            letters_match += 1
                                                    except IndexError:
                                                        isMatch = False
                                                        break
                                                if not isMatch:
                                                    break
                                        del minn, isMatch
                                        if letters_match > 0:
                                            term.clear_line()
                                            if lent > 1:
                                                term.buf[1] = " ".join(
                                                    slicedd[:-1]
                                                    + [candidates[0][:letters_match]]
                                                )
                                            else:
                                                term.buf[1] = candidates[0][
                                                    :letters_match
                                                ]
                                        term.focus = 0
                                        del letters_match
                                    elif len(candidates) == 1:
                                        term.clear_line()
                                        if lent > 1:
                                            term.buf[1] = " ".join(
                                                slicedd[:-1] + [candidates[0]]
                                            )
                                        else:
                                            term.buf[1] = candidates[0]
                                        term.focus = 0
                                    else:
                                        term.clear_line()
                                    del candidates, lent, tofind, slicedd
                                    ljinux.io.ledset(1)  # idle
                                elif term.buf[0] is 4:  # up
                                    ljinux.io.ledset(2)  # keyact
                                    try:
                                        neww = ljinux.history.gett(
                                            ljinux.history.nav[0] + 1
                                        )
                                        # if no historyitem, we wont run the items below
                                        if ljinux.history.nav[0] == 0:
                                            ljinux.history.nav[2] = term.buf[1]
                                            ljinux.history.nav[1] = term.focus
                                        term.buf[1] = neww
                                        del neww
                                        ljinux.history.nav[0] += 1
                                        term.focus = 0
                                    except IndexError:
                                        pass
                                    term.clear_line()
                                    ljinux.io.ledset(1)  # idle
                                elif term.buf[0] is 7:  # down
                                    ljinux.io.ledset(2)  # keyact
                                    if ljinux.history.nav[0] > 0:
                                        if ljinux.history.nav[0] > 1:
                                            term.buf[1] = ljinux.history.gett(
                                                ljinux.history.nav[0] - 1
                                            )
                                            ljinux.history.nav[0] -= 1
                                            term.focus = 0
                                        else:
                                            # have to give back the temporarily stored one
                                            term.buf[1] = ljinux.history.nav[2]
                                            term.focus = ljinux.history.nav[1]
                                            ljinux.history.nav[0] = 0
                                    term.clear_line()
                                elif term.buf[0] in [11, 12]:  # pgup / pgdw
                                    term.clear_line()
                                elif term.buf[0] is 13:  # Ctrl + L (clear screen)
                                    term.clear()
                                elif term.buf[0] is 14:  # overflow
                                    store = term.buf[1]
                                    term.focus = 0
                                    term.buf[1] = ""
                                    term.trigger_dict["prefix"] = "> "
                                    term.clear_line()
                                    term.program()
                                    if term.buf[0] is 0:  # enter
                                        ljinux.history.nav[0] = 0
                                        command_input = store + term.buf[1]
                                        term.buf[1] = ""
                                        stdout.write("\n")
                                    elif term.buf[0] is 14:  # more lines
                                        store += term.buf[1]
                                        ljinux.history.nav[0] = 0
                                        term.buf[1] = ""
                                        term.focus = 0
                                        term.clear_line()
                                    else:  # not gonna
                                        term.buf[0] = ""
                                        term.focus = 0
                                        ljinux.history.nav[0] = 0
                                    del store

                                try:
                                    if (
                                        command_input[:1] != " "
                                        and command_input != ""
                                        and (not command_input.startswith("#"))
                                    ):
                                        ljinux.history.appen(command_input.strip())
                                except (
                                    AttributeError,
                                    TypeError,
                                ):  # idk why this is here, forgor
                                    pass
                            except KeyboardInterrupt:  # duplicate code as by ^C^C you could escape somehow
                                print("^C")
                                term.buf[1] = ""
                                term.focus = 0
                                term.clear_line()
                    else:
                        command_input = inp
                if not Exit:
                    res = ""
                    if led:
                        ljinux.io.ledset(3)  # act
                    while command_input.startswith(" "):
                        command_input = command_input[1:]
                    if not (command_input == "") and (
                        not command_input.startswith("#")
                    ):
                        if (not "|" in command_input) and (not "&&" in command_input):
                            ljinux.based.raw_command_input = command_input
                            command_split = command_input.split(
                                " "
                            )  # making it an arr of words
                            try:
                                if str(command_split[0])[:2] == "./":
                                    command_split[0] = str(command_split[0])[2:]
                                    if command_split[0] != "":

                                        res = function_dict["exec"](command_split)
                                    else:
                                        print("Error: No file specified")
                                elif (not nalias) and (
                                    command_split[0] in ljinux.based.alias_dict
                                ):
                                    ljinux.based.shell(
                                        ljinux.based.alias_dict[command_split[0]],
                                        led=False,
                                        args=command_split[1:],
                                        nalias=True,
                                    )
                                elif (command_split[0] in function_dict) and (
                                    command_split[0]
                                    not in [
                                        "error",
                                        "help",
                                    ]
                                ):  # those are special bois, they will not be special when I make the api great
                                    gc.collect()
                                    gc.collect()
                                    res = function_dict[command_split[0]](command_split)
                                elif command_split[0] == "help":
                                    res = function_dict["help"](function_dict)
                                elif command_split[1] == "=":
                                    res = function_dict["var"](command_split)
                                else:
                                    raise IndexError
                            except IndexError:
                                bins = ljinux.based.get_bins()
                                certain = False
                                for i in bins:
                                    if (
                                        command_split[0] == i
                                    ) and not certain:  # check if currently examined file is same as command
                                        command_split[0] = (
                                            "/LjinuxRoot/bin/" + i + ".lja"
                                        )  # we have to fill in the full path
                                        certain = True
                                del bins  # we no longer need the list
                                if certain:
                                    gc.collect()
                                    gc.collect()
                                    res = function_dict["exec"](command_split)
                                else:
                                    res = function_dict["error"](command_split)
                                del certain
                        elif ("|" in command_input) and not (
                            "&&" in command_input
                        ):  # this is a pipe  :)
                            ljinux.based.silent = True
                            the_pipe_pos = command_input.find("|", 0)
                            ljinux.based.shell(
                                command_input[: the_pipe_pos - 1], led=False
                            )
                            ljinux.based.silent = False
                            ljinux.based.shell(
                                command_input[the_pipe_pos + 2 :]
                                + " "
                                + ljinux.based.user_vars["return"],
                                led=False,
                            )
                            del the_pipe_pos
                        elif ("&&" in command_input) and not (
                            "|" in command_input
                        ):  # this is a dirty pipe  :)
                            the_pipe_pos = command_input.find("&&", 0)
                            ljinux.based.shell(
                                command_input[: the_pipe_pos - 1], led=False
                            )
                            ljinux.based.shell(
                                command_input[the_pipe_pos + 2 :], led=False
                            )
                            del the_pipe_pos
                        elif ("&&" in command_input) and (
                            "|" in command_input
                        ):  # this pipe was used to end me :(
                            the_pipe_pos_1 = command_input.find("|", 0)
                            the_pipe_pos_2 = command_input.find("&&", 0)
                            if the_pipe_pos_1 < the_pipe_pos_2:  # the first pipe is a |
                                ljinux.based.silent = True
                                ljinux.based.shell(command_input[: the_pipe_pos_1 - 1])
                                ljinux.based.silent = False
                                ljinux.based.shell(
                                    command_input[the_pipe_pos_1 + 2 :]
                                    + " "
                                    + ljinux.based.user_vars["return"]
                                )
                            else:  # the first pipe is a &&
                                ljinux.based.shell(
                                    command_input[: the_pipe_pos_2 - 1], led=False
                                )
                                ljinux.based.shell(
                                    command_input[the_pipe_pos_2 + 2 :], led=False
                                )
                            del the_pipe_pos_1
                            del the_pipe_pos_2
                        else:
                            pass
                    if led:
                        ljinux.io.ledset(1)  # idle
                    gc.collect()
                    gc.collect()
                    return res
