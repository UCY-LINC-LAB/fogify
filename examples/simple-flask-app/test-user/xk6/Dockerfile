FROM xk6-output-influxdb:latest as builder
COPY . .

FROM alpine:3.18 
COPY . .
RUN apk update && apk add bash
RUN adduser -D -u 12345 -g 12345 k6
COPY --from=builder /usr/bin/k6 /usr/bin/k6

USER k6
WORKDIR /home/k6


ENTRYPOINT ["/bin/bash"]