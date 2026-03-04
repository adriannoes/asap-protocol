import { get, set } from 'idb-keyval';

const KEY_PAIR_STORE = 'asap_agent_keypair';

export interface AgentKeys {
    publicKey: string; // Base64 or Hex encoded public key
    privateKey: CryptoKey; // Raw CryptoKey stored safely in IndexedDB
}

/** ECDSA P-256 keypair; private key stored in IndexedDB. */
export async function generateAndStoreAgentKeys(): Promise<AgentKeys | null> {
    try {
        const keyPair = await window.crypto.subtle.generateKey(
            {
                name: 'ECDSA',
                namedCurve: 'P-256',
            },
            true,
            ['sign', 'verify']
        );
        const exportedPubKey = await window.crypto.subtle.exportKey('spki', keyPair.publicKey);
        const pubKeyBase64 = arrayBufferToBase64(exportedPubKey);
        await set(KEY_PAIR_STORE, keyPair);

        return {
            publicKey: pubKeyBase64,
            privateKey: keyPair.privateKey,
        };
    } catch (error) {
        console.error('Failed to generate agent keys:', error);
        return null;
    }
}

export async function getStoredAgentKeys(): Promise<CryptoKeyPair | undefined> {
    return get<CryptoKeyPair>(KEY_PAIR_STORE);
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
    return window.btoa(String.fromCharCode(...new Uint8Array(buffer)));
}
