#!/bin/bash

sudo su


cd /var/www/virtualstudio/backend/

echo "Install requirements..."
. /var/www/virtualstudio/backend/env/bin/activate

pip install -r /var/www/virtualstudio/backend/requirements.txt
chown -R www-data:www-data /var/www/virtualstudio/

echo "Main service reload..."
service virtualstudio stop
cp -f /var/www/virtualstudio/backend/scripts/virtualstudio.service /etc/systemd/system/
systemctl daemon-reload
service virtualstudio restart

echo "Nginx reload..."
cp -f /var/www/virtualstudio/backend/scripts/virtualstudio.host /etc/nginx/sites-available/
ln -s -f /etc/nginx/sites-available/virtualstudio.host /etc/nginx/sites-enabled/
service nginx restart

echo "Celery reload..."
cp -f /var/www/virtualstudio/backend/scripts/celery-worker.conf /etc/supervisor/conf.d/
supervisorctl reload
