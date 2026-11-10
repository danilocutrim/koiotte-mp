FROM golang:1.25-alpine AS build
WORKDIR /src
COPY management-plane/go.mod management-plane/go.sum ./
RUN go mod download
COPY management-plane/ ./
RUN CGO_ENABLED=0 go build -o /out/koiotte-proxy-mp ./cmd/server

FROM alpine:3.20
COPY --from=build /out/koiotte-proxy-mp /usr/local/bin/koiotte-proxy-mp
EXPOSE 8080 18000
ENTRYPOINT ["/usr/local/bin/koiotte-proxy-mp"]
