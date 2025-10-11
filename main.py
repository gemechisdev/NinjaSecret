import os
import subprocess
import sys
import time
import threading
import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import uvicorn

from config import PORT

app = FastAPI()

bot_process = None
bot_start_time = None
last_health_status = None  # Track health status to avoid excessive logging

def log_message(message):
    """Timestamped logs for better debugging."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] main: {message}")

def run_bot():
    global bot_process, bot_start_time
    log_message("=== ENTERED run_bot() ===")
    while True:
        try:
            log_message("Preparing to spawn NinjaSecret subprocess...")
            cmd = [sys.executable, "-m", "NinjaSecret"]
            log_message(f"Command: {' '.join(cmd)}")

            # Spawn without capturing output to avoid blocking
            log_message("Calling Popen...")
            bot_process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            bot_start_time = time.time()
            log_message(f"Subprocess spawned successfully (PID: {bot_process.pid})")

            # Wait for exit with periodic log (throttled to avoid spam)
            last_alive_log = time.time()
            while bot_process.poll() is None:
                time.sleep(1)
                # Log every 60s for long runs
                current_time = time.time()
                if current_time - last_alive_log >= 60:
                    uptime = int(current_time - bot_start_time)
                    log_message(f"Bot alive (uptime: {uptime}s)")
                    last_alive_log = current_time

            return_code = bot_process.returncode
            uptime = int(time.time() - bot_start_time)
            log_message(f"NinjaSecret exited after {uptime}s with code {return_code}, restarting in 5s...")
            time.sleep(5)

        except Exception as e:  # Catch *everything* to prevent thread crash
            log_message(f"ERROR in run_bot: {type(e).__name__}: {e}")
            log_message("Restarting loop in 5s...")
            if bot_process:
                try:
                    bot_process.terminate()
                    bot_process.wait(timeout=3)
                    log_message("Cleanup: Process terminated gracefully")
                except subprocess.TimeoutExpired:
                    bot_process.kill()
                    bot_process.wait()
                    log_message("Cleanup: Force killed")
                except Exception as cleanup_e:
                    log_message(f"Cleanup error: {cleanup_e}")
            time.sleep(5)

@app.get("/")
async def root():
    return {"message": "NinjaSecret Bot is running"}

@app.get("/health")
async def health():
    global last_health_status
    if bot_process and bot_process.poll() is None and bot_start_time:
        uptime = int(time.time() - bot_start_time)
        # Only log on status change to avoid spam from frequent health checks
        if last_health_status != "healthy":
            log_message(f"Health probe: healthy (uptime: {uptime}s)")
            last_health_status = "healthy"
        return {"status": "healthy", "uptime_seconds": uptime}
    else:
        # Only log on status change
        if last_health_status != "unhealthy":
            log_message("Health probe: unhealthy")
            last_health_status = "unhealthy"
        raise HTTPException(status_code=503, detail="unhealthy")

@app.head("/ping")
async def ping_head():
    return Response(status_code=200)

@app.get("/ping")
async def ping_get():
    return {"pong": "ok"}

if __name__ == "__main__":
    log_message("=== MAIN SCRIPT STARTING ===")
    log_message("Creating bot thread...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    log_message("Thread created.")
    log_message("Calling bot_thread.start()...")
    bot_thread.start()
    log_message("bot_thread.start() RETURNED IMMEDIATELY - thread running in background")
    log_message("About to start uvicorn...")

    log_message(f"Starting uvicorn on 0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=int(PORT))
