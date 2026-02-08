import zlib
import brotli

def decompress(data: bytes, compression: str) -> bytes:
    if compression == 'none':
        return data
    if compression == 'zlib':
        return zlib.decompress(data)
    elif compression == 'brotli':
        return brotli.decompress(data)
    else:
        raise ValueError(f"Unsupported compression type: {compression}")