# Configuration

## Program Flirc

You can choose any Flirc profile but mapping of the keys might require some experimentation. In some profiles both, Play and Pause keys will send "Play / Pause". And Stop key can send letter "X". Other profiles will send "Stop" for Stop.

## Connect Flirc to eISY/Polisy

###  eISY / PG3x

Once node server is installed, nothing else needs to be done. Just plug-in Flirc. Or if already plugged in, unplug and plug back in.

### Polisy / PG3

At this point Flirc cannot be connected automatically and requires the following procedure:

* SSH into your eISY/Polisy

* Execute

> curl https://raw.githubusercontent.com/firstone/eisy-ir-poly/main/flirc.conf -o flirc.conf

* Execute

> sudo mkdir -p /usr/local/etc/devd

* Execute

> sudo cp ./flirc.conf /usr/local/etc/devd

* Execute

> sudo service devd restart

## Set up node server for learned keys

Once you trigger key press with your remote, node server will create a node for that key. 

Key has the following states: Pressed, Held, Released and Idle.

Pressed and Released are temporary state. The key will then change to Idle after a timeout.

Timeout that switches key to Idle can be changed via "Idle Threshold" parameter.

Timeout that switches key between Pressed and Held can be changed via "Press Threshold". Depending on the remote it can be decreased to as low as 250 ms. Lower value might cause incorrect states.

