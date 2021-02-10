server {
    listen 80;
    server_name api.vokalstudio.com www.api.vokalstudio.com;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/tmp/vokalstudio.sock;
    }

    access_log /var/www/vokalstudio/logs/nginx/access.log;
    error_log /var/www/vokalstudio/logs/nginx/error.log;
}