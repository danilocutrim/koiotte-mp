FROM alpine:3.20
WORKDIR /app
COPY koiotte-proxy-mp /usr/local/bin/koiotte-proxy-mp
EXPOSE 8080 18000
ENTRYPOINT ["/usr/local/bin/koiotte-proxy-mp"]
