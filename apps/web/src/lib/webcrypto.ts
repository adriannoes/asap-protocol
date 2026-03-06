import { set } from 'idb-keyval';

const KEY_PAIR_STORE = 'asap_agent_keypair';

export interface AgentKeys {
    publicKey: string; // Base64 or Hex encoded public key
    privateKey: CryptoKey; // Raw CryptoKey stored safely in IndexedDB
}

/** Ed25519 keypair; private key stored in IndexedDB. */
export async function generateAndStoreAgentKeys(): Promise<AgentKeys | null> {
    try {
        const keyPair = await window.crypto.subtle.generateKey(
            { name: 'Ed25519' },
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

function arrayBufferToBase64(buffer: ArrayBuffer): string {
    return window.btoa(String.fromCharCode(...new Uint8Array(buffer)));
}
