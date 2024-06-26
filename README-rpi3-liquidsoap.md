# How to Install OP25 and LiquidSoap on a Raspberry Pi3 Raspbian Stretch

These high level instructions will lead you through installing op25 and liquidsoap on any Debian based Linux system.  It is geared towards the Raspberry Pi3B which is inexpensive but yet just powerful enough to receive, decode and stream P25 trunked radio system utilizing either Phase 1 or Phase 2 audio codecs. (Pi Zero is not powerful enough)

It is possible to configure and use op25 with other streaming software (such as Darkice) but this setup has the advantage of completely avoiding use of the ALSA sound subsystem with has proven itself to be someway quirky and prone to problems particularly when using the loopback driver (aloop).

There are many refinements which should be made to these instructions, particularly how to configure liquidsoap and op25 to properly auto-start at boot time.

## 1. Install op25

```
sudo apt-get install git
cd ~
git clone https://github.com/boatbod/op25
cd op25
./install.sh 
```

## 2. Install liquidsoap

```
sudo apt-get install liquidsoap liquidsoap-plugin-all
```

## 3. Install PulseAudio (optional, but preferred over alsa for local audio, selected with "-O pulse")

```
sudo apt-get install pulseaudio pulseaudio-utils
```

## 4. Install Icecast (optional)

```
sudo apt-get install icecast2
Follow prompts and set up appropriate passwords
Edit /etc/icecast/icecast.xml and define your mount point(s):
sudo vi /etc/icecast2/icecast.xml
```
```
    <!-- You may have multiple <listener> elements -->
    <listen-socket>
        <port>8000</port>
        <shoutcast-mount>/op25</shoutcast-mount>
    </listen-socket>
```

## 5. Configure op25

Set up `rx.py` command line options, `trunk.tsv`, `meta.json` and other files necessary to make a working instance of op25. Edit `op25.liq` to configure local sound options and/or streaming to icecast server.

## 6. Run op25 and liquidsoap

Terminal #1:
```
cd ~/op25/op25/gr-op25_repeater/apps
./rx.py --nocrypt --args "rtl=0" --gains 'lna:36' -S 57600 -q 0 -d 0 -v 1 -2 -T trunk.tsv -V -w -M meta.json 2> stderr.2
```

(In particular note the new `-w` parameter, that allows liquid to connect)

Terminal #2:
```
cd ~/op25/op25/gr-op25_repeater/apps
./op25.liq
```

Terminal #3: (optional log window)
```
cd ~/op25/op25/gr-op25_repeater/apps
tail -f stderr.2
```

## 7. Making liquidsoap and op25 start automatically at boot

Automatically starting liquidsoap and op25 at boot time is best handled using the systemd services manager `systemctl`.  Two service scripts are required, and although examples are provided, these should best be edited/customized to match your exact environment.  As written they assume `/home/pi` is the home directory which may or may not be the case...

You will also need to edit `op25.sh` (started by `op25-rx.service`) to have the command line parameters that you normally use to start `rx.py`.

Another factor to consider is that op25 should only be auto-started at boot time when it has been configured for the http terminal type.  Auto-starting the default curses terminal is not going to be successful. An example of this is to add `-l http:127.0.0.1:12345`.

First copy the two service files into /etc/systemd/system:
```
sudo cp ~/op25/op25/gr-op25_repeater/apps/op25-liq.service /etc/systemd/system
sudo cp ~/op25/op25/gr-op25_repeater/apps/op25-rx.service /etc/systemd/system
```

Next enable and then start the two services:
```
sudo systemctl enable op25-liq op25-rx
sudo systemctl start op25-liq op25-rx
```

You can subsequently stop the services by issuing the following command:
```
sudo systemctl stop op25-rx
```
or
```
sudo systemctl stop op25-rx op25-liq
```

## 8. Icecast2 low-latency setups (optional)

Buffering may cause the stream to lag behind the metadata.  To decrease latency for low-latency environments, such as highspeed networks, edit `/etc/icecast2/icecast.xml` to disable Icecast2 `burst-on-connect` and reduce `burst-size`.

```
sudo vi /etc/icecast2/icecast.xml
```

```
<!-- If enabled, this will provide a burst of data when a client
	 first connects, thereby significantly reducing the startup
	 time for listeners that do substantial buffering. However,
	 it also significantly increases latency between the source
	 client and listening client.  For low-latency setups, you
	 might want to disable this. -->
<burst-on-connect>0</burst-on-connect>
<!-- same as burst-on-connect, but this allows for being more
	 specific on how much to burst. Most people won't need to
	 change from the default 64k. Applies to all mountpoints  -->
<burst-size>0</burst-size>
```
