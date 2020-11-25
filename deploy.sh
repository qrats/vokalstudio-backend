#!/bin/bash

sudo su


cd /var/www/virtualstudio/backend/

echo "Install requirements..."
. /var/www/audit-engine/backend/env/bin/activate

pip install -r /var/www/audit-engine/backend/requirements.txt
chown -R www-data:www-data /var/www/audit-engine/

echo "Main service reload..."
service audit-engine stop
cp -f /var/www/audit-engine/backend/scripts/audit-engine.service /etc/systemd/system/
systemctl daemon-reload
service audit-engine restart

echo "Nginx reload..."
cp -f /var/www/audit-engine/backend/scripts/audit-engine.conf /etc/nginx/sites-available/
ln -s -f /etc/nginx/sites-available/audit-engine.conf /etc/nginx/sites-enabled/
service nginx restart

echo "Celery reload..."
cp -f /var/www/audit-engine/backend/scripts/celery-worker.conf /etc/supervisor/conf.d/
supervisorctl reload
