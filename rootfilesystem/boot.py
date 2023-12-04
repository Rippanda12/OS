from storage import getmount, remount, disable_usb_drive
from supervisor import runtime, status_bar
from cptoml import fetch

runtime.autoreload = False
status_bar.console = False
print("-" * 16 + "\nL", end="")

devm = fetch("usb_access", "LJINUX")
stash = ""
if devm:
    stash = "Cannot write to filesystem! usb_access has been enabled!\n"
print("J", end="")

lj_mount = getmount("/")
print("I", end="")

desired_label = "ljinux"
if lj_mount.label != desired_label:
    remount("/", False)
    lj_mount.label = desired_label
    remount("/", True)
print("N", end="")

try:
    import usb_hid

    if not fetch("usb_hid", "LJINUX"):
        usb_hid.disable()
        stash += "Disabled HID.\n"
except ImportError:
    pass
print("U", end="")

if not devm:
    try:
        disable_usb_drive()
    except RuntimeError:
        pass
print("X pre-boot core\n" + "-" * 16 + "\nOutput:\n" + stash)
