#!/bin/bash

sudo su


cd /var/www/vokalstudio/backend/

echo "Install requirements..."
. /var/www/vokalstudio/backend/env/bin/activate

pip install -r /var/www/vokalstudio/backend/requirements.txt
chown -R www-data:www-data /var/www/vokalstudio/

echo "Main service reload..."
service vokalstudio stop
cp -f /var/www/vokalstudio/backend/scripts/vokalstudio.service /etc/systemd/system/
systemctl daemon-reload
service vokalstudio restart

echo "Nginx reload..."
# cp -f /var/www/vokalstudio/backend/scripts/api.vokalstudio.host /etc/nginx/sites-available/
# ln -s -f /etc/nginx/sites-available/api.vokalstudio.host /etc/nginx/sites-enabled/
service nginx restart

echo "Celery reload..."
cp -f /var/www/vokalstudio/backend/scripts/celery-worker.conf /etc/supervisor/conf.d/
supervisorctl reload
