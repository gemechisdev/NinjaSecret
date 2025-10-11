import asyncio
import time
from datetime import datetime
from aiohttp import web, web_runner
import json
import psutil
import os

from NinjaSecret.logging import LOGGER

class HealthServer:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.start_time = time.time()
        
        # Setup routes
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ping', self.ping)
        self.app.router.add_get('/', self.root)
    
    async def health_check(self, request):
        """Health check endpoint for Render and other deployment platforms"""
        try:
            # Get system stats
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            uptime_seconds = int(time.time() - self.start_time)
            uptime_minutes = uptime_seconds // 60
            uptime_hours = uptime_minutes // 60
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "uptime": {
                    "seconds": uptime_seconds,
                    "formatted": f"{uptime_hours}h {uptime_minutes % 60}m {uptime_seconds % 60}s"
                },
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "used_mb": round(memory_info.used / 1024 / 1024, 2),
                        "available_mb": round(memory_info.available / 1024 / 1024, 2),
                        "percent": memory_info.percent
                    },
                    "disk": {
                        "used_gb": round(disk_info.used / 1024 / 1024 / 1024, 2),
                        "free_gb": round(disk_info.free / 1024 / 1024 / 1024, 2),
                        "percent": round((disk_info.used / disk_info.total) * 100, 2)
                    }
                },
                "service": "ScorpiTune Telegram Bot",
                "version": "1.0.0"
            }
            
            return web.json_response(health_data, status=200)
            
        except Exception as e:
            LOGGER(__name__).error(f"Health check error: {e}")
            error_data = {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "service": "ScorpiTune Telegram Bot"
            }
            return web.json_response(error_data, status=500)
    
    async def ping(self, request):
        """Simple ping endpoint"""
        try:
            ping_data = {
                "message": "pong",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "uptime_seconds": int(time.time() - self.start_time),
                "service": "ScorpiTune Telegram Bot"
            }
            return web.json_response(ping_data, status=200)
            
        except Exception as e:
            LOGGER(__name__).error(f"Ping endpoint error: {e}")
            return web.json_response({
                "message": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, status=500)
    
    async def root(self, request):
        """Root endpoint with basic info"""
        root_data = {
            "service": "ScorpiTune Telegram Bot",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "endpoints": {
                "health": "/health",
                "ping": "/ping"
            },
            "description": "Telegram music bot with health monitoring endpoints"
        }
        return web.json_response(root_data, status=200)
    
    async def start(self):
        """Start the web server"""
        try:
            self.runner = web_runner.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web_runner.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            LOGGER(__name__).info(f"Health server started on http://{self.host}:{self.port}")
            LOGGER(__name__).info(f"Health endpoint: http://{self.host}:{self.port}/health")
            LOGGER(__name__).info(f"Ping endpoint: http://{self.host}:{self.port}/ping")
            
        except Exception as e:
            LOGGER(__name__).error(f"Failed to start health server: {e}")
            raise
    
    async def stop(self):
        """Stop the web server"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            LOGGER(__name__).info("Health server stopped")
        except Exception as e:
            LOGGER(__name__).error(f"Error stopping health server: {e}")

# Global instance
health_server = None

async def start_health_server(host='0.0.0.0', port=None):
    """Start the health server"""
    global health_server
    
    # Get port from environment or use default
    if port is None:
        port = int(os.getenv('PORT', 8000))
    
    health_server = HealthServer(host, port)
    await health_server.start()
    return health_server

async def stop_health_server():
    """Stop the health server"""
    global health_server
    if health_server:
        await health_server.stop()
        health_server = None