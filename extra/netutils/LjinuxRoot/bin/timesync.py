rename_process("timesync")
if "network" in ljinux.devices and ljinux.devices["network"][0].connected:
    if ljinux.devices["network"][0].timeset():
        ljinux.api.setvar("return", "0")
    else:
        dmtex("Could not sync time.")
        ljinux.api.setvar("return", "1")
