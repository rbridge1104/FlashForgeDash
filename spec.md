# Spec: Flashforge Adventurer 3 Monitor (MVP)

## Functional Requirements
- **Telemetry:** Must poll `~M105` (Temperatures) and `~M119` (Status) over TCP/8899 every 5 seconds.
- **Visuals:** A dashboard showing Nozzle/Bed temps and the MJPEG stream from `http://[IP]:8080/?action=stream`.
- **Orca Integration:** Must parse the selected G-code for `; estimated printing time` to display a "Time Remaining" countdown.
- **Controls:** Functional buttons for Emergency Stop (`~M112`) and LED Toggle (`~M146`).
- **Notifications:** Send a POST request to an n8n webhook (configurable) when status changes to 'complete'.

## Technical Constraints
- **Stack:** Python/FastAPI backend with a Tailwind CSS frontend.
- **Architecture:** Must be modular to allow for future Dockerization on Proxmox.
- **Error Handling:** Must self-correct TCP connection drops without crashing the loop.
