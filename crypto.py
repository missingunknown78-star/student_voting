# crypto.py
from phe import paillier
import pickle
import base64
import os
import json

class CryptoManager:
    def __init__(self):
        self.public_key = None
        self.private_key = None
        self.load_or_generate_keys()
    
    def load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        key_dir = "keys"
        os.makedirs(key_dir, exist_ok=True)
        
        public_key_path = os.path.join(key_dir, "public_key.pem")
        private_key_path = os.path.join(key_dir, "private_key.pem")
        
        if os.path.exists(public_key_path) and os.path.exists(private_key_path):
            # Load existing keys
            with open(public_key_path, 'rb') as f:
                self.public_key = pickle.load(f)
            with open(private_key_path, 'rb') as f:
                self.private_key = pickle.load(f)
        else:
            # Generate new keys
            self.public_key, self.private_key = paillier.generate_paillier_keypair()
            
            # Save keys
            with open(public_key_path, 'wb') as f:
                pickle.dump(self.public_key, f)
            with open(private_key_path, 'wb') as f:
                pickle.dump(self.private_key, f)
        
        print("Keys loaded/generated successfully")
    
    def encrypt_vote_vector(self, vote_vector):
        """Encrypt a vote vector (list of 0s and 1s)"""
        return [self.public_key.encrypt(x) for x in vote_vector]
    
    def decrypt_vote_vector(self, encrypted_vector):
        """Decrypt an encrypted vote vector"""
        return [self.private_key.decrypt(x) for x in encrypted_vector]
    
    def serialize_encrypted_vector(self, encrypted_vector):
        """Serialize encrypted vector for storage"""
        return json.dumps([
            {"ciphertext": str(e.ciphertext()), "exponent": e.exponent} 
            for e in encrypted_vector
        ])
    
    def deserialize_encrypted_vector(self, serialized_data):
        """Deserialize stored encrypted vector"""
        data = json.loads(serialized_data)
        return [
            paillier.EncryptedNumber(
                self.public_key,
                int(item["ciphertext"]),
                int(item["exponent"])
            )
            for item in data
        ]

# Global instance
crypto_manager = CryptoManager()
public_key = crypto_manager.public_key
private_key = crypto_manager.private_key