"""
Main entry point for the autonomous agent system.
"""

import sys
import uvicorn
from app.core.engine import engine
from app.utils.logger import logger


def main():
    """Main entry point."""
    # Check if running in CLI mode with a query argument
    if len(sys.argv) > 1 and sys.argv[1] not in ("--api", "--cli"):
        # Run CLI mode with direct query
        import asyncio
        
        async def run_cli():
            try:
                await engine.initialize()
                logger.info("Dragonite engine initialized")
                
                user_input = " ".join(sys.argv[1:])
                logger.info(f"Processing request: {user_input}")
                response = await engine.execute(user_input)
                
                print("\n" + "=" * 80)
                print("RESPONSE:")
                print("=" * 80)
                print(response)
                print("=" * 80)
                
                await engine.shutdown()
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                await engine.shutdown()
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                await engine.shutdown()
                sys.exit(1)
        
        asyncio.run(run_cli())
        return
    
    # DEFAULT: Run Web UI (API server) for easy API key configuration
    from app.api import app
    print("\n" + "=" * 60)
    print("  Dragonite - AI Agent Framework")
    print("=" * 60)
    print("  Web UI: http://localhost:8000")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()