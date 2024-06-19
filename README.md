# auto-proxy

bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install -u root

systemctl edit xray

[Service]
Group=proxy

install config.json /usr/local/etc/xray
chmod o+wr /usr/local/etc/xray/config.json
systemctl restart xray

install custom-route /etc/NetworkManager/dispatcher.d/pre-up.d
install client.py tproxy.sh /usr/local/bin
install -m 644 tproxy.service /etc/systemd/system
systemctl enable tproxy

Setttings > Power > Screen Blank - Never
Setttings > Displays > Resolution - 1920 x 1080

curl -X POST http://localhost:5000/set_ip -H 'Content-Type: application/json' -d '{"ip": "54.193.188.38"}'
