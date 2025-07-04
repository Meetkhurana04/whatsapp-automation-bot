# WhatsApp Sender

A Dockerized Flask service that automates WhatsApp Web using Selenium to send text messages (and optionally media, with extra work).

## Features

* REST endpoint `POST /send` accepts JSON `{ "phone": "+<countrycode><number>", "message": "..." }`.
* Device-based session persistence – scan the QR code once, the cookie profile is stored under `chrome-data/` and reused.
* Logs important events with timestamps.
* Lightweight Python 3.11-slim base image with Chromium & chromedriver installed.
* Optional simple API-key security using environment variable `API_KEY`.

## Quick Start

1. **Build the image:**

   ```bash
   docker build -t whatsapp-sender ./whatsapp-sender
   ```

2. **Run the container:**

   ```bash
   docker run -it --rm \
     -p 5000:5000 \
     -v $PWD/chrome-data:/app/chrome-data \   # Persist login session
     whatsapp-sender
   ```

   The first time you run the container, a `qr.png` file will appear in the working directory. Open it and scan the QR code with the WhatsApp mobile app to log in.

3. **Send a message:**

   ```bash
   curl -X POST http://localhost:5000/send \
        -H 'Content-Type: application/json' \
        -d '{"phone": "+919876543210", "message": "Hello from Dockerised bot!"}'
   ```

## Environment Variables

* `HEADLESS` (default `true`) – run Chrome in headless mode. Set to `false` for debugging.
* `API_KEY` – if set, clients must supply header `X-API-KEY: <value>` on every request.

## Caveats

* WhatsApp Web selectors change periodically; this code may need updates.
* Media sending is not implemented out-of-the-box but can be added in `whatsapp_bot.py`.
* Running a full browser inside Docker consumes memory (~300 MB+) and may require `--shm-size` increase on some hosts.

## License

MIT
