"""One host identity policy for every Paramiko connection path."""

from paramiko import AutoAddPolicy, RejectPolicy, SSHClient, WarningPolicy

from .connection_config import ConnectionConfig


def configure_host_keys(client: SSHClient, config: ConnectionConfig) -> None:
    # Load trusted keys even when accepting unknown hosts, so changed keys fail.
    client.load_system_host_keys()
    if config.known_hosts_path is not None:
        client.load_host_keys(str(config.known_hosts_path.expanduser()))
    if config.accept_new_host_key:
        client.set_missing_host_key_policy(AutoAddPolicy())
    elif config.strict_host_key_checking:
        client.set_missing_host_key_policy(RejectPolicy())
    else:
        client.set_missing_host_key_policy(WarningPolicy())
