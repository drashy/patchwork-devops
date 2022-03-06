FROM golang:alpine3.15 as builder
WORKDIR /app
COPY main.go go.mod /app/
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o webapp

FROM scratch
COPY --from=builder /app/webapp .
ENTRYPOINT ["./webapp"]