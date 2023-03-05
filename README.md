# Summary
This script schedules the patching of SUMA client systems with action chains or a product migration to a
higher service pack level. An action chain for a client system includes the patching with only security patches by
default and then a reboot, everything at a specified date and time.

If the patching fails for a system, the reboot is not run by the action chain.

## Input

The input this program receives, is a file as first argument that is structured in the following way:

```txt
client-system-name,YYYY-mm-dd HH:MM:SS
group:name-of-group,YYYY-mm-dd HH:MM:SS
client-system-name2,YYYY-mm-dd HH:MM:SS,migration-target-label
group:name-of-group2,YYYY-mm-dd HH:MM:SS,migration-target-label
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
group:Build Hosts,2023-03-03 19:00:00
instance-sles15-sp3,2023-03-06 20:00:00,sle-product-sles15-sp4-pool-x86_64
group:sles15-sp4-systems,2023-03-06 21:00:00,sle-product-sles15-sp5-pool-x86_64
```

This associates each system with a patching date and time when the patching will be scheduled. If the system has no
pending patches, it will be skipped and no action chain will be created for it. In case there is a third argument
with a product target label, a product migration will be scheduled for the system.

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
* `username`: contains a SUMA username with permissions to perform patching on the chosen client servers.
* `password`: contains the password of the SUMA username.

## How to run the script

On the command line, run:

`$ python3 main.py systems.csv`

The _systems.csv_ file has to be structured as described in the _Input_ section.


