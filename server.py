#!/usr/bin/env python3

import argparse
import logging
import uvicorn

from cf_bypasser.server.app import create_app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Cloudflare Bypasser Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--log-level", type=str, default="info", help="Log level")
    
    args = parser.parse_args()
    
    # Update logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info("Features enabled:")
    logger.info("  - Cookie caching system")
    logger.info("  - Request mirroring with x-hostname/x-proxy headers") 
    logger.info("  - Direct proxy configuration")
    logger.info("  - Firefox-only impersonation (no Chrome sec-ch-ua headers)")
    logger.info("  - 403 response cache invalidation and retry")
    logger.info("  - Backward compatible /cookies endpoint")
    logger.info("  - Catch-all mirroring (excludes: health, cookies, cache/*)")
    
    # Create the app
    app = create_app()
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()