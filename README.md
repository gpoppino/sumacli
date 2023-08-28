# Summary
This script schedules the patching of SUMA client systems with action chains or a product migration to a
higher service pack level. An action chain for a client system includes the patching with the type of patches that are
requested by the user and then a reboot if it is suggested by a patch, everything at a specified date and time.

If the patching fails for a system, the reboot is not run by the action chain.

## Input

The input this program receives, is a file as first argument that is structured in the following way:

```txt
client-system-name,YYYY-mm-dd HH:MM:SS
group:name-of-group,YYYY-mm-dd HH:MM:SS
client-system-name2,YYYY-mm-dd HH:MM:SS,migration-target-label
group:name-of-group2,YYYY-mm-dd HH:MM:SS,migration-target-label
client-system-name3,now
group:name-of-group3,now
```

Where:

* YYYY = Year
* mm = Month
* dd = Day
* HH = Hour
* MM = Minutes
* SS = Seconds

or

* now = execution at the earliest time

For example:

```txt
instance-k3s-0,now
instance-k3s-1,2023-03-06 10:00:00
instance-k3s-2,2023-03-13 11:00:00
group:Build Hosts,2023-03-06 19:00:00
instance-sles15-sp3,2023-03-06 20:00:00,sle-product-sles15-sp4-pool-x86_64
group:sles15-sp4-systems,now,sle-product-sles15-sp5-pool-x86_64
```

This associates each system with a patching date and time when the patching will be scheduled. If the system has no
pending patches, it will be skipped and no action chain will be created for it. In case there is a third argument
with a product target label and the `migrate` option is specified, a product migration will be scheduled for the system.

### Patching Policy

The `patch` command has an option called `-p` and `--policy` to indicate a CSV file with the following structure:

```txt
BaseProductName,PatchAdvisoryType1 PatchAdvisoryType2 PatchAdvisoryType3
```

When specified it will patch each system that has _BaseProductName_ as their base product with the patch advisory types
(_security_, _bugfix_, _product_enhancement_ and _all_) that follow after the comma separatd by spaces.

There is an example of patching policies located at `conf/product_patching_policy.conf`. Note: this file does not have
the full list of available products. The user of the script will have to add the desired base products and their
patching policies as needed.

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

On the command line, you may run the following command to apply all the available patches to each system
in `systems.csv`:

`$ python3 main.py patch --all-patches systems.csv`

Or to patch the systems by the policies part of `conf/product_patching_policy.conf` and add a reboot to each
action chain:

`$ python3 main.py patch --policy conf/product_patching_policy.conf --reboot systems.csv`

Or to migrate the systems to a new Service Pack (SP) level:

`$ python3 main.py migrate systems.csv`

Or to request a package refresh for each system:

`$ python3 main.py utils -r systems.csv`

The _systems.csv_ file has to be structured as described in the _Input_ section.

To validate results, you may run:

`$ python3 main.py validate actions/action_ids_file`

## Help

You may add the `-h` or `--help` option after each command to list all their available options with a short description.
For example:

`$ python3 main.py -h`

Or

`$ python3 main.py patch --help`
