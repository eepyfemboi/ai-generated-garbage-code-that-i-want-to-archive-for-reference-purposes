import aiohttp.web
import gzip
import zlib
import brotli
import zstandard
import lz4.frame

async def handle_request(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """
    Handles the incoming request, generates a response, and applies optimal compression.
    """
    response = await generate_response(request)
    optimal_encoding = determine_compression(request, response)
    
    if optimal_encoding:
        response = apply_compression(response, optimal_encoding)
        response.headers["Content-Encoding"] = optimal_encoding

    return response

async def generate_response(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """
    Generates a web response (dummy function for example purposes).
    """
    text = "This is an example response body" * 1000  # Simulated large response
    return aiohttp.web.Response(text=text, content_type="text/plain")

def determine_compression(request: aiohttp.web.Request, response: aiohttp.web.Response) -> str:
    """
    Determines the best compression method based on Accept-Encoding, MIME type, and size.
    """
    accept_encoding = request.headers.get("Accept-Encoding", "").lower()
    mime_type = response.content_type
    response_body = response.body or response.text.encode()  # Ensure bytes
    size = len(response_body)

    # Supported encodings and priorities based on efficiency
    encoding_methods = {
        "br": brotli.compress,
        "gzip": gzip.compress,
        "deflate": zlib.compress,
        "zstd": zstandard.ZstdCompressor().compress,
        "lz4": lz4.frame.compress,
    }

    # Order of preference: Brotli > Zstd > Gzip > Deflate > LZ4 (if supported)
    preferred_encodings = ["br", "zstd", "gzip", "deflate", "lz4"]

    # Ensure requested encodings are supported
    available_encodings = [enc for enc in preferred_encodings if enc in accept_encoding]

    if not available_encodings:
        return None  # No compression if client does not support any

    # Determine compression based on size and type
    if "text" in mime_type or "json" in mime_type or "xml" in mime_type:
        if size < 1024:  # Small responses may not benefit much
            return None
        elif size < 10 * 1024:  # Small-medium responses
            return "gzip" if "gzip" in available_encodings else available_encodings[0]
        else:  # Large responses
            return "br" if "br" in available_encodings else available_encodings[0]
    else:
        # For non-text responses (binary, images, etc.)
        if size > 50 * 1024 and "zstd" in available_encodings:
            return "zstd"
        elif size > 100 * 1024 and "lz4" in available_encodings:
            return "lz4"
    
    return None  # Default: No compression

def apply_compression(response: aiohttp.web.Response, encoding: str) -> aiohttp.web.Response:
    """
    Compresses the response body using the specified encoding method.
    """
    response_body = response.body or response.text.encode()  # Convert to bytes if needed

    compression_methods = {
        "br": brotli.compress,
        "gzip": gzip.compress,
        "deflate": lambda data: zlib.compress(data, level=9),
        "zstd": zstandard.ZstdCompressor().compress,
        "lz4": lz4.frame.compress,
    }

    if encoding in compression_methods:
        compressed_body = compression_methods[encoding](response_body)
        response.body = compressed_body
        response.headers["Content-Length"] = str(len(compressed_body))
        response.headers["Vary"] = "Accept-Encoding"

    return response

# Set up aiohttp web app
app = aiohttp.web.Application()
app.router.add_get("/", handle_request)

if __name__ == "__main__":
    aiohttp.web.run_app(app, port=8080)
