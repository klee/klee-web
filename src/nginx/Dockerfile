FROM nginx:1.17

RUN rm -f /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY sites-available_titb.conf /etc/nginx/sites-available/titb
RUN mkdir /etc/nginx/sites-enabled && \
    ln -s /etc/nginx/sites-available/titb /etc/nginx/sites-enabled/titb

CMD ["nginx", "-g", "daemon off;"]
