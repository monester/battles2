FROM node

ADD . /src

WORKDIR /src

RUN npm install && npm run-script build && npm install -g serve
