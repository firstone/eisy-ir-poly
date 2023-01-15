# Configuration

## Program Flirc

You can choose any Flirc profile but mapping of the keys might require some experimentation. In some profiles both, Play and Pause keys will send "Play / Pause". And Stop key can send letter "X". Other profiles will send "Stop" for Stop.

## Connect Flirc to eISY/Polisy

At this point Flirc cannot be connected automatically and requires the following procedure:

* SSH into your eISY/Polisy

* Execute

> curl https://raw.githubusercontent.com/firstone/eisy-ir-poly/main/reset_flirc.sh -o reset_flirc.sh

* Execute

> chmod +x reset_flirc.sh

* Execute

> sudo ./reset_flirc.sh

Last commands need to be repeated every time Flirc is unpluged or eISY/Polisy is rebooted.

## Set up node server for learned keys

Once you trigger key press with your remote, node server will create a node for that key. 

Key has the following states: Pressed, Held, Released and Idle.

Pressed and Released are temporary state. The key will then change to Idle after a timeout.

Timeout that switched key to Idle can be changed via "Idle Threshold" parameter. But default it's 5000 ms (5 seconds).

