import os
import hashlib
import random
import struct
import argparse


def derive_seed(key, iv):
    """Derive a seed for the random number generator from Key and IV."""
    h = hashlib.sha256()
    h.update(key.encode('utf-8'))
    h.update(iv)
    return int.from_bytes(h.digest(), 'big')

def process_file(input_path, output_path, key, is_encrypt=True):
    """
    Encrypt or Decrypt a file using a stream cipher based on Python's random (Mersenne Twister).
    Uses large integer XOR for performance.
    """
    chunk_size = 1024 * 1024 # 1MB chunks
    
    with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
        if is_encrypt:
            # Generate IV
            iv = os.urandom(16)
            fout.write(iv)
        else:
            # Read IV
            iv = fin.read(16)
            if len(iv) < 16:
                raise ValueError("File too short or corrupted.")
        
        # Initialize PRNG
        seed = derive_seed(key, iv)
        rng = random.Random(seed)
        
        while True:
            chunk = fin.read(chunk_size)
            if not chunk:
                break
            
            # Generate mask (compatible with Python < 3.9, same as encrypt)
            mask = rng.getrandbits(len(chunk) * 8).to_bytes(len(chunk), 'little')
            
            # Fast XOR using integers
            chunk_int = int.from_bytes(chunk, 'little')
            mask_int = int.from_bytes(mask, 'little')
            encrypted_int = chunk_int ^ mask_int
            
            # Convert back to bytes
            encrypted_chunk = encrypted_int.to_bytes(len(chunk), 'little')
            fout.write(encrypted_chunk)

