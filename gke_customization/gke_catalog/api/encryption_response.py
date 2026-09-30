import json
from cryptography.fernet import Fernet
import frappe
import json
import os
import time
import hmac
import hashlib
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecureJSON:


    def __init__(self):

        # store these in site_config.json ideally
        self.aes_key = b'\xe5\xf4\x91f\x91\x9b~\xa9D\x8a_\x8b\xe7\xb6\x1duk\xc9\n9\xfd\x9ew\x14\xfai\xca<\xe7[\xfc9'

        self.hmac_secret = "my-super-secret-key".encode()

        self.aes = AESGCM(self.aes_key)



    def encrypt(self, data):


        payload = {

            "timestamp": int(time.time()),

            "data": data

        }


        raw_json = json.dumps(
            payload,
            default=str
        ).encode()



        nonce = os.urandom(12)


        encrypted = self.aes.encrypt(
            nonce,
            raw_json,
            None
        )


        encrypted_payload = {

            "nonce": base64.b64encode(
                nonce
            ).decode(),

            "payload": base64.b64encode(
                encrypted
            ).decode()

        }


        # message = json.dumps(
        #     encrypted_payload,
        #     sort_keys=True
        # )
        
        message = (
            encrypted_payload["nonce"]
            +
            encrypted_payload["payload"]
            +
            str(payload["timestamp"])
        )


        signature = hmac.new(
            self.hmac_secret,
            message.encode(),
            hashlib.sha256
        ).hexdigest()



        return {

            "encrypted": encrypted_payload,

            "signature": signature

        }




    def decrypt(self, package):

        encrypted_part = package.get("encrypted")

        if not encrypted_part:
            frappe.throw("Encrypted data missing")


        nonce = base64.b64decode(
            encrypted_part["nonce"]
        )


        ciphertext = base64.b64decode(
            encrypted_part["payload"]
        )


        try:

            # First decrypt data
            decrypted = self.aes.decrypt(
                nonce,
                ciphertext,
                None
            )

            payload = json.loads(
                decrypted.decode()
            )


        except Exception:

            frappe.throw(
                "Invalid encrypted payload"
            )



        # get timestamp from decrypted data

        timestamp = payload.get(
            "timestamp"
        )


        if not timestamp:
            frappe.throw(
                "Timestamp missing"
            )



        # recreate signature message

        message = (
            encrypted_part["nonce"]
            +
            encrypted_part["payload"]
            +
            str(timestamp)
        )


        expected_signature = hmac.new(
            self.hmac_secret,
            message.encode(),
            hashlib.sha256
        ).hexdigest()



        # compare signature

        if not hmac.compare_digest(
            expected_signature,
            package.get("signature")
        ):

            frappe.throw(
                "Invalid Signature"
            )



        # replay attack protection

        current_time = int(
            time.time()
        )


        if current_time - int(timestamp) > 300:

            frappe.throw(
                "Expired Request"
            )



        return payload["data"]



@frappe.whitelist()
def encrypt_payload():

    data = frappe.local.form_dict.get("data")

    if isinstance(data, str):
        data = frappe.parse_json(data)


    secure = SecureJSON()


    encrypted = secure.encrypt(
        data
    )


    return encrypted



@frappe.whitelist()
def decrypt_payload():

    data = frappe.local.form_dict


    secure = SecureJSON()


    decrypted = secure.decrypt(
        data
    )


    return decrypted
# SECRET_KEY = b"qzD2jv3cK5x7hN9LmR4YwT8uP1sEaF6BgVcX0ZiJkQ8="
# cipher = Fernet(SECRET_KEY)

# def encrypt_response(data):
#     json_data = json.dumps(data,default=str)
#     encrypted = cipher.encrypt(json_data.encode("utf-8"))
#     return encrypted.decode("utf-8")


# SECRET_KEY = Fernet.generate_key() 
 
SECRET_KEY = b"qzD2jv3cK5x7hN9LmR4YwT8uP1sEaF6BgVcX0ZiJkQ8="
# s_key = Fernet.generate_key()
cipher = Fernet(SECRET_KEY)

def encrypt_response(data):
    json_data = json.dumps(data, default=str)
    encrypted = cipher.encrypt(json_data.encode("utf-8"))
    return encrypted.decode("utf-8")