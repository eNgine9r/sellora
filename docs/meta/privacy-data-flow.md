# Meta Instagram privacy and data flow

Instagram access tokens are encrypted server-side and never returned to the browser. Webhook payloads are stored in a durable journal with workspace routing. Direct messages are visible only within the owning workspace. Logs must not include tokens, app secrets, webhook verify tokens, full signatures, or authorization headers.
