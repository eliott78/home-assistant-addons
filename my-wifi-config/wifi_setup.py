import subprocess
import time
import os
import re
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# --- CONFIGURAZIONE ---
HOTSPOT_SSID = "ConfiguraPi"
HOTSPOT_PSK = "password123"  # Cambia questa password! Deve essere lunga almeno 8 caratteri.

WPA_SUPPLICANT_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"
HOSTAPD_CONF = "/etc/hostapd/hostapd.conf"
DNSMASQ_CONF = "/etc/dnsmasq.conf"
INTERFACCIA = "wlan0"

# --- FUNZIONI ---
def is_connected():
    """Verifica se il Pi è connesso a internet."""
    try:
        subprocess.check_output(["ping", "-c", "1", "8.8.8.8"], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False

def setup_access_point():
    """Configura e avvia il Raspberry Pi come Access Point."""
    print("Configurazione dell'Access Point...")
    
    # Crea il file di configurazione hostapd
    with open(HOSTAPD_CONF, "w") as f:
        f.write(f"""
interface={INTERFACCIA}
driver=nl80211
ssid={HOTSPOT_SSID}
hw_mode=g
channel=7
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={HOTSPOT_PSK}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
""")

    # Configura il file dnsmasq.conf
    with open(DNSMASQ_CONF, "w") as f:
        f.write(f"""
interface={INTERFACCIA}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
bind-interfaces
server=8.8.8.8
log-queries
listen-address=127.0.0.1,192.168.4.1
dhcp-option=option:router,192.168.4.1
""")
    
    # Configura l'indirizzo IP statico per l'interfaccia wlan0
    subprocess.run(["sudo", "ifconfig", INTERFACCIA, "192.168.4.1", "up"])
    subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])
    subprocess.run(["sudo", "systemctl", "start", "hostapd"])

def scan_wifi_networks():
    """Esegue la scansione delle reti Wi-Fi disponibili."""
    try:
        output = subprocess.check_output(["sudo", "iwlist", INTERFACCIA, "scan"], text=True)
        networks = re.findall(r'ESSID:"(.+)"', output)
        return sorted(list(set(networks)))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

def save_wifi_credentials(ssid, psk):
    """Salva le nuove credenziali Wi-Fi."""
    with open(WPA_SUPPLICANT_CONF, "a") as f:
        f.write(f'\n\nnetwork={{\n\tssid="{ssid}"\n\tpsk="{psk}"\n}}')
    print(f"Credenziali salvate per SSID: {ssid}")
    
# --- ROTTE WEB ---
@app.route("/")
def index():
    if is_connected():
        return "Connesso a Internet. L'Access Point non è attivo."
    else:
        networks = scan_wifi_networks()
        return render_template("setup.html", networks=networks)

@app.route("/save", methods=["POST"])
def save():
    ssid = request.form["ssid"]
    psk = request.form["psk"]
    save_wifi_credentials(ssid, psk)
    
    # Riavvia il sistema per connettersi alla nuova rete
    subprocess.run(["sudo", "reboot"])
    return "Credenziali salvate. Il Raspberry Pi si sta riavviando..."

# --- ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    if not is_connected():
        setup_access_point()
        app.run(host="0.0.0.0", port=80, debug=False)
    else:
        print("Il Pi è già connesso. Lo script è inattivo.")
