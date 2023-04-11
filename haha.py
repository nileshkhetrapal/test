import paramiko
from fabric import Connection

# AWS Ubuntu instance details
aws_hostname = "34.230.38.216"
aws_username = "ec2-user"
aws_key_path = "/home/champuser/Downloads/aws_key.pem"

# Xubuntu machine details
xubuntu_hostname = "xubuntu"
xubuntu_username = "champuser"
#Command to generate ssh keys in bash:
xubuntu_key_path = "/home/champuser/.ssh/id_rsa"

# Generate WireGuard keys
with paramiko.SSHClient() as ssh:
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=aws_hostname, username=aws_username, key_filename=aws_key_path)
    _, stdout, _ = ssh.exec_command("sudo -i wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey")
    aws_private_key = stdout.read().strip().decode("utf-8")
    _, stdout, _ = ssh.exec_command("cat /etc/wireguard/publickey")
    aws_public_key = stdout.read().strip().decode("utf-8")
    ssh.close()

with paramiko.SSHClient() as ssh:
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=xubuntu_hostname, username=xubuntu_username, key_filename=xubuntu_key_path)
    _, stdout, _ = ssh.exec_command("sudo -i wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey")
    xubuntu_private_key = stdout.read().strip().decode("utf-8")
    _, stdout, _ = ssh.exec_command("cat /etc/wireguard/publickey")
    xubuntu_public_key = stdout.read().strip().decode("utf-8")
    ssh.close()

# Create WireGuard configuration files
aws_wg_config = f"""[Interface]
Address = 10.0.101.1/24
PrivateKey = {aws_private_key}
ListenPort = 51900

[Peer]
PublicKey = {xubuntu_public_key}
AllowedIPs = 10.0.101.2/32
Endpoint = {xubuntu_hostname}:51900
PersistentKeepalive = 25
"""

xubuntu_wg_config = f"""[Interface]
Address = 10.0.101.2/24
PrivateKey = {xubuntu_private_key}
ListenPort = 51900

[Peer]
PublicKey = {aws_public_key}
AllowedIPs = 10.0.101.1/32
Endpoint = {aws_hostname}:51900
PersistentKeepalive = 25
"""

# Write WireGuard configuration files
with paramiko.SSHClient() as ssh:
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=aws_hostname, username=aws_username, key_filename=aws_key_path)
    _, stdout, _ = ssh.exec_command(f"echo '{aws_wg_config}' | sudo tee /etc/wireguard/wg0.conf")
    ssh.close()

with paramiko.SSHClient() as ssh:
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=xubuntu_hostname, username=xubuntu_username, key_filename=xubuntu_key_path)
    _, stdout, _ = ssh.exec_command(f"echo '{xubuntu_wg_config}'| sudo tee /etc/wireguard/wg0.conf")
ssh.close()
#Install and configure WireGuard
with Connection(host=aws_hostname, user=aws_username, connect_kwargs={"key_filename": aws_key_path}) as conn:
    conn.sudo("apt-get update")
    conn.sudo("apt-get install -y wireguard")
    conn.sudo("systemctl enable wg-quick@wg0")
    conn.sudo("systemctl start wg-quick@wg0")
    conn.run("sudo sysctl -w net.ipv4.ip_forward=1")
    conn.run("sudo sysctl -p")
    conn.sudo(f"sudo sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf")
    conn.sudo("systemctl enable apache2")
    conn.sudo("systemctl start apache2")
    conn.sudo(f"echo 'nile - SEC-440 Wireguard Lab' | sudo tee /var/www/html/index.html")
    conn.sudo("iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o <eth0 or ens160> -j MASQUERADE")
    conn.sudo("iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o <eth0 or ens160> -j MASQUERADE")
    conn.sudo("systemctl restart wg-quick@wg0")

with Connection(host=xubuntu_hostname, user=xubuntu_username, connect_kwargs={"key_filename": xubuntu_key_path}) as conn:
    conn.sudo("apt-get update")
    conn.sudo("apt-get install -y wireguard")
    conn.sudo("systemctl enable wg-quick@wg0")
    conn.sudo("systemctl start wg-quick@wg0")
    conn.run("sudo sysctl -w net.ipv4.ip_forward=1")
    conn.run("sudo sysctl -p")
    conn.sudo(f"echo 'nile - SEC-440 Wireguard Lab' | sudo tee /var/www/html/index.html")
    conn.sudo("iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o <eth0 or ens160> -j MASQUERADE")
    conn.sudo("iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o <eth0 or ens160> -j MASQUERADE")
    conn.sudo("systemctl restart wg-quick@wg0")
