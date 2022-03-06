package main

import (
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"time"
)

var serverStartTime uint

func main() {

	serverRouter := http.NewServeMux()
	server := &http.Server{
		Addr:         ":8080",
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		Handler:      serverRouter,
	}

	fmt.Println("Starting the assessment webserver...")
	serverStartTime = uint(time.Now().Unix())
	serverRouter.HandleFunc("/", Uptime)
	log.Fatal(server.ListenAndServe())
}

func Uptime(response http.ResponseWriter, request *http.Request) {
	rand.Seed(time.Now().UnixNano())

	diceRoll := rand.Float32()
	if diceRoll < 0.9 {
		io.WriteString(response, fmt.Sprintf("Uptime: %d", uint(time.Now().Unix())-serverStartTime))
	} else {
		response.WriteHeader(500)
		io.WriteString(response, "We're down!")
	}

}
