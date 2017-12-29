# building static files
FROM node

RUN mkdir /app
COPY package.json /app
WORKDIR /app
RUN npm install

COPY src /app/src
COPY public /app/public

RUN ls -la /app
RUN npm run-script build

# building frontend container
FROM nginx
COPY --from=0 /app/build/ /var/www

RUN ls -laR /var/www
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
