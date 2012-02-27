import os
import binascii
from ctypes import *
from ctypes.util import find_library

__doc__ = """
Example ROMEO decryption plugin for decoding hex encoded RSA binary strings
with a public key.
"""

def rsa(public_key_file, hex_string):
    """This method decrypts a RSA hex string using the provided public key.
       RSA data may be encoded using binascii.b2a_hex.

       @param public_key_file C{str} absolute location to the public key.
       @param hex_string C{str} hexidecimal representation of binary rsa data.

       @raises AssertionError (malloc, file)
       @raises ValueError (invalid input)
       @raises Exception (multiple issues)
       @return C{str} decrypted data
    """
    txt_string = binascii.a2b_hex(hex_string)
    pub = _PublicKey(public_key_file)
    return pub.decrypt(txt_string)


libc = CDLL( find_library("c") )
libcrypto = CDLL( find_library("crypto") )

# <stdio.h>
libc.fopen.argtypes = [c_char_p, c_char_p]
libc.fopen.restype = c_void_p
libc.fclose.argtypes = [c_void_p]
libc.fclose.restype = None

# <stdlib.h>
libc.malloc.argtypes = [c_int]
libc.malloc.restype = c_void_p
libc.free.argtypes = [c_void_p]
libc.free.restype = None

# <string.h>
libc.memcpy.argtypes = [c_void_p, c_void_p, c_int]
libc.memcpy.restype = c_void_p

# <openssl/PEM.h>
#RSA *PEM_read_RSAPrivateKey(FILE *fp, RSA **x, pem_password_cb *cb, void *u);
libcrypto.PEM_read_RSAPrivateKey.argtypes = [c_void_p] * 4
libcrypto.PEM_read_RSAPrivateKey.restype = c_void_p
#EVP_PKEY *PEM_read_PUBKEY(FILE *fp, EVP_PKEY **x, pem_password_cb *cb, void *u);
libcrypto.PEM_read_PUBKEY.argtypes = [c_void_p] * 4
libcrypto.PEM_read_PUBKEY.restype = c_void_p

# <openssl/evp.h>
libcrypto.EVP_PKEY_get1_RSA.argtypes = [c_void_p]
libcrypto.EVP_PKEY_get1_RSA.restype = c_void_p
libcrypto.EVP_PKEY_free.argtypes = [c_void_p]
libcrypto.EVP_PKEY_free.restype = c_void_p

#for evp memory management
libcrypto.RSA_up_ref.argstime = [c_void_p]
libcrypto.RSA_up_ref.restype = c_int

# <openssl/rsa.h>
PADDING = 1 #value of RSA_PKCS1_PADDING on my system

for p in ('private','public'):
    for c in ('encrypt','decrypt'):
        func = getattr(libcrypto, "RSA_%s_%s" % (p,c))
        func.argtypes = [c_int, c_char_p, c_void_p, c_void_p, c_int]
        func.restype = c_int

libcrypto.RSA_size.argtypes = [c_void_p]
libcrypto.RSA_size.restype = c_int


class _PublicKey(object):
    def __init__(self, path):
        self.path = path
        self.id = os.path.basename(path)
        fp = libc.fopen(path, "r")
        if not fp:
            raise AssertionError("Cannot open file %s" % path)
        evp = libcrypto.PEM_read_PUBKEY(fp, None, None, None)
        libc.fclose(fp)
        if libcrypto.ERR_peek_error() != 0 or not evp:
            libcrypto.ERR_clear_error()
            if evp:
                libcrypto.EVP_PKEY_free(evp)
            raise Exception("Failed to read RSA public key %s" % path)

        rsa_key = libcrypto.EVP_PKEY_get1_RSA(evp)
        if libcrypto.ERR_peek_error() != 0 or not rsa_key:
            libcrypto.ERR_clear_error()
            libcrypto.EVP_PKEY_free(evp)
            #if rsa_key:
            #  libcrypto.RSA_free(rsa_key)
            raise Exception("Failed to extract RSA key from the EVP_PKEY at %s" % path)

        #for proper memory management 
        libcrypto.RSA_up_ref(rsa_key)
        libcrypto.EVP_PKEY_free(evp)

        self.key = rsa_key

    def decrypt(self, text):
        """decrypt the rsa text field"""
        return _process(text, libcrypto.RSA_public_decrypt, self.key)

#The real magic happens here
def _process(source, func, key):
    dest = ""
    dest_buf_size = libcrypto.RSA_size(key)
    dest_buf = libc.malloc( dest_buf_size )
    if not dest_buf:
        raise AssertionError("Failed to malloc. Damn.")
    while source:
        read_len = min( len(source), dest_buf_size )
        i = func(read_len, source, dest_buf, key, PADDING)

        if i == -1 or libcrypto.ERR_peek_error():
            libcrypto.ERR_clear_error()
            libc.free(dest_buf)
            raise ValueError("Operation failed due to invalid input")

        dest += string_at(dest_buf, i)
        source = source[read_len:]
    libc.free(dest_buf)
    return dest

__all__ = ['rsa']
