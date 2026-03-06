import { createHash } from 'crypto';
import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';
import Credentials from 'next-auth/providers/credentials';
import { EncryptJWT, jwtDecrypt } from 'jose';

// JWT secret; fail if unset or too short (CWE-326: weak key derivation).
const authSecret = process.env.AUTH_SECRET;
if (!authSecret || authSecret.length < 32) {
    throw new Error(
        'AUTH_SECRET must be at least 32 characters. Generate one with: npx auth secret'
    );
}
const secretKey = createHash('sha256').update(authSecret).digest();

export async function encryptToken(token: string) {
    return await new EncryptJWT({ token })
        .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
        .encrypt(secretKey);
}

export async function decryptToken(jwe: string) {
    const { payload } = await jwtDecrypt(jwe, secretKey);
    return payload.token as string;
}

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        GitHub({
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET,
            authorization: { params: { scope: 'read:user' } },
        }),
        // Test-login provider only when ENABLE_FIXTURE_ROUTES=true (E2E).
        ...(process.env.ENABLE_FIXTURE_ROUTES === 'true' && process.env.NODE_ENV !== 'production'
            ? [
                Credentials({
                    id: 'test-login',
                    name: 'Test Login',
                    credentials: {
                        username: { label: 'Username', type: 'text' },
                    },
                    async authorize(credentials) {
                        if (credentials?.username) {
                            return {
                                id: 'test-123',
                                name: 'E2E Test User',
                                email: 'test@example.com',

                                username: String(credentials.username),
                            };
                        }
                        return null;
                    },
                }),
            ]
            : []),
    ],
    callbacks: {
        jwt({ token, user, profile, account }) {
            if (user) {
                token.id = user.id;
                if (user.username) {
                    token.username = user.username;
                }
                if (profile?.login) {
                    token.username = profile.login;
                }
            }
            if (account?.access_token) token.accessToken = account.access_token;
            return token;
        },
        async session({ session, token }) {
            if (typeof token.id === 'string' && session.user) {
                session.user.id = token.id;
            }
            if (typeof token.username === "string" && session.user) {
                session.user.username = token.username;
            }
            // Expose access token server-side only (idiomatic next-auth; no cookie reconstruction).
            if (typeof token.accessToken === 'string') {
                session.accessToken = token.accessToken;
            }
            return session;
        },
    },
    pages: { signIn: '/' },
});
