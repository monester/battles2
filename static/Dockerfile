FROM node

ADD . /src

WORKDIR /src

#RUN npm install && npm run-script build

FROM nginx
COPY --from=0 /src/build/ /var/www

RUN ls -laR /var/www
COPY default.conf /etc/nginx/conf.d/default.conf
