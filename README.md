# Summary
This script schedules the patching of SUMA systems with an action chains. An action chain for a system includes the patching with 'Security Advisory' type patches and then a reboot at a specified time and date.

If the patching fails for a system, the reboot is not run by the action chain.

## Input

The input this program receives, is a file as first argument that is structured in the following way:

```txt
client-system-name,YYYY-mm-dd HH:MM:SS
```

Where:

* YYYY = Year
* mm = Month
* dd = Day
* HH = Hour
* MM = Minutes
* SS = Seconds

For example:

```txt
instance-k3s-0,2021-11-06 10:00:00
instance-k3s-1,2021-11-06 10:00:00
instance-k3s-2,2021-11-13 11:00:00
```

This associates each system with a patching date and time when the patching will be scheduled. If the system has no pending patches, it will be skipped
and no action chain will be created for it.

## Configuration

The script needs a separate configuration file named `config.ini` with the following format:

```ini
[server]
api_url = https://your-suma-server-name/rpc/api

[credentials]
username = your-username
password = your-password
```

Options:
* `api_url`: contains the SUMA server FQDN and path to the API (which is `/rpc/api`) using the HTTPS protocol.
* `username`: contains the username with permissions to perform patching on the chosen client servers.
* `password`: contains the password of the username.

## How to run the script

On the command line, run:

`$ python3 susePatching.py systems.csv`

The _systems.csv_ file has to be structured as described in the _Input_ section.


